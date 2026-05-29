"""CLI entry point for Douyin Link Resolver."""

from __future__ import annotations

import asyncio
import json
import sys
from importlib.metadata import version as get_version
from pathlib import Path
from typing import Optional

import httpx
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
    comments: int = typer.Option(50, "--comments", "-c", help="获取评论数量，0 表示不获取"),
    download: bool = typer.Option(False, "--download", "-d", help="下载视频到指定目录"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="下载目录（默认当前目录）"),
    human: bool = typer.Option(False, "--human", help="人类可读输出模式"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="安静模式，仅输出 JSON（适合 Agent 调用）"),
    version: Optional[bool] = typer.Option(None, "--version", "-v", callback=version_callback, is_eager=True, help="显示版本号"),
) -> None:
    """解析抖音分享链接，输出 JSON 结果。"""
    result = asyncio.run(_resolve(url, comments, download))

    # Download video if requested
    if download and result.ok and result.media and result.media.downloadable:
        download_dir = Path(output) if output else Path.cwd()
        downloaded_path = asyncio.run(_download_video(result.media.url, result.aweme_id, download_dir, quiet))
        if downloaded_path:
            result.warnings.append(f"已下载到: {downloaded_path}")

    if quiet:
        # Agent 模式：仅输出 JSON 到 stdout
        typer.echo(json.dumps(result.model_dump(), ensure_ascii=False, separators=(",", ":")))
    elif human:
        _print_human(result)
    else:
        typer.echo(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))

    if not result.ok and result.error:
        sys.exit(_exit_code_for_error(ErrorCode(result.error.code)))


async def _download_video(
    video_url: str,
    aweme_id: str,
    output_dir: Path,
    quiet: bool = False,
) -> Optional[Path]:
    """Download video to specified directory.

    Args:
        video_url: Video download URL.
        aweme_id: Douyin work ID (used as filename).
        output_dir: Target directory.
        quiet: If True, suppress progress output.

    Returns:
        Path to downloaded file, or None if download failed.
    """
    try:
        # Validate output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        # Safe filename: use aweme_id only
        filename = f"{aweme_id}.mp4"
        filepath = output_dir / filename

        # Check for path traversal
        if not filepath.resolve().is_relative_to(output_dir.resolve()):
            if not quiet:
                typer.secho("错误: 无效的输出路径", fg=typer.colors.RED, err=True)
            return None

        if not quiet:
            typer.echo(f"正在下载: {filename}", err=True)

        # Download with streaming
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            async with client.stream("GET", video_url) as resp:
                resp.raise_for_status()
                total = int(resp.headers.get("content-length", 0))

                with open(filepath, "wb") as f:
                    downloaded = 0
                    async for chunk in resp.aiter_bytes(chunk_size=8192):
                        f.write(chunk)
                        downloaded += len(chunk)

                        if not quiet and total > 0:
                            progress = downloaded / total * 100
                            typer.echo(f"\r下载进度: {progress:.1f}%", err=True, nl=False)

                if not quiet:
                    typer.echo("", err=True)  # New line after progress

        if not quiet:
            typer.secho(f"下载完成: {filepath}", fg=typer.colors.GREEN, err=True)

        return filepath

    except httpx.HTTPStatusError as e:
        if not quiet:
            typer.secho(f"下载失败: HTTP {e.response.status_code}", fg=typer.colors.RED, err=True)
        return None
    except Exception as e:
        if not quiet:
            typer.secho(f"下载失败: {e}", fg=typer.colors.RED, err=True)
        return None


async def _resolve(
    url_text: str,
    comment_limit: int,
    download: bool,
) -> ResolveResult:
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
        typer.secho(f"错误: {result.error.message if result.error else '未知错误'}", fg=typer.colors.RED, err=True)
        if result.error and result.error.detail:
            typer.echo(f"  详情: {result.error.detail}", err=True)
        return

    typer.secho("解析成功", fg=typer.colors.GREEN, err=True)
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
            typer.secho(f"  警告: {w}", fg=typer.colors.YELLOW, err=True)


if __name__ == "__main__":
    app()
