"""
Unit tests for Authentication and Rate Limiting API endpoints.
Verifies password hashing, user registration, authentication, token session validation, and server-side rate-limit enforcement.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.auth import (
    hash_password,
    verify_password,
    create_session,
    get_session,
    revoke_session,
    check_rate_limit
)
from app.core.redis import redis_manager


def test_password_hashing():
    """Verify PBKDF2-HMAC-SHA256 password hashing and verification."""
    raw_pwd = "SecretPassword123!"
    h = hash_password(raw_pwd)

    assert h != raw_pwd
    assert "$" in h
    assert verify_password(raw_pwd, h) is True
    assert verify_password("WrongPassword", h) is False


def test_session_token_lifecycle():
    """Verify token generation, session retrieval, and token revocation."""
    user_id = "user-12345"
    email = "analyst@thermaltrace.org"
    name = "Test Analyst"

    token = create_session(user_id, email, name)
    assert token.startswith("tw-")

    session = get_session(token)
    assert session is not None
    assert session["user_id"] == user_id
    assert session["email"] == email

    res = revoke_session(token)
    assert res is True
    assert get_session(token) is None


@pytest.mark.anyio
async def test_rate_limiter_enforcement():
    """Verify server-side rate limit checking for anonymous vs authenticated calls."""
    test_id = "test-user-rate-limit-auth-file"

    # Delete previous key if present in Redis
    redis_manager._client = None
    redis_manager._pool = None
    try:
        client = redis_manager.get_client()
        await client.delete(f"thermalwatch:quota:ai:guest:{test_id}")
    except Exception:
        pass

    # Anonymous AI limit test (10 requests max)
    for _ in range(10):
        allowed, msg = await check_rate_limit(test_id, is_ai_endpoint=True, is_authenticated=False)
        assert allowed is True

    # 11th call should exceed quota
    allowed, msg = await check_rate_limit(test_id, is_ai_endpoint=True, is_authenticated=False)
    assert allowed is False
    assert "limit" in msg.lower()


def test_supabase_jwt_verification(monkeypatch):
    """Verify get_session decodes Supabase JWT tokens correctly and rejects invalid ones."""
    import jwt
    import time
    from app.core.config import settings

    # Mock settings.supabase_jwt_secret
    test_secret = "test-super-secret-jwt-key"
    monkeypatch.setattr(settings, "supabase_jwt_secret", test_secret)

    # 1. Valid correctly signed token -> accepted
    valid_payload = {
        "sub": "supa-user-999",
        "email": "supa@thermaltrace.org",
        "user_metadata": {"name": "Supabase Analyst"},
        "aud": "authenticated",
        "exp": int(time.time()) + 3600
    }
    valid_token = jwt.encode(valid_payload, test_secret, algorithm="HS256")
    sess = get_session(valid_token)
    assert sess is not None
    assert sess["user_id"] == "supa-user-999"
    assert sess["email"] == "supa@thermaltrace.org"

    # 2. Invalid signature -> rejected
    invalid_token = jwt.encode(valid_payload, "wrong-secret", algorithm="HS256")
    assert get_session(invalid_token) is None

    # 3. Token with tampered claims -> rejected
    # (By tampering with claims, the signature becomes invalid)
    parts = valid_token.split(".")
    import base64
    import json
    tampered_payload = dict(valid_payload)
    tampered_payload["role"] = "superadmin"
    encoded_tampered = base64.urlsafe_b64encode(json.dumps(tampered_payload).encode()).decode().rstrip("=")
    tampered_token = f"{parts[0]}.{encoded_tampered}.{parts[2]}"
    assert get_session(tampered_token) is None

    # 4. Expired token -> rejected
    expired_payload = dict(valid_payload)
    expired_payload["exp"] = int(time.time()) - 3600
    expired_token = jwt.encode(expired_payload, test_secret, algorithm="HS256")
    assert get_session(expired_token) is None

    # 5. Missing/invalid authentication -> rejected
    assert get_session("") is None
    assert get_session("Bearer ") is None
    assert get_session("not-a-token") is None
