"""Health check endpoint."""

from fastapi import APIRouter

from packages.core.schemas import HealthResponse

router = APIRouter(tags=["health"])

VERSION = "0.1.0"


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="健康检查",
    description="检查 API 服务是否正常运行",
)
async def health_check():
    """健康检查端点。

    返回：
    - ok: 服务是否正常
    - version: 当前版本号
    """
    return HealthResponse(ok=True, version=VERSION)
