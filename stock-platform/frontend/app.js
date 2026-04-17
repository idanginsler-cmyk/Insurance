const API = "";  // same origin
let state = {
  ticker: "AAPL",
  period: "1y",
  candles: [],
  charts: { price: null, rsi: null, macd: null },
  series: {},
  showSma50: true,
  showSma200: true,
  showBB: false,
};

const $ = (sel) => document.querySelector(sel);

function fmt(n, digits = 2) {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  if (Math.abs(n) >= 1e12) return (n / 1e12).toFixed(digits) + "T";
  if (Math.abs(n) >= 1e9) return (n / 1e9).toFixed(digits) + "B";
  if (Math.abs(n) >= 1e6) return (n / 1e6).toFixed(digits) + "M";
  if (Math.abs(n) >= 1e3) return (n / 1e3).toFixed(digits) + "K";
  return Number(n).toFixed(digits);
}

function fmtPct(n, digits = 2) {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return (n * 100).toFixed(digits) + "%";
}

async function getJSON(url) {
  const r = await fetch(url);
  if (!r.ok) {
    const body = await r.text();
    throw new Error(`${r.status}: ${body}`);
  }
  return r.json();
}

async function checkHealth() {
  try {
    const h = await getJSON("/api/health");
    const badge = $("#llmBadge");
    if (h.llm_available) {
      badge.textContent = "LLM: on";
      badge.className = "badge ok";
    } else {
      badge.textContent = "LLM: off (set API key)";
      badge.className = "badge off";
    }
  } catch (e) {
    $("#llmBadge").textContent = "API down";
  }
}

async function loadOverview(ticker) {
  const data = await getJSON(`/api/stock/${ticker}/overview`);
  const q = data.quote, p = data.profile;
  $("#header").hidden = false;
  $("#name").textContent = p.name || ticker;
  $("#ticker").textContent = q.ticker;
  $("#exchange").textContent = q.currency || "";
  $("#sector").textContent = [p.sector, p.industry].filter(Boolean).join(" · ");
  $("#price").textContent = q.price !== null ? `${q.price.toFixed(2)} ${q.currency || ""}` : "—";
  const chgEl = $("#change");
  if (q.change !== null && q.change_pct !== null) {
    const sign = q.change >= 0 ? "+" : "";
    chgEl.textContent = `${sign}${q.change.toFixed(2)} (${sign}${q.change_pct.toFixed(2)}%)`;
    chgEl.className = "change " + (q.change >= 0 ? "up" : "down");
  } else {
    chgEl.textContent = "—";
  }
  $("#summary").textContent = p.summary || "";
}

async function loadPrices(ticker, period) {
  const data = await getJSON(`/api/stock/${ticker}/prices?period=${period}`);
  state.candles = data.candles;
  renderChart();
}

