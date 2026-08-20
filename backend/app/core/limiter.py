import os
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

def get_rate_limit_key(request: Request) -> str:
    """
    Extracts rate limit identifier:
    - If Authorization header with Bearer token is provided, rate limits per token/user.
    - Otherwise, falls back to client IP address.
    """
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        if token:
            return f"auth:{token}"
    return f"ip:{get_remote_address(request)}"

# Initialize shared Limiter instance with 60/minute default rate limit
limiter = Limiter(
    key_func=get_rate_limit_key,
    default_limits=["60/minute"],
    headers_enabled=False
)
