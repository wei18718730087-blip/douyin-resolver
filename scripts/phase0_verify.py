#!/usr/bin/env python3
"""Phase 0 technical verification script.

Tests the core parsing pipeline against real Douyin links.

Usage:
    python scripts/phase0_verify.py <url>
    python scripts/phase0_verify.py --test-links
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from packages.core.input_parser import parse_input, is_douyin_url, extract_aweme_id_from_url
from packages.core.url_resolver import resolve_url
from packages.core.douyin_provider import fetch_work_info
from packages.core.comment_provider import fetch_comments
from packages.core.errors import ResolverError


async def verify_url(url: str) -> dict:
    """Run full verification pipeline on a single URL."""
    result = {
        "input_url": url,
        "steps": {},
    }

    # Step 1: Parse input
    print(f"\n{'='*60}")
    print(f"Step 1: 解析输入")
    print(f"  输入: {url}")
    try:
        clean_url = parse_input(url)
        result["steps"]["parse_input"] = {"ok": True, "clean_url": clean_url}
        print(f"  结果: {clean_url}")
    except ResolverError as e:
        result["steps"]["parse_input"] = {"ok": False, "error": e.to_dict()}
        print(f"  错误: {e.user_message}")
        return result

    # Step 2: Check if Douyin URL
    print(f"\nStep 2: 判断平台")
    is_dy = is_douyin_url(clean_url)
    result["steps"]["is_douyin"] = {"ok": is_dy}
    print(f"  抖音链接: {is_dy}")

    # Step 3: Try direct aweme_id extraction
    print(f"\nStep 3: 直接提取 aweme_id")
    direct_id = extract_aweme_id_from_url(clean_url)
    result["steps"]["direct_extract"] = {"aweme_id": direct_id}
    print(f"  直接提取: {direct_id or '需要跳转解析'}")

    # Step 4: Resolve URL
    print(f"\nStep 4: 解析链接")
    t0 = time.time()
    try:
        final_url, aweme_id = await resolve_url(clean_url)
        elapsed = time.time() - t0
        result["steps"]["resolve_url"] = {
            "ok": True,
            "final_url": final_url,
            "aweme_id": aweme_id,
            "elapsed_s": round(elapsed, 2),
        }
        print(f"  最终URL: {final_url}")
        print(f"  aweme_id: {aweme_id}")
        print(f"  耗时: {elapsed:.2f}s")
    except ResolverError as e:
        elapsed = time.time() - t0
        result["steps"]["resolve_url"] = {"ok": False, "error": e.to_dict(), "elapsed_s": round(elapsed, 2)}
        print(f"  错误: {e.user_message}")
        return result

    # Step 5: Fetch work info
    print(f"\nStep 5: 获取作品信息")
    t0 = time.time()
    try:
        work_result = await fetch_work_info(aweme_id, clean_url, final_url)
        elapsed = time.time() - t0
        result["steps"]["fetch_work"] = {
            "ok": True,
            "title": work_result.title,
            "author": work_result.author.nickname if work_result.author else None,
            "cover_url": work_result.cover_url,
            "video_url": work_result.media.url if work_result.media and work_result.media.downloadable else None,
            "downloadable": work_result.media.downloadable if work_result.media else False,
            "elapsed_s": round(elapsed, 2),
        }
        print(f"  标题: {work_result.title}")
        print(f"  作者: {work_result.author.nickname if work_result.author else '未知'}")
        print(f"  封面: {work_result.cover_url}")
        if work_result.media and work_result.media.downloadable:
            print(f"  视频: {work_result.media.url[:80]}...")
        else:
            print(f"  视频: 不可下载")
        print(f"  耗时: {elapsed:.2f}s")
    except ResolverError as e:
        elapsed = time.time() - t0
        result["steps"]["fetch_work"] = {"ok": False, "error": e.to_dict(), "elapsed_s": round(elapsed, 2)}
        print(f"  错误: {e.user_message}")
        return result

    # Step 6: Fetch comments
    print(f"\nStep 6: 获取评论")
    t0 = time.time()
    try:
        comments = await fetch_comments(aweme_id, limit=5)
        elapsed = time.time() - t0
        result["steps"]["fetch_comments"] = {
            "ok": True,
            "count": len(comments),
            "top_comments": [
                {"text": c.text[:50], "likes": c.like_count}
                for c in comments[:3]
            ],
            "elapsed_s": round(elapsed, 2),
        }
        print(f"  评论数: {len(comments)}")
        for i, c in enumerate(comments[:3], 1):
            print(f"    {i}. [{c.like_count}赞] {c.text[:50]}")
        print(f"  耗时: {elapsed:.2f}s")
    except ResolverError as e:
        elapsed = time.time() - t0
        result["steps"]["fetch_comments"] = {"ok": False, "error": e.to_dict(), "elapsed_s": round(elapsed, 2)}
        print(f"  评论获取失败: {e.user_message}")
        # Not a fatal error, continue

    return result


async def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("用法: python scripts/phase0_verify.py <抖音链接>")
        print("示例: python scripts/phase0_verify.py 'https://v.douyin.com/xxxx/'")
        sys.exit(1)

    url = sys.argv[1]
    print(f"Phase 0 技术验证")
    print(f"{'='*60}")

    result = await verify_url(url)

    # Print summary
    print(f"\n{'='*60}")
    print(f"验证结果摘要")
    print(f"{'='*60}")

    # Critical steps: resolve_url and fetch_work must succeed
    # direct_extract is optional (fails for short links, that's expected)
    critical_steps = ["resolve_url", "fetch_work"]
    all_ok = all(
        result["steps"].get(step, {}).get("ok", False)
        for step in critical_steps
    )

    for step_name, step_data in result["steps"].items():
        if isinstance(step_data, dict):
            status = "OK" if step_data.get("ok") else "FAIL"
            note = ""
            if step_name == "direct_extract" and not step_data.get("ok"):
                note = " (短链接预期失败，需跳转解析)"
            print(f"  {step_name}: {status}{note}")

    # Save result
    output_path = Path(__file__).parent.parent / "tests" / "phase0_result.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n详细结果已保存到: {output_path}")

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    asyncio.run(main())
