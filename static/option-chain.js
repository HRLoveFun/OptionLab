/* ============================================================
   Option Chain – T-format display with maturity-date subtabs
   ============================================================ */

// State (data + active expiration + abort controller) is encapsulated in
// static/state/optionChainState.js (window.appState.optionChain).
// UI phase ('idle'|'loading'|'loaded'|'error'|'empty') is driven via
// appState.panels.set('option_chain', ...) — the partial subscribes through
// Alpine's `panelState('option_chain')`. NEVER toggle .style.display here;
// the state machine guarantees exactly one block is visible at a time.
const _ocState = () => window.appState.optionChain;
const _ocPanel = (phase, opts) => window.appState.panels.set('option_chain', phase, opts);

function loadOptionChain() {
    const input = document.getElementById('ticker');
    const rawTicker = (input ? input.value : '').trim().toUpperCase();
    // Extract first ticker from potentially comma-separated list
    const ticker = rawTicker.split(/[,\n]+/)[0].trim();

    if (!ticker) {
        _ocPanel('error', { message: 'Please enter a ticker symbol in the Parameter tab.' });
        return;
    }

    _ocPanel('loading', { message: 'Loading option chain...' });
    _ocState().reset();

    // Build URL with config-driven filter params
    const params = new URLSearchParams({ ticker });
    const cfgDte = document.getElementById('cfg-max-dte');
    const cfgMLow = document.getElementById('cfg-moneyness-low');
    const cfgMHigh = document.getElementById('cfg-moneyness-high');
    if (cfgDte && cfgDte.value) params.set('max_dte', cfgDte.value);
    if (cfgMLow && cfgMLow.value) params.set('moneyness_low', cfgMLow.value);
    if (cfgMHigh && cfgMHigh.value) params.set('moneyness_high', cfgMHigh.value);

    const signal = _ocState().beginRequest();

    fetch(`/api/option_chain?${params}`, { signal })
        .then(r => {
            if (!r.ok) {
                return r.json().catch(() => ({ error: `Server error (${r.status})` }));
            }
            return r.json();
        })
        .then(data => {
            if (data.error) { _ocPanel('error', { message: data.error }); return; }
            _ocState().setData(data);
            const exps = data.expirations || [];
            if (exps.length === 0) {
                _ocPanel('empty', { message: 'No expirations returned for this ticker.' });
                return;
            }
            _ocPanel('loaded', { data });
            _ocBuildExpTabs(exps);
            _ocSelectExp(exps[0]);
            _ocRenderKpiStrip(data, exps[0]);
        })
        .catch(err => {
            if (err.name === 'AbortError') return;
            _ocPanel('error', { message: 'Network error: ' + err.message });
        });
}

function _ocBuildExpTabs(expirations) {
    const list = document.getElementById('oc-exp-tab-list');
    if (!list) return;
    list.innerHTML = '';
    expirations.forEach(exp => {
        const btn = document.createElement('button');
        btn.className = 'oc-exp-btn';
        btn.textContent = exp;
        btn.dataset.exp = exp;
        btn.addEventListener('click', function () { _ocSelectExp(this.dataset.exp); });
        list.appendChild(btn);
    });
}

function _ocSelectExp(exp) {
    _ocState().setActiveExp(exp);

    // Highlight active tab
    document.querySelectorAll('.oc-exp-btn').forEach(b => {
        b.classList.toggle('active', b.dataset.exp === exp);
    });

    const data = _ocState().getData();
    if (!data || !data.chain[exp]) return;

    const { calls, puts } = data.chain[exp];
    _ocRenderChain(calls, puts);
    _ocRenderKpiStrip(data, exp);
}


/* Populate Option Chain KPI strip — Design Principle P1 (one primary
   metric per panel: spot price). Pure DOM work; safe to call any time
   after the loaded data is in state.

   `data`:    response payload with `spot` and `expirations`.
   `activeExp`: ISO-date string for the currently selected expiration. */
