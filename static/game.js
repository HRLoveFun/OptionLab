// ── Put Option Decision Game ─────────────────────────────────────

let _gameAbort = null;

(function initGameSliders() {
    const dirSlider = document.getElementById('game-dir-conv');
    const dirVal = document.getElementById('game-dir-conv-val');
    const volSlider = document.getElementById('game-vol-conv');
    const volVal = document.getElementById('game-vol-conv-val');
    if (dirSlider && dirVal) {
        dirSlider.addEventListener('input', function () {
            dirVal.textContent = (parseInt(this.value) / 100).toFixed(2);
        });
    }
    if (volSlider && volVal) {
        volSlider.addEventListener('input', function () {
            volVal.textContent = (parseInt(this.value) / 100).toFixed(2);
        });
    }
})();

async function runGameAnalysis() {
    const tickerInput = document.getElementById('ticker');
    const ticker = (tickerInput ? tickerInput.value : '').trim().toUpperCase();
    if (!ticker) {
        _gameShowError('Please enter a ticker in the Parameter tab first.');
        return;
    }

    const budget = parseFloat(document.getElementById('game-budget').value) || 5000;
    const targetMovePct = (parseFloat(document.getElementById('game-target-move').value) || -8) / 100;
    const horizon = parseInt(document.getElementById('game-horizon').value) || 21;
    const dirConv = parseInt(document.getElementById('game-dir-conv').value) / 100;
    const volConv = parseInt(document.getElementById('game-vol-conv').value) / 100;
    const volTiming = document.getElementById('game-vol-timing').value;

    const btn = document.getElementById('game-run-btn');
    const statusEl = document.getElementById('game-status');
    const emptyEl = document.getElementById('game-empty');
    const resultsEl = document.getElementById('game-results');
    const marketEl = document.getElementById('game-market-ctx');
    const heuristicsEl = document.getElementById('game-heuristics');

    if (btn) { btn.disabled = true; btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Running...'; }
    if (statusEl) { statusEl.style.display = 'none'; }
    if (emptyEl) { emptyEl.style.display = 'none'; }
    if (resultsEl) { resultsEl.style.display = 'none'; }
    if (marketEl) { marketEl.style.display = 'none'; }
    if (heuristicsEl) { heuristicsEl.style.display = 'none'; }

    if (_gameAbort) _gameAbort.abort();
    _gameAbort = new AbortController();

    try {
        const resp = await fetch('/api/game', {
            signal: _gameAbort.signal,
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                ticker: ticker,
                budget: budget,
                target_move_pct: targetMovePct,
                time_horizon_days: horizon,
                directional_conviction: dirConv,
                vol_conviction: volConv,
                vol_timing: volTiming,
            })
        });
        const data = await resp.json();

        if (data.status !== 'ok') {
            _gameShowError(data.message || 'Unknown error');
            return;
        }

        _gameRenderMarketCtx(data);
        _gameRenderHeuristics(data.heuristics || []);
        _gameRenderResults(data);

    } catch (e) {
        if (e.name === 'AbortError') return;
        _gameShowError('Network error: ' + e.message);
    } finally {
        if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fas fa-play"></i> Run'; }
    }
}

function _gameShowError(msg) {
    const statusEl = document.getElementById('game-status');
    const emptyEl = document.getElementById('game-empty');
    if (statusEl) {
        statusEl.style.display = 'block';
        statusEl.innerHTML = '<i class="fas fa-exclamation-circle"></i> ' + escapeHtml(msg);
    }
    if (emptyEl) { emptyEl.style.display = 'none'; }
}

function _gameRenderMarketCtx(data) {
    const el = document.getElementById('game-market-ctx');
    const tbody = document.getElementById('game-market-tbody');
    if (!el || !tbody) return;

    const rows = [
        ['Spot Price', '$' + (data.spot_price || 'N/A')],
        ['IV Rank', data.iv_rank != null ? data.iv_rank + '%' : 'N/A'],
        ['IV Percentile', data.iv_pct != null ? data.iv_pct + '%' : 'N/A'],
        ['DTE Window', data.dte_window ? data.dte_window.min + ' – ' + data.dte_window.max + ' days' : 'N/A'],
        ['Candidates Total', data.candidates_total],
        ['Enriched', data.candidates_enriched],
        ['Passed Filters', data.candidates_passed],
    ];

    tbody.innerHTML = rows.map(function (r) {
        return '<tr><td style="font-weight:600;">' + r[0] + '</td><td>' + r[1] + '</td></tr>';
    }).join('');
    el.style.display = 'block';
}

function _gameRenderHeuristics(notes) {
    const el = document.getElementById('game-heuristics');
    const list = document.getElementById('game-heuristics-list');
    if (!el || !list) return;
    if (!notes.length) { el.style.display = 'none'; return; }

    list.innerHTML = notes.map(function (n) {
        return '<li style="margin-bottom:0.4rem;">' + escapeHtml(n) + '</li>';
    }).join('');
    el.style.display = 'block';
}

function _gameRenderResults(data) {
    const el = document.getElementById('game-results');
    const tbody = document.getElementById('game-results-tbody');
    const info = document.getElementById('game-filter-info');
    const emptyEl = document.getElementById('game-empty');
    if (!el || !tbody) return;

    const ranked = data.ranked || [];
    if (info) {
        info.textContent = '(' + data.candidates_passed + ' of '
            + data.candidates_total + ' passed filters)';
    }

    if (ranked.length === 0) {
        el.style.display = 'none';
        if (emptyEl) {
            emptyEl.style.display = 'block';
            emptyEl.innerHTML = '<i class="fas fa-crosshairs empty-icon"></i>'
                + '<p>No candidates passed all filters. Consider relaxing parameters.</p>';
        }
        return;
    }

    tbody.innerHTML = ranked.map(function (c, i) {
        var d = c.derived || {};
        var evClass = c.ev >= 0 ? 'color:var(--green,#22c55e);' : 'color:var(--red,#ef4444);';
        return '<tr>'
            + '<td>' + (i + 1) + '</td>'
            + '<td>' + c.strike + '</td>'
            + '<td>' + c.dte + '</td>'
            + '<td>' + c.delta + '</td>'
            + '<td>' + c.iv + '</td>'
            + '<td>$' + c.mid_price + '</td>'
            + '<td>' + d.contracts_n + '</td>'
            + '<td>' + d.vega_theta_ratio + '</td>'
            + '<td>' + d.odds_ratio + 'x</td>'
            + '<td>' + (d.implied_win_rate * 100).toFixed(1) + '%</td>'
            + '<td style="' + evClass + 'font-weight:600;">$' + c.ev + '</td>'
            + '<td style="' + evClass + '">' + c.ev_ratio + '</td>'
            + '</tr>';
    }).join('');

    el.style.display = 'block';
}
