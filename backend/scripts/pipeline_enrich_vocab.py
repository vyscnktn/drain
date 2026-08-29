#!/usr/bin/env python3
"""
Vocabulary Enrichment Pipeline for Core Words (A1, A2, B1)
Uses NVIDIA NIM (openai/gpt-oss-120b) to generate simple German definitions
and example sentences with concurrent worker threads and checkpointing/resume support.
"""

import os
import sys
import csv
import json
import time
import threading
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from openai import OpenAI

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
    timeout=45.0
)

MODEL_PRIMARY = "meta/llama-3.2-11b-vision-instruct"
MODEL_FALLBACK = "meta/llama-3.2-90b-vision-instruct"
BATCH_SIZE = 15
MAX_WORKERS = 3

CSV_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../documents/wortliste"))
file_lock = threading.Lock()

def is_valid_entry(row: Dict[str, str]) -> bool:
    lemma = row.get("Lemma", "").strip()
    if not lemma:
        return False
    if len(lemma) < 2 and not lemma.isalpha():
        return False
    if lemma.startswith("-") or lemma.endswith("-"):
        return False
    if lemma in ("%", "&", "§", "$", "#", "@", "+", "=", "<", ">"):
        return False
    return True

def read_source_csv(filepath: str) -> List[Dict[str, str]]:
    entries = []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if is_valid_entry(row):
                entries.append({
                    "lemma": row.get("Lemma", "").strip(),
                    "artikel": row.get("Artikel", "").strip(),
                    "genus": row.get("Genus", "").strip(),
                    "wortart": row.get("Wortart", "").strip(),
                })
    return entries

def load_existing_enriched(filepath: str) -> Dict[str, Dict[str, Any]]:
    if not os.path.exists(filepath):
        return {}
    enriched = {}
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            lemma = row.get("lemma", "").strip()
            if lemma:
                enriched[lemma] = row
    return enriched

def append_to_enriched_csv(filepath: str, rows: List[Dict[str, Any]], write_header: bool = False):
    fieldnames = [
        "lemma", "surface_form", "pos", "cefr_level",
        "german_gloss", "usage_note_de", "is_core", "domain", "subdomains"
    ]
    with file_lock:
        mode = "w" if write_header else "a"
        with open(filepath, mode, encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if write_header:
                writer.writeheader()
            for r in rows:
                writer.writerow({
                    "lemma": r.get("lemma", ""),
                    "surface_form": r.get("surface_form", r.get("lemma", "")),
                    "pos": r.get("pos", "NOUN"),
                    "cefr_level": r.get("cefr_level", "A1"),
                    "german_gloss": r.get("german_gloss", ""),
                    "usage_note_de": r.get("usage_note_de", ""),
                    "is_core": "True",
                    "domain": "",
                    "subdomains": "[]"
                })

def extract_words_from_raw(raw: str) -> List[Dict[str, Any]]:
    import re
    # 1. Standard json parse
    if "{" in raw and "}" in raw:
        try:
            raw_json = raw[raw.find("{"):raw.rfind("}")+1]
            data = json.loads(raw_json)
            if isinstance(data, dict) and "words" in data and isinstance(data["words"], list):
                return data["words"]
        except Exception:
            pass

    # 2. Regex individual JSON object extraction
    found_words = []
    matches = re.findall(r'\{[^{}]*"lemma"[^{}]*\}', raw, re.DOTALL)
    for m in matches:
        try:
            w_obj = json.loads(m)
            if "lemma" in w_obj:
                found_words.append(w_obj)
        except Exception:
            pass
    return found_words

def enrich_batch_with_nim(batch: List[Dict[str, str]], cefr_level: str, max_retries: int = 2) -> List[Dict[str, Any]]:
    items_lines = []
    for i, w in enumerate(batch):
        art_info = f"Artikel: {w['artikel']}" if w['artikel'] else ""
        gen_info = f"Genus: {w['genus']}" if w['genus'] else ""
        art_gen = ", ".join(filter(None, [art_info, gen_info, w['wortart']]))
        items_lines.append(f"{i+1}. {w['lemma']}" + (f" ({art_gen})" if art_gen else ""))

    items_str = "\n".join(items_lines)

    prompt = f"""Du bist ein deutscher Sprachexperte. Erstelle für die folgenden {len(batch)} deutschen {cefr_level}-Wörter:
1. surface_form: Bei Substantiven mit Artikel (z.B. "der Abend", "die Zeit", "das Haus"), bei Verben/Adjektiven die Grundform (z.B. "abfahren", "alt").
2. pos: NOUN, VERB, ADJ, ADV, PREP, CONJ oder OTHER.
3. german_gloss: Eine sehr einfache, kurze deutsche Worterklärung auf {cefr_level}-Niveau (maximal 12 Wörter).
4. usage_note_de: Ein natürlicher, alltagstauglicher Beispielsatz auf {cefr_level}-Niveau.

Wörterliste:
{items_str}

Antworte AUSSCHLIESSLICH mit einem validen JSON-Objekt in folgendem Format:
{{
  "words": [
    {{
      "lemma": "Abend",
      "surface_form": "der Abend",
      "pos": "NOUN",
      "german_gloss": "die Zeit nach dem Nachmittag",
      "usage_note_de": "Am Abend sehen wir einen Film."
    }}
  ]
}}"""

    models_to_try = [MODEL_PRIMARY, MODEL_FALLBACK]
    for model_name in models_to_try:
        for attempt in range(1, max_retries + 1):
            try:
                resp = client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=3000,
                    timeout=45.0
                )
                raw = resp.choices[0].message.content.strip()
                words_list = extract_words_from_raw(raw)
                
                if words_list:
                    aligned_results = []
                    returned_map = {w.get("lemma", "").strip().lower(): w for w in words_list}
                    
                    for orig in batch:
                        orig_lemma = orig["lemma"].strip()
                        matched = returned_map.get(orig_lemma.lower())
                        if matched:
                            aligned_results.append({
                                "lemma": orig_lemma,
                                "surface_form": matched.get("surface_form") or (f"{orig['artikel']} {orig_lemma}".strip() if orig['artikel'] else orig_lemma),
                                "pos": matched.get("pos", "NOUN"),
                                "cefr_level": cefr_level,
                                "german_gloss": matched.get("german_gloss", f"Bedeutung von {orig_lemma}"),
                                "usage_note_de": matched.get("usage_note_de", f"Ein Beispielsatz mit {orig_lemma}.")
                            })
                        else:
                            fallback_surface = f"{orig['artikel']} {orig_lemma}".strip() if orig['artikel'] else orig_lemma
                            aligned_results.append({
                                "lemma": orig_lemma,
                                "surface_form": fallback_surface,
                                "pos": "NOUN" if orig['artikel'] else "OTHER",
                                "cefr_level": cefr_level,
                                "german_gloss": f"Einfacher Begriff {orig_lemma}",
                                "usage_note_de": f"Ein Beispielsatz mit {orig_lemma}."
                            })
                    return aligned_results
                else:
                    raise ValueError("No JSON object extracted from response")

            except Exception as e:
                logger.warning(f"Model {model_name} attempt {attempt}/{max_retries} failed: {e}")
                if attempt < max_retries:
                    time.sleep(1)

    logger.error("All models and retries failed for batch. Generating fallback.")
    return [{
        "lemma": w["lemma"],
        "surface_form": f"{w['artikel']} {w['lemma']}".strip() if w['artikel'] else w['lemma'],
        "pos": "NOUN" if w['artikel'] else "OTHER",
        "cefr_level": cefr_level,
        "german_gloss": f"Grundwort {w['lemma']}",
        "usage_note_de": f"Das Wort {w['lemma']} wird im Alltag verwendet."
    } for w in batch]

