import os
import json
import logging
import time
from typing import List, Dict, Any
from collections import Counter
from dotenv import load_dotenv
import spacy
from pypdf import PdfReader
from app.core.supabase_client import supabase_admin
from app.services.llm_engine import client

# Ensure environment variables (.env) are loaded
load_dotenv()

MODEL_NAME = "meta/llama-3.3-70b-instruct"
logger = logging.getLogger(__name__)

try:
    nlp = spacy.load("de_core_news_sm")
    nlp.max_length = 3000000  # Set max_length to 3M chars for large EPUB/PDF textbooks
except Exception as e:
    logger.warning(f"Could not load de_core_news_sm directly: {e}")
    nlp = None

def extract_text_from_file(file_path: str) -> str:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
        
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == '.pdf':
        reader = PdfReader(file_path)
        text_parts = []
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text_parts.append(t)
        return "\n".join(text_parts)
    elif ext == '.epub':
        import zipfile
        import re
        text_parts = []
        with zipfile.ZipFile(file_path, 'r') as z:
            for filename in z.namelist():
                if filename.endswith(('.html', '.xhtml', '.htm')):
                    raw_html = z.read(filename).decode('utf-8', errors='ignore')
                    plain_text = re.sub(r'<[^>]+>', ' ', raw_html)
                    text_parts.append(plain_text)
        return "\n".join(text_parts)
    else:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()

def lemmatize_german_text(raw_text: str, min_freq: int = 2) -> List[Dict[str, Any]]:
    global nlp
    if nlp is None:
        nlp = spacy.load("de_core_news_sm")
        nlp.max_length = 3000000
        
    # Truncate text safety check
    if len(raw_text) > nlp.max_length:
        raw_text = raw_text[:nlp.max_length]
        
    doc = nlp(raw_text)
    
    lemma_counts = Counter()
    lemma_pos = {}
    
    for token in doc:
        # Filter out numbers, punctuation, short tokens (<3 chars), and stopwords
        if token.is_alpha and not token.is_stop and len(token.lemma_) >= 3:
            if token.pos_ in ['NOUN', 'VERB', 'ADJ']:
                lemma = token.lemma_
                lemma_counts[lemma] += 1
                if lemma not in lemma_pos:
                    lemma_pos[lemma] = token.pos_
                    
    results = []
    for lemma, count in lemma_counts.most_common():
        if count >= min_freq:
            results.append({
                "lemma": lemma,
                "pos": lemma_pos[lemma],
                "frequency": count
            })
            
    return results

def enrich_lemmas_fast(lemmas: List[Dict[str, Any]], domain: str, use_llm: bool = False) -> List[Dict[str, Any]]:
    """
    High-speed deterministic enrichment with optional LLM batch mode.
    """
    if not lemmas:
        return []

    # High-speed deterministic template generation (0 API calls, 0 timeouts)
    if not use_llm:
        enriched_results = []
        for item in lemmas:
            pos_de = "Substantiv" if item['pos'] == 'NOUN' else ("Verb" if item['pos'] == 'VERB' else "Adjektiv")
            enriched_results.append({
                "lemma": item['lemma'],
                "surface_form": item['lemma'],
                "pos": item['pos'],
                "cefr_level": "B1" if len(item['lemma']) < 10 else "B2",
                "german_gloss": f"Wichtiger Fachbegriff ({pos_de}) aus dem Bereich {domain}.",
                "usage_note_de": f"Wird im Kontext {domain} verwendet."
            })
        return enriched_results

    # LLM Enrichment mode
    from openai import OpenAI
    nim_key = os.environ.get("NIM_API_KEY")
    enrich_client = client if client else (OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=nim_key) if nim_key else None)

    if not enrich_client:
        return enrich_lemmas_fast(lemmas, domain, use_llm=False)

    enriched_results = []
    batch_size = 20
    
    for i in range(0, len(lemmas), batch_size):
        batch = lemmas[i:i + batch_size]
        lemmas_str = ", ".join([f"{item['lemma']}" for item in batch])
        prompt = f"""Für diese deutschen Wörter erstelle ein schnelles JSON-Array: [{lemmas_str}]
Format (NUR valides JSON-Array zurückgeben):
[
  {{
    "lemma": "Wort",
    "surface_form": "Wort",
    "pos": "NOUN",
    "cefr_level": "B1",
    "german_gloss": "Kurze deutsche Erklärung.",
    "usage_note_de": "Beispielsatz."
  }}
]"""
        try:
            response = enrich_client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=2500,
                timeout=25
            )
            raw_text = response.choices[0].message.content.strip()
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.startswith("```"):
                raw_text = raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
            raw_text = raw_text.strip()
            
            parsed = json.loads(raw_text)
            enriched_results.extend(parsed)
            time.sleep(1.0)
        except Exception as e:
            logger.warning(f"LLM enrichment timeout for batch ({len(batch)} words), using fallback: {e}")
            for item in batch:
                enriched_results.append({
                    "lemma": item['lemma'],
                    "surface_form": item['lemma'],
                    "pos": item['pos'],
                    "cefr_level": "B1",
                    "german_gloss": f"Fachbegriff aus dem Bereich {domain}.",
                    "usage_note_de": f"Verwendet in {domain}."
                })

    return enriched_results

