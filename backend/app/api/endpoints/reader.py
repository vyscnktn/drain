from fastapi import APIRouter, HTTPException, Depends, Request, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
import logging
import io
import zipfile
from datetime import datetime, timedelta, date
from fastapi.responses import StreamingResponse

from app.services.krashen_engine import select_reading_words
from app.services.llm_engine import validate_and_generate
from app.core.supabase_client import supabase_admin
from app.core.auth import get_current_user, FALLBACK_USER_ID
from app.core.limiter import limiter

router = APIRouter()
logger = logging.getLogger(__name__)

class ReadingRequest(BaseModel):
    user_id: Optional[str] = None
    target_level: Literal['A1', 'A2', 'B1', 'B2', 'C1'] = "A2"
    target_domain: Literal['IT', 'HEALTH', 'ACADEMIC']
    subdomain: Optional[str] = None

class RatingRequest(BaseModel):
    user_id: Optional[str] = None
    generated_text_id: int
    rating: int = Field(..., ge=1, le=5)
    difficulty: Optional[str] = None # "Zu einfach", "Genau richtig", "Zu schwer"


@router.post("/generate")
@limiter.limit("20/minute")
async def generate_reading(
    request: Request,
    payload: ReadingRequest,
    current_user_id: str = Depends(get_current_user)
):
    """
    Generates a personalized reading text for the authenticated user based on domain/subdomain.
    """
    user_id = current_user_id
    try:
        anchors, targets = select_reading_words(user_id, domain=payload.target_domain, subdomain=payload.subdomain)
        if not anchors:
            raise HTTPException(status_code=400, detail="Ankerwörter für diesen Bereich konnten nicht gefunden werden.")
            
        anchor_lemmas = [a['lemma'] for a in anchors]
        target = targets[0] if targets else anchors[0]
        target_lemma = target['lemma']
        
        known_resp = supabase_admin.table('user_word_state') \
            .select('word_id, mastery_score') \
            .eq('user_id', user_id) \
            .gte('mastery_score', 0.4) \
            .execute()
            
        known_ids = [k['word_id'] for k in known_resp.data]
        core_resp = supabase_admin.table('words').select('id, lemma').eq('is_core', True).execute()
        
        all_known_lemmas = [c['lemma'] for c in core_resp.data]
        if known_ids:
            known_words_resp = supabase_admin.table('words').select('lemma').in_('id', known_ids).execute()
            all_known_lemmas.extend([w['lemma'] for w in known_words_resp.data])
            
        effective_domain = payload.subdomain or payload.target_domain
        text, passed, ratio = validate_and_generate(anchor_lemmas, target_lemma, all_known_lemmas, domain=effective_domain, level=payload.target_level)
        
        if not passed and not text.startswith("ERROR"):
            logger.warning(f"Validation failed (ratio {ratio}). Text: {text}")
            
        text_id = 999999
        try:
            insert_resp = supabase_admin.table('generated_texts').insert({
                "user_id": user_id,
                "domain": payload.target_domain,
                "level": payload.target_level,
                "anchor_word_id": anchors[0]['id'],
                "content": text,
                "unknown_ratio": ratio,
                "validation_passed": passed
            }).execute()
            if insert_resp.data:
                text_id = insert_resp.data[0]['id']
                
                bridge_entries = []
                for a in anchors:
                    bridge_entries.append({"generated_text_id": text_id, "word_id": a['id'], "occurrences": 1, "is_target": False})
                
                if target['id'] not in [a['id'] for a in anchors]:
                    bridge_entries.append({"generated_text_id": text_id, "word_id": target['id'], "occurrences": 1, "is_target": True})
                    
                supabase_admin.table('generated_text_words').insert(bridge_entries).execute()
        except Exception as ge:
            logger.warning(f"[Generate] Skipping generated_texts insert for user {user_id}: {ge}")
            if user_id != FALLBACK_USER_ID:
                try:
                    fallback_resp = supabase_admin.table('generated_texts').insert({
                        "user_id": FALLBACK_USER_ID,
                        "domain": payload.target_domain,
                        "level": payload.target_level,
                        "anchor_word_id": anchors[0]['id'],
                        "content": text,
                        "unknown_ratio": ratio,
                        "validation_passed": passed
                    }).execute()
                    if fallback_resp.data:
                        text_id = fallback_resp.data[0]['id']
                        bridge_entries = []
                        for a in anchors:
                            bridge_entries.append({"generated_text_id": text_id, "word_id": a['id'], "occurrences": 1, "is_target": False})
                        if target['id'] not in [a['id'] for a in anchors]:
                            bridge_entries.append({"generated_text_id": text_id, "word_id": target['id'], "occurrences": 1, "is_target": True})
                        supabase_admin.table('generated_text_words').insert(bridge_entries).execute()
                except Exception as fe:
                    logger.warning(f"[Generate] Fallback insert also failed: {fe}")
        
        return {
            "id": text_id,
            "content": text,
            "target_word": target,
            "anchors": anchors,
            "ratio": ratio,
            "validation_passed": passed
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating reading text for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Lesetext konnte nicht generiert werden.")


@router.post("/rate")
@limiter.limit("30/minute")
async def rate_reading(
    request: Request,
    payload: RatingRequest,
    current_user_id: str = Depends(get_current_user)
):
    """
    Submits a user rating for a text and updates mastery scores.
    """
    user_id = current_user_id
    try:
        try:
            supabase_admin.table('text_ratings').insert({
                "user_id": user_id,
                "generated_text_id": payload.generated_text_id,
                "rating": payload.rating
            }).execute()
        except Exception as e:
            logger.warning(f"[Rate] Skipping text_ratings insert for user {user_id}: {e}")
            if user_id != FALLBACK_USER_ID:
                try:
                    supabase_admin.table('text_ratings').insert({
                        "user_id": FALLBACK_USER_ID,
                        "generated_text_id": payload.generated_text_id,
                        "rating": payload.rating
                    }).execute()
                except Exception as fe:
                    logger.warning(f"[Rate] Fallback text_ratings insert failed: {fe}")
        
        words_in_text = supabase_admin.table('generated_text_words') \
            .select('*') \
            .eq('generated_text_id', payload.generated_text_id) \
            .execute()
            
        if not words_in_text.data:
            return {"status": "success", "message": "Bewertung gespeichert."}
            
        diff = payload.difficulty
        rating_val = payload.rating
        
        for record in words_in_text.data:
            word_id = record['word_id']
            is_target = record['is_target']
            
            try:
                state_resp = supabase_admin.table('user_word_state') \
                    .select('*') \
                    .eq('user_id', user_id) \
                    .eq('word_id', word_id) \
                    .execute()
                    
                if state_resp.data:
                    current = state_resp.data[0]
                    mastery = current['mastery_score']
                    exposure = current['exposure_count']
                    
                    delta = 0
                    if rating_val <= 2:
                        delta = -0.1
                    elif rating_val == 3:
                        delta = 0
                    elif rating_val >= 4:
                        if diff in ("Tam kıvam", "Tam kıvamında", "Genau richtig", "Just right", "Perfecto"):
                            delta = 0.2 if is_target else 0.05
                        elif diff in ("Çok kolay", "Zu einfach", "Too easy", "Demasiado fácil"):
                            delta = 0.05 if is_target else 0.01
                        elif diff in ("Çok zor", "Zu schwer", "Too hard", "Demasiado difícil"):
                            delta = -0.05
                        else:
                            delta = 0.1 if is_target else 0.02
                            
                    new_mastery = max(0.0, min(1.0, mastery + delta))
                    
                    supabase_admin.table('user_word_state') \
                        .update({"mastery_score": new_mastery, "exposure_count": exposure + 1, "last_rating": rating_val}) \
                        .eq('user_id', user_id) \
                        .eq('word_id', word_id) \
                        .execute()
                else:
                    initial_mastery = 0.2 if is_target else 0.8
                    supabase_admin.table('user_word_state').insert({
                        "user_id": user_id,
                        "word_id": word_id,
                        "mastery_score": initial_mastery,
                        "exposure_count": 1,
                        "last_rating": rating_val
                    }).execute()
            except Exception as e:
                logger.warning(f"[Rate] Skipping word_state update for user {user_id}: {e}")
                
        return {"status": "success", "message": "Bewertung gespeichert und Wortstatus aktualisiert."}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting rating: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Bewertung konnte nicht gespeichert werden.")


@router.get("/progress/{user_id}")
@limiter.limit("60/minute")
async def get_progress(
    request: Request,
    user_id: str,
    current_user_id: str = Depends(get_current_user)
):
    if user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Zugriff verweigert.")

    try:
        mastered_resp = supabase_admin.table('user_word_state') \
            .select('word_id', count='exact') \
            .eq('user_id', user_id) \
            .gte('mastery_score', 0.8) \
            .execute()
            
        mastered_count = mastered_resp.count if mastered_resp.count is not None else 0
        
        core_resp = supabase_admin.table('words') \
            .select('id', count='exact') \
            .eq('is_core', True) \
            .execute()
            
        core_count = core_resp.count if core_resp.count is not None else 1
        percentage = min(100, int((mastered_count / core_count) * 100))
        
        return {"percentage": percentage, "mastered": mastered_count, "total": core_count}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting progress: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Fortschritt konnte nicht geladen werden.")


@router.get("/export/{user_id}")
@limiter.limit("10/minute")
async def export_digital_brain(
    request: Request,
    user_id: str,
    current_user_id: str = Depends(get_current_user)
):
    if user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Zugriff verweigert.")

    try:
        state_resp = supabase_admin.table('user_word_state') \
            .select('word_id, mastery_score, exposure_count, words(lemma, german_gloss)') \
            .eq('user_id', user_id) \
            .execute()
            
        if not state_resp.data:
            raise HTTPException(status_code=404, detail="Keine Wortdaten für diesen Benutzer gefunden.")
            
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            for record in state_resp.data:
                word_info = record.get('words')
                if not word_info:
                    continue
                    
                lemma = word_info.get('lemma', 'Unknown')
                gloss = word_info.get('german_gloss', '')
                mastery = record.get('mastery_score', 0)
                exposures = record.get('exposure_count', 0)
                
                md_content = f"""# {lemma}

**Gloss**: {gloss}
**Mastery Score**: {mastery:.2f}
**Exposures**: {exposures}

*Generated by LeseFluss (DrainMind Digital Brain)*
"""
                zip_file.writestr(f"{lemma}.md", md_content)
                
        zip_buffer.seek(0)
        return StreamingResponse(
            zip_buffer, 
            media_type="application/zip", 
            headers={'Content-Disposition': f'attachment; filename="brain_{user_id}.zip"'}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting brain: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Export konnte nicht erstellt werden.")


@router.get("/graph/{user_id}")
@limiter.limit("60/minute")
async def get_user_knowledge_graph(
    request: Request,
    user_id: str,
    current_user_id: str = Depends(get_current_user)
):
    if user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Zugriff verweigert.")

    try:
        state_resp = supabase_admin.table('user_word_state') \
            .select('word_id, mastery_score, exposure_count, words(id, lemma, pos, german_gloss, cefr_level)') \
            .eq('user_id', user_id) \
            .execute()
            
        nodes = []
        word_id_set = set()
        
        if state_resp.data:
            for row in state_resp.data:
                w_info = row.get('words')
                if not w_info:
                    continue
                w_id = w_info.get('id')
                word_id_set.add(w_id)
                nodes.append({
                    "id": w_id,
                    "label": w_info.get('lemma', 'Word'),
                    "mastery": row.get('mastery_score', 0.5),
                    "exposures": row.get('exposure_count', 1),
                    "pos": w_info.get('pos', 'NOUN'),
                    "gloss": w_info.get('german_gloss', ''),
                    "level": w_info.get('cefr_level', 'A1')
                })
        else:
            core_resp = supabase_admin.table('words') \
                .select('id, lemma, pos, german_gloss, cefr_level') \
                .eq('is_core', True) \
                .limit(30) \
                .execute()
            for w_info in core_resp.data:
                w_id = w_info['id']
                word_id_set.add(w_id)
                nodes.append({
                    "id": w_id,
                    "label": w_info.get('lemma', 'Word'),
                    "mastery": 0.5,
                    "exposures": 1,
                    "pos": w_info.get('pos', 'NOUN'),
                    "gloss": w_info.get('german_gloss', ''),
                    "level": w_info.get('cefr_level', 'A1')
                })
                
        edges = []
        if word_id_set:
            word_ids_list = list(word_id_set)
            edges_resp = supabase_admin.table('word_edges') \
                .select('source_word_id, target_word_id, relation_type') \
                .in_('source_word_id', word_ids_list) \
                .execute()
                
            if edges_resp.data:
                for edge in edges_resp.data:
                    s_id = edge['source_word_id']
                    t_id = edge['target_word_id']
                    if t_id in word_id_set:
                        edges.append({
                            "source": s_id,
                            "target": t_id,
                            "relation": edge.get('relation_type', 'related')
                        })
                        
        return {
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "total_words": len(nodes),
                "total_connections": len(edges)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching knowledge graph: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Wissensnetzwerk konnte nicht geladen werden.")


def calculate_user_streak(user_id: str):
    ratings_resp = supabase_admin.table('text_ratings') \
        .select('created_at') \
        .eq('user_id', user_id) \
        .order('created_at', desc=True) \
        .execute()
        
    if not ratings_resp.data and user_id != FALLBACK_USER_ID:
        try:
            fallback_resp = supabase_admin.table('text_ratings') \
                .select('created_at') \
                .eq('user_id', FALLBACK_USER_ID) \
                .order('created_at', desc=True) \
                .execute()
            if fallback_resp.data:
                ratings_resp = fallback_resp
        except Exception:
            pass

    if not ratings_resp.data:
        return {
            "current_streak": 0,
            "last_activity_date": None,
            "streak_freeze": True,
            "weekly_history": {"Mo": False, "Di": False, "Mi": False, "Do": False, "Fr": False, "Sa": False, "So": False},
            "daily_goal": {
                "count": 0,
                "target": 10,
                "completed": False
            }
        }
        
    active_dates = set()
    for row in ratings_resp.data:
        dt_str = row['created_at'].split('T')[0]
        active_dates.add(dt_str)
        
    today = date.today()
    today_str = today.isoformat()
    yesterday_str = (today - timedelta(days=1)).isoformat()
    
    current_streak = 0
    check_date = today
    
    if today_str not in active_dates:
        if yesterday_str in active_dates:
            check_date = today - timedelta(days=1)
        else:
            check_date = None
            
    if check_date:
        while check_date.isoformat() in active_dates:
            current_streak += 1
            check_date -= timedelta(days=1)
            
    start_of_week = today - timedelta(days=today.weekday())
    day_keys = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
    weekly_history = {}
    
    for idx, key in enumerate(day_keys):
        day_date = (start_of_week + timedelta(days=idx)).isoformat()
        weekly_history[key] = day_date in active_dates
        
    last_act = max(active_dates) if active_dates else None
    today_count = sum(1 for row in ratings_resp.data if row['created_at'].split('T')[0] == today_str)
    
    return {
        "current_streak": current_streak,
        "last_activity_date": last_act,
        "streak_freeze": True,
        "weekly_history": weekly_history,
        "daily_goal": {
            "count": min(10, today_count),
            "target": 10,
            "completed": today_count >= 10
        }
    }


@router.get("/streak/{user_id}")
@limiter.limit("60/minute")
async def get_user_streak(
    request: Request,
    user_id: str,
    current_user_id: str = Depends(get_current_user)
):
    if user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Zugriff verweigert.")

    try:
        data = calculate_user_streak(user_id)
        return data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching streak: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Streak-Daten konnten nicht geladen werden.")
