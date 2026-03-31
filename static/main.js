// main.js – Form management, ticker validation, and page initialization.
// Depends on: utils.js, position.js, option-chain.js, market-review.js, game.js

const FormManager = {
    saveState() {
        const formData = {
            ticker: document.getElementById('ticker').value,
            start_time: this.normalizeMonth(document.getElementById('start_time').value),
            end_time: document.getElementById('end_time') ? this.normalizeMonth(document.getElementById('end_time').value) : '',
            positions: this.getPositionsData()
        };
        localStorage.setItem('marketAnalysisForm', JSON.stringify(formData));
    },
    saveConfig() {
        const cfg = {
            frequency: (document.getElementById('cfg-frequency') || {}).value || 'ME',
            side_bias: (document.getElementById('cfg-side-bias') || {}).value || 'Natural',
            risk_threshold: (document.getElementById('cfg-risk-threshold') || {}).value || '90',
            rolling_window: (document.getElementById('cfg-rolling-window') || {}).value || '120',
            max_dte: (document.getElementById('cfg-max-dte') || {}).value || '45',
            moneyness_low: (document.getElementById('cfg-moneyness-low') || {}).value || '0.70',
            moneyness_high: (document.getElementById('cfg-moneyness-high') || {}).value || '1.30',
            max_contracts: (document.getElementById('cfg-max-contracts') || {}).value || '1000',
        };
        localStorage.setItem('marketAnalysisConfig', JSON.stringify(cfg));
        this.syncConfigToForm();
    },
    loadConfig() {
        const saved = localStorage.getItem('marketAnalysisConfig');
        if (saved) {
            try {
                const cfg = JSON.parse(saved);
                const el = (id) => document.getElementById(id);
                if (cfg.frequency && el('cfg-frequency')) el('cfg-frequency').value = cfg.frequency;
                if (cfg.side_bias && el('cfg-side-bias')) el('cfg-side-bias').value = cfg.side_bias;
                if (cfg.risk_threshold && el('cfg-risk-threshold')) el('cfg-risk-threshold').value = cfg.risk_threshold;
                if (cfg.rolling_window && el('cfg-rolling-window')) el('cfg-rolling-window').value = cfg.rolling_window;
                if (cfg.max_dte && el('cfg-max-dte')) el('cfg-max-dte').value = cfg.max_dte;
                if (cfg.moneyness_low && el('cfg-moneyness-low')) el('cfg-moneyness-low').value = cfg.moneyness_low;
                if (cfg.moneyness_high && el('cfg-moneyness-high')) el('cfg-moneyness-high').value = cfg.moneyness_high;
                if (cfg.max_contracts && el('cfg-max-contracts')) el('cfg-max-contracts').value = cfg.max_contracts;
            } catch (e) { /* ignore */ }
        }
        this.syncConfigToForm();
    },
    syncConfigToForm() {
        const el = (id) => document.getElementById(id);
        if (el('frequency')) el('frequency').value = (el('cfg-frequency') || {}).value || 'ME';
        if (el('side_bias')) el('side_bias').value = (el('cfg-side-bias') || {}).value || 'Natural';
        if (el('risk_threshold')) el('risk_threshold').value = (el('cfg-risk-threshold') || {}).value || '90';
        if (el('rolling_window')) el('rolling_window').value = (el('cfg-rolling-window') || {}).value || '120';
    },
    loadState() {
        const saved = localStorage.getItem('marketAnalysisForm');
        if (!saved) return;
        try {
            const formData = JSON.parse(saved);
            if (formData.ticker) document.getElementById('ticker').value = formData.ticker;
            if (formData.start_time) document.getElementById('start_time').value = this.toMonthInput(formData.start_time);
            if (formData.end_time && document.getElementById('end_time')) document.getElementById('end_time').value = this.toMonthInput(formData.end_time);
            if (formData.positions && formData.positions.length > 0) {
                this.restorePositionsTable(formData.positions);
            } else if (formData.options && formData.options.length > 0) {
                this.restoreLegacyOptions(formData.options);
            }
        } catch (e) {
            console.error('Error loading saved form state:', e);
        }
    },
    normalizeMonth(val) {
        if (!val) return '';
        const m = val.match(/^(\d{4})[-]?(\d{2})$/);
        return m ? `${m[1]}${m[2]}` : val;
    },
    toMonthInput(val) {
        const m = val.match(/^(\d{4})(\d{2})$/);
        return m ? `${m[1]}-${m[2]}` : val;
    },
    validateHorizon() {
        const startVal = this.normalizeMonth(document.getElementById('start_time').value);
        const endVal = this.normalizeMonth(document.getElementById('end_time').value);
        const warning = document.getElementById('horizon-warning');
        if (!warning) return true;
        warning.style.display = 'none';
        warning.textContent = '';
        if (startVal && endVal && endVal < startVal) {
            warning.textContent = 'End month must be the same or after Start month.';
            warning.style.display = 'block';
            return false;
        }
        return true;
    },
    getPositionsData() {
        return getPositionsData();
    },
    getOptionsData() {
        const positions = getPositionsData();
        return positions.map(p => ({
            option_type: p.option_type,
            strike: String(p.strike),
            quantity: String(p.quantity),
            premium: String(p.price)
        }));
    },
    restorePositionsTable(positionsData) {
        const tbody = document.getElementById('positions-tbody');
        if (!tbody) return;
        tbody.innerHTML = '';
        const count = Math.max(1, positionsData.length);
        for (let i = 0; i < count; i++) {
            const row = createPositionRow();
            if (i < positionsData.length) {
                const p = positionsData[i];
                if (p.ticker) row.querySelector('[name="pos_ticker"]').value = p.ticker;
                if (p.type) row.querySelector('[name="pos_type"]').value = p.type;
                if (p.side) row.querySelector('[name="pos_side"]').value = p.side;
                if (p.price) row.querySelector('[name="pos_price"]').value = p.price;
                if (p.qty) row.querySelector('[name="pos_qty"]').value = p.qty;
            }
            tbody.appendChild(row);
        }
    },
    restoreLegacyOptions(optionsData) {
        const tbody = document.getElementById('positions-tbody');
        if (!tbody) return;
        tbody.innerHTML = '';
        const count = Math.max(1, optionsData.length);
        for (let i = 0; i < count; i++) {
            const row = createPositionRow();
            if (i < optionsData.length) {
                const opt = optionsData[i];
                const ot = opt.option_type || '';
                if (ot.includes('C')) row.querySelector('[name="pos_type"]').value = 'call';
                if (ot.includes('P')) row.querySelector('[name="pos_type"]').value = 'put';
                if (ot.startsWith('L')) row.querySelector('[name="pos_side"]').value = 'long';
                if (ot.startsWith('S')) row.querySelector('[name="pos_side"]').value = 'short';
                if (opt.premium) row.querySelector('[name="pos_price"]').value = opt.premium;
                if (opt.quantity) row.querySelector('[name="pos_qty"]').value = opt.quantity;
            }
            tbody.appendChild(row);
        }
    }
};

