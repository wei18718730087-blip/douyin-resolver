"""Fetch comments for a Douyin work."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import List, Optional

import httpx

from packages.core.errors import ErrorCode, ResolverError
from packages.core.schemas import Comment

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://www.douyin.com/",
}

COMMENT_API_URL = "https://www.iesdouyin.com/web/api/v2/comment/list/"

# Number of API requests to accumulate unique comments
FETCH_ROUNDS = 5


def _parse_timestamp(ts: Optional[int]) -> Optional[str]:
    """Convert Unix timestamp to ISO format string."""
    if ts is None:
        return None
    try:
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    except (ValueError, OSError):
        return None


def _parse_comment(raw: dict) -> Optional[Comment]:
    """Parse a raw comment dict into a Comment model."""
    cid = str(raw.get("cid", ""))
    text = raw.get("text", "")
    if not cid or not text:
        return None

    # API uses "createTime" (camelCase), try both
    create_time = raw.get("createTime") or raw.get("create_time")

    return Comment(
        cid=cid,
        text=text,
        like_count=raw.get("digg_count", 0),
        reply_count=raw.get("reply_comment_total", None),
        create_time=_parse_timestamp(create_time),
    )


async def fetch_comments(
    aweme_id: str,
    limit: int = 50,
    client: Optional[httpx.AsyncClient] = None,
) -> List[Comment]:
    """Fetch hot comments for a Douyin work.

    Strategy:
    1. Call /web/api/v2/comment/list/ with cursor pagination
    2. Merge and deduplicate by cid
    3. Sort by like_count descending
    4. Return top N

    Args:
        aweme_id: The Douyin work ID.
        limit: Maximum number of comments to return (default 50).
        client: Optional shared httpx client. If None, creates a new one.

    Returns:
        List of Comment objects, sorted by like_count descending.
        Returns empty list if comments cannot be fetched (non-fatal).
    """
    all_comments: dict[str, Comment] = {}
    cursor = 0

    async def _fetch_with_client(c: httpx.AsyncClient) -> None:
        nonlocal cursor
        for _ in range(FETCH_ROUNDS):
            resp = await c.get(
                COMMENT_API_URL,
                params={"aweme_id": aweme_id, "cursor": cursor, "count": 50},
            )
            if resp.status_code != 200:
                break

            data = resp.json()
            raw_comments = data.get("comments", [])
            if not raw_comments:
                break

            for raw in raw_comments:
                comment = _parse_comment(raw)
                if comment and comment.cid not in all_comments:
                    all_comments[comment.cid] = comment

            # Update cursor for next page
            cursor = data.get("cursor", cursor + 50)
            # Stop if no more comments
            if not data.get("has_more", False):
                break

    try:
        if client:
            await _fetch_with_client(client)
        else:
            async with httpx.AsyncClient(
                timeout=15.0,
                headers=BROWSER_HEADERS,
                follow_redirects=True,
            ) as new_client:
                await _fetch_with_client(new_client)
    except Exception:
        # Comments are non-fatal, return whatever we have
        pass

    # Sort by likes descending
    sorted_comments = sorted(
        all_comments.values(), key=lambda c: c.like_count, reverse=True
    )

    return sorted_comments[:limit]
