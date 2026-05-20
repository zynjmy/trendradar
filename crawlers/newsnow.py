"""Unified client for the newsnow.busiyi.world hot-list aggregator.

Adapted from BettaFish/MindSpider/BroadTopicExtraction/get_today_news.py
Synchronous requests wrapper — no async needed for TrendRadar's sequential pipeline.

Source coverage (12 confirmed + 2 experimental):
    weibo, zhihu, bilibili-hot-search, toutiao, douyin,
    github-trending-today, coolapk, tieba, wallstreetcn,
    thepaper, cls-hot, xueqiu,
    wechat*, kuaishou*   (* experimental — may not exist on newsnow)
"""

import requests

from crawlers._common import HEADERS

BASE_URL = "https://newsnow.busiyi.world"

# Source ID mapping — use the exact IDs from BettaFish's SOURCE_NAMES dict
SOURCE_IDS = {
    "weibo":       "weibo",
    "zhihu":       "zhihu",
    "bilibili":    "bilibili-hot-search",
    "toutiao":     "toutiao",
    "douyin":      "douyin",
    "github":      "github-trending-today",
    "coolapk":     "coolapk",
    "tieba":       "tieba",
    "wallstreetcn": "wallstreetcn",
    "thepaper":    "thepaper",
    "cls":         "cls-hot",
    "xueqiu":      "xueqiu",
    # Experimental — not in BettaFish's confirmed list
    "wechat":      "wechat",
    "kuaishou":    "kuaishou",
}

SOURCE_NAMES = {
    "weibo":       "微博热搜",
    "zhihu":       "知乎热榜",
    "bilibili":    "B站热搜",
    "toutiao":     "今日头条",
    "douyin":      "抖音热榜",
    "github":      "GitHub趋势",
    "coolapk":     "酷安热榜",
    "tieba":       "百度贴吧",
    "wallstreetcn": "华尔街见闻",
    "thepaper":    "澎湃新闻",
    "cls":         "财联社",
    "xueqiu":      "雪球热榜",
    "wechat":      "微信热文",
    "kuaishou":    "快手热门",
}


def fetch(source_name: str) -> list[dict]:
    """Fetch hot items from one source via newsnow.busiyi.world.

    Returns list[dict] with keys: title, url, heat, rank.
    Raises RuntimeError on failure.
    """
    source_id = SOURCE_IDS.get(source_name)
    if not source_id:
        raise RuntimeError(f"Unknown newsnow source: {source_name}")

    url = f"{BASE_URL}/api/s?id={source_id}&latest"
    headers = dict(HEADERS)
    headers["Referer"] = BASE_URL

    resp = requests.get(url, headers=headers, timeout=20)
    resp.raise_for_status()

    # Detect Cloudflare or other HTML responses
    ct = resp.headers.get("Content-Type", "")
    if "html" in ct or resp.text.lstrip().startswith("<!DOCTYPE"):
        raise RuntimeError(
            f"newsnow API returned HTML (likely blocked by Cloudflare) "
            f"for source '{source_name}'"
        )

    data = resp.json()
    raw_items = data.get("items", [])
    if isinstance(raw_items, dict):
        raw_items = raw_items.get("list", [])

    items = []
    for i, item in enumerate(raw_items, 1):
        title = (item.get("title") or "").strip()
        if not title:
            continue
        # Truncate excessively long titles (e.g. concatenated news blurbs)
        if len(title) > 120:
            title = title[:117] + "..."
        items.append({
            "title": title,
            "url": item.get("url", ""),
            "heat": str(item.get("heat") or item.get("hot") or ""),
            "rank": i,
        })
        if len(items) >= 10:
            break

    if not items:
        raise RuntimeError(
            f"newsnow returned no items for source '{source_name}'"
        )
    return items