function _ocRenderKpiStrip(data, activeExp) {
    const strip = document.getElementById('oc-kpi-strip');
    if (!strip || !data) return;

    const setCard = (key, value, sub) => {
        const card = strip.querySelector(`[data-oc-kpi="${key}"]`);
        if (!card) return;
        const v = card.querySelector('[data-oc-kpi-value]');
        const s = card.querySelector('[data-oc-kpi-sub]');
        if (v) v.textContent = value;
        if (s && sub !== undefined) s.textContent = sub;
    };

    const spot = (data.spot !== null && data.spot !== undefined && !isNaN(data.spot))
        ? Number(data.spot) : null;
    setCard('spot',
        spot !== null ? `$${spot.toFixed(2)}` : '—',
        data.ticker ? `${data.ticker} · live` : 'Live');

    const expCount = (data.expirations || []).length;
    setCard('expirations', String(expCount),
        expCount > 0 ? `Through ${data.expirations[expCount - 1]}` : 'No data');

    if (activeExp) {
        const days = _ocDaysToExpiry(activeExp);
        setCard('active-exp', activeExp,
            days !== null ? `${days} day${days === 1 ? '' : 's'} to expiry` : 'Days to expiry');
    } else {
        setCard('active-exp', '—', 'Days to expiry');
    }
}

function _ocDaysToExpiry(isoDate) {
    if (!isoDate) return null;
    const exp = new Date(isoDate + 'T00:00:00');
    if (isNaN(exp.getTime())) return null;
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    return Math.max(0, Math.round((exp - today) / (1000 * 60 * 60 * 24)));
}

function _ocRenderChain(calls, puts) {
    const body = document.getElementById('oc-chain-body');
    if (!body) return;

    // Build strike-keyed maps
    const callMap = {};
    const putMap = {};
    (calls || []).forEach(c => { callMap[c.strike] = c; });
    (puts || []).forEach(p => { putMap[p.strike] = p; });

    // Merge all unique strikes
    const strikes = Array.from(new Set([
        ...(calls || []).map(c => c.strike),
        ...(puts || []).map(p => p.strike),
    ])).sort((a, b) => a - b);

    if (strikes.length === 0) {
        body.innerHTML = '';
        _ocPanel('empty', { message: 'No data for this expiration.' });
        return;
    }

    const _ocData = _ocState().getData();
    const spot = _ocData ? _ocData.spot : null;

    const fmt = (v, digits = 2) => (v === null || v === undefined) ? '<span class="oc-null">—</span>' : Number(v).toFixed(digits);
    const fmtInt = (v) => (v === null || v === undefined) ? '<span class="oc-null">—</span>' : Math.round(Number(v)).toLocaleString();
    // Call Premium%: how much the stock needs to RISE to break even = (Last + Strike − Spot) / Spot × 100
    // Put  Premium%: magnitude of drop needed to break even        = (Last − Strike + Spot) / Spot × 100
    const fmtPrem = (strike, last, isCall) => {
        if (spot === null || spot === undefined || !last || last === 0) return '<span class="oc-null">—</span>';
        const val = isCall
            ? (last + strike - spot) / spot * 100
            : (last - strike + spot) / spot * 100;
        const cls = isCall
            ? (val >= 0 ? 'oc-prem-pos' : 'oc-prem-neg')
            : (val >= 0 ? 'oc-prem-neg' : 'oc-prem-pos');  // put: positive means stock must fall
        return `<span class="${cls}">${val.toFixed(2)}%</span>`;
    };

    // Find insertion index for spot-price divider
    let spotInsertIdx = null;  // insert divider BEFORE strikes[spotInsertIdx]
    if (spot !== null && spot !== undefined) {
        if (spot < strikes[0]) {
            spotInsertIdx = 0;
        } else if (spot >= strikes[strikes.length - 1]) {
            spotInsertIdx = strikes.length; // after last
        } else {
            for (let i = 0; i < strikes.length - 1; i++) {
                if (spot >= strikes[i] && spot < strikes[i + 1]) {
                    spotInsertIdx = i + 1; // insert between i and i+1
                    break;
                }
            }
        }
    }

    const spotRow = spot !== null && spot !== undefined
        ? `<div class="oc-spot-row"><span class="oc-spot-label"><i class="fas fa-circle-dot"></i> Spot&nbsp;&nbsp;<strong>${Number(spot).toFixed(2)}</strong></span></div>`
        : '';

    let html = '';
    strikes.forEach((strike, i) => {
        if (i === spotInsertIdx) html += spotRow;

        const c = callMap[strike] || {};
        const p = putMap[strike] || {};
        const callItm = c.itm === true;
        const putItm = p.itm === true;

        // Liquidity score: pick worst of call/put for the row
        const cLiq = c.liq_score || '';
        const pLiq = p.liq_score || '';
        const worstLiq = (cLiq === 'AVOID' || pLiq === 'AVOID') ? 'AVOID'
            : (cLiq === 'FAIR' || pLiq === 'FAIR') ? 'FAIR' : '';
        const liqClass = worstLiq === 'AVOID' ? ' oc-liq-avoid'
            : worstLiq === 'FAIR' ? ' oc-liq-fair' : '';

        html += `<div class="oc-t-row${liqClass}">
            <div class="oc-t-calls${callItm ? ' oc-itm' : ''}">
                <span>${fmt(c.iv, 1)}%</span>
                <span>${fmtInt(c.openInterest)}</span>
                <span>${fmtInt(c.volume)}</span>
                <span>${fmt(c.bid)}</span>
                <span>${fmt(c.ask)}</span>
                <span>${fmt(c.lastPrice)}</span>
                <span>${fmtPrem(strike, c.lastPrice, true)}</span>
            </div>
            <div class="oc-t-strike">${strike.toFixed(2)}</div>
            <div class="oc-t-puts${putItm ? ' oc-itm' : ''}">
                <span>${fmtPrem(strike, p.lastPrice, false)}</span>
                <span>${fmt(p.lastPrice)}</span>
                <span>${fmt(p.ask)}</span>
                <span>${fmt(p.bid)}</span>
                <span>${fmtInt(p.volume)}</span>
                <span>${fmtInt(p.openInterest)}</span>
                <span>${fmt(p.iv, 1)}%</span>
            </div>
        </div>`;
    });
    // Append spot row if it belongs after the last strike
    if (spotInsertIdx === strikes.length) html += spotRow;

    body.innerHTML = html;
}