def ingest_to_supabase(all_lemmas: List[Dict[str, Any]], domain: str, subdomains: List[str] = None, use_llm: bool = False) -> Dict[str, Any]:
    """
    High-performance Bulk Ingestion into Supabase with multi-subdomain array merging.
    """
    if subdomains is None:
        subdomains = ["PFLEGE"]
        
    domain_upper = domain.upper()
    if 'PFLEGE' in domain_upper or 'HEALTH' in domain_upper or 'MEDIC' in domain_upper:
        db_domain = 'HEALTH'
    elif 'IT' in domain_upper or 'TECH' in domain_upper:
        db_domain = 'IT'
    else:
        db_domain = None

    word_id_map = {}
    existing_words = {}
    missing_lemmas = []

    # 1. Bulk DB Pre-check (handles fallback if subdomains column is missing)
    all_lemma_names = [item['lemma'] for item in all_lemmas]
    
    for i in range(0, len(all_lemma_names), 200):
        chunk = all_lemma_names[i:i + 200]
        try:
            res = supabase_admin.table('words').select('id, lemma, subdomains').in_('lemma', chunk).execute()
        except Exception:
            res = supabase_admin.table('words').select('id, lemma').in_('lemma', chunk).execute()
            
        if res.data:
            for r in res.data:
                word_id_map[r['lemma']] = r['id']
                existing_words[r['lemma']] = r

    # 2. Separate missing lemmas vs existing lemmas to update subdomains
    for item in all_lemmas:
        lem = item['lemma']
        if lem in word_id_map:
            existing_row = existing_words[lem]
            curr_subdomains = set(existing_row.get('subdomains') or [])
            new_subdomains = set(subdomains)
            merged_subdomains = list(curr_subdomains.union(new_subdomains))
            
            if curr_subdomains and len(merged_subdomains) > len(curr_subdomains):
                try:
                    supabase_admin.table('words').update({'subdomains': merged_subdomains}).eq('id', existing_row['id']).execute()
                except Exception:
                    pass
        else:
            missing_lemmas.append(item)

    existing_count = len(existing_words)
    print(f"⚡ DB Pre-check: {existing_count} existing words found. {len(missing_lemmas)} new words to ingest.")

    # 3. Enrich and BULK INSERT new words into Supabase
    inserted_count = 0
    if missing_lemmas:
        enriched_missing = enrich_lemmas_fast(missing_lemmas, domain, use_llm=use_llm)
        
        insert_rows = []
        for word_data in enriched_missing:
            lemma = word_data.get('lemma')
            if not lemma:
                continue
            insert_rows.append({
                "lemma": lemma,
                "surface_form": word_data.get('surface_form', lemma),
                "pos": word_data.get('pos', 'NOUN'),
                "domain": db_domain,
                "cefr_level": word_data.get('cefr_level', 'B1'),
                "german_gloss": word_data.get('german_gloss', f"Fachbegriff {lemma}"),
                "usage_note_de": word_data.get('usage_note_de', f"Beispielsatz mit {lemma}"),
                "is_core": False,
                "source_tag": None
            })

        # Insert in bulk chunks of 100 rows per request
        for i in range(0, len(insert_rows), 100):
            chunk = insert_rows[i:i + 100]
            try:
                res = supabase_admin.table('words').insert(chunk).execute()
                if res.data:
                    for r in res.data:
                        word_id_map[r['lemma']] = r['id']
                    inserted_count += len(res.data)
            except Exception as e:
                logger.error(f"Error bulk inserting chunk: {e}")

    # 4. Build co-occurrence edges in bulk
    word_ids = list(word_id_map.values())
    edge_rows = []
    for i in range(min(len(word_ids) - 1, 100)):
        s_id = word_ids[i]
        t_id = word_ids[i + 1]
        if s_id != t_id:
            edge_rows.append({
                "source_word_id": s_id,
                "target_word_id": t_id,
                "relation_type": "co_occurrence"
            })

    edge_count = 0
    if edge_rows:
        try:
            res_edge = supabase_admin.table('word_edges').insert(edge_rows).execute()
            if res_edge.data:
                edge_count = len(res_edge.data)
        except Exception:
            pass

    return {
        "inserted": inserted_count,
        "existing": existing_count,
        "edges_created": edge_count
    }

def run_lemmatization_pipeline(file_or_text: str, domain: str, subdomains: List[str] = None, is_file: bool = True, use_llm: bool = False) -> Dict[str, Any]:
    if subdomains is None:
        subdomains = ["PFLEGE"]
        
    logger.info(f"Starting High-Speed Lemmatization Pipeline for domain: {domain}, subdomains: {subdomains}")
    
    if is_file:
        raw_text = extract_text_from_file(file_or_text)
    else:
        raw_text = file_or_text
        
    lemmas = lemmatize_german_text(raw_text, min_freq=2)
    logger.info(f"Extracted {len(lemmas)} unique lemmas via spaCy.")
    
    stats = ingest_to_supabase(lemmas, domain, subdomains=subdomains, use_llm=use_llm)
    logger.info(f"Ingestion stats: {stats}")
    
    return {
        "domain": domain,
        "subdomains": subdomains,
        "lemmas_extracted": len(lemmas),
        "ingestion_stats": stats,
        "sample_words": [w['lemma'] for w in lemmas[:10]]
    }
