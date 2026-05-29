"""Resolve endpoint for Douyin links."""

from __future__ import annotations

import asyncio

import httpx
from fastapi import APIRouter, Request

from packages.core.input_parser import parse_input
from packages.core.url_resolver import resolve_url
from packages.core.douyin_provider import BROWSER_HEADERS as DOUYIN_HEADERS, fetch_work_info
from packages.core.comment_provider import fetch_comments
from packages.core.errors import ResolverError
from packages.core.schemas import ResolveRequest, ResolveResult

router = APIRouter(tags=["resolve"])


@router.post(
    "/douyin/resolve",
    response_model=ResolveResult,
    summary="解析抖音链接",
    description=(
        "传入抖音分享链接，返回作品信息、视频资源和热门评论。\n\n"
        "支持的输入格式：\n"
        "- 短链：`https://v.douyin.com/xxxx/`\n"
        "- 长链：`https://www.douyin.com/video/xxxx`\n"
        "- 分享文本：`复制打开抖音，看看... https://v.douyin.com/xxxx/`"
    ),
    responses={
        200: {
            "description": "解析结果（即使失败也返回 200，通过 ok 字段判断成功与否）",
            "content": {
                "application/json": {
                    "example": {
                        "ok": True,
                        "platform": "douyin",
                        "aweme_id": "7637819731894649507",
                        "title": "视频标题",
                        "author": {"nickname": "作者昵称", "sec_uid": "..."},
                        "cover_url": "https://...",
                        "media": {
                            "type": "video",
                            "downloadable": True,
                            "url": "https://...",
                            "mime": "video/mp4",
                        },
                        "comments": [],
                        "warnings": [],
                    }
                }
            },
        }
    },
)
async def resolve_douyin_link(request: ResolveRequest, req: Request):
    """解析抖音分享链接。

    - **url**: 抖音分享链接或包含链接的文本
    - **include_comments**: 是否包含评论（默认 true）
    - **comment_limit**: 评论数量上限（默认 20，最大 100）
    - **download**: 是否请求下载信息（暂不支持）
    """
    try:
        # Step 1: Parse input
        clean_url = parse_input(request.url)

        # Step 2: Check cache first (before HTTP requests)
        cache = getattr(req.app.state, "cache", None)

        # Use shared HTTP client for all requests
        async with httpx.AsyncClient(
            timeout=15.0,
            headers=DOUYIN_HEADERS,
            follow_redirects=True,
        ) as client:
            # Step 3: Resolve URL
            final_url, aweme_id = await resolve_url(clean_url, client=client)

            # Step 3.5: Check cache after resolving URL
            if cache:
                cached = cache.get(aweme_id)
                if cached:
                    cached.warnings.append("from_cache")
                    return cached

            # Step 4: Parallel fetch work info + comments
            if request.include_comments and request.comment_limit > 0:
                work_info_task = fetch_work_info(aweme_id, clean_url, final_url, client=client)
                comments_task = fetch_comments(aweme_id, limit=request.comment_limit, client=client)

                results = await asyncio.gather(
                    work_info_task,
                    comments_task,
                    return_exceptions=True,
                )

                result = results[0]
                if isinstance(result, Exception):
                    raise result

                # Handle comments result
                if isinstance(results[1], Exception):
                    result.warnings.append(f"评论获取失败: {results[1]}")
                else:
                    result.comments = results[1]
            else:
                result = await fetch_work_info(aweme_id, clean_url, final_url, client=client)

        # Step 5: Cache successful result
        if result.ok and cache:
            cache.set(aweme_id, result)

        return result

    except ResolverError as e:
        return ResolveResult(
            ok=False,
            platform="douyin",
            input_url=request.url,
            error=e.to_dict(),
        )
    except Exception as e:
        return ResolveResult(
            ok=False,
            platform="douyin",
            input_url=request.url,
            error={
                "code": "UNKNOWN",
                "message": f"未知错误: {type(e).__name__}",
                "detail": str(e),
            },
        )
