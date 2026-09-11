// main.js – Form management, ticker validation, and page initialization.
// Depends on: utils.js, position.js, option-chain.js, market_review.js

const FormManager = {
    saveState() {
        // Batch B7: the horizon lives in state/marketParamsState.js and positions
        // in the Portfolio tab — this store is only the viewer's convenience copy
        // of the bar's ticker and the positions table.
        const formData = {
            ticker: document.getElementById('ticker').value,
            positions: this.getPositionsData()
        };
        localStorage.setItem('marketAnalysisForm', JSON.stringify(formData));
    },
    loadState() {
        const saved = localStorage.getItem('marketAnalysisForm');
        if (!saved) return;
        try {
            const formData = JSON.parse(saved);
            if (formData.ticker) document.getElementById('ticker').value = formData.ticker;
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
        const params = (window.appState && window.appState.marketParams && window.appState.marketParams.get()) || {};
        const startVal = this.normalizeMonth(params.from || (document.getElementById('start_time') || {}).value || '');
        const endVal = this.normalizeMonth(params.to || (document.getElementById('end_time') || {}).value || '');
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

// Validity feedback is a single ✅/❌ icon per ticker, rendered to the right
// of the input (#ticker-badges) — no separate status sentence.
let validationTimeout;
function validateTicker() {
    const rawInput = document.getElementById('ticker').value.trim().toUpperCase();
    const badgesDiv = document.getElementById('ticker-badges');

    if (!rawInput) {
        if (badgesDiv) badgesDiv.innerHTML = '';
        currentPrice = null;
        return;
    }

    clearTimeout(validationTimeout);
    validationTimeout = setTimeout(() => {
        const tickers = parseTickers(rawInput);
        if (tickers.length === 0) {
            if (badgesDiv) {
                badgesDiv.innerHTML = '<span class="ticker-badge invalid" title="No valid symbols">❌</span>';
            }
            return;
        }
        if (badgesDiv) badgesDiv.innerHTML = '';

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
                            const symbol = info.valid ? '✅' : '❌';
                            const priceTxt = info.valid && info.price ? ` $${info.price.toFixed(2)}` : '';
                            const title = `${escapeHtml(t)}${priceTxt}`;
                            return `<span class="${cls}" title="${title}">${symbol}</span>`;
                        }).join('');
                    }
                    const firstValid = Object.entries(results).find(([, info]) => info.valid);
                    currentPrice = firstValid ? firstValid[1].price : null;

                    const validTickers = Object.entries(results)
                        .filter(([, info]) => info.valid)
                        .map(([t]) => t);
                    if (validTickers.length > 0) preloadOptionChains(validTickers);
                }
            })
            .catch(() => {
                if (badgesDiv) {
                    badgesDiv.innerHTML = '<span class="ticker-badge invalid" title="Error checking ticker validity">❌</span>';
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
    const submitBtn = this.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = 'Analyzing...';
    submitBtn.disabled = true;
    this.submit();
    setTimeout(() => {
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    }, 30000);
});

document.addEventListener('DOMContentLoaded', function () {
    FormManager.loadState();
    FormManager.validateHorizon();
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

    // ── Global data-action delegation ──────────────────────────────
    // Buttons opt out of inline onclick by setting data-action="<id>".
    // Register handlers here; the click listener routes to the right fn.
    const actionHandlers = {
        'game-run': () => runGameAnalysis(),
        'oc-reload': () => loadOptionChain(),
        'payoff-ratio-reload': () => loadPayoffRatioData(),
        'sim-run': () => runSimulation(),
    };
    document.addEventListener('click', function (ev) {
        const target = ev.target.closest('[data-action]');
        if (!target) return;
        const action = target.getAttribute('data-action');
        const handler = actionHandlers[action];
        if (handler) {
            ev.preventDefault();
            handler(ev, target);
        }
    });
});
