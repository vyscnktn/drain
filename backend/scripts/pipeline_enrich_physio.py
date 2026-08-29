#!/usr/bin/env python3
"""
2-Stage Physiotherapy Vocabulary Extraction & Enrichment Pipeline
Extracts lemmas from physiotherapy textbooks, filters out A1/A2/B1 core words,
applies an LLM Relevance Gate to remove publisher/general junk,
and enriches verified terms as B2/C1 domain vocabulary with caching & checkpointing.
"""

import os
import sys
import csv
import json
import time
import re
import threading
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter
from typing import List, Dict, Any, Set
from dotenv import load_dotenv
from openai import OpenAI
import pypdf
import spacy

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

NIM_API_KEY = os.getenv("NIM_API_KEY")
if not NIM_API_KEY:
    logger.error("NIM_API_KEY is not set.")
    sys.exit(1)

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=NIM_API_KEY,
    max_retries=0,
    timeout=60.0
)

MODEL_PRIMARY = "meta/llama-3.2-11b-vision-instruct"
MODEL_FALLBACK = "meta/llama-3.2-90b-vision-instruct"

DOCS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../documents"))
PHYSIO_DIR = os.path.join(DOCS_DIR, "physiotherapie")
CORE_DIR = os.path.join(DOCS_DIR, "wortliste")
OUTPUT_CSV = os.path.join(PHYSIO_DIR, "physio_enriched.csv")
VERIFIED_CACHE = os.path.join(PHYSIO_DIR, "physio_verified_terms.json")

file_lock = threading.Lock()

def load_core_lemmas() -> Set[str]:
    core_lemmas = set()
    for lvl in ["A1", "A2", "B1"]:
        path = os.path.join(CORE_DIR, f"{lvl}.csv")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    lem = row.get("Lemma", "").strip().lower()
                    if lem:
                        core_lemmas.add(lem)
    logger.info(f"Loaded {len(core_lemmas)} core A1/A2/B1 lemmas to exclude from domain list.")
    return core_lemmas

def extract_text_from_pdfs() -> str:
    combined_text = []
    pdf_files = [f for f in os.listdir(PHYSIO_DIR) if f.endswith(".pdf")]
    for pdf_name in pdf_files:
        pdf_path = os.path.join(PHYSIO_DIR, pdf_name)
        logger.info(f"Extracting text from PDF: {pdf_name}")
        try:
            reader = pypdf.PdfReader(pdf_path)
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    combined_text.append(text)
        except Exception as e:
            logger.warning(f"Error reading {pdf_name}: {e}")
    return "\n".join(combined_text)

def extract_candidate_lemmas(text: str, core_lemmas: Set[str]) -> List[Dict[str, Any]]:
    logger.info("Loading German NLP model (spaCy)...")
    try:
        nlp = spacy.load("de_core_news_sm")
    except Exception:
        logger.info("Downloading de_core_news_sm...")
        spacy.cli.download("de_core_news_sm")
        nlp = spacy.load("de_core_news_sm")

    text = re.sub(r"[^\w\säöüÄÖÜß-]", " ", text)
    chunk_size = 100000
    lemma_counts = Counter()
    lemma_pos = {}

    for i in range(0, len(text), chunk_size):
        chunk = text[i:i + chunk_size]
        doc = nlp(chunk)
        for token in doc:
            if not token.is_stop and len(token.lemma_) >= 3 and token.lemma_.isalpha():
                lem = token.lemma_.strip()
                lem_lower = lem.lower()
                if lem_lower not in core_lemmas:
                    lemma_counts[lem] += 1
                    if lem not in lemma_pos:
                        lemma_pos[lem] = token.pos_

    candidates = []
    for lem, count in lemma_counts.most_common(1200):
        if count >= 2 and len(lem) >= 4:
            candidates.append({
                "lemma": lem,
                "count": count,
                "pos": lemma_pos.get(lem, "NOUN")
            })

    logger.info(f"Extracted {len(candidates)} non-core candidate lemmas for Physiotherapy.")
    return candidates