/* ============================================================
   Odds Tab – Line charts for Long Call / Long Put odds
   ============================================================ */

// State (data + abort) is encapsulated in static/state/oddsChainState.js.
// UI phase driven via appState.panels.set('odds', ...).
const _oddsState = () => window.appState.oddsChain;
const _oddsPanel = (phase, opts) => window.appState.panels.set('odds', phase, opts);
let _oddsCallChart = null;
let _oddsPutChart = null;

// Palette for expiration lines
const ODDS_COLORS = [
    '#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6',
    '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#6366f1',
    '#14b8a6', '#e11d48', '#a855f7', '#0ea5e9', '#d946ef',
];

document.addEventListener('DOMContentLoaded', function () {
    const tgt = document.getElementById('odds-target-pct');
    if (tgt) {
        tgt.addEventListener('input', function () {
            _oddsUpdateTargetDisplay();
            if (_oddsState().getData()) _oddsRenderCharts();
        });
    }
});

function _oddsUpdateTargetDisplay() {
    const el = document.getElementById('odds-target-value');
    const estMove = parseFloat((document.getElementById('odds-target-pct') || {}).value) || 0;
    const data = _oddsState().getData();
    const spot = data ? data.spot : null;
    if (!el) return;
    if (spot !== null && spot !== undefined) {
        const callTarget = (1 + estMove / 100) * spot;
        const putTarget = (1 - estMove / 100) * spot;
        el.textContent = `Call target ${callTarget.toFixed(2)} / Put target ${putTarget.toFixed(2)}  (Spot ${spot.toFixed(2)})`;
    } else {
        el.textContent = '';
    }
}

