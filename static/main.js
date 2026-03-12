// Extracted JavaScript from index.html
// Handles options section, form persistence, ticker validation, and submission.

let currentPrice = null;

function toggleOptionsSection() {
    const content = document.getElementById('options-content');
    const icon = document.getElementById('options-toggle-icon');
    if (content.style.display === 'none' || content.style.display === '') {
        content.style.display = 'block';
        icon.classList.remove('fa-chevron-down');
        icon.classList.add('fa-chevron-up');
    } else {
        content.style.display = 'none';
        icon.classList.remove('fa-chevron-up');
        icon.classList.add('fa-chevron-down');
    }
}

function toggleSizingSection() {
    const content = document.getElementById('sizing-content');
    const icon = document.getElementById('sizing-toggle-icon');
    if (content.style.display === 'none' || content.style.display === '') {
        content.style.display = 'block';
        icon.classList.remove('fa-chevron-down');
        icon.classList.add('fa-chevron-up');
    } else {
        content.style.display = 'none';
        icon.classList.remove('fa-chevron-up');
        icon.classList.add('fa-chevron-down');
    }
}

function initializeOptionsTable() {
    const tbody = document.getElementById('options-tbody');
    tbody.innerHTML = '';
    addOptionRow();
}

function createOptionRow() {
    const row = document.createElement('tr');
    row.innerHTML = `
        <td>
            <select name="option_type" class="option-select">
                <option value="">Select Type</option>
                <option value="SC">Short Call</option>
                <option value="SP">Short Put</option>
                <option value="LC">Long Call</option>
                <option value="LP">Long Put</option>
            </select>
        </td>
        <td>
            <input type="number" name="strike" step="0.01" placeholder="${currentPrice || 'Strike'}" value="" class="strike-input">
        </td>
        <td>
            <input type="number" name="quantity" placeholder="Quantity" value="" class="quantity-input">
        </td>
        <td>
            <input type="number" name="premium" step="0.01" placeholder="Premium" value="" class="premium-input">
        </td>
        <td>
            <button type="button" class="btn-delete" onclick="deleteOptionRow(this)">
                <i class="fas fa-trash"></i>
            </button>
        </td>`;
    return row;
}

function addOptionRow() {
    const tbody = document.getElementById('options-tbody');
    const row = createOptionRow();
    tbody.appendChild(row);
    FormManager.saveState();
}

function deleteOptionRow(button) {
    const tbody = document.getElementById('options-tbody');
    const row = button.closest('tr');
    row.remove();
    if (tbody.children.length === 0) {
        addOptionRow();
    }
    FormManager.saveState();
}

