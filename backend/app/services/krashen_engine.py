from typing import List, Dict, Any, Tuple
from app.core.supabase_client import supabase_admin
import random
import re

INVALID_LEMMAS = {
    "gmbh", "ggmbh", "ag", "ev", "e.v.", "kg", "inc", "ltd", "gbr", "ohg", "kgaa",
    "bzw", "bzw.", "ca", "ca.", "etc", "etc.", "sog", "sog.", "z.b.", "zb", "u.a.", "d.h.", "dh",
    "missen", "kommend", "ergeben", "ebenso", "binnen", "hinsichtlich", "infolge", "bezüglich",
    "herr", "frau", "schmidt", "meyer", "weber", "müller", "schneider", "fischer"
}

VALID_SHORT_TERMS = {"OP", "CT", "EKG", "MRT", "HNO", "BMI", "HIV", "DNA"}

def is_valid_target_word(w: Dict[str, Any]) -> bool:
    """
    Validates if a word candidate is suitable to be a target vocabulary word.
    Filters out corporate terms, acronyms, ligatures, names, and generic noise.
    """
    if not w or not isinstance(w, dict):
        return False
    lemma = (w.get("lemma") or "").strip()
    if not lemma:
        return False
    lemma_lower = lemma.lower()
    
    if lemma_lower in INVALID_LEMMAS:
        return False
    if len(lemma) < 3 and lemma not in VALID_SHORT_TERMS:
        return False
    if lemma.isupper() and len(lemma) > 1 and lemma not in VALID_SHORT_TERMS:
        return False
    if not re.match(r"^[a-zA-ZäöüÄÖÜß\s\-\.]+$", lemma):
        return False
    return True

def get_candidate_anchors(user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Fetch high-mastery words for the user to serve as anchors.
    """
    response = supabase_admin.table('user_word_state') \
        .select('word_id, mastery_score') \
        .eq('user_id', user_id) \
        .gte('mastery_score', 0.8) \
        .limit(100) \
        .execute()
    
    candidates = response.data
    if candidates:
        return random.sample(candidates, min(limit, len(candidates)))
    return []

def get_target_words_from_anchors(user_id: str, anchor_word_ids: List[int], limit: int = 1) -> List[Dict[str, Any]]:
    """
    Find target words that are connected to anchor words but have low/no mastery.
    """
    if not anchor_word_ids:
        return []

    # Get words connected to the anchors
    edges_resp = supabase_admin.table('word_edges') \
        .select('target_word_id, relation_type') \
        .in_('source_word_id', anchor_word_ids) \
        .execute()
    
    candidate_target_ids = list(set([edge['target_word_id'] for edge in edges_resp.data]))
    if not candidate_target_ids:
        return []
        
    # Get user's current mastery for these candidates
    mastery_resp = supabase_admin.table('user_word_state') \
        .select('word_id, mastery_score') \
        .eq('user_id', user_id) \
        .in_('word_id', candidate_target_ids) \
        .execute()
        
    known_masteries = {row['word_id']: row['mastery_score'] for row in mastery_resp.data}
    
    # Filter candidates: keep if mastery is < 0.4 or unseen (not in known_masteries)
    valid_targets = [
        word_id for word_id in candidate_target_ids 
        if word_id not in known_masteries or known_masteries[word_id] < 0.4
    ]
    
    if not valid_targets:
        return []
        
    # Fetch full word details
    words_resp = supabase_admin.table('words') \
        .select('*') \
        .in_('id', valid_targets) \
        .execute()
        
    clean_words = [w for w in words_resp.data if is_valid_target_word(w)]
    if not clean_words:
        return []
        
    return random.sample(clean_words, min(limit, len(clean_words)))

def select_reading_words(user_id: str, domain: str = "HEALTH", subdomain: str = None) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Main algorithm to select anchors and targets for the next reading text.
    Filters targets by domain / subdomain if provided.
    """
    anchors_state = get_candidate_anchors(user_id)
    anchor_ids = [a['word_id'] for a in anchors_state]
    
    # If user has no high mastery words (new user), we need to bootstrap with core words
    if not anchor_ids:
        try:
            if subdomain:
                core_resp = supabase_admin.table('words').select('*').eq('is_core', True).contains('subdomains', [subdomain]).limit(50).execute()
            else:
                core_resp = supabase_admin.table('words').select('*').eq('is_core', True).limit(50).execute()
        except Exception:
            core_resp = supabase_admin.table('words').select('*').eq('is_core', True).limit(50).execute()
        
        all_core_words = [w for w in core_resp.data if is_valid_target_word(w)] if core_resp.data else []
        if not all_core_words:
            try:
                core_resp = supabase_admin.table('words').select('*').eq('is_core', True).limit(50).execute()
                all_core_words = [w for w in core_resp.data if is_valid_target_word(w)] if core_resp.data else []
            except Exception:
                all_core_words = []
            
        anchors = random.sample(all_core_words, min(10, len(all_core_words))) if all_core_words else []
        anchor_ids = [a['id'] for a in anchors]
    else:
        anchors_resp = supabase_admin.table('words') \
            .select('*') \
            .in_('id', anchor_ids) \
            .execute()
        anchors = [w for w in anchors_resp.data if is_valid_target_word(w)]
        random.shuffle(anchors)
        
    targets = get_target_words_from_anchors(user_id, anchor_ids)
    
    # If no targets found via graph, fallback to random unmastered domain words
    if not targets:
        all_words_resp = None
        if subdomain:
            try:
                all_words_resp = supabase_admin.table('words').select('*').eq('source_ref', subdomain).limit(100).execute()
                if not all_words_resp.data:
                    all_words_resp = supabase_admin.table('words').select('*').eq('notes', subdomain).limit(100).execute()
            except Exception:
                pass
        
        if not all_words_resp or not all_words_resp.data:
            try:
                all_words_resp = supabase_admin.table('words').select('*').eq('domain', domain).limit(100).execute()
            except Exception:
                all_words_resp = supabase_admin.table('words').select('*').limit(100).execute()
            
        candidate_words = [w for w in (all_words_resp.data if all_words_resp else []) if w['id'] not in anchor_ids and is_valid_target_word(w)]
        if not candidate_words:
            candidate_words = supabase_admin.table('words').select('*').limit(100).execute().data
            candidate_words = [w for w in candidate_words if w['id'] not in anchor_ids and is_valid_target_word(w)]
            
        if candidate_words:
            targets = [random.choice(candidate_words)]
        
    return anchors, targets
