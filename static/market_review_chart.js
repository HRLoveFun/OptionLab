/* ============================================================
   Market Review – Interactive Time-Series Chart (Module 4A)
   ============================================================ */

const MR_CHART_CONFIG = {
    COLORS: {
        SPX: '#2196F3',
        USD: '#4CAF50',
        Gold: '#FFD700',
        US10Y: '#9C27B0',
        CSI300: '#F44336',
        HSI: '#00BCD4',
        NKY: '#FF9800',
        STOXX: '#795548',
    },
    DEFAULT_COLOR: '#FF6B35',
};

let mrChart = null;
let mrData = null;
let mrMode = 'return';
let mrPeriod = 'ETD';
let mrVisibleAssets = new Set();
let _mrTickerCache = {};  // per-ticker response cache
const _MR_CACHE_TTL = 5 * 60 * 1000;  // 5 minutes in ms
let _mrAbort = null;

async function loadMarketReviewChart(ticker, startDate) {
    const container = document.getElementById('market-review-chart-container');
    if (!container) return;

    // Check client-side cache first (with TTL)
    const cacheKey = ticker + '|' + (startDate || '');
    const cached = _mrTickerCache[cacheKey];
    if (cached && (Date.now() - cached._ts) < _MR_CACHE_TTL) {
        mrData = cached.data;
        container.innerHTML = '<canvas id="market-review-chart"></canvas>';
        mrVisibleAssets = new Set(Object.keys(mrData.assets));
        renderMarketReviewChart();
        renderAssetToggleButtons();
        renderMrKpiStrip();
        return;
    }

    container.innerHTML = '<div style="text-align:center;padding:4rem;color:#94a3b8;"><i class="fas fa-spinner fa-spin"></i> Loading time-series data...</div>';

    if (_mrAbort) _mrAbort.abort();
    _mrAbort = new AbortController();

    try {
        const resp = await fetch('/api/market_review_ts', {
            signal: _mrAbort.signal,
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ticker, start_date: startDate || null })
        });
        mrData = await resp.json();

        if (mrData.status !== 'ok') {
            container.innerHTML = `<div style="color:#ef4444;padding:2rem;">${mrData.message || 'Error loading data'}</div>`;
            renderMrKpiStrip(/* error */ true);
            return;
        }

        // Cache the successful response (with TTL timestamp)
        _mrTickerCache[cacheKey] = { data: mrData, _ts: Date.now() };

        // Restore canvas
        container.innerHTML = '<canvas id="market-review-chart"></canvas>';
        mrVisibleAssets = new Set(Object.keys(mrData.assets));
        renderMarketReviewChart();
        renderAssetToggleButtons();
        renderMrKpiStrip();
    } catch (e) {
        if (e.name === 'AbortError') return;
        container.innerHTML = `<div style="color:#ef4444;padding:2rem;">Network error: ${e.message}</div>`;
        renderMrKpiStrip(/* error */ true);
    }
}


/* Compute and render the KPI strip (Design Principle P1).
   Shows Total Return / Annualized Volatility / Sharpe over the entire-to-date
   window for the main instrument. Pure browser-side derivation from the
   already-loaded mrData time-series; no extra HTTP request.

   When `errored` is truthy, renders a neutral fallback (em-dash) so the
   strip never gets stuck on "Loading…" after a fetch failure. */