const FormManager = {
    saveState() {
        const formData = {
            ticker: document.getElementById('ticker').value,
            start_time: this.normalizeMonth(document.getElementById('start_time').value),
            end_time: document.getElementById('end_time') ? this.normalizeMonth(document.getElementById('end_time').value) : '',
            frequency: document.getElementById('frequency').value,
            risk_threshold: document.getElementById('risk_threshold').value,
            side_bias: document.getElementById('side_bias').value,
            options: this.getOptionsData()
        };
        localStorage.setItem('marketAnalysisForm', JSON.stringify(formData));
    },
    loadState() {
        const saved = localStorage.getItem('marketAnalysisForm');
        if (!saved) return;
        try {
            const formData = JSON.parse(saved);
            if (formData.ticker) document.getElementById('ticker').value = formData.ticker;
            if (formData.start_time) document.getElementById('start_time').value = this.toMonthInput(formData.start_time);
            if (formData.end_time && document.getElementById('end_time')) document.getElementById('end_time').value = this.toMonthInput(formData.end_time);
            if (formData.frequency) document.getElementById('frequency').value = formData.frequency;
            if (formData.risk_threshold) document.getElementById('risk_threshold').value = formData.risk_threshold;
            if (formData.side_bias) document.getElementById('side_bias').value = formData.side_bias;
            // No periods checkboxes anymore
            if (formData.options && formData.options.length > 0) {
                this.restoreOptionsTable(formData.options);
            }
        } catch (e) {
            console.error('Error loading saved form state:', e);
        }
    },
    normalizeMonth(val) {
        // Accept 'YYYY-MM' (from month input) or 'YYYYMM'; return 'YYYYMM'
        if (!val) return '';
        const m = val.match(/^(\d{4})[-]?(\d{2})$/);
        return m ? `${m[1]}${m[2]}` : val;
    },
    toMonthInput(val) {
        // Convert 'YYYYMM' to 'YYYY-MM' for month input
        const m = val.match(/^(\d{4})(\d{2})$/);
        return m ? `${m[1]}-${m[2]}` : val;
    },
    validateHorizon() {
        const startVal = this.normalizeMonth(document.getElementById('start_time').value);
        const endVal = this.normalizeMonth(document.getElementById('end_time').value);
        const warning = document.getElementById('horizon-warning');
        warning.style.display = 'none';
        warning.textContent = '';
        if (startVal && endVal && endVal < startVal) {
            warning.textContent = 'End month must be the same or after Start month.';
            warning.style.display = 'block';
            return false;
        }
        return true;
    },
    getOptionsData() {
        const rows = document.querySelectorAll('#options-table tbody tr');
        const optionsData = [];
        rows.forEach(row => {
            const option_type = row.querySelector('select[name="option_type"]').value;
            const strike = row.querySelector('input[name="strike"]').value;
            const quantity = row.querySelector('input[name="quantity"]').value;
            const premium = row.querySelector('input[name="premium"]').value;
            if (option_type && strike && quantity && premium && parseFloat(strike) > 0 && parseInt(quantity) !== 0 && parseFloat(premium) > 0) {
                optionsData.push({ option_type, strike, quantity, premium });
            }
        });
        return optionsData;
    },
    restoreOptionsTable(optionsData) {
        const tbody = document.getElementById('options-tbody');
        tbody.innerHTML = '';
        const rowCount = Math.max(1, optionsData.length);
        for (let i = 0; i < rowCount; i++) {
            const row = createOptionRow();
            if (i < optionsData.length) {
                const option = optionsData[i];
                row.querySelector('select[name="option_type"]').value = option.option_type;
                row.querySelector('input[name="strike"]').value = option.strike;
                row.querySelector('input[name="quantity"]').value = option.quantity;
                row.querySelector('input[name="premium"]').value = option.premium;
            }
            tbody.appendChild(row);
        }
    }
};

let validationTimeout;
function validateTicker() {
    const ticker = document.getElementById('ticker').value.trim().toUpperCase();
    const validationDiv = document.getElementById('ticker-validation');
    if (!ticker) {
        validationDiv.innerHTML = '';
        currentPrice = null;
        updateStrikePlaceholders();
        return;
    }
    clearTimeout(validationTimeout);
    validationTimeout = setTimeout(() => {
        validationDiv.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Validating...';
        fetch('/api/validate_ticker', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ticker })
        })
        .then(response => response.json())
        .then(data => {
            if (data.valid) {
                validationDiv.innerHTML = '<i class="fas fa-check-circle"></i> Valid';
                validationDiv.className = 'ticker-validation valid';
                currentPrice = data.price || null;
            } else {
                validationDiv.innerHTML = '<i class="fas fa-exclamation-circle"></i> Invalid';
                validationDiv.className = 'ticker-validation invalid';
                currentPrice = null;
            }
            updateStrikePlaceholders();
        })
        .catch(() => {
            validationDiv.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Error';
            validationDiv.className = 'ticker-validation warning';
            currentPrice = null;
            updateStrikePlaceholders();
        });
    }, 500);
}

function updateStrikePlaceholders() {
    document.querySelectorAll('.strike-input').forEach(input => {
        input.placeholder = currentPrice ? currentPrice.toString() : 'Strike';
    });
}

document.getElementById('analysis-form')?.addEventListener('submit', function(e) {
    e.preventDefault();
    if (!FormManager.validateHorizon()) {
        return; // Block submit on invalid horizon
    }
    FormManager.saveState();
    const optionsData = FormManager.getOptionsData();
    document.getElementById('option_position').value = JSON.stringify(optionsData);
    const submitBtn = this.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Analyzing...';
    submitBtn.disabled = true;
    this.submit();
    setTimeout(() => {
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    }, 30000);
});