let validationTimeout;
function validateTicker() {
    const rawInput = document.getElementById('ticker').value.trim().toUpperCase();
    const validationDiv = document.getElementById('ticker-validation');
    const badgesDiv = document.getElementById('ticker-badges');

    if (!rawInput) {
        if (validationDiv) validationDiv.innerHTML = '';
        if (badgesDiv) badgesDiv.innerHTML = '';
        currentPrice = null;
        return;
    }

    clearTimeout(validationTimeout);
    validationTimeout = setTimeout(() => {
        const tickers = parseTickers(rawInput);
        if (tickers.length === 0) {
            if (validationDiv) validationDiv.innerHTML = '<i class="fas fa-exclamation-circle"></i> No valid symbols';
            return;
        }
        if (validationDiv) validationDiv.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Validating...';

        fetch('/api/validate_tickers', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tickers })
        })
            .then(r => r.json())
            .then(data => {
                if (data.status === 'ok') {
                    const results = data.results || {};
                    if (badgesDiv) {
                        badgesDiv.innerHTML = Object.entries(results).map(([t, info]) => {
                            const cls = info.valid ? 'ticker-badge valid' : 'ticker-badge invalid';
                            const icon = info.valid ? 'check-circle' : 'exclamation-circle';
                            const priceTxt = info.valid && info.price ? ` $${info.price.toFixed(2)}` : '';
                            return `<span class="${cls}"><i class="fas fa-${icon}"></i> ${escapeHtml(t)}${priceTxt}</span>`;
                        }).join(' ');
                    }
                    const firstValid = Object.entries(results).find(([, info]) => info.valid);
                    currentPrice = firstValid ? firstValid[1].price : null;

                    const validCount = Object.values(results).filter(r => r.valid).length;
                    const totalCount = Object.keys(results).length;
                    if (validationDiv) {
                        if (validCount === totalCount) {
                            validationDiv.innerHTML = `<i class="fas fa-check-circle"></i> ${validCount} ticker(s) valid`;
                            validationDiv.className = 'ticker-validation valid';
                        } else {
                            validationDiv.innerHTML = `<i class="fas fa-exclamation-triangle"></i> ${validCount}/${totalCount} valid`;
                            validationDiv.className = 'ticker-validation warning';
                        }
                    }

                    const validTickers = Object.entries(results)
                        .filter(([, info]) => info.valid)
                        .map(([t]) => t);
                    if (validTickers.length > 0) preloadOptionChains(validTickers);
                }
            })
            .catch(() => {
                if (validationDiv) {
                    validationDiv.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Error';
                    validationDiv.className = 'ticker-validation warning';
                }
                currentPrice = null;
            });
    }, 500);
}

document.getElementById('analysis-form')?.addEventListener('submit', function (e) {
    e.preventDefault();
    if (!FormManager.validateHorizon()) {
        return;
    }
    FormManager.saveState();
    FormManager.syncConfigToForm();
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

document.addEventListener('DOMContentLoaded', function () {
    FormManager.loadConfig();
    FormManager.loadState();
    FormManager.validateHorizon();
    ['start_time', 'end_time'].forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('change', () => {
                FormManager.validateHorizon();
                FormManager.saveState();
            });
        }
    });
    ['cfg-frequency', 'cfg-side-bias', 'cfg-risk-threshold', 'cfg-rolling-window',
        'cfg-max-dte', 'cfg-moneyness-low', 'cfg-moneyness-high', 'cfg-max-contracts'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.addEventListener('change', () => FormManager.saveConfig());
        });
    const tbody = document.getElementById('positions-tbody');
    if (tbody && tbody.children.length === 0) {
        initializeOptionsTable();
    }
    const tickerInput = document.getElementById('ticker');
    if (tickerInput) {
        tickerInput.addEventListener('input', validateTicker);
        if (tickerInput.value.trim()) validateTicker();
    }
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
