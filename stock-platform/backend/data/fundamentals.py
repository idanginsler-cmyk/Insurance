from __future__ import annotations

from functools import lru_cache
from datetime import datetime

import yfinance as yf


def _safe(value):
    if value is None:
        return None
    try:
        if isinstance(value, float) and (value != value):  # NaN
            return None
    except Exception:
        pass
    return value


@lru_cache(maxsize=64)
def _cached_info(ticker: str, cache_bucket: int) -> dict:
    del cache_bucket
    tk = yf.Ticker(ticker)
    try:
        return dict(tk.info)
    except Exception:
        return {}


def get_fundamentals(ticker: str) -> dict:
    bucket = int(datetime.utcnow().timestamp() // (6 * 60 * 60))  # 6h cache
    info = _cached_info(ticker.upper(), bucket)

    return {
        "ticker": ticker.upper(),
        "name": info.get("longName") or info.get("shortName"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "country": info.get("country"),
        "website": info.get("website"),
        "summary": info.get("longBusinessSummary"),
        "employees": _safe(info.get("fullTimeEmployees")),
        "valuation": {
            "market_cap": _safe(info.get("marketCap")),
            "enterprise_value": _safe(info.get("enterpriseValue")),
            "pe_trailing": _safe(info.get("trailingPE")),
            "pe_forward": _safe(info.get("forwardPE")),
            "peg_ratio": _safe(info.get("pegRatio")),
            "price_to_book": _safe(info.get("priceToBook")),
            "price_to_sales": _safe(info.get("priceToSalesTrailing12Months")),
            "ev_to_ebitda": _safe(info.get("enterpriseToEbitda")),
        },
        "profitability": {
            "profit_margin": _safe(info.get("profitMargins")),
            "operating_margin": _safe(info.get("operatingMargins")),
            "gross_margin": _safe(info.get("grossMargins")),
            "roe": _safe(info.get("returnOnEquity")),
            "roa": _safe(info.get("returnOnAssets")),
        },
        "growth": {
            "revenue_growth_yoy": _safe(info.get("revenueGrowth")),
            "earnings_growth_yoy": _safe(info.get("earningsGrowth")),
            "earnings_quarterly_growth": _safe(info.get("earningsQuarterlyGrowth")),
        },
        "balance_sheet": {
            "total_cash": _safe(info.get("totalCash")),
            "total_debt": _safe(info.get("totalDebt")),
            "debt_to_equity": _safe(info.get("debtToEquity")),
            "current_ratio": _safe(info.get("currentRatio")),
            "quick_ratio": _safe(info.get("quickRatio")),
            "book_value": _safe(info.get("bookValue")),
        },
        "dividend": {
            "yield": _safe(info.get("dividendYield")),
            "rate": _safe(info.get("dividendRate")),
            "payout_ratio": _safe(info.get("payoutRatio")),
        },
        "analyst": {
            "recommendation_mean": _safe(info.get("recommendationMean")),
            "recommendation_key": info.get("recommendationKey"),
            "target_mean": _safe(info.get("targetMeanPrice")),
            "target_high": _safe(info.get("targetHighPrice")),
            "target_low": _safe(info.get("targetLowPrice")),
            "num_analysts": _safe(info.get("numberOfAnalystOpinions")),
        },
    }
