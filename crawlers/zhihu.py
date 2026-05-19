"""Zhihu hot list crawler.

Uses the public Zhihu API (no auth required).
"""

import requests

from crawlers._common import HEADERS

URL = "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total?limit=50&desktop=true"


def crawl() -> list[dict]:
    """Return top-10 Zhihu hot list items."""
    resp = requests.get(
        URL,
        headers={**HEADERS, "Referer": "https://www.zhihu.com/hot"},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()

    items = []
    for item in data.get("data", []):
        target = item.get("target", {})
        title = (target.get("title") or "").strip()
        if not title:
            continue
        url = target.get("url", "")
        if url and not url.startswith("http"):
            url = "https://www.zhihu.com" + url
        items.append({
            "title": title,
            "url": url,
            "heat": str(target.get("follower_count", "")),
            "rank": len(items) + 1,
        })
        if len(items) >= 10:
            break
    return items