function renderMrKpiStrip(errored) {
    const strip = document.getElementById('mr-kpi-strip');
    if (!strip) return;

    const setCard = (kpi, value, sub, semanticClass) => {
        const card = strip.querySelector(`[data-mr-kpi="${kpi}"]`);
        if (!card) return;
        const valEl = card.querySelector('[data-mr-kpi-value]');
        const subEl = card.querySelector('[data-mr-kpi-sub]');
        if (valEl) {
            valEl.textContent = value;
            valEl.classList.remove('semantic-pos', 'semantic-neg', 'semantic-info', 'semantic-warn');
            if (semanticClass) valEl.classList.add(semanticClass);
        }
        if (subEl && sub !== undefined) subEl.textContent = sub;
    };

    if (errored || !mrData || !mrData.instrument || !mrData.assets) {
        setCard('total_return', '—', errored ? 'Unavailable' : 'No data');
        setCard('volatility', '—', '');
        setCard('sharpe', '—', '');
        return;
    }

    const series = mrData.assets[mrData.instrument];
    if (!series || !Array.isArray(series.prices)) {
        setCard('total_return', '—', 'No data');
        setCard('volatility', '—', '');
        setCard('sharpe', '—', '');
        return;
    }

    // Drop nulls for total-return (first / last finite price).
    const prices = series.prices.filter(p => p !== null && !isNaN(p));
    if (prices.length < 2) {
        setCard('total_return', '—', 'Insufficient data');
        setCard('volatility', '—', '');
        setCard('sharpe', '—', '');
        return;
    }

    const totalReturnPct = ((prices[prices.length - 1] / prices[0]) - 1) * 100;

    // Daily log returns from full price series.
    const logRets = [];
    for (let i = 1; i < prices.length; i++) {
        if (prices[i - 1] > 0) logRets.push(Math.log(prices[i] / prices[i - 1]));
    }
    let mean = 0, variance = 0, annVolPct = NaN, sharpe = NaN;
    if (logRets.length > 1) {
        mean = logRets.reduce((a, b) => a + b, 0) / logRets.length;
        variance = logRets.reduce((s, r) => s + (r - mean) ** 2, 0) / (logRets.length - 1);
        const std = Math.sqrt(variance);
        annVolPct = std * Math.sqrt(252) * 100;
        const annRet = mean * 252;
        sharpe = std > 0 ? annRet / (std * Math.sqrt(252)) : NaN;
    }

    // Total Return — semantic color (green positive / red negative / blue zero).
    const trClass = totalReturnPct > 0.05 ? 'semantic-pos'
        : totalReturnPct < -0.05 ? 'semantic-neg'
            : 'semantic-info';
    const trSign = totalReturnPct > 0 ? '+' : '';
    setCard('total_return', `${trSign}${totalReturnPct.toFixed(2)}%`,
        `${prices.length} days · ${mrData.instrument}`, trClass);

    // Volatility — orange when elevated (> 30% annualized).
    if (isFinite(annVolPct)) {
        const volClass = annVolPct > 30 ? 'semantic-warn' : null;
        setCard('volatility', `${annVolPct.toFixed(1)}%`,
            '20-day rolling, σ × √252', volClass);
    } else {
        setCard('volatility', '—', 'Insufficient data');
    }

    // Sharpe — green if > 0.5, red if < -0.5, neutral otherwise.
    if (isFinite(sharpe)) {
        const sClass = sharpe > 0.5 ? 'semantic-pos'
            : sharpe < -0.5 ? 'semantic-neg' : 'semantic-info';
        setCard('sharpe', sharpe.toFixed(2),
            'Annualized return / vol', sClass);
    } else {
        setCard('sharpe', '—', 'Insufficient data');
    }
}


