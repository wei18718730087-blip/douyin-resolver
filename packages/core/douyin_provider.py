"""Fetch Douyin work metadata and media info using mobile share page."""

from __future__ import annotations

import json
import re
from typing import Optional

import httpx

from packages.core.errors import ErrorCode, ResolverError
from packages.core.schemas import Author, Media, ResolveResult

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/16.6 Mobile/15E148 Safari/604.1"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

# Pattern for embedded data in mobile share page
ROUTER_DATA_RE = re.compile(
    r"window\._ROUTER_DATA\s*=\s*(\{.*?\})\s*</script>",
    re.DOTALL,
)


def _find_video_item(data: dict) -> Optional[dict]:
    """Find video item in _ROUTER_DATA structure."""
    loader_data = data.get("loaderData", {})
    for key, value in loader_data.items():
        if isinstance(value, dict) and "videoInfoRes" in value:
            video_info = value["videoInfoRes"]
            item_list = video_info.get("item_list", [])
            if item_list:
                return item_list[0]
    return None


def _extract_video_url(video_data: dict) -> Optional[str]:
    """Extract the best video URL from video data."""
    video = video_data.get("video", {})

    # Try play_addr first
    play_addr = video.get("play_addr", {})
    url_list = play_addr.get("url_list", [])
    if url_list:
        return url_list[0]

    # Try play_addr_h264
    play_addr_h264 = video.get("play_addr_h264", {})
    url_list = play_addr_h264.get("url_list", [])
    if url_list:
        return url_list[0]

    # Try bit_rate list
    bit_rate = video.get("bit_rate", [])
    if bit_rate:
        best = max(bit_rate, key=lambda x: x.get("bit_rate", 0))
        play_addr = best.get("play_addr", {})
        url_list = play_addr.get("url_list", [])
        if url_list:
            return url_list[0]

    return None


def _remove_watermark(url: str) -> str:
    """Replace playwm (with watermark) URL with play (no watermark)."""
    return url.replace("/playwm/", "/play/")


def _extract_cover_url(video_data: dict) -> Optional[str]:
    """Extract cover image URL."""
    video = video_data.get("video", {})
    cover = video.get("cover", {})
    url_list = cover.get("url_list", [])
    if url_list:
        return url_list[0]

    origin_cover = video.get("origin_cover", {})
    url_list = origin_cover.get("url_list", [])
    if url_list:
        return url_list[0]

    return None


def _parse_video_item(item: dict, input_url: str, final_url: str) -> ResolveResult:
    """Parse a video item dict into ResolveResult."""
    aweme_id = str(item.get("aweme_id", ""))
    desc = item.get("desc", "")
    author_data = item.get("author", {})

    author = None
    if author_data:
        author = Author(
            nickname=author_data.get("nickname", ""),
            sec_uid=author_data.get("sec_uid"),
        )

    video_url = _extract_video_url(item)
    if video_url:
        video_url = _remove_watermark(video_url)
    cover_url = _extract_cover_url(item)

    media = None
    if video_url:
        media = Media(
            type="video",
            downloadable=True,
            url=video_url,
            mime="video/mp4",
        )
    else:
        media = Media(
            type="video",
            downloadable=False,
            reason_if_unavailable="无法在合规边界内获取视频资源",
        )

    return ResolveResult(
        ok=True,
        platform="douyin",
        input_url=input_url,
        resolved_url=final_url,
        aweme_id=aweme_id,
        title=desc,
        author=author,
        cover_url=cover_url,
        media=media,
        comments=[],
        warnings=[],
    )


async def fetch_work_info(
    aweme_id: str,
    input_url: str,
    final_url: str,
    client: Optional[httpx.AsyncClient] = None,
) -> ResolveResult:
    """Fetch work metadata from Douyin mobile share page.

    Strategy:
    1. Fetch the mobile share page (iesdouyin.com)
    2. Extract _ROUTER_DATA JSON
    3. Parse video info from embedded data

    Args:
        aweme_id: The Douyin work ID.
        input_url: Original input URL.
        final_url: Resolved final URL.
        client: Optional shared httpx client. If None, creates a new one.

    Returns:
        ResolveResult with video metadata.

    Raises:
        ResolverError: If metadata cannot be fetched.
    """
    share_url = f"https://www.iesdouyin.com/share/video/{aweme_id}/"

    async def _fetch_with_client(c: httpx.AsyncClient) -> str:
        resp = await c.get(share_url)
        resp.raise_for_status()
        return resp.text

    try:
        if client:
            html = await _fetch_with_client(client)
        else:
            async with httpx.AsyncClient(
                timeout=15.0,
                headers=BROWSER_HEADERS,
                follow_redirects=True,
            ) as new_client:
                html = await _fetch_with_client(new_client)

    except httpx.TimeoutException:
        raise ResolverError(
            code=ErrorCode.RESOLVE_FAILED,
            message="获取作品页面超时",
            detail=f"aweme_id: {aweme_id}",
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 403:
            raise ResolverError(
                code=ErrorCode.RATE_LIMITED,
                message="请求被限制，稍后再试",
                detail=f"aweme_id: {aweme_id}",
            )
        raise ResolverError(
            code=ErrorCode.RESOLVE_FAILED,
            message=f"获取作品页面失败: HTTP {e.response.status_code}",
            detail=f"aweme_id: {aweme_id}",
        )
    except httpx.HTTPError as e:
        raise ResolverError(
            code=ErrorCode.RESOLVE_FAILED,
            message=f"获取作品页面失败: {e}",
            detail=f"aweme_id: {aweme_id}",
        )

    # Extract _ROUTER_DATA
    m = ROUTER_DATA_RE.search(html)
    if not m:
        if len(html) < 1000:
            raise ResolverError(
                code=ErrorCode.UPSTREAM_CHANGED,
                message="页面内容异常，解析规则可能需要更新",
                detail=f"aweme_id: {aweme_id}, html_len: {len(html)}",
            )
        raise ResolverError(
            code=ErrorCode.UPSTREAM_CHANGED,
            message="无法从页面提取视频数据，解析规则可能需要更新",
            detail=f"aweme_id: {aweme_id}",
        )

    try:
        data = json.loads(m.group(1), strict=False)
    except json.JSONDecodeError:
        raise ResolverError(
            code=ErrorCode.UPSTREAM_CHANGED,
            message="页面数据解析失败",
            detail=f"aweme_id: {aweme_id}",
        )

    item = _find_video_item(data)
    if not item:
        raise ResolverError(
            code=ErrorCode.AWEME_ID_NOT_FOUND,
            message="页面中未找到视频信息",
            detail=f"aweme_id: {aweme_id}",
        )

    return _parse_video_item(item, input_url, final_url)
