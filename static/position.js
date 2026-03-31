/* ============================================================
   Position Module — cascade dropdowns, portfolio analysis,
   and option chain preload
   ============================================================ */

function createPositionRow(defaultTicker) {
    const row = document.createElement('tr');
    const tickerOpts = getValidTickers().map(t => {
        const escaped = escapeHtml(t);
        return `<option value="${escaped}" ${t === defaultTicker ? 'selected' : ''}>${escaped}</option>`;
    }).join('');

    row.innerHTML = `
        <td>
            <select name="pos_ticker" class="pos-select" onchange="onPositionTickerChange(this)">
                <option value="">-- ticker --</option>
                ${tickerOpts}
            </select>
        </td>
        <td>
            <select name="pos_type" class="pos-select" onchange="onPositionTypeChange(this)">
                <option value="call">Call</option>
                <option value="put">Put</option>
            </select>
        </td>
        <td>
            <select name="pos_expiry" class="pos-select" onchange="onPositionExpiryChange(this)">
                <option value="">-- expiry --</option>
            </select>
        </td>
        <td>
            <select name="pos_strike" class="pos-select" onchange="onPositionStrikeChange(this)">
                <option value="">-- strike --</option>
            </select>
        </td>
        <td>
            <select name="pos_side" class="pos-select">
                <option value="long">Long</option>
                <option value="short">Short</option>
            </select>
        </td>
        <td>
            <input type="number" name="pos_price" step="0.01" class="pos-price-input" placeholder="Mid">
        </td>
        <td>
            <input type="number" name="pos_qty" step="1" min="1" value="1" class="pos-qty-input">
        </td>
        <td>
            <button type="button" class="btn-delete" onclick="deletePositionRow(this)">
                <i class="fas fa-trash"></i>
            </button>
        </td>`;
    return row;
}

function addPositionRow(defaultTicker) {
    const tbody = document.getElementById('positions-tbody');
    if (!tbody) return;
    tbody.appendChild(createPositionRow(defaultTicker || ''));
    FormManager.saveState();
}

function deletePositionRow(button) {
    const tbody = document.getElementById('positions-tbody');
    const row = button.closest('tr');
    row.remove();
    if (tbody && tbody.children.length === 0) addPositionRow();
    FormManager.saveState();
}

function onPositionTickerChange(selectEl) {
    const row = selectEl.closest('tr');
    const ticker = selectEl.value;
    const expirySelect = row.querySelector('[name="pos_expiry"]');
    const strikeSelect = row.querySelector('[name="pos_strike"]');
    expirySelect.innerHTML = '<option value="">-- expiry --</option>';
    strikeSelect.innerHTML = '<option value="">-- strike --</option>';
    row.querySelector('[name="pos_price"]').value = '';

    if (!ticker) return;

    const cache = _chainCacheGet(ticker);
    if (!cache) {
        expirySelect.innerHTML = '<option value="">Loading...</option>';
        // Trigger preload and wait
        fetch('/api/preload_option_chain', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ticker })
        }).then(r => r.json()).then(data => {
            if (data.status === 'ok') {
                _chainCacheSet(ticker, data);
                document.dispatchEvent(new CustomEvent('chainLoaded', { detail: { ticker } }));
                populateExpiryDropdown(expirySelect, ticker);
            } else {
                expirySelect.innerHTML = '<option value="">No data</option>';
            }
        }).catch(() => {
            expirySelect.innerHTML = '<option value="">Error</option>';
        });
        return;
    }
    populateExpiryDropdown(expirySelect, ticker);
}

function onPositionTypeChange(selectEl) {
    // When type changes, refresh strike dropdown  if expiry is selected
    const row = selectEl.closest('tr');
    const expirySelect = row.querySelector('[name="pos_expiry"]');
    if (expirySelect.value) onPositionExpiryChange(expirySelect);
}