function renderMarketReviewChart() {
    if (!mrData || !mrData.dates) return;

    const startDate = mrData.periods[mrPeriod] || mrData.periods['ETD'];
    const startIdx = mrData.dates.findIndex(d => d >= startDate);
    const filteredDates = mrData.dates.slice(Math.max(0, startIdx));

    const datasets = [];
    for (const [asset, series] of Object.entries(mrData.assets)) {
        if (!mrVisibleAssets.has(asset)) continue;

        let yData;
        if (mrMode === 'return') {
            const prices = series.prices.slice(Math.max(0, startIdx));
            const basePrice = prices.find(p => p !== null);
            yData = prices.map(p => p !== null && basePrice ? ((p / basePrice) - 1) * 100 : null);
        } else if (mrMode === 'vol') {
            yData = series.rolling_vol.slice(Math.max(0, startIdx));
        } else {
            yData = series.rolling_corr.slice(Math.max(0, startIdx));
        }

        const color = asset === mrData.instrument
            ? MR_CHART_CONFIG.DEFAULT_COLOR
            : (MR_CHART_CONFIG.COLORS[asset] || '#999');

        datasets.push({
            label: asset,
            data: filteredDates.map((d, i) => ({ x: d, y: yData[i] })),
            borderColor: color,
            backgroundColor: 'transparent',
            borderWidth: asset === mrData.instrument ? 2.5 : 1.5,
            pointRadius: 0,
            tension: 0.3,
        });
    }

    const ctx = document.getElementById('market-review-chart');
    if (!ctx) return;
    if (mrChart) mrChart.destroy();

    mrChart = new Chart(ctx, {
        type: 'line',
        data: { datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: { display: true, position: 'top', labels: { font: { size: 11 }, boxWidth: 14 } },
                tooltip: {
                    callbacks: {
                        label: function (ctx) {
                            const v = ctx.parsed.y;
                            if (v === null || v === undefined) return null;
                            if (mrMode === 'return') return `${ctx.dataset.label}: ${v.toFixed(2)}%`;
                            if (mrMode === 'vol') return `${ctx.dataset.label}: ${v.toFixed(1)}%`;
                            return `${ctx.dataset.label}: ${v.toFixed(3)}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    type: 'time',
                    time: { unit: 'month' },
                    grid: { display: false },
                    ticks: { font: { size: 10 } }
                },
                y: {
                    title: {
                        display: true,
                        text: mrMode === 'return' ? 'Cumulative Return (%)'
                            : mrMode === 'vol' ? 'Rolling 20d Vol (%)'
                                : 'Rolling 20d Correlation',
                        font: { size: 12 }
                    },
                    grid: { color: 'rgba(200,200,200,0.2)' },
                    ticks: { font: { size: 10 } }
                }
            }
        }
    });
}


function renderAssetToggleButtons() {
    const container = document.getElementById('asset-toggle-container');
    if (!container || !mrData) return;
    container.innerHTML = '';

    for (const asset of Object.keys(mrData.assets)) {
        const btn = document.createElement('button');
        const color = asset === mrData.instrument
            ? MR_CHART_CONFIG.DEFAULT_COLOR
            : (MR_CHART_CONFIG.COLORS[asset] || '#999');
        btn.className = 'btn-toggle btn-sm' + (mrVisibleAssets.has(asset) ? ' active' : '');
        btn.style.borderColor = color;
        btn.style.color = mrVisibleAssets.has(asset) ? '#fff' : color;
        btn.style.backgroundColor = mrVisibleAssets.has(asset) ? color : 'transparent';
        btn.textContent = asset;
        btn.addEventListener('click', function () {
            if (mrVisibleAssets.has(asset)) {
                mrVisibleAssets.delete(asset);
                this.classList.remove('active');
                this.style.color = color;
                this.style.backgroundColor = 'transparent';
            } else {
                mrVisibleAssets.add(asset);
                this.classList.add('active');
                this.style.color = '#fff';
                this.style.backgroundColor = color;
            }
            renderMarketReviewChart();
        });
        container.appendChild(btn);
    }
}


function setMrMode(mode) {
    mrMode = mode;
    document.querySelectorAll('#mr-mode-btns .btn-toggle').forEach(b => {
        b.classList.toggle('active', b.textContent.toLowerCase().startsWith(mode.slice(0, 3)));
    });
    renderMarketReviewChart();
}

function setMrPeriod(period) {
    mrPeriod = period;
    document.querySelectorAll('#mr-period-btns .btn-toggle').forEach(b => {
        b.classList.toggle('active', b.textContent === period);
    });
    renderMarketReviewChart();
}

function toggleSummaryTable() {
    const wrapper = document.getElementById('market-review-table-wrapper');
    if (wrapper) {
        wrapper.style.display = wrapper.style.display === 'none' ? 'block' : 'none';
    }
}


/* ============================================================
   Module 5: Correlation Heatmap (SVG)
   ============================================================ */

function renderCorrelationHeatmap(corrData) {
    const container = document.getElementById('correlation-heatmap-container');
    if (!container || !corrData) return;
    const { labels, values } = corrData;
    const n = labels.length;
    const cellSize = 60;
    const margin = 80;
    const totalSize = cellSize * n + margin + 20;

    let svgCells = '';
    for (let i = 0; i < n; i++) {
        for (let j = 0; j < n; j++) {
            const corr = values[i][j];
            const color = corrToColor(corr);
            const x = margin + j * cellSize;
            const y = margin + i * cellSize;
            svgCells += `<rect x="${x}" y="${y}" width="${cellSize}" height="${cellSize}" fill="${color}" stroke="white" stroke-width="1"/>`;
            svgCells += `<text x="${x + cellSize / 2}" y="${y + cellSize / 2 + 5}" text-anchor="middle" font-size="12" fill="${Math.abs(corr) > 0.5 ? 'white' : 'black'}">${corr.toFixed(2)}</text>`;
        }
    }

    let axisLabels = labels.map((label, i) => {
        const cx = margin + i * cellSize + cellSize / 2;
        return `<text x="${cx}" y="${margin - 10}" text-anchor="middle" font-size="11" transform="rotate(-30,${cx},${margin - 10})">${label}</text>` +
            `<text x="${margin - 10}" y="${margin + i * cellSize + cellSize / 2 + 5}" text-anchor="end" font-size="11">${label}</text>`;
    }).join('');

    container.innerHTML = `<svg viewBox="0 0 ${totalSize} ${totalSize}" xmlns="http://www.w3.org/2000/svg" style="max-width:${totalSize}px;">${axisLabels}${svgCells}</svg>`;
}

function corrToColor(corr) {
    if (corr > 0) {
        const r = Math.round(255 * (1 - corr));
        const g = Math.round(255 * (1 - corr));
        return `rgb(${r},${g},255)`;
    } else {
        const intensity = Math.abs(corr);
        const g = Math.round(255 * (1 - intensity));
        const b = Math.round(255 * (1 - intensity));
        return `rgb(255,${g},${b})`;
    }
}


/* ============================================================
   Multi-ticker context switcher
   ============================================================ */

// Tabs that are rendered via HTMX streaming (must match _RENDER_KIND_SLICES
// in app.py). Each entry maps the kind suffix to the DOM container id that
// the fragment will swap into.
const STREAMING_TABS = [
    { kind: 'market_review', containerId: 'tab-market-review-content', parentId: 'tab-market-review' },
    { kind: 'statistical', containerId: 'tab-statistical-analysis-content', parentId: 'tab-statistical-analysis' },
    { kind: 'assessment', containerId: 'tab-market-assessment-content', parentId: 'tab-market-assessment' },
    { kind: 'options_chain', containerId: 'tab-options-chain-content', parentId: 'tab-options-chain' },
];

function switchTickerContext(ticker) {
    document.querySelectorAll('.ticker-tab-btn').forEach(b => {
        b.classList.toggle('active', b.dataset.ticker === ticker);
    });

    // Streaming-mode: replace each streamed tab body with a fresh skeleton
    // and fire a new /render/<kind>?ticker=<new>&job=<id> request. The
    // server's JobCache memoises per (ticker, kind) so re-clicking a ticker
    // is cheap after the first switch.
    const jobId = window.STREAMING_JOB_ID || '';
    if (jobId && typeof htmx !== 'undefined') {
        STREAMING_TABS.forEach(tab => {
            // Find current content (could be the original swapped fragment or
            // a skeleton from a previous switch). Replace it with a skeleton
            // and trigger a fresh load.
            const parent = document.getElementById(tab.parentId);
            if (!parent) return;
            const old = document.getElementById(tab.containerId);
            const skel = document.createElement('div');
            skel.id = tab.containerId;
            skel.className = 'loading-skeleton';
            skel.setAttribute('hx-get', `/render/${tab.kind}?job=${encodeURIComponent(jobId)}&ticker=${encodeURIComponent(ticker)}`);
            skel.setAttribute('hx-trigger', 'load');
            skel.setAttribute('hx-swap', 'outerHTML');
            skel.innerHTML = `<div class="empty-state"><i class="fas fa-spinner fa-spin empty-icon"></i><p>Loading ${tab.kind.replace('_', ' ')}…</p></div>`;
            if (old && old.parentNode === parent) {
                parent.replaceChild(skel, old);
            } else {
                parent.appendChild(skel);
            }
            htmx.process(skel);
        });
    }

    // Update the global ticker input so existing tab-load handlers
    // (Option Chain, Odds, Regime) target the new ticker on activation.
    const tickerInput = document.getElementById('ticker');
    if (tickerInput) tickerInput.value = ticker;
    if (window.appState && window.appState.tabFlags) {
        // Force re-fetch of lazy-loaded tabs against the new ticker.
        ['option_chain', 'odds', 'regime', 'market_review'].forEach(k => window.appState.tabFlags.reset(k));
    }

    // Reload the JS-driven Market Review chart for the new ticker if its tab
    // has been visited before (otherwise it loads on first activation).
    if (window.appState && window.appState.tabFlags.isLoaded('market_review')) {
        loadMarketReviewChart(ticker);
    }
}
