"""
Authentication & Rate Limiting Service for ThermalTrace.
Provides PBKDF2-HMAC-SHA256 password hashing, token session management, and server-side API rate-limiting / quota controls.
"""
import asyncio
import hashlib
import hmac
import logging
import secrets
import time
from typing import Dict, Optional, Tuple, Any

logger = logging.getLogger(__name__)

# In-memory token store: token -> {user_id, email, name, created_at}
ACTIVE_SESSIONS: Dict[str, Dict[str, Any]] = {}

# Server-side Rate Limiter tracking: key (ip_or_user_id) -> list of timestamp floats
RATE_LIMIT_TRACKER: Dict[str, list] = {}

# Rate limit configs (requests per minute window)
ANONYMOUS_RATE_LIMIT = 30       # 30 requests / minute for unauthenticated requests
AUTHENTICATED_RATE_LIMIT = 120   # 120 requests / minute for logged-in users
ANONYMOUS_AI_QUOTA = 10         # 10 AI chat queries / hour for anonymous
AUTHENTICATED_AI_QUOTA = 100    # 100 AI chat queries / hour for authenticated users


def hash_password(password: str) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with 16-byte random salt."""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    )
    return f"{salt}${key.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify password against stored salt$hash string."""
    try:
        salt, key_hex = stored_hash.split('$')
        computed_key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        )
        return hmac.compare_digest(computed_key.hex(), key_hex)
    except Exception:
        return False


def create_session(user_id: str, email: str, name: str) -> str:
    """Generate a secure bearer token and store active session payload."""
    token = f"tw-{secrets.token_urlsafe(32)}"
    ACTIVE_SESSIONS[token] = {
        "user_id": user_id,
        "email": email,
        "name": name,
        "created_at": time.time()
    }
    return token


import jwt


def get_session(token: str) -> Optional[Dict[str, Any]]:
    """Retrieve session dictionary if token is valid (supports internal sessions and Supabase JWTs)."""
    if not token:
        return None
    clean_token = token.replace("Bearer ", "").strip()

    # 1. Check internal active sessions
    if clean_token in ACTIVE_SESSIONS:
        return ACTIVE_SESSIONS[clean_token]

    # 2. Verify Supabase JWT token signature / claims
    from app.core.config import settings
    try:
        if not settings.supabase_jwt_secret:
            logger.warning("SUPABASE_JWT_SECRET is not configured.")
            return None

        decoded = jwt.decode(
            clean_token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated"
        )
        user_id = decoded.get("sub") or decoded.get("user_id") or "supa-user"
        email = decoded.get("email") or "analyst@thermaltrace.org"
        user_metadata = decoded.get("user_metadata", {})
        name = user_metadata.get("name") or email.split("@")[0].capitalize()
        return {
            "user_id": user_id,
            "email": email,
            "name": name,
            "role": decoded.get("role", "authenticated")
        }
    except Exception:
        pass

    return None


def revoke_session(token: str) -> bool:
    """Revoke session token on logout."""
    if not token:
        return False
    clean_token = token.replace("Bearer ", "").strip()
    if clean_token in ACTIVE_SESSIONS:
        del ACTIVE_SESSIONS[clean_token]
        return True
    return False


from app.core.redis import redis_manager


async def check_rate_limit(identifier: str, is_ai_endpoint: bool = False, is_authenticated: bool = False) -> Tuple[bool, str]:
    """
    Check if request complies with Redis server-side rate limits and atomic AI quotas.
    Returns (allowed: bool, message: str).
    Falls back gracefully to in-memory tracker if Redis is temporarily unreachable.
    """
    if is_ai_endpoint:
        max_quota = AUTHENTICATED_AI_QUOTA if is_authenticated else ANONYMOUS_AI_QUOTA
        try:
            allowed, count, limit = await redis_manager.check_ai_quota_atomic(
                identifier=identifier,
                is_authenticated=is_authenticated,
                limit_override=max_quota,
                period_seconds=3600,
            )
            if not allowed:
                return False, f"AI usage limit reached ({max_quota} requests/hour). Please try again later."
            return True, "OK"
        except Exception as e:
            logger.warning("Redis AI quota check error for %s (using fallback): %s", identifier, e)

    # General API Rate Limiting check
    max_requests = AUTHENTICATED_RATE_LIMIT if is_authenticated else ANONYMOUS_RATE_LIMIT
    try:
        allowed, count, ttl = await redis_manager.check_rate_limit(
            key=f"{'user' if is_authenticated else 'guest'}:{identifier}",
            limit=max_requests,
            window_seconds=60,
        )
        if not allowed:
            return False, f"Rate limit exceeded ({max_requests} requests/minute). Please wait before retrying."
        return True, "OK"
    except Exception as e:
        logger.warning("Redis rate limit check error for %s (using in-memory fallback): %s", identifier, e)

    # In-memory conservative fallback when Redis is unreachable
    now = time.time()
    window_seconds = 3600 if is_ai_endpoint else 60
    max_requests = (
        (AUTHENTICATED_AI_QUOTA if is_authenticated else ANONYMOUS_AI_QUOTA)
        if is_ai_endpoint
        else (AUTHENTICATED_RATE_LIMIT if is_authenticated else ANONYMOUS_RATE_LIMIT)
    )

    tracker_key = f"{'ai' if is_ai_endpoint else 'api'}:{identifier}"
    timestamps = RATE_LIMIT_TRACKER.get(tracker_key, [])
    timestamps = [t for t in timestamps if now - t < window_seconds]

    if len(timestamps) >= max_requests:
        limit_desc = f"{max_requests} requests per {'hour' if is_ai_endpoint else 'minute'}"
        return False, f"Rate limit exceeded ({limit_desc}). Please try again later."

    timestamps.append(now)
    RATE_LIMIT_TRACKER[tracker_key] = timestamps
    return True, "OK"
