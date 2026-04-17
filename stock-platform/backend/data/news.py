from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache

import yfinance as yf


@lru_cache(maxsize=64)
def _cached_news(ticker: str, cache_bucket: int) -> list[dict]:
    del cache_bucket
    tk = yf.Ticker(ticker)
    try:
        items = tk.news or []
    except Exception:
        items = []
    out = []
    for it in items[:20]:
        # yfinance schema changed in 0.2.x - handle both shapes
        content = it.get("content") or it
        title = content.get("title") or it.get("title")
        publisher = (
            content.get("provider", {}).get("displayName")
            if isinstance(content.get("provider"), dict)
            else it.get("publisher")
        )
        link = (
            content.get("canonicalUrl", {}).get("url")
            if isinstance(content.get("canonicalUrl"), dict)
            else it.get("link")
        )
        ts = content.get("pubDate") or it.get("providerPublishTime")
        if isinstance(ts, (int, float)):
            published = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
        elif isinstance(ts, str):
            published = ts
        else:
            published = None
        summary = content.get("summary") or content.get("description")
        if not title:
            continue
        out.append({
            "title": title,
            "publisher": publisher,
            "link": link,
            "published": published,
            "summary": summary,
        })
    return out


def get_news(ticker: str) -> list[dict]:
    bucket = int(datetime.utcnow().timestamp() // (30 * 60))
    return _cached_news(ticker.upper(), bucket)