function loadOddsData() {
    const input = document.getElementById('ticker');
    const rawTicker = (input ? input.value : '').trim().toUpperCase();
    // Extract first ticker from potentially comma-separated list
    const ticker = rawTicker.split(/[,\n]+/)[0].trim();
    const tvEl = document.getElementById('odds-target-value');

    if (!ticker) {
        _oddsPanel('error', { message: 'Please enter a ticker symbol in the Parameter tab.' });
        return;
    }

    if (tvEl) { tvEl.textContent = ''; }
    _oddsPanel('loading', { message: 'Loading odds data...' });
    _oddsState().reset();
    const signal = _oddsState().beginRequest();

    // Build URL with config-driven filter params
    const params = new URLSearchParams({ ticker });
    const cfgDte = document.getElementById('cfg-max-dte');
    const cfgMLow = document.getElementById('cfg-moneyness-low');
    const cfgMHigh = document.getElementById('cfg-moneyness-high');
    if (cfgDte && cfgDte.value) params.set('max_dte', cfgDte.value);
    if (cfgMLow && cfgMLow.value) params.set('moneyness_low', cfgMLow.value);
    if (cfgMHigh && cfgMHigh.value) params.set('moneyness_high', cfgMHigh.value);

    fetch(`/api/option_chain?${params}`, { signal })
        .then(r => {
            if (!r.ok) {
                return r.json().catch(() => ({ error: `Server error (${r.status})` }));
            }
            return r.json();
        })
        .then(data => {
            if (data.error) { _oddsPanel('error', { message: data.error }); return; }
            _oddsState().setData(data);
            _oddsUpdateTargetDisplay();
            _oddsPanel('loaded', { data });
            _oddsRenderCharts();
        })
        .catch(err => {
            if (err.name === 'AbortError') return;
            _oddsPanel('error', { message: 'Network error: ' + err.message });
        });
}