function populateExpiryDropdown(expirySelect, ticker) {
    const cache = _chainCacheGet(ticker);
    if (!cache) return;
    expirySelect.innerHTML = '<option value="">-- expiry --</option>';
    (cache.expiries || []).forEach(exp => {
        const opt = document.createElement('option');
        opt.value = exp;
        const dte = Math.max(0, Math.round((new Date(exp) - new Date()) / (1000 * 60 * 60 * 24)));
        opt.textContent = `${exp} (${dte}d)`;
        expirySelect.appendChild(opt);
    });
}

function onPositionExpiryChange(selectEl) {
    const row = selectEl.closest('tr');
    const ticker = row.querySelector('[name="pos_ticker"]').value;
    const type = row.querySelector('[name="pos_type"]').value;
    const expiry = selectEl.value;
    const strikeSelect = row.querySelector('[name="pos_strike"]');
    strikeSelect.innerHTML = '<option value="">-- strike --</option>';
    row.querySelector('[name="pos_price"]').value = '';

    if (!ticker || !expiry) return;
    const cacheEntry = _chainCacheGet(ticker);
    const chain = cacheEntry?.chain?.[expiry];
    if (!chain) return;

    const contracts = type === 'call' ? chain.calls : chain.puts;
    const spot = cacheEntry.spot;

    contracts.sort((a, b) => a.strike - b.strike).forEach(c => {
        const opt = document.createElement('option');
        opt.value = c.strike;
        const moneyLabel = getMoneyLabel(c.strike, spot, type);
        opt.textContent = `${c.strike} | IV:${c.iv_pct}% | Mid:${c.mid} ${moneyLabel}`;
        opt.dataset.iv = c.iv;
        opt.dataset.mid = c.mid;
        opt.dataset.dte = c.dte;
        strikeSelect.appendChild(opt);
    });
}

function onPositionStrikeChange(selectEl) {
    const row = selectEl.closest('tr');
    const selectedOpt = selectEl.options[selectEl.selectedIndex];
    const priceInput = row.querySelector('[name="pos_price"]');
    if (selectedOpt && selectedOpt.dataset.mid) {
        priceInput.value = selectedOpt.dataset.mid;
    }
}

function getMoneyLabel(strike, spot, type) {
    const ratio = strike / spot;
    if (type === 'call') {
        if (ratio < 0.99) return '(ITM)';
        if (ratio > 1.01) return '(OTM)';
        return '(ATM)';
    } else {
        if (ratio > 1.01) return '(ITM)';
        if (ratio < 0.99) return '(OTM)';
        return '(ATM)';
    }
}

function getPositionsData() {
    const rows = document.querySelectorAll('#positions-table tbody tr');
    const positions = [];
    rows.forEach(row => {
        const ticker = row.querySelector('[name="pos_ticker"]')?.value;
        const type = row.querySelector('[name="pos_type"]')?.value;
        const expiry = row.querySelector('[name="pos_expiry"]')?.value;
        const strike = parseFloat(row.querySelector('[name="pos_strike"]')?.value);
        const side = row.querySelector('[name="pos_side"]')?.value;
        const price = parseFloat(row.querySelector('[name="pos_price"]')?.value);
        const qty = parseInt(row.querySelector('[name="pos_qty"]')?.value);

        if (!ticker || !expiry || !strike || !price || !qty) return;

        const optionType = `${side === 'long' ? 'L' : 'S'}${type === 'call' ? 'C' : 'P'}`;
        const strikeOpt = row.querySelector('[name="pos_strike"]').options[row.querySelector('[name="pos_strike"]').selectedIndex];
        const iv = parseFloat(strikeOpt?.dataset?.iv || 0);
        const dte = parseInt(strikeOpt?.dataset?.dte || 30);

        positions.push({ ticker, option_type: optionType, expiry, strike, side, price, quantity: qty, iv, dte });
    });
    return positions;
}


/* ============================================================
   Portfolio Analysis
   ============================================================ */

