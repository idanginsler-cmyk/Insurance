from __future__ import annotations

from functools import lru_cache
from datetime import datetime, timedelta
from typing import Literal

import yfinance as yf
import pandas as pd

Period = Literal["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"]
Interval = Literal["1d", "1wk", "1mo"]


@lru_cache(maxsize=64)
def _cached_history(ticker: str, period: str, interval: str, cache_bucket: int) -> pd.DataFrame:
    # cache_bucket invalidates the cache every ~15 minutes to keep quotes fresh
    del cache_bucket
    tk = yf.Ticker(ticker)
    df = tk.history(period=period, interval=interval, auto_adjust=True)
    if df.empty:
        return df
    df.index = df.index.tz_localize(None) if df.index.tz is not None else df.index
    return df


def get_history(ticker: str, period: Period = "1y", interval: Interval = "1d") -> pd.DataFrame:
    bucket = int(datetime.utcnow().timestamp() // (15 * 60))
    return _cached_history(ticker.upper(), period, interval, bucket).copy()


def _safe_attr(obj, name):
    try:
        v = getattr(obj, name, None)
        if v is None:
            return None
        return v
    except Exception:
        return None


def get_quote(ticker: str) -> dict:
    tk = yf.Ticker(ticker.upper())
    info = tk.fast_info
    hist = get_history(ticker, period="5d", interval="1d")

    last = float(hist["Close"].iloc[-1]) if not hist.empty else None
    prev = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else None
    if last is None:
        last = _safe_attr(info, "last_price")
        last = float(last) if last is not None else None
    if prev is None:
        prev = _safe_attr(info, "previous_close")
        prev = float(prev) if prev is not None else None
    change = (last - prev) if (last is not None and prev is not None) else None
    change_pct = (change / prev * 100) if (change is not None and prev) else None

    def _num(x):
        try:
            return float(x) if x is not None else None
        except Exception:
            return None

    mcap = _safe_attr(info, "market_cap")
    return {
        "ticker": ticker.upper(),
        "price": last,
        "previous_close": prev,
        "change": change,
        "change_pct": change_pct,
        "day_high": _num(_safe_attr(info, "day_high")),
        "day_low": _num(_safe_attr(info, "day_low")),
        "year_high": _num(_safe_attr(info, "year_high")),
        "year_low": _num(_safe_attr(info, "year_low")),
        "currency": _safe_attr(info, "currency"),
        "market_cap": int(mcap) if mcap else None,
    }
