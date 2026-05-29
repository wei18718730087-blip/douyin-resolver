"""Phase 0 unit tests for core modules."""

import pytest

from packages.core.input_parser import (
    extract_aweme_id_from_url,
    extract_urls,
    is_douyin_url,
    parse_input,
)
from packages.core.errors import ErrorCode, ResolverError


class TestExtractUrls:
    """Test URL extraction from text."""

    def test_single_url(self):
        urls = extract_urls("https://v.douyin.com/abc123/")
        assert urls == ["https://v.douyin.com/abc123/"]

    def test_url_in_text(self):
        text = "在抖音看到了好视频 https://v.douyin.com/abc123/ 快来看"
        urls = extract_urls(text)
        assert len(urls) == 1
        assert "v.douyin.com" in urls[0]

    def test_multiple_urls(self):
        text = "https://a.com https://b.com"
        urls = extract_urls(text)
        assert len(urls) == 2

    def test_no_urls(self):
        urls = extract_urls("没有链接")
        assert urls == []

    def test_empty_text(self):
        urls = extract_urls("")
        assert urls == []


class TestIsDouyinUrl:
    """Test Douyin URL detection."""

    def test_short_link(self):
        assert is_douyin_url("https://v.douyin.com/abc123/") is True

    def test_long_link(self):
        assert is_douyin_url("https://www.douyin.com/video/1234567890") is True

    def test_discover_link(self):
        assert is_douyin_url("https://www.douyin.com/discover?modal_id=1234567890") is True

    def test_non_douyin(self):
        assert is_douyin_url("https://www.bilibili.com/video/BV123") is False

    def test_invalid_url(self):
        assert is_douyin_url("not a url") is False


class TestExtractAwemeId:
    """Test aweme_id extraction from URLs."""

    def test_video_url(self):
        aweme_id = extract_aweme_id_from_url("https://www.douyin.com/video/7123456789012345678")
        assert aweme_id == "7123456789012345678"

    def test_discover_url(self):
        aweme_id = extract_aweme_id_from_url("https://www.douyin.com/discover?modal_id=7123456789012345678")
        assert aweme_id == "7123456789012345678"

    def test_note_url(self):
        aweme_id = extract_aweme_id_from_url("https://www.douyin.com/note/7123456789012345678")
        assert aweme_id == "7123456789012345678"

    def test_short_link_returns_none(self):
        aweme_id = extract_aweme_id_from_url("https://v.douyin.com/abc123/")
        assert aweme_id is None

    def test_no_id(self):
        aweme_id = extract_aweme_id_from_url("https://www.douyin.com/")
        assert aweme_id is None


class TestParseInput:
    """Test input parsing."""

    def test_direct_url(self):
        url = parse_input("https://v.douyin.com/abc123/")
        assert "v.douyin.com" in url

    def test_url_in_text(self):
        url = parse_input("在抖音搜xxx https://v.douyin.com/abc123/ 看看")
        assert "v.douyin.com" in url

    def test_empty_input(self):
        with pytest.raises(ResolverError) as exc_info:
            parse_input("")
        assert exc_info.value.code == ErrorCode.INVALID_INPUT

    def test_no_url(self):
        with pytest.raises(ResolverError) as exc_info:
            parse_input("没有链接的文本")
        assert exc_info.value.code == ErrorCode.INVALID_INPUT

    def test_non_douyin_url(self):
        with pytest.raises(ResolverError) as exc_info:
            parse_input("https://www.bilibili.com/video/BV123")
        assert exc_info.value.code == ErrorCode.UNSUPPORTED_PLATFORM


class TestErrorCodes:
    """Test error code system."""

    def test_resolver_error_to_dict(self):
        err = ResolverError(
            code=ErrorCode.RATE_LIMITED,
            message="被限流",
            detail="test detail",
        )
        d = err.to_dict()
        assert d["code"] == "RATE_LIMITED"
        assert d["message"] == "请稍后再试"
        assert d["detail"] == "test detail"

    def test_user_message_fallback(self):
        err = ResolverError(code=ErrorCode.INVALID_INPUT, message="custom")
        assert err.user_message == "请粘贴有效的抖音分享链接"
