"""Phase 4 regression tests: cache, metrics, API integration."""

import json
import time
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from packages.core.cache import ResolveCache
from packages.core.schemas import ResolveResult, Author, Media
from packages.core.errors import ResolverError, ErrorCode


# ──────────────────────────────────────────────────────────────────
# Cache Tests
# ──────────────────────────────────────────────────────────────────


class TestResolveCache:
    """Test SQLite cache layer."""

    @pytest.fixture
    def cache(self, tmp_path):
        """Create a temporary cache for testing."""
        db_path = tmp_path / "test_cache.db"
        c = ResolveCache(db_path=db_path, ttl=60)
        yield c
        c.close()

    @pytest.fixture
    def sample_result(self):
        """Sample resolve result."""
        return ResolveResult(
            ok=True,
            platform="douyin",
            input_url="https://v.douyin.com/test/",
            aweme_id="123456789",
            title="Test Video",
            author=Author(nickname="TestUser", sec_uid="sec123"),
            media=Media(
                type="video",
                downloadable=True,
                url="https://example.com/video.mp4",
                mime="video/mp4",
            ),
        )

    def test_set_and_get(self, cache, sample_result):
        cache.set("123456789", sample_result)
        result = cache.get("123456789")
        assert result is not None
        assert result.aweme_id == "123456789"
        assert result.title == "Test Video"
        assert result.author.nickname == "TestUser"

    def test_get_missing(self, cache):
        result = cache.get("nonexistent")
        assert result is None

    def test_expiration(self, tmp_path, sample_result):
        db_path = tmp_path / "expire_test.db"
        cache = ResolveCache(db_path=db_path, ttl=0)  # Immediate expiration
        cache.set("123456789", sample_result)
        time.sleep(0.1)
        result = cache.get("123456789")
        assert result is None
        cache.close()

    def test_delete(self, cache, sample_result):
        cache.set("123456789", sample_result)
        cache.delete("123456789")
        assert cache.get("123456789") is None

    def test_clear_expired(self, tmp_path, sample_result):
        db_path = tmp_path / "clear_test.db"
        cache = ResolveCache(db_path=db_path, ttl=0)
        cache.set("aaa", sample_result)
        cache.set("bbb", sample_result)
        time.sleep(0.1)
        cleared = cache.clear_expired()
        assert cleared == 2
        cache.close()

    def test_stats(self, cache, sample_result):
        cache.set("123456789", sample_result)
        stats = cache.stats()
        assert stats["total_entries"] == 1
        assert stats["active_entries"] == 1
        assert stats["expired_entries"] == 0
        assert stats["ttl_seconds"] == 60

    def test_overwrite(self, cache, sample_result):
        cache.set("123456789", sample_result)
        updated = sample_result.model_copy(update={"title": "Updated Title"})
        cache.set("123456789", updated)
        result = cache.get("123456789")
        assert result.title == "Updated Title"


# ──────────────────────────────────────────────────────────────────
# Metrics Tests
# ──────────────────────────────────────────────────────────────────


class TestMetrics:
    """Test metrics recording."""

    def test_record_request(self):
        import apps.api.routes.metrics as metrics_mod

        initial = metrics_mod._total_requests
        metrics_mod.record_request("/test_metric", is_error=False)
        assert metrics_mod._total_requests == initial + 1

    def test_record_error(self):
        import apps.api.routes.metrics as metrics_mod

        initial = metrics_mod._total_errors
        metrics_mod.record_request("/test_err", is_error=True)
        assert metrics_mod._total_errors == initial + 1


# ──────────────────────────────────────────────────────────────────
# Schema Tests
# ──────────────────────────────────────────────────────────────────


class TestSchemas:
    """Test Pydantic schemas serialization."""

    def test_resolve_result_json_roundtrip(self):
        result = ResolveResult(
            ok=True,
            platform="douyin",
            input_url="https://v.douyin.com/test/",
            aweme_id="123",
            title="Test",
        )
        json_str = result.model_dump_json()
        data = json.loads(json_str)
        assert data["ok"] is True
        assert data["platform"] == "douyin"
        assert data["aweme_id"] == "123"

    def test_health_response(self):
        from packages.core.schemas import HealthResponse

        resp = HealthResponse(ok=True, version="0.1.0")
        assert resp.ok is True
        assert resp.version == "0.1.0"

    def test_resolve_request_defaults(self):
        from packages.core.schemas import ResolveRequest

        req = ResolveRequest(url="https://v.douyin.com/test/")
        assert req.include_comments is True
        assert req.comment_limit == 50
        assert req.download is False


# ──────────────────────────────────────────────────────────────────
# Error Handler Tests
# ──────────────────────────────────────────────────────────────────


class TestErrorHandler:
    """Test error code mappings."""

    def test_all_error_codes_have_user_message(self):
        for code in ErrorCode:
            err = ResolverError(code=code, message="test")
            assert err.user_message  # Should not be empty

    def test_error_to_dict_structure(self):
        err = ResolverError(
            code=ErrorCode.UPSTREAM_CHANGED,
            message="page structure changed",
            detail="regex mismatch",
        )
        d = err.to_dict()
        assert "code" in d
        assert "message" in d
        assert "detail" in d
        assert d["code"] == "UPSTREAM_CHANGED"