function _oddsRenderCharts() {
    const data = _oddsState().getData();
    if (!data || !data.chain || !data.spot) return;

    const estMove = parseFloat((document.getElementById('odds-target-pct') || {}).value) || 0;
    const spot = data.spot;
    const callTarget = (1 + estMove / 100) * spot;
    const putTarget = (1 - estMove / 100) * spot;
    const exps = data.expirations || [];

    // Build datasets per expiration
    const callDatasets = [];
    const putDatasets = [];
    let allStrikes = new Set();

    exps.forEach((exp, idx) => {
        const ch = data.chain[exp];
        if (!ch) return;

        // Format legend as YYYYMMDD
        const legend = exp.replace(/-/g, '');
        const color = ODDS_COLORS[idx % ODDS_COLORS.length];

        // Calls – use ask price for long call
        const callPoints = [];
        (ch.calls || []).forEach(c => {
            if (c.strike == null) return;
            const price = (c.ask != null && c.ask > 0) ? c.ask : c.lastPrice;
            if (!price || price <= 0) return;
            const payoff = Math.max(callTarget - c.strike, 0);
            const odd = (payoff - price) / price;
            callPoints.push({ x: c.strike, y: parseFloat(odd.toFixed(4)) });
            allStrikes.add(c.strike);
        });
        if (callPoints.length > 0) {
            callPoints.sort((a, b) => a.x - b.x);
            callDatasets.push({
                label: legend,
                data: callPoints,
                borderColor: color,
                backgroundColor: color,
                borderWidth: 1.5,
                pointRadius: 2,
                pointHoverRadius: 4,
                tension: 0.1,
                fill: false,
            });
        }

        // Puts – use bid price for long put
        const putPoints = [];
        (ch.puts || []).forEach(p => {
            if (p.strike == null) return;
            const price = (p.bid != null && p.bid > 0) ? p.bid : p.lastPrice;
            if (!price || price <= 0) return;
            const payoff = Math.max(p.strike - putTarget, 0);
            const odd = (payoff - price) / price;
            putPoints.push({ x: p.strike, y: parseFloat(odd.toFixed(4)) });
            allStrikes.add(p.strike);
        });
        if (putPoints.length > 0) {
            putPoints.sort((a, b) => a.x - b.x);
            putDatasets.push({
                label: legend,
                data: putPoints,
                borderColor: color,
                backgroundColor: color,
                borderWidth: 1.5,
                pointRadius: 2,
                pointHoverRadius: 4,
                tension: 0.1,
                fill: false,
            });
        }
    });

    if (callDatasets.length === 0 && putDatasets.length === 0) {
        _oddsPanel('empty', { message: 'No valid option data to compute odds.' });
        return;
    }

    // Spot vertical line plugin
    const spotLinePlugin = {
        id: 'spotLine',
        afterDraw(chart) {
            const xScale = chart.scales.x;
            const yScale = chart.scales.y;
            if (!xScale || !yScale) return;
            const xPx = xScale.getPixelForValue(spot);
            if (xPx < xScale.left || xPx > xScale.right) return;
            const ctx = chart.ctx;
            ctx.save();
            ctx.beginPath();
            ctx.setLineDash([5, 4]);
            ctx.strokeStyle = '#f59e0b';
            ctx.lineWidth = 2;
            ctx.moveTo(xPx, yScale.top);
            ctx.lineTo(xPx, yScale.bottom);
            ctx.stroke();
            // Label
            ctx.setLineDash([]);
            ctx.fillStyle = '#92400e';
            ctx.font = 'bold 11px Inter, sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText('Spot ' + spot.toFixed(2), xPx, yScale.top - 6);
            ctx.restore();
        }
    };

    function makeChartOpts({ xMin, xMax } = {}) {
        const xCfg = {
            type: 'linear',
            title: { display: true, text: 'Strike', font: { size: 12 } },
            ticks: { font: { size: 10 } }
        };
        if (xMin !== undefined) xCfg.min = xMin;
        if (xMax !== undefined) xCfg.max = xMax;
        return {
            responsive: true,
            maintainAspectRatio: true,
            interaction: { mode: 'nearest', intersect: false },
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { font: { size: 11 }, boxWidth: 14, padding: 10 }
                },
                tooltip: {
                    callbacks: {
                        label: function (ctx) { return ctx.dataset.label + ': ' + ctx.parsed.y.toFixed(2) + 'x'; }
                    }
                }
            },
            scales: {
                x: xCfg,
                y: {
                    title: { display: true, text: 'Odd', font: { size: 12 } },
                    ticks: {
                        font: { size: 10 },
                        callback: function (v) { return v.toFixed(1) + 'x'; }
                    }
                }
            }
        };
    }

    // Destroy existing charts
    if (_oddsCallChart) { _oddsCallChart.destroy(); _oddsCallChart = null; }
    if (_oddsPutChart) { _oddsPutChart.destroy(); _oddsPutChart = null; }

    // X-axis range: (1 - estMove/100 - 0.05)*spot to (1 + estMove/100 + 0.05)*spot
    const xRangeMin = (1 - estMove / 100 - 0.05) * spot;
    const xRangeMax = (1 + estMove / 100 + 0.05) * spot;

    // Call chart
    const callCtx = document.getElementById('odds-call-chart');
    if (callCtx && callDatasets.length > 0) {
        _oddsCallChart = new Chart(callCtx, {
            type: 'line',
            data: { datasets: callDatasets },
            options: makeChartOpts({ xMin: xRangeMin, xMax: xRangeMax }),
            plugins: [spotLinePlugin]
        });
    }

    // Put chart
    const putCtx = document.getElementById('odds-put-chart');
    if (putCtx && putDatasets.length > 0) {
        _oddsPutChart = new Chart(putCtx, {
            type: 'line',
            data: { datasets: putDatasets },
            options: makeChartOpts({ xMin: xRangeMin, xMax: xRangeMax }),
            plugins: [spotLinePlugin]
        });
    }

    // UI visibility is driven by appState.panels.set('odds', 'loaded') in
    // loadOddsData(); no display-toggle needed here.

    // Module 4B: Load vol-context data
    _oddsLoadVolContext();
}