function renderChart() {
  const container = $("#priceChart");
  container.innerHTML = "";
  $("#rsiChart").innerHTML = "";
  $("#macdChart").innerHTML = "";

  const priceChart = LightweightCharts.createChart(container, {
    layout: { background: { color: "#1a2333" }, textColor: "#8aa0bd" },
    grid: { vertLines: { color: "#222d40" }, horzLines: { color: "#222d40" } },
    timeScale: { borderColor: "#222d40" },
    rightPriceScale: { borderColor: "#222d40" },
    crosshair: { mode: 1 },
  });
  const candle = priceChart.addCandlestickSeries({
    upColor: "#2ecc71", downColor: "#e74c3c",
    borderUpColor: "#2ecc71", borderDownColor: "#e74c3c",
    wickUpColor: "#2ecc71", wickDownColor: "#e74c3c",
  });
  candle.setData(state.candles.map(c => ({ time: c.t, open: c.o, high: c.h, low: c.l, close: c.c })));

  if (state.showSma50) {
    const s = priceChart.addLineSeries({ color: "#f1c40f", lineWidth: 1, title: "SMA50" });
    s.setData(state.candles.filter(c => c.sma50 !== null).map(c => ({ time: c.t, value: c.sma50 })));
  }
  if (state.showSma200) {
    const s = priceChart.addLineSeries({ color: "#4c8bf5", lineWidth: 1, title: "SMA200" });
    s.setData(state.candles.filter(c => c.sma200 !== null).map(c => ({ time: c.t, value: c.sma200 })));
  }
  if (state.showBB) {
    const up = priceChart.addLineSeries({ color: "#8aa0bd", lineWidth: 1, title: "BB Upper" });
    up.setData(state.candles.filter(c => c.bb_upper !== null).map(c => ({ time: c.t, value: c.bb_upper })));
    const lo = priceChart.addLineSeries({ color: "#8aa0bd", lineWidth: 1, title: "BB Lower" });
    lo.setData(state.candles.filter(c => c.bb_lower !== null).map(c => ({ time: c.t, value: c.bb_lower })));
  }
  priceChart.timeScale().fitContent();

  const rsiChart = LightweightCharts.createChart($("#rsiChart"), {
    layout: { background: { color: "#1a2333" }, textColor: "#8aa0bd" },
    grid: { vertLines: { color: "#222d40" }, horzLines: { color: "#222d40" } },
    timeScale: { borderColor: "#222d40", visible: false },
    rightPriceScale: { borderColor: "#222d40" },
  });
  const rsi = rsiChart.addLineSeries({ color: "#4c8bf5", lineWidth: 1, title: "RSI14" });
  rsi.setData(state.candles.filter(c => c.rsi14 !== null).map(c => ({ time: c.t, value: c.rsi14 })));
  rsi.createPriceLine({ price: 70, color: "#e74c3c", lineWidth: 1, lineStyle: 2 });
  rsi.createPriceLine({ price: 30, color: "#2ecc71", lineWidth: 1, lineStyle: 2 });
  rsiChart.timeScale().fitContent();

  const macdChart = LightweightCharts.createChart($("#macdChart"), {
    layout: { background: { color: "#1a2333" }, textColor: "#8aa0bd" },
    grid: { vertLines: { color: "#222d40" }, horzLines: { color: "#222d40" } },
    timeScale: { borderColor: "#222d40", visible: false },
    rightPriceScale: { borderColor: "#222d40" },
  });
  const macd = macdChart.addLineSeries({ color: "#4c8bf5", lineWidth: 1, title: "MACD" });
  macd.setData(state.candles.filter(c => c.macd !== null).map(c => ({ time: c.t, value: c.macd })));
  const sig = macdChart.addLineSeries({ color: "#f1c40f", lineWidth: 1, title: "Signal" });
  sig.setData(state.candles.filter(c => c.macd_signal !== null).map(c => ({ time: c.t, value: c.macd_signal })));
  const hist = macdChart.addHistogramSeries({ color: "#8aa0bd" });
  hist.setData(state.candles.filter(c => c.macd_hist !== null).map(c => ({
    time: c.t, value: c.macd_hist,
    color: c.macd_hist >= 0 ? "#2ecc71" : "#e74c3c",
  })));
  macdChart.timeScale().fitContent();

  state.charts = { price: priceChart, rsi: rsiChart, macd: macdChart };
}

async function loadTechSnapshot(ticker) {
  const data = await getJSON(`/api/stock/${ticker}/technical`);
  const s = data.snapshot || {};
  const grid = $("#techSnapshot");
  grid.innerHTML = "";
  const items = [
    ["RSI 14", s.rsi14 !== null ? `${s.rsi14?.toFixed(1)} (${s.rsi_zone || "—"})` : "—"],
    ["MACD state", s.macd_state || "—"],
    ["SMA 50", fmt(s.sma50)],
    ["SMA 200", fmt(s.sma200)],
    ["52w high", fmt(s.high_52w)],
    ["52w low", fmt(s.low_52w)],
    ["From 52w high", s.pct_from_52w_high !== null ? `${s.pct_from_52w_high?.toFixed(1)}%` : "—"],
    ["Signals", (s.trend_signals || []).join(", ") || "—"],
  ];
  items.forEach(([k, v]) => {
    const d = document.createElement("div");
    d.className = "kv";
    d.innerHTML = `<span class="k">${k}</span><span class="v">${v}</span>`;
    grid.appendChild(d);
  });
}

