"""Weibo hot search crawler.

Primary: weibo.com/ajax/side/hotSearch (web AJAX, clean JSON).
Fallback: m.weibo.cn mobile API (more stable, slightly different format).
"""

import requests

from crawlers._common import HEADERS

AJAX_URL = "https://weibo.com/ajax/side/hotSearch"
MOBILE_URL = (
    "https://m.weibo.cn/api/container/getIndex"
    "?containerid=106003type%3D25%26t%3D3%26disable_hot%3D1%26filter_type%3Drealtimehot"
)


def _parse_ajax(data: dict) -> list[dict]:
    items = []
    for item in data.get("data", {}).get("realtime", []):
        word = (item.get("word") or "").strip()
        if not word:
            continue
        url = item.get("word_scheme", "")
        if url and url.startswith("//"):
            url = "https:" + url
        items.append({
            "title": word,
            "url": url,
            "heat": str(item.get("num", "")),
            "rank": len(items) + 1,
        })
        if len(items) >= 10:
            break
    return items


def _parse_mobile(data: dict) -> list[dict]:
    items = []
    for card in data.get("data", {}).get("cards", []):
        for cg in card.get("card_group", []):
            title = (
                cg.get("desc")
                or cg.get("title_sub")
                or cg.get("title", "")
            ).strip()
            if not title:
                continue
            url = cg.get("scheme", "")
            if url and url.startswith("//"):
                url = "https:" + url
            heat = cg.get("desc_extr") or cg.get("desc1") or ""
            items.append({
                "title": title,
                "url": url,
                "heat": str(heat),
                "rank": len(items) + 1,
            })
            if len(items) >= 10:
                break
        if len(items) >= 10:
            break
    return items


def crawl() -> list[dict]:
    """Return top-10 Weibo hot search items.

    Tries the web AJAX API first; falls back to the mobile API if the
    response is empty (common when running without a login cookie).
    """
    session = requests.Session()
    session.headers.update(HEADERS)

    # --- attempt 1: web AJAX ---
    try:
        resp = session.get(
            AJAX_URL,
            headers={"Referer": "https://weibo.com/", "X-Requested-With": "XMLHttpRequest"},
            timeout=15,
        )
        if resp.status_code == 200:
            items = _parse_ajax(resp.json())
            if items:
                return items[:10]
    except Exception:
        pass

    # --- attempt 2: mobile API ---
    resp = session.get(
        MOBILE_URL,
        headers={"Referer": "https://m.weibo.cn/"},
        timeout=15,
    )
    resp.raise_for_status()
    return _parse_mobile(resp.json())[:10]
