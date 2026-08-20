from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
import logging
from app.pipeline.lemmatizer import run_lemmatization_pipeline
from app.core.limiter import limiter

router = APIRouter()
logger = logging.getLogger(__name__)

class IngestTextRequest(BaseModel):
    text: str
    domain: str = "IT"

@router.post("/ingest")
@limiter.limit("10/minute")
async def ingest_custom_text(request: Request, payload: IngestTextRequest):
    """
    Lemmatizes and enriches a custom German text payload, ingesting new words into Supabase.
    """
    try:
        if not payload.text.strip():
            raise HTTPException(status_code=400, detail="Text darf nicht leer sein.")
            
        result = run_lemmatization_pipeline(payload.text, payload.domain, is_file=False)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in pipeline ingest API: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Text-Ingestion fehlgeschlagen.")
