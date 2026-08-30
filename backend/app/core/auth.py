import os
import logging
from typing import Optional
import jwt
from jwt import PyJWKClient, PyJWKClientError, InvalidTokenError
from fastapi import Security, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.supabase_client import supabase_admin

logger = logging.getLogger(__name__)
security_scheme = HTTPBearer(auto_error=False)

FALLBACK_USER_ID = "00000000-0000-0000-0000-000000000000"

SUPABASE_JWKS_URL = os.getenv(
    "SUPABASE_JWKS_URL",
    f"{os.getenv('SUPABASE_URL', 'https://ypqqoefegnshavxsznmq.supabase.co').rstrip('/')}/auth/v1/.well-known/jwks.json"
)

# PyJWKClient caches signing keys locally with automatic refresh
_jwks_client: Optional[PyJWKClient] = None
if SUPABASE_JWKS_URL and SUPABASE_JWKS_URL.startswith("http"):
    try:
        _jwks_client = PyJWKClient(SUPABASE_JWKS_URL)
    except Exception as e:
        logger.warning(f"[Auth] Could not initialize PyJWKClient for {SUPABASE_JWKS_URL}: {e}")

def verify_jwt_signature(token: str) -> str:
    """
    Cryptographically verifies the Supabase Auth JWT signature and claims.
    Uses JWKS public keys (ES256 / RS256) and Supabase Auth API verification.
    Returns authenticated user UUID string (sub).
    Raises HTTPException 401 Unauthorized if signature verification fails.
    """
    # 1. Fast local cryptographic verification via project JWKS public key
    if _jwks_client:
        try:
            signing_key = _jwks_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["ES256", "RS256", "HS256"],
                audience="authenticated",
                options={"verify_signature": True, "verify_aud": True, "verify_exp": True}
            )
            user_id = payload.get("sub")
            if user_id:
                return user_id
        except (PyJWKClientError, InvalidTokenError) as jwt_err:
            logger.debug(f"[Auth] Local JWKS verification rejected token: {jwt_err}")
        except Exception as e:
            logger.debug(f"[Auth] JWKS verification error: {e}")

    # 2. Direct Supabase Auth API verification
    try:
        user_response = supabase_admin.auth.get_user(token)
        if user_response and user_response.user and user_response.user.id:
            return user_response.user.id
    except Exception as sb_err:
        logger.warning(f"[Auth] Supabase Auth verification rejected token: {sb_err}")

    # If verification fails on both layers, strictly reject with 401
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Ungültiges oder abgelaufenes Authentifizierungs-Token.",
        headers={"WWW-Authenticate": "Bearer"}
    )

def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security_scheme)) -> str:
    """
    FastAPI dependency for protected routes.
    Strictly validates Authorization: Bearer <token> against Supabase JWKS/Auth.
    Returns user_id string if valid; raises HTTP 401 Unauthorized otherwise.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentifizierung erforderlich. Bitte übergeben Sie ein gültiges Bearer-Token.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return verify_jwt_signature(credentials.credentials)
