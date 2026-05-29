"""CLI entry point for Douyin Link Resolver."""

from __future__ import annotations

import asyncio
import json
import sys
from importlib.metadata import version as get_version
from typing import Optional

import typer

from packages.core.errors import EXIT_INPUT_ERROR, EXIT_PLATFORM_ERROR, EXIT_RATE_LIMITED, EXIT_SUCCESS, EXIT_UPSTREAM_ERROR, ErrorCode, ResolverError
from packages.core.schemas import ResolveResult

APP_VERSION = get_version("douyin-resolver")

app = typer.Typer(
    name="douyin-resolver",
    help="Douyin Link Resolver — 解析抖音公开分享链接",
    no_args_is_help=True,
)


def version_callback(value: bool) -> None:
    if value:
        typer.echo(f"douyin-resolver, version {APP_VERSION}")
        raise typer.Exit()


def _exit_code_for_error(code: ErrorCode) -> int:
    mapping = {
        ErrorCode.INVALID_INPUT: EXIT_INPUT_ERROR,
        ErrorCode.UNSUPPORTED_PLATFORM: EXIT_INPUT_ERROR,
        ErrorCode.RESOLVE_FAILED: EXIT_PLATFORM_ERROR,
        ErrorCode.AWEME_ID_NOT_FOUND: EXIT_PLATFORM_ERROR,
        ErrorCode.MEDIA_UNAVAILABLE: EXIT_PLATFORM_ERROR,
        ErrorCode.COMMENTS_UNAVAILABLE: EXIT_PLATFORM_ERROR,
        ErrorCode.RATE_LIMITED: EXIT_RATE_LIMITED,
        ErrorCode.UPSTREAM_CHANGED: EXIT_UPSTREAM_ERROR,
        ErrorCode.LEGAL_RESTRICTED: EXIT_INPUT_ERROR,
    }
    return mapping.get(code, EXIT_PLATFORM_ERROR)


@app.command()
def main(
    url: str = typer.Argument(help="抖音分享链接或包含链接的文本"),
    comments: int = typer.Option(0, "--comments", "-c", help="获取评论数量，0 表示不获取"),
    download: bool = typer.Option(False, "--download", "-d", help="请求下载信息"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="下载目录（暂不支持）"),
    human: bool = typer.Option(False, "--human", help="人类可读输出模式"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="安静模式，仅输出 JSON（适合 Agent 调用）"),
    version: Optional[bool] = typer.Option(None, "--version", "-v", callback=version_callback, is_eager=True, help="显示版本号"),
) -> None:
    """解析抖音分享链接，输出 JSON 结果。"""
    result = asyncio.run(_resolve(url, comments, download))

    if quiet:
        # Agent 模式：仅输出 JSON 到 stdout
        typer.echo(json.dumps(result.model_dump(), ensure_ascii=False, separators=(",", ":")))
    elif human:
        _print_human(result)
    else:
        typer.echo(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))

    if not result.ok and result.error:
        sys.exit(_exit_code_for_error(ErrorCode(result.error.code)))


async def _resolve(
    url_text: str,
    comment_limit: int,
    download: bool,
) -> ResolveResult:
    import httpx

    from packages.core.input_parser import parse_input
    from packages.core.url_resolver import resolve_url
    from packages.core.douyin_provider import BROWSER_HEADERS as DOUYIN_HEADERS, fetch_work_info
    from packages.core.comment_provider import fetch_comments

    try:
        clean_url = parse_input(url_text)

        # Use shared HTTP client for all requests
        async with httpx.AsyncClient(
            timeout=15.0,
            headers=DOUYIN_HEADERS,
            follow_redirects=True,
        ) as client:
            final_url, aweme_id = await resolve_url(clean_url, client=client)

            # Parallel fetch: work info + comments
            if comment_limit > 0:
                work_info_task = fetch_work_info(aweme_id, clean_url, final_url, client=client)
                comments_task = fetch_comments(aweme_id, limit=comment_limit, client=client)

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

        return result

    except ResolverError as e:
        return ResolveResult(
            ok=False,
            platform="douyin",
            input_url=url_text,
            error={
                "code": e.code.value,
                "message": e.user_message,
                "detail": e.detail,
            },
        )
    except Exception as e:
        return ResolveResult(
            ok=False,
            platform="douyin",
            input_url=url_text,
            error={
                "code": "UNKNOWN",
                "message": f"未知错误: {type(e).__name__}",
                "detail": str(e),
            },
        )


def _print_human(result: ResolveResult) -> None:
    if not result.ok:
        typer.secho(f"错误: {result.error.message if result.error else '未知错误'}", fg=typer.colors.RED)
        if result.error and result.error.detail:
            typer.echo(f"  详情: {result.error.detail}")
        return

    typer.secho("解析成功", fg=typer.colors.GREEN)
    typer.echo(f"  标题: {result.title}")
    typer.echo(f"  作者: {result.author.nickname if result.author else '未知'}")
    typer.echo(f"  作品ID: {result.aweme_id}")

    if result.media:
        if result.media.downloadable:
            typer.echo(f"  视频: {result.media.url}")
        else:
            typer.echo(f"  视频: 不可下载 — {result.media.reason_if_unavailable}")

    if result.comments:
        typer.echo(f"  评论: {len(result.comments)} 条")
        for i, c in enumerate(result.comments, 1):
            typer.echo(f"    {i}. [{c.like_count}赞] {c.text[:50]}")

    if result.warnings:
        for w in result.warnings:
            typer.secho(f"  警告: {w}", fg=typer.colors.YELLOW)


if __name__ == "__main__":
    app()