document.addEventListener('DOMContentLoaded', function() {
    FormManager.loadState();
    // Validate horizon on load and on change
    FormManager.validateHorizon();
    ['start_time','end_time'].forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('change', () => {
                FormManager.validateHorizon();
                FormManager.saveState();
            });
        }
    });
    const tbody = document.getElementById('options-tbody');
    if (tbody && tbody.children.length === 0) {
        initializeOptionsTable();
    }
    const content = document.getElementById('options-content');
    if (content) content.style.display = 'none';
    const tickerInput = document.getElementById('ticker');
    if (tickerInput) tickerInput.addEventListener('input', validateTicker);
    document.querySelectorAll('input, select').forEach(el => {
        el.addEventListener('change', FormManager.saveState.bind(FormManager));
    });
    if (document.querySelector('.results-section')) {
        setTimeout(() => {
            document.querySelector('.results-section').scrollIntoView({ behavior: 'smooth' });
        }, 500);
    }
    enhanceMarketReviewTable();
});

/* ============================================================
   Option Chain – T-format display with maturity-date subtabs
   ============================================================ */

let _ocChainData = null;   // { expirations, chain, spot }
let _ocActivExp  = null;   // currently selected expiration

// No auto-fill needed — Option Chain now reads from the main Parameter ticker directly

// No auto-fill needed — Option Chain now reads from the main Parameter ticker directly

