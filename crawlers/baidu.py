"""Baidu hot search crawler.

Uses the internal Baidu board API (JSON, no auth required).
"""

import requests

from crawlers._common import HEADERS

URL = "https://top.baidu.com/api/board?platform=wise&tab=realtime"


def crawl() -> list[dict]:
    """Return top-10 Baidu hot search items."""
    resp = requests.get(
        URL,
        headers={**HEADERS, "Referer": "https://top.baidu.com/"},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()

    items = []
    for card in data.get("data", {}).get("cards", []):
        for c in card.get("content", []):
            title = (c.get("word") or c.get("query") or "").strip()
            if not title:
                continue
            url = c.get("url") or c.get("appUrl") or ""
            items.append({
                "title": title,
                "url": url,
                "heat": str(c.get("hotScore", "")),
                "rank": len(items) + 1,
            })
            if len(items) >= 10:
                break
        if len(items) >= 10:
            break
    return items
