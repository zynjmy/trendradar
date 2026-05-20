"""Baidu hot search crawler.

Uses the internal Baidu board API (JSON, no auth required).
"""

import requests

from crawlers._common import HEADERS

URL = "https://top.baidu.com/api/board?platform=wise&tab=realtime"


def _extract_items(container) -> list[dict]:
    """Extract items from a card content container, handling nested lists."""
    items = []
    if isinstance(container, list):
        for elem in container:
            if isinstance(elem, dict):
                word = elem.get("word") or elem.get("query")
                if word:
                    items.append(elem)
                # Recurse into nested content lists
                nested = elem.get("content")
                if isinstance(nested, list):
                    items.extend(_extract_items(nested))
    return items


def crawl() -> list[dict]:
    """Return top-10 Baidu hot search items."""
    resp = requests.get(
        URL,
        headers={**HEADERS, "Referer": "https://top.baidu.com/"},
        timeout=15,
    )
    resp.raise_for_status()
    # Baidu API may return latin-1 mislabeled as utf-8
    if resp.encoding and resp.encoding.lower() != "utf-8":
        try:
            resp.json()
        except (ValueError, UnicodeDecodeError):
            resp.encoding = "utf-8"
    data = resp.json()

    result = []
    for card in data.get("data", {}).get("cards", []):
        raw = _extract_items(card.get("content", []))
        for item in raw:
            title = (item.get("word") or item.get("query") or "").strip()
            if not title:
                continue
            url = item.get("url") or item.get("appUrl") or ""
            result.append({
                "title": title,
                "url": url,
                "heat": str(item.get("hotScore", "")),
                "rank": len(result) + 1,
            })
            if len(result) >= 10:
                break
        if len(result) >= 10:
            break
    return result