async function loadFundamentals(ticker) {
  const data = await getJSON(`/api/stock/${ticker}/fundamentals`);
  const grid = $("#fundGrid");
  grid.innerHTML = "";

  const sections = [
    ["Valuation", {
      "Market Cap": fmt(data.valuation.market_cap),
      "Enterprise Value": fmt(data.valuation.enterprise_value),
      "P/E (trailing)": fmt(data.valuation.pe_trailing),
      "P/E (forward)": fmt(data.valuation.pe_forward),
      "PEG": fmt(data.valuation.peg_ratio),
      "P/B": fmt(data.valuation.price_to_book),
      "P/S": fmt(data.valuation.price_to_sales),
      "EV/EBITDA": fmt(data.valuation.ev_to_ebitda),
    }],
    ["Profitability", {
      "Gross margin": fmtPct(data.profitability.gross_margin),
      "Operating margin": fmtPct(data.profitability.operating_margin),
      "Net margin": fmtPct(data.profitability.profit_margin),
      "ROE": fmtPct(data.profitability.roe),
      "ROA": fmtPct(data.profitability.roa),
    }],
    ["Growth (YoY)", {
      "Revenue": fmtPct(data.growth.revenue_growth_yoy),
      "Earnings": fmtPct(data.growth.earnings_growth_yoy),
      "Earnings (Q)": fmtPct(data.growth.earnings_quarterly_growth),
    }],
    ["Balance Sheet", {
      "Cash": fmt(data.balance_sheet.total_cash),
      "Debt": fmt(data.balance_sheet.total_debt),
      "Debt/Equity": fmt(data.balance_sheet.debt_to_equity),
      "Current ratio": fmt(data.balance_sheet.current_ratio),
      "Book value": fmt(data.balance_sheet.book_value),
    }],
    ["Dividend", {
      "Yield": fmtPct(data.dividend.yield),
      "Rate": fmt(data.dividend.rate),
      "Payout ratio": fmtPct(data.dividend.payout_ratio),
    }],
    ["Analyst Consensus", {
      "Recommendation": data.analyst.recommendation_key || "—",
      "Mean rating": fmt(data.analyst.recommendation_mean),
      "Target (mean)": fmt(data.analyst.target_mean),
      "Target range": `${fmt(data.analyst.target_low)} – ${fmt(data.analyst.target_high)}`,
      "# analysts": data.analyst.num_analysts || "—",
    }],
  ];

  sections.forEach(([title, kv]) => {
    const sec = document.createElement("div");
    sec.className = "kvsection";
    sec.innerHTML = `<h3>${title}</h3>`;
    const rows = document.createElement("div");
    rows.className = "kvgrid";
    Object.entries(kv).forEach(([k, v]) => {
      const d = document.createElement("div");
      d.className = "kv";
      d.innerHTML = `<span class="k">${k}</span><span class="v">${v}</span>`;
      rows.appendChild(d);
    });
    sec.appendChild(rows);
    grid.appendChild(sec);
  });
}

async function loadScore(ticker) {
  $("#score").hidden = false;
  $("#scoreNumber").textContent = "…";
  $("#scoreLabel").textContent = "computing";
  $("#scoreBars").innerHTML = `<div class="muted">Calculating combined score…</div>`;
  try {
    const data = await getJSON(`/api/stock/${ticker}/score`);
    const c = data.combined;
    $("#scoreNumber").textContent = c.score !== null ? c.score.toFixed(0) : "—";
    $("#scoreLabel").textContent = c.rating || "—";

    const parts = [
      ["Technical", data.technical],
      ["Fundamental", data.fundamental],
      ["Sentiment", data.sentiment],
    ];
    const bars = $("#scoreBars");
    bars.innerHTML = "";
    parts.forEach(([name, p]) => {
      const val = p && p.score;
      const row = document.createElement("div");
      row.className = "bar-row";
      const pct = val !== null && val !== undefined ? Math.max(0, Math.min(100, val)) : 0;
      const cls = val === null || val === undefined ? "" : val >= 60 ? "good" : val >= 40 ? "warn" : "bad";
      row.innerHTML = `
        <span>${name}</span>
        <span class="bar"><span class="${cls}" style="width:${pct}%"></span></span>
        <span>${val !== null && val !== undefined ? val.toFixed(0) : "—"}</span>
      `;
      bars.appendChild(row);
    });
  } catch (e) {
    $("#scoreBars").innerHTML = `<div class="error">Score failed: ${e.message}</div>`;
  }
}

async function loadNews(ticker) {
  const list = $("#newsList");
  const sentimentBox = $("#sentimentBox");
  list.innerHTML = `<li class="loading">Loading news…</li>`;
  sentimentBox.innerHTML = "";
  try {
    const data = await getJSON(`/api/stock/${ticker}/news`);
    list.innerHTML = "";
    (data.headlines || []).forEach(n => {
      const li = document.createElement("li");
      li.innerHTML = `
        <a href="${n.link || "#"}" target="_blank" rel="noopener">${n.title}</a>
        <div class="news-meta">${n.publisher || ""} · ${n.published ? new Date(n.published).toLocaleString() : ""}</div>
      `;
      list.appendChild(li);
    });
    const s = data.sentiment;
    if (s && !s.error && s.sentiment_score !== undefined) {
      sentimentBox.innerHTML = `
        <div class="filing-block">
          <h4>Aggregate sentiment: ${s.sentiment_label || "—"} (${s.sentiment_score})</h4>
          <div>${(s.themes || []).map(t => `<span class="badge">${t}</span>`).join(" ")}</div>
        </div>
      `;
    } else if (s && s.error === "no_api_key") {
      sentimentBox.innerHTML = `<p class="muted">LLM sentiment unavailable — set ANTHROPIC_API_KEY.</p>`;
    }
  } catch (e) {
    list.innerHTML = `<li class="error">${e.message}</li>`;
  }
}

