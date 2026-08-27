from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any
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

# In-memory storage for fast calibration text staging across steps
_CALIBRATION_CACHE: Dict[str, Dict[str, Any]] = {}


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


def _generate_single_calibration_text(
    user_id: str,
    domain_tag: str,
    subdomain: Optional[str],
    level: str,
    step: int
) -> Dict[str, Any]:
    """Generates a single calibration text and records it in cache & database."""
    try:
        core_resp = supabase_admin.table('words').select('lemma').eq('is_core', True).execute()
        all_known_lemmas = [c['lemma'] for c in core_resp.data] if core_resp.data else []

        anchors, targets = select_reading_words(
            user_id,
            domain=domain_tag,
            subdomain=subdomain,
        )
        anchor_lemmas = [a['lemma'] for a in anchors] if anchors else []
        target = targets[0] if targets else (anchors[0] if anchors else {"id": 1, "lemma": "lernen"})

        text, passed, ratio = validate_and_generate(
            anchor_lemmas=anchor_lemmas,
            target_lemma=target,
            all_known_lemmas=all_known_lemmas,
            domain=domain_tag,
            level=level,
            max_retries=1
        )

        text_id = step
        try:
            anchor_id = anchors[0]['id'] if anchors else 1
            insert_resp = supabase_admin.table('generated_texts').insert({
                "user_id": user_id,
                "domain": domain_tag,
                "level": level,
                "anchor_word_id": anchor_id,
                "content": text,
                "unknown_ratio": ratio,
                "validation_passed": passed
            }).execute()
            if insert_resp.data:
                text_id = insert_resp.data[0]['id']
        except Exception as dbe:
            logger.warning(f"[Onboarding] Could not insert calibration text into generated_texts: {dbe}")

        text_item = {
            "id": text_id,
            "step": step,
            "level": level,
            "content": text,
            "target_word": target,
            "anchors": anchors,
            "status": "ready"
        }

        if user_id not in _CALIBRATION_CACHE:
            _CALIBRATION_CACHE[user_id] = {"texts": {}}
        if "texts" not in _CALIBRATION_CACHE[user_id]:
            _CALIBRATION_CACHE[user_id]["texts"] = {}

        _CALIBRATION_CACHE[user_id]["texts"][step] = text_item
        logger.info(f"[Onboarding] Pre-generated step {step} for user {user_id} (Level: {level}) ✓")
        return text_item

    except Exception as e:
        logger.error(f"[Onboarding] Failed generating step {step} for user {user_id}: {e}", exc_info=True)
        if user_id in _CALIBRATION_CACHE and "texts" in _CALIBRATION_CACHE[user_id]:
            _CALIBRATION_CACHE[user_id]["texts"][step] = {
                "id": step,
                "step": step,
                "level": level,
                "status": "error",
                "error": str(e)
            }
        raise


