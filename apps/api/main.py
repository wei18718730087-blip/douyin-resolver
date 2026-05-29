"""FastAPI application entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from apps.api.error_handler import ErrorHandlingMiddleware
from apps.api.rate_limiter import RateLimitMiddleware
from apps.api.routes.health import router as health_router
from apps.api.routes.resolve import router as resolve_router
from apps.api.routes.metrics import router as metrics_router
from packages.core.cache import ResolveCache

VERSION = "0.1.0"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("douyin-resolver")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("Douyin Link Resolver API starting (v%s)", VERSION)
    cache = ResolveCache()
    app.state.cache = cache
    logger.info("Cache initialized: %s", cache.stats())
    yield
    cache.close()
    logger.info("Douyin Link Resolver API shutting down")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Douyin Link Resolver API",
        description=(
            "解析抖音公开分享链接，返回作品信息、视频资源和热门评论。\n\n"
            "## 使用说明\n"
            "1. 传入抖音分享链接（支持短链、长链、分享文本）\n"
            "2. 返回结构化 JSON，包含标题、作者、封面、视频资源\n"
            "3. 可选获取热门评论\n\n"
            "## 限制\n"
            "- 每 IP 每分钟最多 30 次请求\n"
            "- 仅支持公开作品链接\n"
            "- 不支持批量解析"
        ),
        version=VERSION,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Middleware (order matters: outermost first)
    # 1. Error handling (catches all errors)
    app.add_middleware(ErrorHandlingMiddleware)

    # 2. Rate limiting
    app.add_middleware(RateLimitMiddleware, requests_per_minute=30)

    # 3. CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routes
    app.include_router(health_router)
    app.include_router(resolve_router, prefix="/api/v1")
    app.include_router(metrics_router)

    # Serve frontend static files
    static_dir = Path(__file__).parent.parent.parent / "static"
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

    return app


app = create_app()
