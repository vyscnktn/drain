import os
import logging
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from app.core.limiter import limiter
from app.api.endpoints import reader, onboarding, pipeline

logger = logging.getLogger(__name__)

# Environment detection for production security (Görev 1.3)
env_mode = os.getenv("ENVIRONMENT", os.getenv("ENV", "development")).lower()
is_production = env_mode in ("production", "prod")

app = FastAPI(
    title="Drain Backend Engine",
    description="FastAPI Backend for the Drain German Learning Platform",
    version="0.1.0",
    docs_url=None if is_production else "/docs",
    redoc_url=None if is_production else "/redoc",
    openapi_url=None if is_production else "/openapi.json"
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS whitelist from FRONTEND_ORIGIN env var
frontend_origin_env = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000,http://127.0.0.1:3000,https://drain-umber-ten.vercel.app")
allowed_origins = [origin.strip() for origin in frontend_origin_env.split(",") if origin.strip()]

for default_origin in [
    "https://drain-umber-ten.vercel.app",
    "https://ypqqoefegnshavxsznmq.supabase.co"
]:
    if default_origin not in allowed_origins:
        allowed_origins.append(default_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"^https:\/\/.*\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Exception Handler (Rule 6: Prevent internal detail/stack trace leakage)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"[GlobalError] Internal server error on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Ein interner Fehler ist aufgetreten. Bitte versuchen Sie es später erneut."}
    )

app.include_router(reader.router, prefix="/api/reader", tags=["reader"])
app.include_router(onboarding.router, prefix="/api/onboarding", tags=["onboarding"])
app.include_router(pipeline.router, prefix="/api/pipeline", tags=["pipeline"])

@app.get("/health")
def health_check():
    return {"status": "ok"}
