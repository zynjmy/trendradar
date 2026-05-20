#!/usr/bin/env python3
"""TrendRadar — zero-server sentiment monitoring.

Runs on GitHub Actions. Crawls hot topics from 6 Chinese platforms,
deduplicates against the previous run, pushes a markdown digest to
DingTalk (work notice or group webhook), and commits the results back
to the repo as an audit trail.

Usage:
    python main.py                     # print preview if no push config
    # 方案B (个人推送):
    DINGTALK_APP_KEY=... DINGTALK_APP_SECRET=... \
    DINGTALK_AGENT_ID=... DINGTALK_USER_IDS=... \
    python main.py
    # 方案A (群机器人):
    DINGTALK_WEBHOOK_URL=https://oapi.dingtalk.com/robot/send?access_token=... \
    python main.py
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Fix Windows console encoding for emoji/unicode
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
LATEST_FILE = DATA_DIR / "latest.json"
ARCHIVE_DIR = DATA_DIR / "archive"

CST = timezone(timedelta(hours=8))


# ── persistence ────────────────────────────────────────────────────────────

def _load_previous() -> dict[str, list[dict]]:
    if LATEST_FILE.exists():
        return json.loads(LATEST_FILE.read_text(encoding="utf-8"))
    return {}


def _save_current(snapshot: dict[str, list[dict]]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    LATEST_FILE.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    ts = datetime.now(CST).strftime("%Y%m%d_%H%M")
    (ARCHIVE_DIR / f"{ts}.json").write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ── dedup ──────────────────────────────────────────────────────────────────

def _new_items(items: list[dict], prev_items: list[dict]) -> list[dict]:
    seen = {p["title"] for p in prev_items}
    return [i for i in items if i["title"] not in seen]


# ── formatting ─────────────────────────────────────────────────────────────

_SOURCE_EMOJI = {
    "weibo":        "\U0001F4E2",
    "zhihu":        "\U0001F4A1",
    "baidu":        "\U0001F50D",
    "wechat":       "\U0001F4AC",
    "douyin":       "\U0001F3B5",
    "kuaishou":     "⚡",
    "bilibili":     "\U0001F3AC",
    "toutiao":      "\U0001F4F0",
    "tieba":        "\U0001F4AC",
    "thepaper":     "\U0001F4CB",
    "wallstreetcn": "\U0001F4C8",
    "cls":          "\U0001F3E6",
    "xueqiu":       "\U0001F4B0",
    "github":       "\U0001F4BB",
    "coolapk":      "\U0001F4F1",
}


def _count_total_items(all_results: list[dict]) -> int:
    return sum(len(e.get("items", [])) for e in all_results)


def _count_active_sources(all_results: list[dict]) -> int:
    return sum(1 for e in all_results if not e.get("error"))


def _collect_top_items(all_results: list[dict], n: int = 5) -> list[dict]:
    """Collect top items across all platforms sorted by rank."""
    collected = []
    for entry in all_results:
        if entry.get("error"):
            continue
        for item in entry.get("items", []):
            collected.append({
                "title": item["title"],
                "heat": item.get("heat", ""),
                "source": entry["source"],
                "display_name": entry["display_name"],
            })
    # Sort: prefer items with heat values, then by rank implicitly
    collected.sort(key=lambda x: x["heat"], reverse=True)
    return collected[:n]


def _format_report(all_results: list[dict]) -> str:
    now = datetime.now(CST).strftime("%Y-%m-%d %H:%M")
    total_items = _count_total_items(all_results)
    active_sources = _count_active_sources(all_results)
    total_sources = len(all_results)

    lines = [
        f"## \U0001F525 TrendRadar 舆情日报",
        f"### {now} (CST)",
        "",
        f"> \U0001F4CA {total_items} 条热闻 · {active_sources}/{total_sources} 平台在线",
        "",
    ]

    # Cross-platform TOP 5
    top_items = _collect_top_items(all_results, n=5)
    if top_items:
        lines.append("### \U0001F3AF 跨平台热闻 TOP 5")
        lines.append("")
        for i, item in enumerate(top_items, 1):
            emoji = _SOURCE_EMOJI.get(item["source"], "\U0001F4CC")
            title = item["title"].replace("[", "【").replace("]", "】")
            heat_str = f"  \U0001F525{item['heat']}" if item.get("heat") else ""
            lines.append(f"{i}. {emoji} {title}{heat_str}")
        lines.append("")

    lines.append("---")
    lines.append("### \U0001F4E1 各平台详情")
    lines.append("")

    for entry in all_results:
        emoji = _SOURCE_EMOJI.get(entry["source"], "\U0001F4CC")
        name = entry["display_name"]
        items = entry["items"]
        error = entry.get("error")

        lines.append(f"**{emoji} {name}**  ")
        if error:
            lines.append(f"> ⚠️ {error}")
        elif not items:
            lines.append("> 暂无新内容")
        else:
            for i, item in enumerate(items, 1):
                title = item["title"].replace("[", "【").replace("]", "】")
                url = item.get("url", "")
                heat = item.get("heat", "")
                heat_str = f"  \U0001F525{heat}" if heat else ""
                if url:
                    lines.append(f"{i}. [{title}]({url}){heat_str}")
                else:
                    lines.append(f"{i}. {title}{heat_str}")
        lines.append("")

    lines.append("---")
    lines.append(f"> \U0001F4CA 数据更新: {now} CST  |  \U0001F916 由 TrendRadar 自动生成")
    return "\n".join(lines)


# ── main ───────────────────────────────────────────────────────────────────

def main() -> None:
    from crawlers.weibo import crawl as weibo_crawl
    from crawlers.zhihu import crawl as zhihu_crawl
    from crawlers.baidu import crawl as baidu_crawl
    from crawlers.douyin import crawl as douyin_crawl
    from crawlers.newsnow import fetch as newsnow_fetch

    crawlers = [
        # Direct official APIs (most reliable)
        ("weibo",    "微博热搜",  weibo_crawl),
        ("zhihu",    "知乎热榜",  zhihu_crawl),
        ("baidu",    "百度热搜",  baidu_crawl),
        # newsnow aggregator
        ("douyin",   "抖音热点",  douyin_crawl),
        ("bilibili", "B站热搜",   lambda: newsnow_fetch("bilibili")),
        ("toutiao",  "今日头条",  lambda: newsnow_fetch("toutiao")),
        ("tieba",    "百度贴吧",  lambda: newsnow_fetch("tieba")),
        ("thepaper", "澎湃新闻",  lambda: newsnow_fetch("thepaper")),
        ("wallstreetcn", "华尔街见闻", lambda: newsnow_fetch("wallstreetcn")),
        ("cls",      "财联社",    lambda: newsnow_fetch("cls")),
        ("xueqiu",   "雪球热榜",  lambda: newsnow_fetch("xueqiu")),
        ("github",   "GitHub趋势", lambda: newsnow_fetch("github")),
        ("coolapk",  "酷安热榜",  lambda: newsnow_fetch("coolapk")),
        # wechat/kuaishou: no stable public API available (2026-05)
    ]

    previous = _load_previous()
    all_results: list[dict] = []
    current: dict[str, list[dict]] = {}

    for source_id, display_name, crawl_func in crawlers:
        try:
            print(f"[{source_id}] crawling ...")
            from crawlers.retry import retry_call
            items = retry_call(crawl_func)
            prev = previous.get(source_id, [])
            fresh = _new_items(items, prev)
            print(f"  {len(items)} total, {len(fresh)} new")

            all_results.append({
                "source": source_id,
                "display_name": display_name,
                "items": fresh if fresh else items[:5],
            })
            current[source_id] = items

        except Exception as exc:
            print(f"  ✗ {exc}")
            all_results.append({
                "source": source_id,
                "display_name": display_name,
                "items": [],
                "error": str(exc),
            })
            current[source_id] = previous.get(source_id, [])

    _save_current(current)

    # ── notify ────────────────────────────────────────────────────────
    md = _format_report(all_results)

    # Optional AI insight (only when TREND_LLM_API_KEY is set)
    from analyst.summarizer import summarize
    insight = summarize(all_results)
    if insight:
        md += "\n\n---\n## \U0001F9E0 AI 跨平台洞察\n\n" + insight

    from notifier.dingtalk import send

    # Auto-detect: work notice (方案B) > webhook (方案A) > print preview
    has_work_notice = bool(os.environ.get("DINGTALK_APP_KEY"))
    has_webhook = bool(os.environ.get("DINGTALK_WEBHOOK_URL"))

    if has_work_notice or has_webhook:
        try:
            send("\U0001F514 TrendRadar 舆情日报", md)
            print("✅ 推送成功")
        except Exception as exc:
            print(f"❌ 推送失败: {exc}")
            sys.exit(1)
    else:
        print("\n⚠️ 未配置钉钉推送 — 仅打印预览\n")
        print(md)


if __name__ == "__main__":
    main()