function loadOptionChain() {
    const input   = document.getElementById('ticker');
    const ticker  = (input ? input.value : '').trim().toUpperCase();
    const btn     = document.getElementById('oc-load-btn');
    const status  = document.getElementById('oc-status');
    const empty   = document.getElementById('oc-empty');
    const expTabs = document.getElementById('oc-exp-tabs');
    const wrapper = document.getElementById('oc-chain-wrapper');

    if (!ticker) { _ocShowError('Please enter a ticker symbol in the Parameter tab.'); return; }

    // Loading state
    if (btn)     { btn.disabled = true; btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading...'; }
    if (status)  { status.style.display = 'none'; }
    if (empty)   { empty.style.display = 'none'; }
    if (expTabs) { expTabs.style.display = 'none'; }
    if (wrapper) { wrapper.style.display = 'none'; }

    _ocChainData = null;
    _ocActivExp  = null;

    fetch(`/api/option_chain?ticker=${encodeURIComponent(ticker)}`)
        .then(r => r.json())
        .then(data => {
            if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fas fa-download"></i> Load Chain'; }
            if (data.error) { _ocShowError(data.error); return; }
            _ocChainData = data;
            _ocBuildExpTabs(data.expirations);
            if (data.expirations && data.expirations.length > 0) {
                _ocSelectExp(data.expirations[0]);
            }
        })
        .catch(err => {
            if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fas fa-download"></i> Load Chain'; }
            _ocShowError('Network error: ' + err.message);
        });
}

function _ocShowError(msg) {
    const status  = document.getElementById('oc-status');
    const empty   = document.getElementById('oc-empty');
    const expTabs = document.getElementById('oc-exp-tabs');
    const wrapper = document.getElementById('oc-chain-wrapper');
    if (status)  { status.style.display = 'block'; status.innerHTML = `<i class="fas fa-exclamation-circle"></i> ${msg}`; }
    if (empty)   { empty.style.display = 'none'; }
    if (expTabs) { expTabs.style.display = 'none'; }
    if (wrapper) { wrapper.style.display = 'none'; }
}

function _ocBuildExpTabs(expirations) {
    const list = document.getElementById('oc-exp-tab-list');
    const expTabs = document.getElementById('oc-exp-tabs');
    if (!list || !expTabs) return;
    list.innerHTML = '';
    expirations.forEach(exp => {
        const btn = document.createElement('button');
        btn.className = 'oc-exp-btn';
        btn.textContent = exp;
        btn.dataset.exp = exp;
        btn.addEventListener('click', function() { _ocSelectExp(this.dataset.exp); });
        list.appendChild(btn);
    });
    expTabs.style.display = 'block';
}

function _ocSelectExp(exp) {
    _ocActivExp = exp;

    // Highlight active tab
    document.querySelectorAll('.oc-exp-btn').forEach(b => {
        b.classList.toggle('active', b.dataset.exp === exp);
    });

    if (!_ocChainData || !_ocChainData.chain[exp]) return;

    const { calls, puts } = _ocChainData.chain[exp];
    _ocRenderChain(calls, puts);
}

function _ocRenderChain(calls, puts) {
    const body    = document.getElementById('oc-chain-body');
    const wrapper = document.getElementById('oc-chain-wrapper');
    const empty   = document.getElementById('oc-empty');
    const status  = document.getElementById('oc-status');
    if (!body) return;

    // Build strike-keyed maps
    const callMap = {};
    const putMap  = {};
    (calls || []).forEach(c => { callMap[c.strike] = c; });
    (puts  || []).forEach(p => { putMap[p.strike]  = p; });

    // Merge all unique strikes
    const strikes = Array.from(new Set([
        ...(calls || []).map(c => c.strike),
        ...(puts  || []).map(p => p.strike),
    ])).sort((a, b) => a - b);

    if (strikes.length === 0) {
        body.innerHTML = '<div class="oc-no-data">No data for this expiration.</div>';
        wrapper.style.display = 'block';
        if (empty) empty.style.display = 'none';
        if (status) status.style.display = 'none';
        return;
    }

    const spot   = _ocChainData ? _ocChainData.spot : null;

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
        const p = putMap[strike]  || {};
        const callItm = c.itm === true;
        const putItm  = p.itm === true;

        // Liquidity score: pick worst of call/put for the row
        const cLiq = c.liq_score || '';
        const pLiq = p.liq_score || '';
        const worstLiq = (cLiq === 'AVOID' || pLiq === 'AVOID') ? 'AVOID'
                       : (cLiq === 'FAIR'  || pLiq === 'FAIR')  ? 'FAIR' : '';
        const liqClass = worstLiq === 'AVOID' ? ' oc-liq-avoid'
                       : worstLiq === 'FAIR'  ? ' oc-liq-fair' : '';

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
    wrapper.style.display = 'block';
    if (empty)  empty.style.display  = 'none';
    if (status) status.style.display = 'none';
}


/* ============================================================
   Odds Tab – Line charts for Long Call / Long Put odds
   ============================================================ */

let _oddsChainData = null;   // same shape as _ocChainData
let _oddsCallChart = null;
let _oddsPutChart  = null;

// Palette for expiration lines
const ODDS_COLORS = [
    '#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6',
    '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#6366f1',
    '#14b8a6', '#e11d48', '#a855f7', '#0ea5e9', '#d946ef',
];

document.addEventListener('DOMContentLoaded', function() {
    const tgt = document.getElementById('odds-target-pct');
    if (tgt) {
        tgt.addEventListener('input', function() {
            _oddsUpdateTargetDisplay();
            if (_oddsChainData) _oddsRenderCharts();
        });
    }
});

function _oddsUpdateTargetDisplay() {
    const el       = document.getElementById('odds-target-value');
    const estMove  = parseFloat((document.getElementById('odds-target-pct') || {}).value) || 0;
    const spot     = _oddsChainData ? _oddsChainData.spot : null;
    if (!el) return;
    if (spot !== null && spot !== undefined) {
        const callTarget = (1 + estMove / 100) * spot;
        const putTarget  = (1 - estMove / 100) * spot;
        el.textContent = `Call target ${callTarget.toFixed(2)} / Put target ${putTarget.toFixed(2)}  (Spot ${spot.toFixed(2)})`;
    } else {
        el.textContent = '';
    }
}

function loadOddsData() {
    const input  = document.getElementById('ticker');
    const ticker = (input ? input.value : '').trim().toUpperCase();
    const btn    = document.getElementById('odds-load-btn');
    const status = document.getElementById('odds-status');
    const empty  = document.getElementById('odds-empty');
    const wrap   = document.getElementById('odds-charts-wrapper');
    const tvEl   = document.getElementById('odds-target-value');

    if (!ticker) { _oddsShowError('Please enter a ticker symbol in the Parameter tab.'); return; }

    if (btn)    { btn.disabled = true; btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading...'; }
    if (status) { status.style.display = 'none'; }
    if (empty)  { empty.style.display = 'none'; }
    if (wrap)   { wrap.style.display = 'none'; }
    if (tvEl)   { tvEl.textContent = ''; }

    _oddsChainData = null;

    fetch(`/api/option_chain?ticker=${encodeURIComponent(ticker)}`)
        .then(r => r.json())
        .then(data => {
            if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fas fa-download"></i> Load Chain'; }
            if (data.error) { _oddsShowError(data.error); return; }
            _oddsChainData = data;
            _oddsUpdateTargetDisplay();
            _oddsRenderCharts();
        })
        .catch(err => {
            if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fas fa-download"></i> Load Chain'; }
            _oddsShowError('Network error: ' + err.message);
        });
}

function _oddsShowError(msg) {
    const status = document.getElementById('odds-status');
    const empty  = document.getElementById('odds-empty');
    const wrap   = document.getElementById('odds-charts-wrapper');
    if (status) { status.style.display = 'block'; status.innerHTML = `<i class="fas fa-exclamation-circle"></i> ${msg}`; }
    if (empty)  { empty.style.display = 'none'; }
    if (wrap)   { wrap.style.display = 'none'; }
}

function _oddsRenderCharts() {
    const data = _oddsChainData;
    if (!data || !data.chain || !data.spot) return;

    const estMove    = parseFloat((document.getElementById('odds-target-pct') || {}).value) || 0;
    const spot       = data.spot;
    const callTarget = (1 + estMove / 100) * spot;
    const putTarget  = (1 - estMove / 100) * spot;
    const exps       = data.expirations || [];

    // Build datasets per expiration
    const callDatasets = [];
    const putDatasets  = [];
    let allStrikes = new Set();

    exps.forEach((exp, idx) => {
        const ch = data.chain[exp];
        if (!ch) return;

        // Format legend as YYYYMMDD
        const legend = exp.replace(/-/g, '');
        const color  = ODDS_COLORS[idx % ODDS_COLORS.length];

        // Calls – use ask price for long call
        const callPoints = [];
        (ch.calls || []).forEach(c => {
            if (c.strike == null) return;
            const price = (c.ask != null && c.ask > 0) ? c.ask : c.lastPrice;
            if (!price || price <= 0) return;
            const payoff = Math.max(callTarget - c.strike, 0);
            const odd    = (payoff - price) / price;
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
            const odd    = (payoff - price) / price;
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
        _oddsShowError('No valid option data to compute odds.');
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
                        label: function(ctx) { return ctx.dataset.label + ': ' + ctx.parsed.y.toFixed(2) + 'x'; }
                    }
                }
            },
            scales: {
                x: xCfg,
                y: {
                    title: { display: true, text: 'Odd', font: { size: 12 } },
                    ticks: {
                        font: { size: 10 },
                        callback: function(v) { return v.toFixed(1) + 'x'; }
                    }
                }
            }
        };
    }

    // Destroy existing charts
    if (_oddsCallChart) { _oddsCallChart.destroy(); _oddsCallChart = null; }
    if (_oddsPutChart)  { _oddsPutChart.destroy();  _oddsPutChart  = null; }

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

    // Show wrapper
    const wrap   = document.getElementById('odds-charts-wrapper');
    const empty  = document.getElementById('odds-empty');
    const status = document.getElementById('odds-status');
    if (wrap)   wrap.style.display   = 'block';
    if (empty)  empty.style.display  = 'none';
    if (status) status.style.display = 'none';
}

/* ============================================================
   Market Review – inline bars & sortable columns
   ============================================================ */
function enhanceMarketReviewTable() {
    const wrapper = document.querySelector('#tab-market-review .table-wrapper');
    if (!wrapper) return;
    const table = wrapper.querySelector('table');
    if (!table) return;

    const tbody = table.tBodies[0];
    if (!tbody) return;
    const rows = Array.from(tbody.rows);
    if (!rows.length) return;

    const colCount = rows[0].cells.length;

    // Parse a formatted value (e.g. "-5.3%", "0.7", "N/A") to float or null
    function parseVal(text) {
        if (!text) return null;
        const s = text.replace('%', '').trim();
        if (s === 'N/A' || s === '') return null;
        const v = parseFloat(s);
        return isNaN(v) ? null : v;
    }

    // Collect original text and build per-column stats BEFORE modifying DOM
    const cellVals = rows.map(r =>
        Array.from(r.cells).map(td => parseVal(td.textContent))
    );
    const colStats = [];
    for (let c = 0; c < colCount; c++) {
        const nums = cellVals.map(rv => rv[c]).filter(v => v !== null);
        const min  = nums.length ? Math.min(...nums) : 0;
        const max  = nums.length ? Math.max(...nums) : 0;
        colStats.push({ min, max, hasNeg: nums.some(v => v < 0) });
    }

    // Build set of column indices that belong to "Last Close" group (no bar)
    const noBarsSet = new Set();
    const theadRowsEarly = Array.from(table.tHead ? table.tHead.rows : []);
    if (theadRowsEarly.length >= 1) {
        let colCursor = 0;
        Array.from(theadRowsEarly[0].cells).forEach(th => {
            const span = parseInt(th.getAttribute('colspan') || '1', 10);
            if (th.textContent.trim() === 'Last Close') {
                for (let k = 0; k < span; k++) noBarsSet.add(colCursor + k);
            }
            colCursor += span;
        });
    }

    // Add inline bar to every data cell (skip the index column at c=0)
    rows.forEach((row, ri) => {
        Array.from(row.cells).forEach((td, ci) => {
            if (ci === 0) return;                         // row index (asset name)
            if (noBarsSet.has(ci)) {                      // no bar for Last Close
                td.innerHTML = `<div class="mr-cell-inner">${td.textContent.trim()}</div>`;
                return;
            }
            const val  = cellVals[ri][ci];
            const stat = colStats[ci];
            const range = stat.max - stat.min;

            // Wrap existing text
            const origText = td.textContent.trim();
            td.innerHTML = `<div class="mr-cell-inner">${origText}</div>`;

            if (val === null || range === 0) {
                td.innerHTML += '<div class="mr-bar-wrap"></div>';
                return;
            }

            const wrapDiv = document.createElement('div');
            wrapDiv.className = 'mr-bar-wrap';

            const barDiv = document.createElement('div');
            barDiv.className = 'mr-bar';

            if (stat.hasNeg) {
                // Diverging bar centered at 0
                wrapDiv.classList.add('diverging');
                const absMax    = Math.max(Math.abs(stat.min), Math.abs(stat.max)) || 1;
                const halfWidth = Math.min(Math.abs(val) / absMax * 50, 50);
                if (val >= 0) {
                    barDiv.classList.add('mr-bar-pos');
                    barDiv.style.left  = '50%';
                    barDiv.style.width = halfWidth + '%';
                } else {
                    barDiv.classList.add('mr-bar-neg');
                    barDiv.style.left  = (50 - halfWidth) + '%';
                    barDiv.style.width = halfWidth + '%';
                }
            } else {
                // Simple positive bar (0 → max)
                barDiv.classList.add('mr-bar-neutral');
                const pct = stat.max > 0 ? Math.min((val / stat.max) * 100, 100) : 0;
                barDiv.style.width = pct + '%';
            }

            wrapDiv.appendChild(barDiv);
            td.appendChild(wrapDiv);
        });
    });

    // ── Sortable column headers ──
    // With pandas MultiIndex there are 2 header rows; the last one has one <th>
    // per data column and aligns 1-to-1 with the body cell indices.
    const theadRows = Array.from(table.tHead ? table.tHead.rows : []);
    if (!theadRows.length) return;
    const sortRow = theadRows[theadRows.length - 1];

    let sortColIdx = null;
    let sortDir    = 'asc';

    // Rebuild colStats from ORIGINAL values (already captured)
    // so sorting still works after DOM modification.
    const origVals = cellVals;   // alias for clarity

    Array.from(sortRow.cells).forEach((th, ci) => {
        if (ci === 0) return;   // skip row-index header
        th.classList.add('mr-sortable');
        const icon = document.createElement('span');
        icon.className = 'mr-sort-icon';
        icon.textContent = ' ⇅';
        th.appendChild(icon);

        th.addEventListener('click', () => {
            if (sortColIdx === ci) {
                sortDir = sortDir === 'asc' ? 'desc' : 'asc';
            } else {
                sortColIdx = ci;
                sortDir    = 'asc';
            }

            // Update sort icons
            Array.from(sortRow.cells).forEach((h, j) => {
                const ic = h.querySelector('.mr-sort-icon');
                if (!ic) return;
                h.classList.remove('sorted');
                ic.textContent = ' ⇅';
            });
            th.classList.add('sorted');
            icon.textContent = sortDir === 'asc' ? ' ↑' : ' ↓';

            // Snapshot current row order with their original numeric values
            const rowEntries = Array.from(tbody.rows).map(r => ({
                row: r,
                val: parseVal(r.cells[ci].querySelector('.mr-cell-inner')
                              ? r.cells[ci].querySelector('.mr-cell-inner').textContent
                              : r.cells[ci].textContent)
            }));

            rowEntries.sort((a, b) => {
                if (a.val === null && b.val === null) return 0;
                if (a.val === null) return 1;
                if (b.val === null) return -1;
                return sortDir === 'asc' ? a.val - b.val : b.val - a.val;
            });

            rowEntries.forEach(({ row }) => tbody.appendChild(row));
        });
    });
}