@router.post("/start")
@limiter.limit("15/minute")
async def start_onboarding(request: Request, payload: OnboardingStartRequest, background_tasks: BackgroundTasks):
    """
    Produces ONLY the first calibration text (Step 1) immediately and schedules
    the generation of the subsequent text (Step 2) in the background.
    """
    try:
        domain_tag = payload.domain
        levels = get_calibration_levels(payload.current_level)

        logger.debug(f"[Onboarding] Starting calibration for {payload.user_id}, level range: {levels}")

        _CALIBRATION_CACHE[payload.user_id] = {
            "session": {
                "domain": domain_tag,
                "subdomain": payload.subdomain,
                "current_level": payload.current_level,
                "target_level": payload.target_level,
                "levels": levels
            },
            "texts": {
                2: {"status": "pending"},
                3: {"status": "pending"}
            }
        }

        # 1. Generate ONLY the first text synchronously
        text_1 = _generate_single_calibration_text(
            user_id=payload.user_id,
            domain_tag=domain_tag,
            subdomain=payload.subdomain,
            level=levels[0],
            step=1
        )

        # 2. Schedule Text 2 generation in background
        background_tasks.add_task(
            _generate_single_calibration_text,
            payload.user_id,
            domain_tag,
            payload.subdomain,
            levels[1],
            2
        )

        return {
            "calibration_texts": [text_1],
            "total_steps": 3,
            "current_step": 1
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in onboarding start: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Fehler beim Starten der Kalibrierung.")


@router.get("/text/{user_id}/{step}")
async def get_calibration_text(user_id: str, step: int):
    """
    Lightweight polling endpoint to retrieve a calibration text when ready.
    """
    if step not in (1, 2, 3):
        raise HTTPException(status_code=400, detail="Ungültiger Kalibrierungsschritt.")

    session_data = _CALIBRATION_CACHE.get(user_id, {})
    text_info = session_data.get("texts", {}).get(step)

    if text_info and text_info.get("status") == "ready":
        return {"ready": True, "text": text_info}

    if text_info and text_info.get("status") == "error":
        session_info = session_data.get("session", {})
        levels = session_info.get("levels", ["A1", "A2", "B1"])
        domain_tag = session_info.get("domain", "HEALTH")
        subdomain = session_info.get("subdomain")
        try:
            fresh = _generate_single_calibration_text(
                user_id,
                domain_tag,
                subdomain,
                levels[step - 1],
                step
            )
            return {"ready": True, "text": fresh}
        except Exception:
            raise HTTPException(status_code=503, detail="Text konnte nicht vorbereitet werden.")

    return {"ready": False, "status": "preparing", "message": "Text wird vorbereitet..."}


@router.post("/submit")
@limiter.limit("30/minute")
async def submit_onboarding(request: Request, payload: OnboardingSubmitRequest, background_tasks: BackgroundTasks):
    """
    Handles step ratings:
    - Step 1 rating: Queues Text 3 generation in background and returns Text 2 if ready.
    - Step 2 rating: Returns Text 3 if ready.
    - Step 3 rating: Completes user profile registration & calculates baseline mastery.
    """
    try:
        num_ratings = len(payload.ratings)
        if num_ratings == 0:
            raise HTTPException(status_code=400, detail="Bewertungen erforderlich.")

        session_data = _CALIBRATION_CACHE.get(payload.user_id, {})
        session_info = session_data.get("session", {})
        levels = session_info.get("levels") or get_calibration_levels(payload.current_level)
        domain_tag = payload.domain or session_info.get("domain") or "HEALTH"
        subdomain = session_info.get("subdomain")

        # ── Intermediate Rating (Step 1 or 2 submitted) ───────────────────────
        if num_ratings < 3:
            next_step = num_ratings + 1

            # If transitioning to step 2, trigger background generation of step 3
            if next_step == 2:
                background_tasks.add_task(
                    _generate_single_calibration_text,
                    payload.user_id,
                    domain_tag,
                    subdomain,
                    levels[2],
                    3
                )

            # Check if next step text is ready
            cached_text = session_data.get("texts", {}).get(next_step)
            if cached_text and cached_text.get("status") == "ready":
                return {
                    "status": "next",
                    "ready": True,
                    "step": next_step,
                    "text": cached_text
                }
            elif cached_text and cached_text.get("status") == "error":
                try:
                    fresh = _generate_single_calibration_text(
                        payload.user_id,
                        domain_tag,
                        subdomain,
                        levels[next_step - 1],
                        next_step
                    )
                    return {
                        "status": "next",
                        "ready": True,
                        "step": next_step,
                        "text": fresh
                    }
                except Exception:
                    raise HTTPException(status_code=503, detail="Text konnte nicht vorbereitet werden.")
            else:
                return {
                    "status": "pending",
                    "ready": False,
                    "step": next_step,
                    "message": "Text wird vorbereitet..."
                }

        # ── Final Rating (Step 3 submitted) -> Complete Profile Registration ──
        try:
            user_email = payload.email
            user_name = payload.full_name

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
        too_easy_count = sum(1 for r in payload.ratings if r.difficulty in ("Zu einfach", "Çok kolay", "Demasiado fácil", "Too easy"))
        too_hard_count = sum(1 for r in payload.ratings if r.difficulty in ("Zu schwer", "Çok zor", "Demasiado difícil", "Too hard"))

        if avg_rating >= 4 and too_easy_count >= 2:
            calibrated_mastery = 0.75
        elif avg_rating <= 2.5 or too_hard_count >= 2:
            calibrated_mastery = 0.40
        elif avg_rating >= 3.5:
            calibrated_mastery = 0.65
        else:
            calibrated_mastery = 0.50

        core_resp = supabase_admin.table('words').select('id').eq('is_core', True).limit(30).execute()
        core_ids = [c['id'] for c in core_resp.data] if core_resp.data else []

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

        # Clean up cache
        _CALIBRATION_CACHE.pop(payload.user_id, None)

        return {
            "status": "success",
            "step": "done",
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