def stage1_relevance_gate(candidates: List[Dict[str, Any]], batch_size: int = 30) -> List[str]:
    if os.path.exists(VERIFIED_CACHE):
        with open(VERIFIED_CACHE, "r", encoding="utf-8") as f:
            cached = json.load(f)
            if cached and isinstance(cached, list):
                logger.info(f"⚡ Loaded {len(cached)} verified terms from cache: {VERIFIED_CACHE}")
                return cached

    logger.info(f"Starting Stage 1: Relevance Gate on {len(candidates)} candidates...")
    batches = [candidates[i:i + batch_size] for i in range(0, len(candidates), batch_size)]
    verified_terms = []
    lock = threading.Lock()

    def _process_batch(b_idx, batch):
        lemmas_str = ", ".join([c["lemma"] for c in batch])
        prompt = f"""Du bist ein Experte für medizinische und physiotherapeutische Fachsprache in Deutschland.
Prüfe für die folgenden deutschen Begriffe, ob es sich um relevante Fachbegriffe oder typische berufliche Kontextbegriffe für das Berufsfeld PHYSIOTHERAPIE (Rehabilitation, Bewegungstherapie, Muskeln/Gelenke, Befund, Krankengymnastik) handelt.

Ausschließen (is_physio_term: false):
- Verlags-/Buchangaben (z.B. GmbH, Verlag, Auflage, Kapitel, Seite, ISBN, Druck, Abb)
- Allgemeine Alltagswörter ohne Bezug zur Therapie
- Abkürzungen oder fehlerhafte Wörter

Begriffe:
{lemmas_str}

Antworte AUSSCHLIESSLICH im validen JSON-Format:
{{
  "results": [
    {{"lemma": "Mobilisation", "is_physio_term": true}},
    {{"lemma": "GmbH", "is_physio_term": false}}
  ]
}}"""

        for model_name in [MODEL_PRIMARY, MODEL_FALLBACK]:
            try:
                resp = client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=2000,
                    timeout=50.0
                )
                raw = resp.choices[0].message.content.strip()
                if "{" in raw and "}" in raw:
                    raw_json = raw[raw.find("{"):raw.rfind("}")+1]
                    data = json.loads(raw_json)
                    batch_terms = []
                    for item in data.get("results", []):
                        if item.get("is_physio_term") is True:
                            batch_terms.append(item.get("lemma"))
                    with lock:
                        verified_terms.extend(batch_terms)
                    return len(batch_terms)
            except Exception as e:
                logger.warning(f"Relevance gate batch {b_idx} with {model_name} failed: {e}")
        return 0

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(_process_batch, idx + 1, b) for idx, b in enumerate(batches)]
        for f in as_completed(futures):
            f.result()

    unique_verified = list(dict.fromkeys(filter(None, verified_terms)))
    with open(VERIFIED_CACHE, "w", encoding="utf-8") as f:
        json.dump(unique_verified, f, ensure_ascii=False, indent=2)

    logger.info(f"🎉 Relevance Gate finished: {len(unique_verified)} confirmed Physiotherapy terms.")
    return unique_verified

