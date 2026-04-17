// Deterministic synthetic AAPL-like data for demo.html
// Generated client-side so the file works when opened directly (file://).

(function () {
  // ---------- deterministic RNG (mulberry32) ----------
  function mulberry32(seed) {
    return function () {
      seed |= 0; seed = (seed + 0x6D2B79F5) | 0;
      let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  // ---------- generate ~1 year of business-day candles ----------
  function genCandles() {
    const rand = mulberry32(20250417);
    const candles = [];
    let close = 155.0;
    const today = new Date("2026-04-17");
    const start = new Date(today);
    start.setDate(start.getDate() - 370);
    for (let d = new Date(start); d <= today; d.setDate(d.getDate() + 1)) {
      const dow = d.getDay();
      if (dow === 0 || dow === 6) continue;
      const drift = 0.0010;
      const vol = 0.0165;
      const shock = (rand() - 0.5) * 2 * vol;
      const ret = drift + shock;
      const open = close * (1 + (rand() - 0.5) * 0.004);
      close = Math.max(10, open * (1 + ret));
      const hi = Math.max(open, close) * (1 + rand() * 0.009);
      const lo = Math.min(open, close) * (1 - rand() * 0.009);
      const vol_ = Math.floor(35e6 + rand() * 55e6);
      candles.push({
        t: d.toISOString().slice(0, 10),
        o: +open.toFixed(2), h: +hi.toFixed(2),
        l: +lo.toFixed(2), c: +close.toFixed(2), v: vol_,
      });
    }
    // anchor last close to displayed price
    candles[candles.length - 1].c = 192.47;
    candles[candles.length - 1].h = Math.max(candles[candles.length - 1].h, 193.2);
    candles[candles.length - 1].l = Math.min(candles[candles.length - 1].l, 190.9);
    return candles;
  }

  function sma(arr, w) {
    const out = new Array(arr.length).fill(null);
    let s = 0;
    for (let i = 0; i < arr.length; i++) {
      s += arr[i];
      if (i >= w) s -= arr[i - w];
      if (i >= w - 1) out[i] = s / w;
    }
    return out;
  }

  function ema(arr, w) {
    const k = 2 / (w + 1);
    const out = new Array(arr.length).fill(null);
    let prev = null;
    for (let i = 0; i < arr.length; i++) {
      if (prev == null) prev = arr[i];
      else prev = arr[i] * k + prev * (1 - k);
      out[i] = prev;
    }
    return out;
  }

  function rsi(arr, w = 14) {
    const out = new Array(arr.length).fill(null);
    let gainSum = 0, lossSum = 0;
    for (let i = 1; i < arr.length; i++) {
      const ch = arr[i] - arr[i - 1];
      const g = Math.max(0, ch), l = Math.max(0, -ch);
      if (i <= w) {
        gainSum += g; lossSum += l;
        if (i === w) {
          const rs = lossSum === 0 ? 100 : gainSum / lossSum;
          out[i] = 100 - 100 / (1 + rs);
        }
      } else {
        gainSum = (gainSum * (w - 1) + g) / w;
        lossSum = (lossSum * (w - 1) + l) / w;
        const rs = lossSum === 0 ? 100 : gainSum / lossSum;
        out[i] = 100 - 100 / (1 + rs);
      }
    }
    return out;
  }

  function macd(arr) {
    const ef = ema(arr, 12), es = ema(arr, 26);
    const line = arr.map((_, i) => (ef[i] != null && es[i] != null) ? ef[i] - es[i] : null);
    const clean = line.map(v => v == null ? 0 : v);
    const sig = ema(clean, 9).map((v, i) => line[i] == null ? null : v);
    const hist = line.map((v, i) => v == null || sig[i] == null ? null : v - sig[i]);
    return { line, sig, hist };
  }

  function bollinger(arr, w = 20, k = 2) {
    const m = sma(arr, w);
    const upper = new Array(arr.length).fill(null);
    const lower = new Array(arr.length).fill(null);
    for (let i = w - 1; i < arr.length; i++) {
      let s = 0;
      for (let j = i - w + 1; j <= i; j++) s += (arr[j] - m[i]) ** 2;
      const sd = Math.sqrt(s / w);
      upper[i] = m[i] + k * sd;
      lower[i] = m[i] - k * sd;
    }
    return { upper, lower };
  }

  // ---------- build chart datasets ----------
  const candles = genCandles();
  const closes = candles.map(c => c.c);
  const sma50 = sma(closes, 50);
  const sma200 = sma(closes, 200);
  const rsi14 = rsi(closes, 14);
  const md = macd(closes);
  const bb = bollinger(closes, 20, 2);

  const last = candles.length - 1;
  window.__DEMO__ = { candles, sma50, sma200, rsi14, md, bb, last };

  // ---------- fundamentals & filing & news fixtures ----------
  window.__FIXTURES__ = {
    fundamentals: {
      valuation: {
        "Market Cap": "2.97T", "Enterprise Value": "2.95T",
        "P/E (trailing)": "31.4", "P/E (forward)": "27.9",
        "PEG": "2.10", "P/B": "48.6", "P/S": "7.85", "EV/EBITDA": "22.7",
      },
      profitability: {
        "Gross margin": "44.10%", "Operating margin": "29.85%",
        "Net margin": "25.31%", "ROE": "156.10%", "ROA": "27.50%",
      },
      growth: {
        "Revenue (YoY)": "4.90%", "Earnings (YoY)": "7.70%",
        "Earnings (Q, YoY)": "9.10%",
      },
      balance_sheet: {
        "Cash": "67.15B", "Debt": "104.6B", "Debt/Equity": "180.2",
        "Current ratio": "0.98", "Book value": "3.96",
      },
      dividend: {
        "Yield": "0.49%", "Rate": "0.96", "Payout ratio": "15.40%",
      },
      analyst: {
        "Recommendation": "buy", "Mean rating": "1.9",
        "Target (mean)": "215.40", "Target range": "178.00 – 260.00", "# analysts": "41",
      },
    },
    filing: {
      form: "10-Q", filed: "2026-02-01",
      url: "https://www.sec.gov/Archives/edgar/data/320193/demo.htm",
      summary: {
        overall_tone: "neutral",
        headline: "Services revenue sets a record but iPhone unit growth stalls as China demand weakens.",
        key_numbers: [
          { metric: "Total revenue", value: "$119.6B", yoy_change: "+2%", note: "Beat consensus by ~0.7B" },
          { metric: "Services revenue", value: "$23.1B", yoy_change: "+11%", note: "All-time high; record gross margin 72.9%" },
          { metric: "iPhone revenue", value: "$69.7B", yoy_change: "-1%", note: "Greater China down 13% YoY" },
          { metric: "Operating cash flow", value: "$39.9B", yoy_change: "+3%", note: "Capex held flat" },
          { metric: "EPS (diluted)", value: "$2.18", yoy_change: "+16%", note: "Buybacks reduced share count ~3%" },
        ],
        business_highlights: [
          "Services segment reached 1B+ paid subscriptions - first time disclosed this quarter.",
          "App Store and advertising revenue grew double-digits despite regulatory headwinds in EU.",
          "Gross margin expanded 130bps YoY on favorable product mix.",
          "Returned $27B to shareholders via buybacks and dividends.",
        ],
        risks: [
          "Greater China revenue contracted 13% YoY; management cited 'competitive dynamics'.",
          "EU Digital Markets Act compliance costs disclosed as 'material' but not quantified.",
          "Ongoing antitrust case (DOJ v. Apple) referenced with expanded legal reserves.",
          "FX headwind of ~2% on reported revenue; guidance assumes similar in next quarter.",
          "Wearables segment declined 2% YoY - first decline in 8 quarters.",
        ],
        red_flags: [
          { flag: "Deferred revenue jumped 12%", evidence: "Disclosed in Note 4 - may indicate aggressive revenue recognition shift; watch next quarter's recognition cadence." },
          { flag: "Inventory up 9% vs revenue +2%", evidence: "Channel inventory buildup in Asia-Pacific; potential writedown risk if demand stays soft." },
          { flag: "Auditor change not flagged but reserve bucket reclassified", evidence: "Footnote 11 moves $1.4B from 'other accrued' to 'contingent' - unusual reclassification." },
          { flag: "Stock-based comp up 14% while headcount flat", evidence: "Per-employee SBC rose notably; dilution offset depends on continued buybacks." },
        ],
        guidance: "Management guided Q3 revenue to flat-to-low-single-digit growth; Services expected to sustain double-digit expansion.",
      },
    },
    news: {
      sentiment: {
        sentiment_score: 42, sentiment_label: "bullish",
        themes: ["AI rollout", "Services growth", "China weakness", "Antitrust", "Buybacks"],
      },
      headlines: [
        { title: "Apple's Services Revenue Hits Record, Easing iPhone Slowdown Fears", publisher: "Bloomberg", published: "2026-04-16T14:20:00Z", link: "#" },
        { title: "Analysts Raise AAPL Price Targets After Upbeat Services Outlook", publisher: "Reuters", published: "2026-04-16T11:05:00Z", link: "#" },
        { title: "China iPhone Shipments Drop 13%, Pressuring Apple's Growth", publisher: "WSJ", published: "2026-04-15T22:40:00Z", link: "#" },
        { title: "Apple Intelligence Rollout Accelerates - On-Device Model Expands to iPad", publisher: "CNBC", published: "2026-04-15T18:10:00Z", link: "#" },
        { title: "DOJ Antitrust Case Against Apple: Key Hearing Set for Next Month", publisher: "Financial Times", published: "2026-04-14T09:30:00Z", link: "#" },
        { title: "Apple Announces $110B Buyback - Largest in Corporate History", publisher: "MarketWatch", published: "2026-04-13T20:00:00Z", link: "#" },
        { title: "Wearables Segment Declines for First Time in Two Years", publisher: "The Information", published: "2026-04-12T15:45:00Z", link: "#" },
        { title: "Vision Pro Sales Below Internal Targets, Sources Say", publisher: "Bloomberg", published: "2026-04-11T13:20:00Z", link: "#" },
      ],
    },
    technical: {
      "RSI 14": "58.4 (neutral)", "MACD state": "bullish",
      "SMA 50": "184.73", "SMA 200": "175.21",
      "52w high": "198.42", "52w low": "148.90",
      "From 52w high": "-3.0%",
      "Signals": "above_sma50, above_sma200, golden_cross",
    },
  };
})();