/* ============================================================
   Module 4B: Odds + Vol Context
   ============================================================ */

async function _oddsLoadVolContext() {
    const input = document.getElementById('ticker');
    const ticker = (input ? input.value : '').trim().toUpperCase();
    const tgt = parseFloat((document.getElementById('odds-target-pct') || {}).value) || 0;
    const volCtxDiv = document.getElementById('odds-vol-context');
    if (!volCtxDiv || !ticker) return;

    try {
        const resp = await fetch('/api/odds_with_vol', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ticker, target_pct: tgt })
        });
        const data = await resp.json();
        if (data.status === 'ok') {
            renderVolContextTable(volCtxDiv, data);
        }
    } catch (e) {
        console.warn('Vol context load error:', e);
    }
}

function renderVolContextTable(container, data) {
    const ctx = data.vol_context || {};
    let html = '<table class="data-table vol-context-table"><thead><tr>';
    html += '<th>Metric</th><th>Value</th>';
    html += '</tr></thead><tbody>';

    if (ctx.implied_vol != null) {
        html += `<tr><td>Avg Implied Vol (ATM)</td><td>${(ctx.implied_vol * 100).toFixed(1)}%</td></tr>`;
    }
    if (ctx.realized_vol != null) {
        html += `<tr><td>Realized Vol (20d)</td><td>${(ctx.realized_vol * 100).toFixed(1)}%</td></tr>`;
    }
    if (ctx.vol_premium != null) {
        const cls = ctx.vol_premium > 0 ? 'vol-premium-high' : 'vol-premium-low';
        html += `<tr><td>Vol Premium (IV - RV)</td><td class="${cls}">${(ctx.vol_premium * 100).toFixed(1)}%</td></tr>`;
    }
    if (ctx.vol_regime) {
        html += `<tr><td>Vol Regime</td><td>${ctx.vol_regime}</td></tr>`;
    }
    if (ctx.expected_move_1d != null) {
        html += `<tr><td>Expected Move (1d)</td><td>±${(ctx.expected_move_1d * 100).toFixed(2)}%</td></tr>`;
    }
    if (ctx.prob_above_target != null) {
        html += `<tr><td>P(above target)</td><td>${(ctx.prob_above_target * 100).toFixed(1)}%</td></tr>`;
    }
    if (ctx.prob_below_target != null) {
        html += `<tr><td>P(below target)</td><td>${(ctx.prob_below_target * 100).toFixed(1)}%</td></tr>`;
    }

    // Per-expiry odds
    if (data.odds_by_expiry && data.odds_by_expiry.length > 0) {
        html += '</tbody></table>';
        html += '<h4 class="section-subtitle" style="margin-top:1rem">Odds by Expiry (Vol-Adjusted)</h4>';
        html += '<table class="data-table vol-context-table"><thead><tr>';
        html += '<th>Expiry</th><th>DTE</th><th>IV</th><th>P(ITM Call)</th><th>P(ITM Put)</th><th>Expected Move</th>';
        html += '</tr></thead><tbody>';
        data.odds_by_expiry.forEach(row => {
            html += `<tr>
                <td>${row.expiry || ''}</td>
                <td>${row.dte || ''}</td>
                <td>${row.iv != null ? (row.iv * 100).toFixed(1) + '%' : '-'}</td>
                <td>${row.p_itm_call != null ? (row.p_itm_call * 100).toFixed(1) + '%' : '-'}</td>
                <td>${row.p_itm_put != null ? (row.p_itm_put * 100).toFixed(1) + '%' : '-'}</td>
                <td>${row.expected_move != null ? '±' + (row.expected_move * 100).toFixed(2) + '%' : '-'}</td>
            </tr>`;
        });
    }

    html += '</tbody></table>';
    container.innerHTML = html;
    container.style.display = 'block';
}
