"""Metrics and monitoring endpoint."""

from __future__ import annotations

import time
from collections import defaultdict

from fastapi import APIRouter, Request

router = APIRouter(tags=["metrics"])

# In-memory request counters
_request_counts: dict[str, int] = defaultdict(int)
_error_counts: dict[str, int] = defaultdict(int)
_total_requests = 0
_total_errors = 0
_start_time = time.time()


def record_request(endpoint: str, is_error: bool = False) -> None:
    """Record a request for metrics."""
    global _total_requests, _total_errors
    _total_requests += 1
    _request_counts[endpoint] += 1
    if is_error:
        _total_errors += 1
        _error_counts[endpoint] += 1


@router.get(
    "/metrics",
    summary="服务监控指标",
    description="返回服务运行状态、缓存统计和请求计数",
)
async def metrics(request: Request):
    """监控指标端点。

    返回：
    - uptime: 运行时间（秒）
    - cache: 缓存统计
    - requests: 请求计数
    """
    cache = getattr(request.app.state, "cache", None)
    cache_stats = cache.stats() if cache else {"status": "disabled"}

    uptime = time.time() - _start_time

    return {
        "uptime_seconds": round(uptime, 1),
        "cache": cache_stats,
        "requests": {
            "total": _total_requests,
            "errors": _total_errors,
            "by_endpoint": dict(_request_counts),
            "errors_by_endpoint": dict(_error_counts),
        },
    }


@router.post(
    "/cache/clear",
    summary="清除过期缓存",
    description="手动触发清除过期的缓存条目",
)
async def clear_cache(request: Request):
    """清除过期缓存条目。"""
    cache = getattr(request.app.state, "cache", None)
    if not cache:
        return {"status": "disabled", "cleared": 0}

    cleared = cache.clear_expired()
    return {"status": "ok", "cleared": cleared}
