// Demo renderer - draws charts and panels using window.__DEMO__ and window.__FIXTURES__

(function () {
  const D = window.__DEMO__;
  const F = window.__FIXTURES__;
  const $ = (s) => document.querySelector(s);

  // ---------- tabs ----------
  document.querySelectorAll(".tab").forEach(tab => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach(t => t.classList.toggle("active", t === tab));
      document.querySelectorAll(".tab-panel").forEach(p => {
        p.hidden = p.id !== `tab-${tab.dataset.tab}`;
      });
    });
  });

  // ---------- chart ----------
  const priceChart = LightweightCharts.createChart($("#priceChart"), {
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
  candle.setData(D.candles.map(c => ({ time: c.t, open: c.o, high: c.h, low: c.l, close: c.c })));

  const sma50Series = priceChart.addLineSeries({ color: "#f1c40f", lineWidth: 1, title: "SMA50" });
  sma50Series.setData(D.candles
    .map((c, i) => D.sma50[i] != null ? { time: c.t, value: D.sma50[i] } : null)
    .filter(Boolean));
  const sma200Series = priceChart.addLineSeries({ color: "#4c8bf5", lineWidth: 1, title: "SMA200" });
  sma200Series.setData(D.candles
    .map((c, i) => D.sma200[i] != null ? { time: c.t, value: D.sma200[i] } : null)
    .filter(Boolean));
  let bbUp = null, bbLo = null;
  function applyBB(show) {
    if (show && !bbUp) {
      bbUp = priceChart.addLineSeries({ color: "#8aa0bd", lineWidth: 1, title: "BB+" });
      bbLo = priceChart.addLineSeries({ color: "#8aa0bd", lineWidth: 1, title: "BB-" });
      bbUp.setData(D.candles.map((c, i) => D.bb.upper[i] != null ? { time: c.t, value: D.bb.upper[i] } : null).filter(Boolean));
      bbLo.setData(D.candles.map((c, i) => D.bb.lower[i] != null ? { time: c.t, value: D.bb.lower[i] } : null).filter(Boolean));
    } else if (!show && bbUp) {
      priceChart.removeSeries(bbUp); priceChart.removeSeries(bbLo);
      bbUp = null; bbLo = null;
    }
  }
  priceChart.timeScale().fitContent();

  $("#toggleSma50").addEventListener("change", e => {
    sma50Series.applyOptions({ visible: e.target.checked });
  });
  $("#toggleSma200").addEventListener("change", e => {
    sma200Series.applyOptions({ visible: e.target.checked });
  });
  $("#toggleBB").addEventListener("change", e => applyBB(e.target.checked));

  // ---------- RSI ----------
  const rsiChart = LightweightCharts.createChart($("#rsiChart"), {
    layout: { background: { color: "#1a2333" }, textColor: "#8aa0bd" },
    grid: { vertLines: { color: "#222d40" }, horzLines: { color: "#222d40" } },
    timeScale: { borderColor: "#222d40", visible: false },
    rightPriceScale: { borderColor: "#222d40" },
  });
  const rsiSeries = rsiChart.addLineSeries({ color: "#4c8bf5", lineWidth: 1, title: "RSI14" });
  rsiSeries.setData(D.candles
    .map((c, i) => D.rsi14[i] != null ? { time: c.t, value: D.rsi14[i] } : null)
    .filter(Boolean));
  rsiSeries.createPriceLine({ price: 70, color: "#e74c3c", lineWidth: 1, lineStyle: 2 });
  rsiSeries.createPriceLine({ price: 30, color: "#2ecc71", lineWidth: 1, lineStyle: 2 });
  rsiChart.timeScale().fitContent();

  // ---------- MACD ----------
  const macdChart = LightweightCharts.createChart($("#macdChart"), {
    layout: { background: { color: "#1a2333" }, textColor: "#8aa0bd" },
    grid: { vertLines: { color: "#222d40" }, horzLines: { color: "#222d40" } },
    timeScale: { borderColor: "#222d40", visible: false },
    rightPriceScale: { borderColor: "#222d40" },
  });
  const macdLine = macdChart.addLineSeries({ color: "#4c8bf5", lineWidth: 1, title: "MACD" });
  macdLine.setData(D.candles.map((c, i) => D.md.line[i] != null ? { time: c.t, value: D.md.line[i] } : null).filter(Boolean));
  const sigLine = macdChart.addLineSeries({ color: "#f1c40f", lineWidth: 1, title: "Signal" });
  sigLine.setData(D.candles.map((c, i) => D.md.sig[i] != null ? { time: c.t, value: D.md.sig[i] } : null).filter(Boolean));
  const histSeries = macdChart.addHistogramSeries();
  histSeries.setData(D.candles.map((c, i) => D.md.hist[i] != null ? {
    time: c.t, value: D.md.hist[i],
    color: D.md.hist[i] >= 0 ? "#2ecc71" : "#e74c3c",
  } : null).filter(Boolean));
  macdChart.timeScale().fitContent();

  // ---------- technical snapshot grid ----------
  const tech = F.technical;
  const techGrid = $("#techSnapshot");
  Object.entries(tech).forEach(([k, v]) => {
    const el = document.createElement("div");
    el.className = "kv";
    el.innerHTML = `<span class="k">${k}</span><span class="v">${v}</span>`;
    techGrid.appendChild(el);
  });

  // ---------- fundamentals ----------
  const fundGrid = $("#fundGrid");
  const labels = {
    valuation: "Valuation", profitability: "Profitability", growth: "Growth (YoY)",
    balance_sheet: "Balance Sheet", dividend: "Dividend", analyst: "Analyst Consensus",
  };
  Object.entries(F.fundamentals).forEach(([section, kv]) => {
    const sec = document.createElement("div");
    sec.className = "kvsection";
    sec.innerHTML = `<h3>${labels[section] || section}</h3>`;
    const rows = document.createElement("div");
    rows.className = "kvgrid";
    Object.entries(kv).forEach(([k, v]) => {
      const d = document.createElement("div");
      d.className = "kv";
      d.innerHTML = `<span class="k">${k}</span><span class="v">${v}</span>`;
      rows.appendChild(d);
    });
    sec.appendChild(rows);
    fundGrid.appendChild(sec);
  });

  // ---------- filing ----------
  const f = F.filing;
  const s = f.summary;
  const out = $("#filingOutput");
  let html = `
    <div class="muted">${f.form} filed ${f.filed} &middot;
      <a href="${f.url}" target="_blank">source</a> &middot;
      tone: <strong>${s.overall_tone}</strong></div>
    <div class="filing-block good"><h4>Headline</h4><p>${s.headline}</p></div>
    <div class="filing-block"><h4>Key numbers</h4><ul>
      ${s.key_numbers.map(n =>
        `<li><strong>${n.metric}</strong>: ${n.value}${n.yoy_change ? ` (${n.yoy_change} YoY)` : ""}${n.note ? ` - ${n.note}` : ""}</li>`
      ).join("")}
    </ul></div>
    <div class="filing-block good"><h4>Business highlights</h4><ul>
      ${s.business_highlights.map(x => `<li>${x}</li>`).join("")}
    </ul></div>
    <div class="filing-block risks"><h4>Risks</h4><ul>
      ${s.risks.map(x => `<li>${x}</li>`).join("")}
    </ul></div>
    <div class="filing-block red"><h4>Red flags</h4><ul>
      ${s.red_flags.map(r => `<li><strong>${r.flag}</strong> - ${r.evidence}</li>`).join("")}
    </ul></div>
    <div class="filing-block"><h4>Forward guidance</h4><p>${s.guidance}</p></div>
  `;
  out.innerHTML = html;

  // ---------- news + sentiment ----------
  const n = F.news;
  $("#sentimentBox").innerHTML = `
    <div class="filing-block good">
      <h4>Aggregate sentiment: ${n.sentiment.sentiment_label} (${n.sentiment.sentiment_score})</h4>
      <div>${n.sentiment.themes.map(t => `<span class="badge">${t}</span>`).join(" ")}</div>
    </div>`;
  const list = $("#newsList");
  n.headlines.forEach(h => {
    const li = document.createElement("li");
    li.innerHTML = `
      <a href="${h.link}" target="_blank" rel="noopener">${h.title}</a>
      <div class="news-meta">${h.publisher} &middot; ${new Date(h.published).toLocaleString()}</div>
    `;
    list.appendChild(li);
  });
})();
