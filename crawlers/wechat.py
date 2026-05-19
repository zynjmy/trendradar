"""WeChat hot articles crawler.

NOTE: WeChat has NO public hot-list API. This module relies on a
third-party aggregator (vvhan). If it stops working, update ENDPOINTS
or replace with another aggregator that speaks a similar JSON shape.
"""

import requests

from crawlers._common import HEADERS

# ---------------------------------------------------------------------------
# List of (url, parser) tuples — tried in order until one succeeds.
# Add or reorder entries here when APIs come and go.
# ---------------------------------------------------------------------------
ENDPOINTS = [
    "https://api.vvhan.com/api/hotlist/wxHot",
    # fallback — some deployments use a query-string style
    "https://api.vvhan.com/api/hotlist?type=wxHot",
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
    """Return top-10 WeChat hot articles (best-effort)."""
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
        "WeChat aggregator APIs are currently unavailable. "
        "Try updating crawlers/wechat.py with a working endpoint."
    )
