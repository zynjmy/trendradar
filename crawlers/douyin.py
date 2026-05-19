"""Douyin (TikTok CN) hot list crawler.

NOTE: Douyin has no stable public API for hot trends. This module uses a
third-party aggregator. If it breaks, update ENDPOINTS.
"""

import requests

from crawlers._common import HEADERS

ENDPOINTS = [
    "https://api.vvhan.com/api/hotlist/douyinHot",
    "https://api.vvhan.com/api/hotlist?type=douyinHot",
]


def _parse(data: dict) -> list[dict]:
    items = []
    raw = data.get("data", [])
    if isinstance(raw, dict):
        raw = raw.get("list", [])
    for item in raw:
        title = (item.get("title") or "").strip()
        if not title:
            continue
        items.append({
            "title": title,
            "url": item.get("url", ""),
            "heat": str(item.get("hot", "")),
            "rank": len(items) + 1,
        })
        if len(items) >= 10:
            break
    return items


def crawl() -> list[dict]:
    """Return top-10 Douyin hot topics (best-effort)."""
    for url in ENDPOINTS:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                items = _parse(resp.json())
                if items:
                    return items[:10]
        except Exception:
            continue
    raise RuntimeError(
        "Douyin aggregator APIs are currently unavailable. "
        "Try updating crawlers/douyin.py with a working endpoint."
    )
