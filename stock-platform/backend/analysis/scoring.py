from __future__ import annotations

from typing import Optional


def _clip(v: float, lo: float = 0, hi: float = 100) -> float:
    return max(lo, min(hi, v))


def technical_score(tech: dict) -> dict:
    if not tech or tech.get("insufficient_data"):
        return {"score": None, "components": {}, "notes": ["Insufficient price history"]}

    components = {}
    notes = []
    signals = tech.get("trend_signals", [])

    trend = 50
    if "above_sma50" in signals:
        trend += 10
    else:
        trend -= 10
    if "above_sma200" in signals:
        trend += 15
    else:
        trend -= 15
    if "golden_cross" in signals:
        trend += 10
    elif "death_cross" in signals:
        trend -= 10
    components["trend"] = _clip(trend)

    rsi_val = tech.get("rsi14")
    if rsi_val is None:
        components["momentum"] = 50
    else:
        # peak score near 60 (strong but not overbought)
        if rsi_val <= 30:
            m = 30 + rsi_val  # oversold: 30-60
        elif rsi_val <= 60:
            m = 50 + (rsi_val - 30)  # rising: 50-80
        elif rsi_val <= 70:
            m = 80 - (rsi_val - 60) * 2  # 80 -> 60
        else:
            m = max(20, 60 - (rsi_val - 70) * 2)  # overbought: drop
        components["momentum"] = _clip(m)

    macd_state = tech.get("macd_state")
    macd_map = {"bullish_cross": 85, "bullish": 65, "bearish": 35, "bearish_cross": 15}
    components["macd"] = macd_map.get(macd_state, 50)

    pct_high = tech.get("pct_from_52w_high")
    if pct_high is None:
        components["position"] = 50
    else:
        # closer to 52w high = stronger, but not penalized for new highs
        components["position"] = _clip(80 + pct_high)  # pct_high is <= 0

    score = sum(components.values()) / len(components)
    if rsi_val and rsi_val >= 70:
        notes.append(f"RSI {rsi_val:.0f} indicates overbought conditions.")
    if "death_cross" in signals:
        notes.append("SMA50 below SMA200 (death cross).")
    if "golden_cross" in signals:
        notes.append("SMA50 above SMA200 (golden cross).")

    return {"score": round(score, 1), "components": {k: round(v, 1) for k, v in components.items()}, "notes": notes}


def fundamental_score(fund: dict) -> dict:
    val = fund.get("valuation", {})
    prof = fund.get("profitability", {})
    growth = fund.get("growth", {})
    bs = fund.get("balance_sheet", {})

    components = {}
    notes = []

    pe = val.get("pe_trailing")
    if pe is None or pe <= 0:
        components["valuation"] = 40
        if pe is not None and pe <= 0:
            notes.append("Negative earnings - P/E not meaningful.")
    else:
        if pe < 10:
            v = 85
        elif pe < 20:
            v = 70
        elif pe < 30:
            v = 55
        elif pe < 50:
            v = 40
        else:
            v = 25
        components["valuation"] = v

    roe = prof.get("roe")
    margin = prof.get("profit_margin")
    prof_score = 50
    if roe is not None:
        prof_score += _clip(roe * 100, -30, 40) / 2
    if margin is not None:
        prof_score += _clip(margin * 100, -30, 40) / 2
    components["profitability"] = _clip(prof_score)

    rev_g = growth.get("revenue_growth_yoy")
    earn_g = growth.get("earnings_growth_yoy")
    g = 50
    if rev_g is not None:
        g += _clip(rev_g * 100, -30, 30) / 2
    if earn_g is not None:
        g += _clip(earn_g * 100, -30, 30) / 2
    components["growth"] = _clip(g)

    de = bs.get("debt_to_equity")
    cr = bs.get("current_ratio")
    hs = 50
    if de is not None:
        if de < 30:
            hs += 20
        elif de < 100:
            hs += 5
        elif de < 200:
            hs -= 10
        else:
            hs -= 20
            notes.append(f"High debt/equity: {de:.0f}.")
    if cr is not None:
        if cr >= 1.5:
            hs += 10
        elif cr < 1:
            hs -= 15
            notes.append(f"Current ratio {cr:.2f} below 1 - liquidity concern.")
    components["balance_sheet"] = _clip(hs)

    score = sum(components.values()) / len(components)
    return {"score": round(score, 1), "components": {k: round(v, 1) for k, v in components.items()}, "notes": notes}


def sentiment_score_from_llm(sentiment: Optional[dict]) -> dict:
    if not sentiment or "sentiment_score" not in sentiment:
        return {"score": None, "label": None, "notes": ["No sentiment data available."]}
    raw = sentiment.get("sentiment_score")
    try:
        raw = float(raw)
    except Exception:
        return {"score": None, "label": sentiment.get("sentiment_label"), "notes": []}
    score = _clip(50 + raw / 2)  # map -100..100 -> 0..100
    return {"score": round(score, 1), "label": sentiment.get("sentiment_label"), "notes": []}


def combined_score(tech_s: dict, fund_s: dict, sent_s: dict) -> dict:
    weights = []
    if tech_s.get("score") is not None:
        weights.append(("technical", tech_s["score"], 0.35))
    if fund_s.get("score") is not None:
        weights.append(("fundamental", fund_s["score"], 0.45))
    if sent_s.get("score") is not None:
        weights.append(("sentiment", sent_s["score"], 0.20))

    if not weights:
        return {"score": None, "rating": "insufficient_data"}

    total_w = sum(w for _, _, w in weights)
    composite = sum(s * w for _, s, w in weights) / total_w

    if composite >= 75:
        rating = "strong"
    elif composite >= 60:
        rating = "favorable"
    elif composite >= 45:
        rating = "neutral"
    elif composite >= 30:
        rating = "weak"
    else:
        rating = "poor"

    return {
        "score": round(composite, 1),
        "rating": rating,
        "weights": {name: w for name, _, w in weights},
        "disclaimer": "This score is for research purposes only and does not constitute investment advice.",
    }
