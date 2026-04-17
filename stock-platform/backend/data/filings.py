from __future__ import annotations

import os
from functools import lru_cache
from datetime import datetime
from typing import Optional

import requests


SEC_BASE = "https://data.sec.gov"
SEC_WWW = "https://www.sec.gov"


def _headers() -> dict:
    ua = os.getenv("SEC_USER_AGENT", "StockPlatform research@example.com")
    return {"User-Agent": ua, "Accept": "application/json"}


@lru_cache(maxsize=1)
def _ticker_to_cik_map() -> dict:
    url = f"{SEC_WWW}/files/company_tickers.json"
    try:
        r = requests.get(url, headers=_headers(), timeout=15)
        r.raise_for_status()
        data = r.json()
    except Exception:
        return {}
    out = {}
    for row in data.values():
        out[row["ticker"].upper()] = str(row["cik_str"]).zfill(10)
    return out


def ticker_to_cik(ticker: str) -> Optional[str]:
    return _ticker_to_cik_map().get(ticker.upper())


@lru_cache(maxsize=32)
def _cached_filings(cik: str, cache_bucket: int) -> dict:
    del cache_bucket
    url = f"{SEC_BASE}/submissions/CIK{cik}.json"
    try:
        r = requests.get(url, headers=_headers(), timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception:
        return {}


def list_filings(ticker: str, forms: tuple = ("10-K", "10-Q", "8-K"), limit: int = 10) -> list[dict]:
    cik = ticker_to_cik(ticker)
    if not cik:
        return []
    bucket = int(datetime.utcnow().timestamp() // (6 * 60 * 60))
    data = _cached_filings(cik, bucket)
    recent = data.get("filings", {}).get("recent", {})
    if not recent:
        return []

    results = []
    n = len(recent.get("accessionNumber", []))
    for i in range(n):
        form = recent["form"][i]
        if form not in forms:
            continue
        accession = recent["accessionNumber"][i].replace("-", "")
        primary_doc = recent["primaryDocument"][i]
        filed = recent["filingDate"][i]
        report_date = recent.get("reportDate", [""] * n)[i]
        url = f"{SEC_WWW}/Archives/edgar/data/{int(cik)}/{accession}/{primary_doc}"
        results.append({
            "form": form,
            "filed": filed,
            "report_date": report_date,
            "url": url,
            "accession": recent["accessionNumber"][i],
        })
        if len(results) >= limit:
            break
    return results


def fetch_filing_text(url: str, max_chars: int = 400_000) -> str:
    r = requests.get(url, headers={**_headers(), "Accept": "text/html"}, timeout=30)
    r.raise_for_status()
    html = r.text
    # crude HTML->text stripping to keep deps minimal
    import re
    text = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]
