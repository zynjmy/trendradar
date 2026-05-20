"""WeChat hot articles crawler.

Backed by newsnow.busiyi.world aggregator API (experimental — "wechat"
may not be a supported source). Falls back to vvhan if newsnow fails.
Reference: BettaFish/MindSpider/BroadTopicExtraction/get_today_news.py
"""
import requests

from crawlers._common import HEADERS
from crawlers.newsnow import fetch as newsnow_fetch

# Legacy vvhan endpoints — used only as fallback
_VVHAN_URLS = [
    "https://api.vvhan.com/api/hotlist/wxHot",
    "https://api.vvhan.com/api/hotlist?type=wxHot",
]


def _crawl_vvhan() -> list[dict]:
    """Legacy vvhan-based crawl (kept as fallback)."""
    for url in _VVHAN_URLS:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                raw = data.get("data", [])
                if isinstance(raw, dict):
                    raw = raw.get("list", [])
                items = []
                for i, item in enumerate(raw, 1):
                    title = (item.get("title") or "").strip()
                    if not title:
                        continue
                    items.append({
                        "title": title,
                        "url": item.get("url", ""),
                        "heat": str(item.get("hot", "")),
                        "rank": i,
                    })
                    if len(items) >= 10:
                        break
                if items:
                    return items[:10]
        except Exception:
            continue
    raise RuntimeError("vvhan WeChat API unavailable")


def crawl() -> list[dict]:
    """Return top-10 WeChat hot articles."""
    try:
        return newsnow_fetch("wechat")
    except Exception:
        pass
    try:
        return _crawl_vvhan()
    except Exception:
        raise RuntimeError(
            "WeChat hot-list unavailable: both newsnow and vvhan APIs failed."
        )
