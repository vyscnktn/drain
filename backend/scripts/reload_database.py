#!/usr/bin/env python3
"""
Database Reload & Ingestion Script
Cleans existing words and related data in Supabase,
and bulk inserts all enriched core (A1, A2, B1) and domain-specific (Physiotherapy) vocabulary
with strict case-insensitive lemma deduplication.
"""

import os
import sys
import csv
import logging
from typing import List, Dict, Any
from dotenv import load_dotenv

# Add backend directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.core.supabase_client import supabase_admin

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DOCS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../documents"))
CORE_DIR = os.path.join(DOCS_DIR, "wortliste")
PHYSIO_DIR = os.path.join(DOCS_DIR, "physiotherapie")

ALLOWED_POS = {"NOUN", "VERB", "ADJ", "ADV"}

def normalize_pos(raw_pos: str) -> str:
    pos = (raw_pos or "NOUN").strip().upper()
    if pos in ALLOWED_POS:
        return pos
    if pos in ("ADVERB", "ADV"):
        return "ADV"
    if pos in ("ADJECTIVE", "ADJ"):
        return "ADJ"
    if pos in ("VERB", "V"):
        return "VERB"
    if pos in ("PREP", "CONJ", "PRON", "PART", "INTJ"):
        return "ADV"
    return "NOUN"

def clean_database():
    logger.info("🧹 Cleaning old database records...")
    tables_to_clear = [
        "generated_text_words",
        "word_edges",
        "user_word_state",
        "text_ratings",
        "generated_texts",
        "words"
    ]
    for table_name in tables_to_clear:
        try:
            logger.info(f"Clearing table: {table_name}...")
            if table_name in ("word_edges",):
                supabase_admin.table(table_name).delete().gte('source_word_id', 0).execute()
            elif table_name in ("generated_text_words", "user_word_state"):
                supabase_admin.table(table_name).delete().gte('word_id', 0).execute()
            else:
                supabase_admin.table(table_name).delete().gte('id', 0).execute()
            logger.info(f"✅ Table {table_name} cleared.")
        except Exception as e:
            logger.warning(f"Note on clearing {table_name}: {e}")

def load_csv_rows(filepath: str, is_domain: bool = False) -> List[Dict[str, Any]]:
    if not os.path.exists(filepath):
        logger.warning(f"File {filepath} does not exist!")
        return []
    
    rows = []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            lemma = r.get("lemma", "").strip()
            if not lemma:
                continue

            is_core_val = not is_domain
            cefr = r.get("cefr_level", "A1").strip().upper()
            pos = normalize_pos(r.get("pos", "NOUN"))
            
            source_tag = "manual" if is_domain else f"goethe_{cefr.lower()}"
            if source_tag not in ("goethe_a1", "goethe_a2", "goethe_b1", "manual"):
                source_tag = "manual"

            row_dict = {
                "lemma": lemma,
                "surface_form": r.get("surface_form", lemma).strip(),
                "pos": pos,
                "cefr_level": cefr,
                "german_gloss": r.get("german_gloss", f"Bedeutung von {lemma}").strip(),
                "usage_note_de": r.get("usage_note_de", f"Beispielsatz mit {lemma}.").strip(),
                "is_core": is_core_val,
                "domain": "HEALTH" if is_domain else None,
                "source_tag": source_tag,
                "source_ref": "PHYSIO" if is_domain else None,
                "notes": "PHYSIO" if is_domain else None
            }
            rows.append(row_dict)

    logger.info(f"Loaded {len(rows)} records from: {os.path.basename(filepath)}")
    return rows

def bulk_insert_words(words: List[Dict[str, Any]], chunk_size: int = 100):
    logger.info(f"🚀 Inserting {len(words)} words into Supabase in chunks of {chunk_size}...")
    total_inserted = 0
    
    for i in range(0, len(words), chunk_size):
        chunk = words[i:i + chunk_size]
        try:
            supabase_admin.table('words').insert(chunk).execute()
            total_inserted += len(chunk)
            if (i // chunk_size) % 5 == 0 or (i + chunk_size) >= len(words):
                logger.info(f"Progress: {total_inserted}/{len(words)} words inserted.")
        except Exception as e:
            logger.warning(f"Chunk insert issue at index {i}: {e}. Retrying row-by-row...")
            for row in chunk:
                try:
                    supabase_admin.table('words').insert(row).execute()
                    total_inserted += 1
                except Exception:
                    pass

    logger.info(f"🎉 Total words successfully inserted into Supabase: {total_inserted}")

def main():
    logger.info("=== Starting Clean Database Reload ===")
    
    # 1. Clean old records
    clean_database()

    # 2. Collect core A1, A2, B1 files
    core_files = [
        os.path.join(CORE_DIR, "A1_enriched.csv"),
        os.path.join(CORE_DIR, "A2_enriched.csv"),
        os.path.join(CORE_DIR, "B1_enriched.csv")
    ]
    physio_file = os.path.join(PHYSIO_DIR, "physio_enriched.csv")

    all_words = []
    seen_lemmas = set()

    for fp in core_files:
        rows = load_csv_rows(fp, is_domain=False)
        for r in rows:
            lem_lower = r['lemma'].lower()
            if lem_lower not in seen_lemmas:
                seen_lemmas.add(lem_lower)
                all_words.append(r)

    # Physio domain terms (strictly non-core)
    physio_rows = load_csv_rows(physio_file, is_domain=True)
    for r in physio_rows:
        lem_lower = r['lemma'].lower()
        if lem_lower not in seen_lemmas:
            seen_lemmas.add(lem_lower)
            all_words.append(r)

    logger.info(f"Total unique words prepared for DB: {len(all_words)}")
    
    # 3. Bulk insert
    if all_words:
        bulk_insert_words(all_words)
    else:
        logger.warning("No words found to insert!")

if __name__ == "__main__":
    main()
