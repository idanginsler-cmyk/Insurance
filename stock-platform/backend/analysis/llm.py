from __future__ import annotations

import os
import json
from functools import lru_cache
from typing import Optional

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None


MODEL = "claude-sonnet-4-6"


def _client() -> Optional["Anthropic"]:
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key or not Anthropic:
        return None
    return Anthropic(api_key=key)


def llm_available() -> bool:
    return _client() is not None


SYSTEM_FILING = """You are a seasoned equity research analyst reading an SEC filing.
Return a strict JSON object with these fields:
- headline: one-sentence takeaway (string)
- key_numbers: array of {metric, value, yoy_change, note} objects for the most important financials
- business_highlights: array of 3-6 bullet strings (positive developments)
- risks: array of 3-6 bullet strings (explicit risks / concerns from the filing)
- red_flags: array of {flag, evidence} objects for subtle concerns a careful reader should notice (accounting policy changes, going-concern language, related-party transactions, unusual footnotes, restatements, auditor issues, large one-time items, rising receivables vs revenue, inventory buildup). Empty array if none found.
- guidance: short string summarizing forward-looking statements, or null
- overall_tone: one of "bullish", "neutral", "cautious", "bearish"
Respond with ONLY the JSON object. No markdown fences, no commentary."""


SYSTEM_NEWS = """You are a market sentiment analyst. Given recent news headlines for a stock,
return a strict JSON object:
- sentiment_score: number from -100 (very bearish) to 100 (very bullish)
- sentiment_label: one of "very_bearish","bearish","neutral","bullish","very_bullish"
- themes: array of 2-5 short strings describing recurring topics
- notable_items: array of up to 5 {title, take} objects highlighting the most market-moving items
Respond with ONLY the JSON object."""


def _parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    try:
        return json.loads(text)
    except Exception:
        # try to find first { ... }
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            try:
                return json.loads(text[start:end + 1])
            except Exception:
                pass
        return {"error": "failed_to_parse", "raw": text[:1000]}


@lru_cache(maxsize=32)
def _cached_filing_summary(ticker: str, filing_url: str, text_hash: int, text: str) -> dict:
    del text_hash
    client = _client()
    if not client:
        return {"error": "no_api_key", "message": "Set ANTHROPIC_API_KEY to enable LLM analysis."}

    msg = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        system=SYSTEM_FILING,
        messages=[{
            "role": "user",
            "content": f"Ticker: {ticker}\nFiling URL: {filing_url}\n\nFiling text (may be truncated):\n\n{text}",
        }],
    )
    out = _parse_json(msg.content[0].text)
    out["_meta"] = {"model": MODEL, "filing_url": filing_url}
    return out


def summarize_filing(ticker: str, filing_url: str, text: str) -> dict:
    return _cached_filing_summary(ticker, filing_url, hash(text), text)


@lru_cache(maxsize=64)
def _cached_news_sentiment(ticker: str, payload_hash: int, payload: str) -> dict:
    del payload_hash
    client = _client()
    if not client:
        return {"error": "no_api_key", "message": "Set ANTHROPIC_API_KEY to enable sentiment analysis."}

    msg = client.messages.create(
        model=MODEL,
        max_tokens=800,
        system=SYSTEM_NEWS,
        messages=[{"role": "user", "content": f"Ticker: {ticker}\n\nHeadlines (JSON):\n{payload}"}],
    )
    return _parse_json(msg.content[0].text)


def news_sentiment(ticker: str, headlines: list[dict]) -> dict:
    slim = [{"title": h.get("title"), "publisher": h.get("publisher"), "published": h.get("published")}
            for h in headlines[:15]]
    payload = json.dumps(slim, ensure_ascii=False)
    return _cached_news_sentiment(ticker, hash(payload), payload)
