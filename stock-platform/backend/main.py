from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Any, Optional

import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from data import prices, fundamentals, filings, news
from analysis import technical, llm, scoring


ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT / "frontend"

load_dotenv(ROOT / ".env")

def _sanitize(obj: Any) -> Any:
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize(v) for v in obj]
    return obj


class SafeJSONResponse(JSONResponse):
    def render(self, content: Any) -> bytes:
        return super().render(_sanitize(content))


app = FastAPI(title="Stock Research Platform", version="0.1.0", default_response_class=SafeJSONResponse)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "llm_available": llm.llm_available(),
    }


@app.get("/api/stock/{ticker}/overview")
def overview(ticker: str):
    try:
        quote = prices.get_quote(ticker)
        fund = fundamentals.get_fundamentals(ticker)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Data provider error: {e}")
    return {
        "quote": quote,
        "profile": {
            "name": fund.get("name"),
            "sector": fund.get("sector"),
            "industry": fund.get("industry"),
            "country": fund.get("country"),
            "website": fund.get("website"),
            "summary": fund.get("summary"),
            "employees": fund.get("employees"),
        },
    }


@app.get("/api/stock/{ticker}/prices")
def price_history(
    ticker: str,
    period: str = Query("1y"),
    interval: str = Query("1d"),
):
    df = prices.get_history(ticker, period=period, interval=interval)  # type: ignore[arg-type]
    if df.empty:
        raise HTTPException(status_code=404, detail="No price history available")
    enriched = technical.enrich(df)
    out = []
    for idx, row in enriched.iterrows():
        out.append({
            "t": idx.strftime("%Y-%m-%d"),
            "o": _f(row["Open"]),
            "h": _f(row["High"]),
            "l": _f(row["Low"]),
            "c": _f(row["Close"]),
            "v": _f(row["Volume"]),
            "sma20": _f(row.get("sma20")),
            "sma50": _f(row.get("sma50")),
            "sma200": _f(row.get("sma200")),
            "rsi14": _f(row.get("rsi14")),
            "macd": _f(row.get("macd")),
            "macd_signal": _f(row.get("macd_signal")),
            "macd_hist": _f(row.get("macd_hist")),
            "bb_upper": _f(row.get("bb_upper")),
            "bb_lower": _f(row.get("bb_lower")),
        })
    return {"ticker": ticker.upper(), "period": period, "interval": interval, "candles": out}


@app.get("/api/stock/{ticker}/fundamentals")
def get_fund(ticker: str):
    return fundamentals.get_fundamentals(ticker)


@app.get("/api/stock/{ticker}/technical")
def get_technical(ticker: str, period: str = "1y"):
    df = prices.get_history(ticker, period=period)  # type: ignore[arg-type]
    snap = technical.technical_snapshot(df)
    return {"ticker": ticker.upper(), "snapshot": snap}


@app.get("/api/stock/{ticker}/filings")
def list_filings(ticker: str, limit: int = 10):
    items = filings.list_filings(ticker, limit=limit)
    return {"ticker": ticker.upper(), "filings": items}


@app.get("/api/stock/{ticker}/filings/latest-summary")
def latest_filing_summary(ticker: str, form: str = "10-Q"):
    forms_filter = ("10-K",) if form.upper() == "10-K" else ("10-Q", "10-K")
    items = filings.list_filings(ticker, forms=forms_filter, limit=5)
    if not items:
        raise HTTPException(status_code=404, detail="No filings found")
    target = items[0]
    try:
        text = filings.fetch_filing_text(target["url"])
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch filing: {e}")
    summary = llm.summarize_filing(ticker.upper(), target["url"], text)
    return {"ticker": ticker.upper(), "filing": target, "summary": summary}


@app.get("/api/stock/{ticker}/news")
def get_news(ticker: str, analyze: bool = True):
    headlines = news.get_news(ticker)
    response: dict = {"ticker": ticker.upper(), "headlines": headlines}
    if analyze and headlines:
        response["sentiment"] = llm.news_sentiment(ticker.upper(), headlines)
    return response


@app.get("/api/stock/{ticker}/score")
def score(ticker: str, include_sentiment: bool = True):
    df = prices.get_history(ticker, period="1y")
    tech_snap = technical.technical_snapshot(df)
    fund = fundamentals.get_fundamentals(ticker)

    tech_s = scoring.technical_score(tech_snap)
    fund_s = scoring.fundamental_score(fund)

    sent_s = {"score": None}
    sentiment_raw = None
    if include_sentiment:
        headlines = news.get_news(ticker)
        if headlines:
            sentiment_raw = llm.news_sentiment(ticker.upper(), headlines)
            sent_s = scoring.sentiment_score_from_llm(sentiment_raw)

    combined = scoring.combined_score(tech_s, fund_s, sent_s)
    return {
        "ticker": ticker.upper(),
        "technical": tech_s,
        "fundamental": fund_s,
        "sentiment": sent_s,
        "sentiment_detail": sentiment_raw,
        "combined": combined,
    }


# ---- frontend serving ----
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    def root():
        index = FRONTEND_DIR / "index.html"
        if index.exists():
            return FileResponse(str(index))
        return {"status": "ok"}


def _f(v) -> Optional[float]:
    try:
        if v is None:
            return None
        if isinstance(v, float) and (v != v):
            return None
        if pd.isna(v):
            return None
        return float(v)
    except Exception:
        return None


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
