from __future__ import annotations

import pandas as pd
import numpy as np


def sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window=window, min_periods=window).mean()


def ema(series: pd.Series, window: int) -> pd.Series:
    return series.ewm(span=window, adjust=False).mean()


def rsi(series: pd.Series, window: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / window, adjust=False).mean()
    loss = -delta.clip(upper=0).ewm(alpha=1 / window, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    out = 100 - (100 / (1 + rs))
    return out.fillna(50)


def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    macd_line = ema(series, fast) - ema(series, slow)
    signal_line = ema(macd_line, signal)
    hist = macd_line - signal_line
    return pd.DataFrame({"macd": macd_line, "signal": signal_line, "hist": hist})


def bollinger(series: pd.Series, window: int = 20, num_std: float = 2.0) -> pd.DataFrame:
    mid = sma(series, window)
    std = series.rolling(window=window, min_periods=window).std()
    return pd.DataFrame({
        "mid": mid,
        "upper": mid + num_std * std,
        "lower": mid - num_std * std,
    })


def enrich(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    close = out["Close"]
    out["sma20"] = sma(close, 20)
    out["sma50"] = sma(close, 50)
    out["sma200"] = sma(close, 200)
    out["rsi14"] = rsi(close, 14)
    m = macd(close)
    out["macd"] = m["macd"]
    out["macd_signal"] = m["signal"]
    out["macd_hist"] = m["hist"]
    b = bollinger(close)
    out["bb_upper"] = b["upper"]
    out["bb_lower"] = b["lower"]
    return out


def technical_snapshot(df: pd.DataFrame) -> dict:
    if df.empty or len(df) < 50:
        return {"insufficient_data": True}

    enriched = enrich(df)
    last = enriched.iloc[-1]
    prev = enriched.iloc[-2] if len(enriched) >= 2 else last

    def _f(v):
        try:
            if pd.isna(v):
                return None
            return float(v)
        except Exception:
            return None

    trend_signals = []
    close = _f(last["Close"])
    sma50v = _f(last["sma50"])
    sma200v = _f(last["sma200"])
    if close and sma50v:
        trend_signals.append("above_sma50" if close > sma50v else "below_sma50")
    if close and sma200v:
        trend_signals.append("above_sma200" if close > sma200v else "below_sma200")
    if sma50v and sma200v:
        trend_signals.append("golden_cross" if sma50v > sma200v else "death_cross")

    rsi_val = _f(last["rsi14"])
    rsi_zone = None
    if rsi_val is not None:
        if rsi_val >= 70:
            rsi_zone = "overbought"
        elif rsi_val <= 30:
            rsi_zone = "oversold"
        else:
            rsi_zone = "neutral"

    macd_signal = None
    if _f(last["macd"]) is not None and _f(last["macd_signal"]) is not None:
        cur = last["macd"] - last["macd_signal"]
        prv = prev["macd"] - prev["macd_signal"]
        if prv <= 0 < cur:
            macd_signal = "bullish_cross"
        elif prv >= 0 > cur:
            macd_signal = "bearish_cross"
        else:
            macd_signal = "bullish" if cur > 0 else "bearish"

    # 52-week perf
    lookback = min(len(enriched), 252)
    window = enriched.tail(lookback)
    high52 = _f(window["High"].max())
    low52 = _f(window["Low"].min())
    pct_from_high = ((close - high52) / high52 * 100) if (close and high52) else None
    pct_from_low = ((close - low52) / low52 * 100) if (close and low52) else None

    return {
        "close": close,
        "sma20": _f(last["sma20"]),
        "sma50": sma50v,
        "sma200": sma200v,
        "rsi14": rsi_val,
        "rsi_zone": rsi_zone,
        "macd": _f(last["macd"]),
        "macd_signal_line": _f(last["macd_signal"]),
        "macd_hist": _f(last["macd_hist"]),
        "macd_state": macd_signal,
        "bb_upper": _f(last["bb_upper"]),
        "bb_lower": _f(last["bb_lower"]),
        "high_52w": high52,
        "low_52w": low52,
        "pct_from_52w_high": pct_from_high,
        "pct_from_52w_low": pct_from_low,
        "trend_signals": trend_signals,
    }
