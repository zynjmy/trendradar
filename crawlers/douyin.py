"""Douyin (TikTok CN) hot list crawler.

Backed by newsnow.busiyi.world aggregator API.
Reference: BettaFish/MindSpider/BroadTopicExtraction/get_today_news.py
"""
from crawlers.newsnow import fetch as newsnow_fetch


def crawl() -> list[dict]:
    """Return top-10 Douyin hot topics."""
    return newsnow_fetch("douyin")
