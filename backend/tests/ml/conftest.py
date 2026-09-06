"""
Isolated conftest for ML unit tests.
Override the parent conftest's async autouse fixtures to prevent
interference with synchronous-compatible tests.
"""
import os
import pytest

os.environ["TESTING"] = "true"


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    """Set dummy FIRMS key for tests."""
    from app.core.config import settings
    if not settings.firms_map_key:
        monkeypatch.setattr(settings, "firms_map_key", "test_mock_key")


@pytest.fixture(autouse=True)
def cleanup_redis_client_autouse():
    """Override parent conftest async fixture — synchronous no-op for ML unit tests."""
    yield
