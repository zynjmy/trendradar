"""Lightweight cross-platform trend summarizer.

Adapted from BettaFish/MindSpider/BroadTopicExtraction/topic_extractor.py.
Only activates when TREND_LLM_API_KEY is set in the environment.
When the key is absent or the LLM call fails, returns None silently —
the report renders exactly as before.
"""
import json
import os
import re

_INSIGHT_PROMPT = """请分析以下来自多个中文平台的热搜标题，写一段100-200字的跨平台舆情洞察。

热点标题：
{headlines}

要求：
1. 找出跨平台共同出现的热点主题（至少2个平台同时出现）
2. 指出当前最受关注的社会情绪方向
3. 语言简洁，客观中性，不要评价性语言

请以JSON格式输出（不要包含其他文字）：
{{"insight": "你的洞察段落..."}}"""


def _build_headlines_text(all_results: list[dict]) -> str:
    lines = []
    for entry in all_results:
        if entry.get("error"):
            continue
        name = entry.get("display_name", entry.get("source", "?"))
        for item in entry.get("items", []):
            title = item["title"].replace("[", "【").replace("]", "】")
            lines.append(f"- [{name}] {title}")
    return "\n".join(lines)


def summarize(all_results: list[dict]) -> str | None:
    """Return a one-paragraph cross-platform insight, or None.

    Requires TREND_LLM_API_KEY env var. Set TREND_LLM_BASE_URL and
    TREND_LLM_MODEL to override defaults.
    """
    api_key = (os.environ.get("TREND_LLM_API_KEY") or "").strip()
    if not api_key:
        return None

    base_url = (os.environ.get("TREND_LLM_BASE_URL") or "https://api.deepseek.com").strip()
    model = (os.environ.get("TREND_LLM_MODEL") or "deepseek-chat").strip()

    headlines = _build_headlines_text(all_results)
    if not headlines.strip():
        return None

    prompt = _INSIGHT_PROMPT.format(headlines=headlines)

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=base_url)
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.5,
            timeout=60,
        )
        content = resp.choices[0].message.content or ""

        # Strip markdown code fences if present
        content = re.sub(r"```(?:json)?\s*", "", content)
        content = re.sub(r"```", "", content)
        content = content.strip()

        # Try JSON parse: first regex extraction, then full parse
        match = re.search(r'"insight"\s*:\s*"((?:[^"\\]|\\.)*)"', content)
        if match:
            raw = match.group(1)
            return raw.encode().decode("unicode_escape") if "\\u" in raw else raw
        try:
            data = json.loads(content)
            return data.get("insight", "")
        except json.JSONDecodeError:
            pass
        # Last resort: return the raw content if it looks like natural text
        if len(content) > 20:
            return content
    except Exception as exc:
        print(f"  [analyst] LLM summarization failed: {exc}")
        return None