let _portfolioAbort = null;
async function runPortfolioAnalysis() {
    const positions = getPositionsData();
    if (positions.length === 0) {
        alert('请至少添加一个有效持仓');
        return;
    }

    const btn = document.getElementById('portfolio-analysis-btn');
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 分析中...';
    btn.disabled = true;

    if (_portfolioAbort) _portfolioAbort.abort();
    _portfolioAbort = new AbortController();

    try {
        const resp = await fetch('/api/portfolio_analysis', {
            signal: _portfolioAbort.signal,
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                positions,
                account_size: parseFloat(document.getElementById('account_size')?.value) || null,
                max_risk_pct: parseFloat(document.getElementById('max_risk_pct')?.value) || 2.0
            })
        });
        const data = await resp.json();

        if (data.status === 'ok') {
            renderPortfolioResults(data);
            const panel = document.getElementById('portfolio-results-panel');
            if (panel) { panel.style.display = 'block'; panel.scrollIntoView({ behavior: 'smooth' }); }
        } else {
            alert('分析失败：' + (data.message || 'Unknown error'));
        }
    } catch (e) {
        if (e.name === 'AbortError') return;
        alert('Network error: ' + e.message);
    } finally {
        btn.innerHTML = '<i class="fas fa-chart-pie"></i> 组合分析';
        btn.disabled = false;
    }
}

function renderPortfolioResults(data) {
    // Greeks summary
    const gs = data.greeks_summary || {};
    const gsCard = document.getElementById('greeks-summary-card');
    if (gsCard) {
        gsCard.innerHTML = `
            <div class="greeks-grid">
                <div class="greek-item"><span class="greek-label">Delta</span><span class="greek-value">${(gs.delta || 0).toFixed(3)}</span></div>
                <div class="greek-item"><span class="greek-label">Gamma</span><span class="greek-value">${(gs.gamma || 0).toFixed(5)}</span></div>
                <div class="greek-item"><span class="greek-label">Theta/d</span><span class="greek-value">${(gs.theta || 0).toFixed(2)}</span></div>
                <div class="greek-item"><span class="greek-label">Vega/1%</span><span class="greek-value">${(gs.vega || 0).toFixed(2)}</span></div>
                <div class="greek-item"><span class="greek-label">Net Premium</span><span class="greek-value">${(gs.net_premium || 0).toFixed(2)}</span></div>
                <div class="greek-item"><span class="greek-label">VaR (1d, 95%)</span><span class="greek-value">$${(data.portfolio_var_1d || 0).toFixed(2)}</span></div>
            </div>`;
    }

    // PnL chart
    if (data.pnl_chart) {
        const img = document.getElementById('pnl-chart-img');
        if (img) { img.src = 'data:image/png;base64,' + data.pnl_chart; img.style.display = 'block'; }
    }

    // Theta decay chart
    if (data.theta_decay_chart) {
        const img = document.getElementById('theta-decay-chart-img');
        if (img) { img.src = 'data:image/png;base64,' + data.theta_decay_chart; img.style.display = 'block'; }
    }

    // Breakevens
    if (data.breakevens && data.breakevens.length > 0) {
        const card = document.getElementById('breakeven-card');
        const vals = document.getElementById('breakeven-values');
        if (card && vals) {
            card.style.display = 'block';
            vals.innerHTML = data.breakevens.map(b => `<span class="meta-chip">${b}</span>`).join(' ');
        }
    }

    // VaR
    const varCard = document.getElementById('var-card');
    const varVals = document.getElementById('var-values');
    if (varCard && varVals && data.portfolio_var_1d) {
        varCard.style.display = 'block';
        varVals.innerHTML = `<span class="meta-chip">1-Day VaR (95%): <strong>$${data.portfolio_var_1d.toFixed(2)}</strong></span>`;
    }
}


/* ============================================================
   Option chain preload after validation
   ============================================================ */

async function preloadOptionChains(validTickers) {
    window._chainCache = window._chainCache || {};
    for (const ticker of validTickers) {
        if (_chainCacheGet(ticker)) continue;
        fetch('/api/preload_option_chain', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ticker })
        })
            .then(r => r.json())
            .then(data => {
                if (data.status === 'ok') {
                    _chainCacheSet(ticker, data);
                    document.dispatchEvent(new CustomEvent('chainLoaded', { detail: { ticker } }));
                }
            })
            .catch(err => console.warn('Chain preload failed for ' + ticker + ':', err));
    }
}
