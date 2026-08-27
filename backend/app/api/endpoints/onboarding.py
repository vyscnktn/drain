from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
import time
import logging

from app.services.krashen_engine import select_reading_words
from app.services.llm_engine import validate_and_generate
from app.core.supabase_client import supabase_admin
from app.core.limiter import limiter

router = APIRouter()
logger = logging.getLogger(__name__)

class OnboardingStartRequest(BaseModel):
    user_id: str
    current_level: Literal['A1', 'A2', 'B1', 'B2', 'C1']
    target_level: Literal['A1', 'A2', 'B1', 'B2', 'C1']
    domain: Literal['IT', 'HEALTH', 'ACADEMIC']
    subdomain: Optional[str] = None

class RatingItem(BaseModel):
    text_id: int
    rating: int = Field(..., ge=1, le=5)
    difficulty: str  # "Zu einfach", "Genau richtig", "Zu schwer"

class OnboardingSubmitRequest(BaseModel):
    user_id: str
    current_level: Literal['A1', 'A2', 'B1', 'B2', 'C1']
    target_level: Literal['A1', 'A2', 'B1', 'B2', 'C1']
    domain: Optional[Literal['IT', 'HEALTH', 'ACADEMIC']] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    ratings: List[RatingItem]

LEVEL_ORDER = ["A1", "A2", "B1", "B2", "C1"]

def get_calibration_levels(current_level: str) -> List[str]:
    clean = current_level.strip().upper()
    if clean not in LEVEL_ORDER:
        clean = "A2"
        
    idx = LEVEL_ORDER.index(clean)
    
    lower_idx = max(0, idx - 1)
    lower_level = LEVEL_ORDER[lower_idx]
    curr_level = LEVEL_ORDER[idx]
    upper_idx = min(len(LEVEL_ORDER) - 1, idx + 1)
    upper_level = LEVEL_ORDER[upper_idx]
    
    return [lower_level, curr_level, upper_level]


@router.post("/start")
@limiter.limit("15/minute")
async def start_onboarding(request: Request, payload: OnboardingStartRequest):
    """
    Generates 3 calibration texts based on user's entered CURRENT level and selected domain:
    - Text 1: Level - 1 (min A1)
    - Text 2: Current Level
    - Text 3: Level + 1 (max C1)
    """
    try:
        domain_tag = payload.domain

        logger.debug(f"Onboarding generation using domain: {domain_tag}, level range: {payload.current_level} → {payload.target_level}")
        calibration_texts = []
        levels = get_calibration_levels(payload.current_level)

        core_resp = supabase_admin.table('words').select('lemma').eq('is_core', True).execute()
        all_known_lemmas = [c['lemma'] for c in core_resp.data] if core_resp.data else []

        for idx, lvl in enumerate(levels):
            if idx > 0:
                time.sleep(1.0)  # Brief pause between sequential LLM calls to prevent rate limiting
            anchors, targets = select_reading_words(
                payload.user_id,
                domain=domain_tag,
                subdomain=payload.subdomain,
            )
            anchor_lemmas = [a['lemma'] for a in anchors] if anchors else []
            target = targets[0] if targets else (anchors[0] if anchors else {"id": 1, "lemma": "lernen"})
            
            text, passed, ratio = validate_and_generate(
                anchor_lemmas=anchor_lemmas,
                target_lemma=target,
                all_known_lemmas=all_known_lemmas,
                domain=domain_tag,
                level=lvl,
                max_retries=1
            )
            calibration_texts.append({
                "id": idx + 1,
                "level": lvl,
                "content": text,
                "target_word": target,
                "anchors": anchors
            })
            
        return {"calibration_texts": calibration_texts}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in onboarding start: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Fehler beim Starten der Kalibrierung.")


@router.post("/submit")
@limiter.limit("15/minute")
async def submit_onboarding(request: Request, payload: OnboardingSubmitRequest):
    """
    Calculates starting baseline mastery band based on the 3 calibration ratings.
    Ensures complete user profile exists in profiles table via service role.
    """
    try:
        if not payload.ratings:
            raise HTTPException(status_code=400, detail="Bewertungen erforderlich.")

        # Ensure user profile row exists in profiles table
        try:
            user_email = payload.email
            user_name = payload.full_name
            
            # Fetch from auth admin if not explicitly passed
            if not user_email or not user_name:
                try:
                    u_info = supabase_admin.auth.admin.get_user_by_id(payload.user_id)
                    if u_info and u_info.user:
                        if not user_email:
                            user_email = u_info.user.email
                        if not user_name and u_info.user.user_metadata:
                            user_name = u_info.user.user_metadata.get("full_name")
                except Exception as ae:
                    logger.debug(f"[Onboarding] Auth admin info fetch notice: {ae}")

            domain_val = payload.domain if payload.domain else "HEALTH"
            profile_payload = {
                "id": payload.user_id,
                "target_domain": domain_val,
                "domain": domain_val,
                "target_level": payload.target_level,
                "current_level": payload.current_level
            }
            if user_email:
                profile_payload["email"] = user_email
            if user_name:
                profile_payload["full_name"] = user_name

            supabase_admin.table('profiles').upsert(profile_payload, on_conflict="id").execute()
            logger.info(f"[Onboarding] Successfully upserted profile for user {payload.user_id}")
        except Exception as pe:
            logger.warning(f"[Onboarding] Profile ensure warning for user {payload.user_id}: {pe}")
            
        avg_rating = sum(r.rating for r in payload.ratings) / len(payload.ratings)
        too_easy_count = sum(1 for r in payload.ratings if r.difficulty in ("Zu einfach", "Çok kolay"))
        too_hard_count = sum(1 for r in payload.ratings if r.difficulty in ("Zu schwer", "Çok zor"))
        
        if avg_rating >= 4 and too_easy_count >= 2:
            calibrated_mastery = 0.75
        elif avg_rating <= 2.5 or too_hard_count >= 2:
            calibrated_mastery = 0.40
        elif avg_rating >= 3.5:
            calibrated_mastery = 0.65
        else:
            calibrated_mastery = 0.50
            
        core_resp = supabase_admin.table('words').select('id').eq('is_core', True).limit(30).execute()
        core_ids = [c['id'] for c in core_resp.data]
        
        for w_id in core_ids:
            try:
                supabase_admin.table('user_word_state').upsert({
                    "user_id": payload.user_id,
                    "word_id": w_id,
                    "mastery_score": calibrated_mastery,
                    "exposure_count": 1,
                    "last_rating": int(avg_rating)
                }).execute()
            except Exception as e:
                logger.warning(f"[Onboarding] Skipping word_state upsert for user {payload.user_id}: {e}")
            
        return {
            "status": "success",
            "calibrated_mastery": calibrated_mastery,
            "current_level": payload.current_level,
            "target_level": payload.target_level,
            "message": "Kalibrierung erfolgreich abgeschlossen."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in onboarding submit: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Kalibrierung konnte nicht gespeichert werden.")