def load_existing_enriched() -> Dict[str, Dict[str, Any]]:
    if not os.path.exists(OUTPUT_CSV):
        return {}
    enriched = {}
    with open(OUTPUT_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            lem = row.get("lemma", "").strip()
            if lem:
                enriched[lem] = row
    return enriched

def append_to_physio_csv(rows: List[Dict[str, Any]], write_header: bool = False):
    fieldnames = [
        "lemma", "surface_form", "pos", "cefr_level",
        "german_gloss", "usage_note_de", "is_core", "domain", "subdomains"
    ]
    with file_lock:
        mode = "w" if write_header else "a"
        with open(OUTPUT_CSV, mode, encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if write_header:
                writer.writeheader()
            for r in rows:
                if r.get("lemma"):
                    writer.writerow(r)

def stage2_enrich_b2_c1(verified_lemmas: List[str], batch_size: int = 10):
    existing = load_existing_enriched()
    if not os.path.exists(OUTPUT_CSV):
        append_to_physio_csv([], write_header=True)

    pending = [lem for lem in verified_lemmas if lem not in existing]
    logger.info(f"Starting Stage 2: B2/C1 Enrichment for {len(verified_lemmas)} total verified terms (Already enriched: {len(existing)}, Pending: {len(pending)})...")

    if not pending:
        logger.info("All Physiotherapy terms already enriched!")
        return

    batches = [pending[i:i + batch_size] for i in range(0, len(pending), batch_size)]
    completed = 0

    def _process_enrich_batch(b_idx, batch):
        items_str = "\n".join([f"{idx+1}. {lem}" for idx, lem in enumerate(batch)])
        prompt = f"""Du bist ein deutscher Sprachexperte für medizinische und physiotherapeutische Fachsprache.
Erstelle für die folgenden {len(batch)} Physiotherapie-Fachbegriffe:
1. surface_form: Bei Substantiven MIT passendem Artikel (der / die / das, z.B. "die Mobilisation", "der Musculus biceps"), bei Verben/Adjektiven die Grundform (z.B. "dehnen", "isometrisch").
2. pos: NOUN, VERB, ADJ, ADV, PREP oder OTHER.
3. cefr_level: AUSSCHLIESSLICH "B2" oder "C1" (kein A1, A2, B1!).
4. german_gloss: Eine präzise, aber verständliche deutsche Facherklärung (maximal 15 Wörter).
5. usage_note_de: Ein realistischer Beispielsatz aus dem physiotherapeutischen Praxis- oder Klinikalltag.

Fachbegriffe:
{items_str}

Antworte AUSSCHLIESSLICH im validen JSON-Format:
{{
  "words": [
    {{
      "lemma": "Mobilisation",
      "surface_form": "die Mobilisation",
      "pos": "NOUN",
      "cefr_level": "B2",
      "german_gloss": "das Wiederherstellen der Beweglichkeit von Gelenken oder Muskeln",
      "usage_note_de": "Der Physiotherapeut beginnt nach der Operation mit der sanften Mobilisation des Knies."
    }}
  ]
}}"""

        for model_name in [MODEL_PRIMARY, MODEL_FALLBACK]:
            try:
                resp = client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=2500,
                    timeout=50.0
                )
                raw = resp.choices[0].message.content.strip()
                words_list = []
                if "{" in raw and "}" in raw:
                    try:
                        raw_json = raw[raw.find("{"):raw.rfind("}")+1]
                        data = json.loads(raw_json)
                        if isinstance(data, dict) and "words" in data:
                            words_list = data["words"]
                    except Exception:
                        pass

                if not words_list:
                    matches = re.findall(r'\{[^{}]*"lemma"[^{}]*\}', raw, re.DOTALL)
                    for m in matches:
                        try:
                            w_obj = json.loads(m)
                            if "lemma" in w_obj:
                                words_list.append(w_obj)
                        except Exception:
                            pass

                if words_list:
                    batch_rows = []
                    for w in words_list:
                        lvl = str(w.get("cefr_level", "B2")).strip().upper()
                        if lvl not in ("B2", "C1"):
                            lvl = "B2"
                        batch_rows.append({
                            "lemma": w.get("lemma"),
                            "surface_form": w.get("surface_form", w.get("lemma")),
                            "pos": w.get("pos", "NOUN"),
                            "cefr_level": lvl,
                            "german_gloss": w.get("german_gloss", f"Physiotherapeutischer Fachbegriff {w.get('lemma')}"),
                            "usage_note_de": w.get("usage_note_de", f"Beispiel mit {w.get('lemma')} in der Therapie."),
                            "is_core": "False",
                            "domain": "HEALTH",
                            "subdomains": "['PHYSIO']"
                        })
                    append_to_physio_csv(batch_rows)
                    return len(batch_rows)
            except Exception as e:
                logger.warning(f"Stage 2 batch {b_idx} with {model_name} failed: {e}")

        # Fallback for batch
        fallback_rows = [{
            "lemma": lem,
            "surface_form": lem,
            "pos": "NOUN",
            "cefr_level": "B2",
            "german_gloss": f"Physiotherapeutischer Fachbegriff {lem}",
            "usage_note_de": f"Der Begriff {lem} wird in der Physiotherapie verwendet.",
            "is_core": "False",
            "domain": "HEALTH",
            "subdomains": "['PHYSIO']"
        } for lem in batch]
        append_to_physio_csv(fallback_rows)
        return len(fallback_rows)

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(_process_enrich_batch, idx + 1, b): idx + 1 for idx, b in enumerate(batches)}
        for f in as_completed(futures):
            count = f.result()
            completed += 1
            logger.info(f"Enrichment batch saved ({completed}/{len(batches)} batches done).")

    logger.info(f"🎉 Stage 2 Enrichment complete! Saved to: {OUTPUT_CSV}")

def main():
    core_lemmas = load_core_lemmas()
    raw_text = extract_text_from_pdfs()
    if not raw_text.strip():
        logger.error("No text extracted from Physiotherapy PDFs!")
        return

    candidates = extract_candidate_lemmas(raw_text, core_lemmas)
    verified_terms = stage1_relevance_gate(candidates)
    stage2_enrich_b2_c1(verified_terms)

if __name__ == "__main__":
    main()