async function runFiling() {
  const ticker = state.ticker;
  const form = $("#filingForm").value;
  $("#filingStatus").textContent = "Fetching & analyzing (can take 30-60s)…";
  $("#filingOutput").innerHTML = "";
  try {
    const data = await getJSON(`/api/stock/${ticker}/filings/latest-summary?form=${form}`);
    $("#filingStatus").textContent = "";
    renderFilingSummary(data);
  } catch (e) {
    $("#filingStatus").innerHTML = `<span class="error">${e.message}</span>`;
  }
}

function renderFilingSummary(data) {
  const out = $("#filingOutput");
  const f = data.filing;
  const s = data.summary || {};
  if (s.error === "no_api_key") {
    out.innerHTML = `<p class="muted">LLM unavailable — set ANTHROPIC_API_KEY in .env. Filing link: <a href="${f.url}" target="_blank">${f.form} filed ${f.filed}</a></p>`;
    return;
  }
  const tone = s.overall_tone || "—";
  let html = `
    <div class="muted">${f.form} filed ${f.filed} · <a href="${f.url}" target="_blank">source</a> · tone: <strong>${tone}</strong></div>
    <div class="filing-block good"><h4>Headline</h4><p>${s.headline || "—"}</p></div>
  `;
  if (s.key_numbers?.length) {
    html += `<div class="filing-block"><h4>Key numbers</h4><ul>`;
    s.key_numbers.forEach(n => {
      html += `<li><strong>${n.metric}</strong>: ${n.value}${n.yoy_change ? ` (${n.yoy_change} YoY)` : ""}${n.note ? ` — ${n.note}` : ""}</li>`;
    });
    html += `</ul></div>`;
  }
  if (s.business_highlights?.length) {
    html += `<div class="filing-block good"><h4>Business highlights</h4><ul>${s.business_highlights.map(x => `<li>${x}</li>`).join("")}</ul></div>`;
  }
  if (s.risks?.length) {
    html += `<div class="filing-block risks"><h4>Risks</h4><ul>${s.risks.map(x => `<li>${x}</li>`).join("")}</ul></div>`;
  }
  if (s.red_flags?.length) {
    html += `<div class="filing-block red"><h4>Red flags</h4><ul>`;
    s.red_flags.forEach(r => {
      const flag = typeof r === "string" ? r : r.flag;
      const ev = typeof r === "string" ? "" : r.evidence;
      html += `<li><strong>${flag}</strong>${ev ? ` — ${ev}` : ""}</li>`;
    });
    html += `</ul></div>`;
  }
  if (s.guidance) {
    html += `<div class="filing-block"><h4>Forward guidance</h4><p>${s.guidance}</p></div>`;
  }
  out.innerHTML = html;
}

function switchTab(name) {
  document.querySelectorAll(".tab").forEach(t => t.classList.toggle("active", t.dataset.tab === name));
  document.querySelectorAll(".tab-panel").forEach(p => {
    p.hidden = p.id !== `tab-${name}`;
  });
}

async function analyze(ticker) {
  state.ticker = ticker.toUpperCase();
  try {
    await Promise.all([
      loadOverview(state.ticker),
      loadPrices(state.ticker, state.period),
      loadTechSnapshot(state.ticker),
      loadFundamentals(state.ticker),
      loadNews(state.ticker),
    ]);
    loadScore(state.ticker);  // don't await - may be slower
  } catch (e) {
    alert(`Failed: ${e.message}`);
  }
}

// events
$("#searchForm").addEventListener("submit", (e) => {
  e.preventDefault();
  const t = $("#tickerInput").value.trim();
  if (t) analyze(t);
});

document.querySelectorAll(".tab").forEach(t => {
  t.addEventListener("click", () => switchTab(t.dataset.tab));
});

$("#rangeGroup").addEventListener("click", (e) => {
  const btn = e.target.closest("button[data-period]");
  if (!btn) return;
  document.querySelectorAll("#rangeGroup button").forEach(b => b.classList.toggle("active", b === btn));
  state.period = btn.dataset.period;
  loadPrices(state.ticker, state.period);
});

$("#toggleSma50").addEventListener("change", e => { state.showSma50 = e.target.checked; renderChart(); });
$("#toggleSma200").addEventListener("change", e => { state.showSma200 = e.target.checked; renderChart(); });
$("#toggleBB").addEventListener("change", e => { state.showBB = e.target.checked; renderChart(); });

$("#runFiling").addEventListener("click", runFiling);

// init
$("#tickerInput").value = "AAPL";
checkHealth();
analyze("AAPL");