def process_level_csv(level_name: str):
    source_file = os.path.join(CSV_DIR, f"{level_name}.csv")
    output_file = os.path.join(CSV_DIR, f"{level_name}_enriched.csv")

    if not os.path.exists(source_file):
        logger.error(f"Source file {source_file} not found!")
        return

    all_entries = read_source_csv(source_file)
    existing = load_existing_enriched(output_file)

    logger.info(f"[{level_name}] Total valid entries: {len(all_entries)}, Already enriched: {len(existing)}")

    if not os.path.exists(output_file):
        append_to_enriched_csv(output_file, [], write_header=True)

    pending = [e for e in all_entries if e["lemma"] not in existing]
    logger.info(f"[{level_name}] Remaining to process: {len(pending)}")
    if not pending:
        logger.info(f"[{level_name}] All words already enriched!")
        return

    batches = [pending[i:i + BATCH_SIZE] for i in range(0, len(pending), BATCH_SIZE)]
    total_batches = len(batches)
    completed_batches = 0

    def _worker(batch_idx, batch_data):
        t0 = time.time()
        enriched = enrich_batch_with_nim(batch_data, cefr_level=level_name)
        elapsed = time.time() - t0
        append_to_enriched_csv(output_file, enriched, write_header=False)
        return batch_idx, len(batch_data), elapsed

    logger.info(f"[{level_name}] Launching {total_batches} batches with {MAX_WORKERS} concurrent threads...")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(_worker, idx + 1, b): idx + 1 for idx, b in enumerate(batches)}
        for future in as_completed(futures):
            b_idx, count, el = future.result()
            completed_batches += 1
            logger.info(f"[{level_name}] Batch {b_idx}/{total_batches} ({count} words) saved ({completed_batches}/{total_batches} complete in {el:.2f}s).")

    logger.info(f"🎉 [{level_name}] Enrichment complete! Output saved to: {output_file}")

def main():
    levels = ["A1", "A2", "B1"]
    if len(sys.argv) > 1:
        levels = [sys.argv[1].upper()]

    logger.info(f"Starting Core Vocabulary Enrichment for levels: {levels}")
    for lvl in levels:
        process_level_csv(lvl)

if __name__ == "__main__":
    main()
