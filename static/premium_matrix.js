/* Premium matrix tab — strike × DTE grid of option prices and premium rates.
 *
 * DOM layer only: reads the four inputs, asks the pure engine
 * (static/sim/premium_matrix.js, exposed as window.PremiumMatrix) for the grid,
 * and renders one <table>. No math lives here and no network is touched —
 * the panel is a hypothetical-input calculator.
 *
 * Rendering contract:
 *   - the table is built as a single HTML string and swapped in one assignment
 *   - the four visibility toggles only write data-show-* attributes on the
 *     table; CSS hides the matching spans, so toggling never recomputes or
 *     re-renders
 *   - the row-header sigma column is the only thing that changes when the
 *     reference expiry changes (hover, focus or the select) — 41 text updates
 */
(function () {
    'use strict';

    const PANEL = 'premium_matrix';
    const DEBOUNCE_MS = 150;

    let data = null;          // last engine payload
    let refCol = 0;           // column index whose sigma the row headers show
    let wired = false;
    let debounceTimer = null;
    let rafPending = false;

    const el = (id) => document.getElementById(id);

    const TOGGLES = ['price', 'premium', 'call', 'put'];

    function fmt(v, digits) {
        if (v === null || v === undefined || !isFinite(v)) return '—';
        return Number(v).toLocaleString('en-US', {
            minimumFractionDigits: digits === undefined ? 2 : digits,
            maximumFractionDigits: digits === undefined ? 2 : digits,
        });
    }

    function fmtPct(v, digits) {
        if (v === null || v === undefined || !isFinite(v)) return '—';
        return (v * 100).toFixed(digits === undefined ? 2 : digits) + '%';
    }

    function fmtSigma(v) {
        if (v === null || v === undefined || !isFinite(v)) return '—';
        if (Math.abs(v) > 99.9) return (v > 0 ? '>' : '<') + '99.9σ';
        return (v > 0 ? '+' : '') + v.toFixed(2) + 'σ';
    }

    /* -- inputs --------------------------------------------------------- */
    function readInputs() {
        return {
            spot: parseFloat((el('pm-price') || {}).value),
            ivPct: parseFloat((el('pm-iv') || {}).value),
            rPct: parseFloat((el('pm-rate') || {}).value),
            spreadPct: parseFloat((el('pm-spread') || {}).value) || 0,
            perspective: (el('pm-perspective') || {}).value === 'sell' ? 'sell' : 'buy',
        };
    }

    function chineseMessage(err) {
        const raw = (err && err.message) || String(err);
        if (/spot/i.test(raw)) return '标的价格必须为正数。';
        if (/ivPct/i.test(raw)) return '隐含波动率需在 0.1% ~ 500% 之间。';
        if (/rPct/i.test(raw)) return '无风险利率需在 -5% ~ 50% 之间。';
        if (/DTE/i.test(raw)) return '至少需要 1 ~ 3650 天之间的一个到期期限。';
        if (/ladder|widen/i.test(raw)) return '当前价格下行权价过密，请提高标的价格。';
        return '溢价率矩阵计算失败：' + raw;
    }

    /* -- run ------------------------------------------------------------ */
    function compute() {
        const engine = window.PremiumMatrix;
        if (!engine || typeof engine.buildPremiumMatrix !== 'function') {
            throw new Error('engine unavailable');
        }
        const p = readInputs();
        if (!isFinite(p.spot) || p.spot <= 0) {
            window.appState.panels.set(PANEL, 'idle', { message: '请输入标的价格。' });
            return null;
        }
        const started = (window.performance && performance.now) ? performance.now() : Date.now();
        const res = engine.buildPremiumMatrix({
            spot: p.spot,
            ivPct: p.ivPct,
            rPct: p.rPct,
            spreadPct: p.spreadPct,
            perspective: p.perspective,
        });
        const ms = ((window.performance && performance.now) ? performance.now() : Date.now()) - started;
        console.info(`[premium_matrix] ${res.rows.length}×${res.columns.length} grid built in ${ms.toFixed(2)}ms`);
        return res;
    }

    function run() {
        window.appState.panels.set(PANEL, 'loading', { message: '正在计算溢价率矩阵…' });
        let res = null;
        try {
            res = compute();
        } catch (err) {
            console.error('[premium_matrix] build failed:', err);
            window.appState.panels.set(PANEL, 'error', { message: chineseMessage(err) });
            return;
        }
        if (!res) return;
        if (!res.rows || res.rows.length < 2) {
            window.appState.panels.set(PANEL, 'empty', { message: '当前输入下没有可用的行权价。' });
            return;
        }

        const first = !data;
        data = res;
        if (first) refCol = res.ref_column_index;
        refCol = Math.min(refCol, res.columns.length - 1);

        renderAll();
        window.appState.panels.set(PANEL, 'loaded', { data: res });
    }

    function scheduleRun() {
        if (debounceTimer) clearTimeout(debounceTimer);
        debounceTimer = setTimeout(function () {
            debounceTimer = null;
            run();
        }, DEBOUNCE_MS);
    }

    /* -- rendering ------------------------------------------------------- */
    function halfMarkup(side) {
        return '<span class="pm-half pm-half--' + side.kind + '">'
            + '<span class="pm-val pm-val--price">' + fmt(side.fill) + '</span>'
            + '<span class="pm-val pm-val--rate">' + fmtPct(side.premium_rate) + '</span>'
            + '</span>';
    }

    function buildTableHtml() {
        const decimals = data.decimals;
        const head = ['<thead><tr>'
            + '<th scope="col" class="pm-head-strike">Strike</th>'
            + '<th scope="col" class="pm-head-sigma" id="pm-head-sigma">σ</th>'];

        data.columns.forEach(function (col, i) {
            head.push('<th scope="col" data-col="' + i + '" class="pm-head-dte">'
                + '<span class="pm-col-main">' + col.dte + 'D</span>'
                + '<span class="pm-col-sub">1σ ' + fmt(col.sigma_move) + ' · ' + fmtPct(col.sigma_pct, 1) + '</span>'
                + '</th>');
        });
        head.push('</tr></thead>');

        const body = ['<tbody>'];
        data.rows.forEach(function (row, i) {
            const atm = i === data.atm_index ? ' pm-row-atm' : '';
            const cells = row.cells.map(function (cell, j) {
                return '<td class="pm-cell" data-col="' + j + '">'
                    + halfMarkup(Object.assign({ kind: 'call' }, cell.call))
                    + halfMarkup(Object.assign({ kind: 'put' }, cell.put))
                    + '</td>';
            }).join('');
            body.push('<tr class="pm-row' + atm + '" data-strike="' + row.strike + '">'
                + '<th scope="row" class="pm-strike">' + row.strike.toFixed(decimals) + '</th>'
                + '<td class="pm-sigma" data-row="' + i + '">' + fmtSigma(row.cells[refCol].sigma_mult) + '</td>'
                + cells
                + '</tr>');
        });
        body.push('</tbody>');

        return '<table class="pm-matrix" id="pm-matrix"'
            + ' data-show-price="1" data-show-premium="1" data-show-call="1" data-show-put="1">'
            + '<caption class="pm-caption">Premium matrix — call / put price and premium rate '
            + 'by strike (rows) and days to expiration (columns)</caption>'
            + head.join('')
            + body.join('')
            + '</table>';
    }

    function renderTable() {
        const host = el('pm-matrix-body');
        if (!host) return;
        if (rafPending) return;
        rafPending = true;
        requestAnimationFrame(function () {
            rafPending = false;
            host.innerHTML = buildTableHtml();
            applyToggles();
            renderSigmaHeader();
        });
    }

    function renderSigmaHeader() {
        const head = el('pm-head-sigma');
        if (head) head.textContent = 'σ @' + data.columns[refCol].dte + 'D';
    }

    // Only the 41 row-header cells change when the reference column moves.
    function renderSigmaColumn() {
        const host = el('pm-matrix');
        if (!host || !data) return;
        renderSigmaHeader();
        const cells = host.querySelectorAll('td.pm-sigma');
        for (let i = 0; i < cells.length; i++) {
            const rowIdx = Number(cells[i].dataset.row);
            const row = data.rows[rowIdx];
            cells[i].textContent = row ? fmtSigma(row.cells[refCol].sigma_mult) : '—';
        }
    }

    function renderRefSelect() {
        const sel = el('pm-ref-dte');
        if (!sel || !data) return;
        sel.innerHTML = data.columns.map(function (col, i) {
            return '<option value="' + i + '"' + (i === refCol ? ' selected' : '') + '>'
                + col.dte + 'D</option>';
        }).join('');
    }

    function renderHero() {
        if (!data) return;
        const row = data.rows[data.atm_index];
        const cell = row.cells[refCol];
        const col = data.columns[refCol];

        const heroValue = el('pm-hero-value');
        if (heroValue) heroValue.textContent = fmtPct(cell.call.premium_rate);
        const heroSub = el('pm-hero-sub');
        if (heroSub) {
            heroSub.textContent = 'ATM ' + row.strike.toFixed(data.decimals)
                + ' · ' + col.dte + 'D · put ' + fmtPct(cell.put.premium_rate);
        }

        setText('pm-kpi-sigma', fmt(col.sigma_move));
        setText('pm-kpi-sigma-sub', fmtPct(col.sigma_pct, 2) + ' of ' + fmt(data.spot) + ' · ' + col.dte + 'D');
        setText('pm-kpi-call', fmt(cell.call.fill));
        setText('pm-kpi-call-sub', 'mid ' + fmt(cell.call.mid) + ' · ' + fmtPct(cell.call.premium_rate));
        setText('pm-kpi-put', fmt(cell.put.fill));
        setText('pm-kpi-put-sub', 'mid ' + fmt(cell.put.mid) + ' · ' + fmtPct(cell.put.premium_rate));
        setText('pm-kpi-grid', data.rows.length + ' × ' + data.columns.length);
    }

    function setText(id, text) {
        const node = el(id);
        if (node) node.textContent = text;
    }

    function renderAll() {
        renderRefSelect();
        renderHero();
        renderTable();
    }

    /* -- toggles --------------------------------------------------------- */
    function toggleState() {
        const out = {};
        TOGGLES.forEach(function (name) {
            const btn = document.querySelector('[data-pm-toggle="' + name + '"]');
            out[name] = btn ? btn.getAttribute('aria-pressed') !== 'false' : true;
        });
        return out;
    }

    // Pure CSS visibility: one attribute per switch, no re-render.
    function applyToggles() {
        const table = el('pm-matrix');
        if (!table) return;
        const state = toggleState();
        TOGGLES.forEach(function (name) {
            table.setAttribute('data-show-' + name, state[name] ? '1' : '0');
        });
        const nothingVisible = (!state.price && !state.premium) || (!state.call && !state.put);
        const hint = el('pm-all-hidden');
        if (hint) hint.hidden = !nothingVisible;
    }

    function wireToggles() {
        TOGGLES.forEach(function (name) {
            const btn = document.querySelector('[data-pm-toggle="' + name + '"]');
            if (!btn) return;
            btn.addEventListener('click', function () {
                const on = btn.getAttribute('aria-pressed') === 'true';
                btn.setAttribute('aria-pressed', on ? 'false' : 'true');
                btn.classList.toggle('active', !on);
                applyToggles();
            });
        });
    }

    /* -- events ---------------------------------------------------------- */
    function wire() {
        if (wired) return;
        wired = true;

        ['pm-price', 'pm-iv', 'pm-rate', 'pm-spread'].forEach(function (id) {
            const node = el(id);
            if (node) node.addEventListener('input', scheduleRun);
        });
        const perspective = el('pm-perspective');
        if (perspective) perspective.addEventListener('change', run);

        const runBtn = document.querySelector('[data-action="pm-run"]');
        if (runBtn) runBtn.addEventListener('click', run);

        const refSel = el('pm-ref-dte');
        if (refSel) {
            refSel.addEventListener('change', function () {
                refCol = Number(refSel.value) || 0;
                renderSigmaColumn();
                renderHero();
            });
        }

        // Hover / keyboard focus previews a column's sigma multiples.
        const host = el('pm-matrix-body');
        if (host) {
            host.addEventListener('mouseover', function (ev) {
                const target = ev.target.closest ? ev.target.closest('[data-col]') : null;
                if (!target) return;
                const idx = Number(target.dataset.col);
                if (idx === refCol) return;
                refCol = idx;
                renderSigmaColumn();
            });
            host.addEventListener('focusin', function (ev) {
                const target = ev.target.closest ? ev.target.closest('[data-col]') : null;
                if (!target) return;
                refCol = Number(target.dataset.col) || 0;
                renderSigmaColumn();
            });
        }

        wireToggles();
    }

    /* -- entry point ----------------------------------------------------- */
    window.loadPremiumMatrix = function loadPremiumMatrix() {
        wire();
        if (!data) run();
    };

    window.premiumMatrixDebug = function premiumMatrixDebug() {
        return { data, refCol };
    };
})();
