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
 *   - the fill-side switch (buy at ask / sell at bid) is mutually exclusive
 *     and DOES recompute: it changes the price basis of every cell
 *   - a DTE header cell is built from the SAME two halves as a data cell
 *     (.pm-head-pair mirrors .pm-cell), and the header <th> / data <td> are
 *     both padding-free — that is what keeps the call / put sub-columns
 *     pixel-aligned with the numbers they label (the x axis)
 *   - the two sticky left rails share one measured width: after every render
 *     JS writes the real strike-column width into --pm-sigma-left, so the
 *     sigma rail can never drift when a long strike stretches column one
 *   - hovering a column only highlights it (the y axis); it never rewrites
 *     values. Clicking a column promotes it to the sigma reference.
 */
(function () {
    'use strict';

    const PANEL = 'premium_matrix';
    const DEBOUNCE_MS = 150;
    // Must stay in sync with the (max-width: 720px) block in styles.css, which
    // drops the sigma rail on narrow screens.
    const NARROW_MQ = '(max-width: 720px)';

    let data = null;          // last engine payload
    let calendar = null;      // last expiry calendar (the matrix columns)
    let refCol = 0;           // column index whose sigma the row headers show
    let hoverCol = null;      // column index under the cursor / keyboard focus
    let narrow = false;       // sigma rail hidden by the narrow-screen media query
    let wired = false;
    let debounceTimer = null;
    let rafPending = false;
    let resizeRaf = false;
    let railObserver = null;   // keeps --pm-sigma-left in step with column one

    const el = (id) => document.getElementById(id);

    const TOGGLES = ['price', 'premium', 'call', 'put'];
    // Fill side is a two-way switch (buy at ask / sell at bid), not a select:
    // it reprices the whole grid, so it lives in the panel toolbar.
    const SIDES = ['buy', 'sell'];
    // Mirrors the min / max on #pm-spread. There is no percentage floor: the
    // engine floors the spread's DOLLAR effect at one cent (MIN_SPREAD_ABS),
    // so even the 1% minimum still leaves the two fill sides one tick apart on
    // cheap wing premiums where 1% of the mid is below a penny.
    const SPREAD_MIN_PCT = 1;
    const SPREAD_MAX_PCT = 100;

    function isNarrow() {
        return !!(window.matchMedia && window.matchMedia(NARROW_MQ).matches);
    }

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
    // The input is clamped on read, so a blank or oversized spread can never
    // reach the engine. The minimum is 1% (not zero): below that the engine
    // floors the spread's dollar effect at one cent, so both fill sides still
    // differ by a tick.
    function clampSpread(raw) {
        const v = parseFloat(raw);
        if (!isFinite(v)) return SPREAD_MIN_PCT;
        return Math.min(Math.max(v, SPREAD_MIN_PCT), SPREAD_MAX_PCT);
    }

    function readSide() {
        const pressed = document.querySelector('[data-pm-side][aria-pressed="true"]');
        return pressed && pressed.getAttribute('data-pm-side') === 'sell' ? 'sell' : 'buy';
    }

    function readInputs() {
        return {
            spot: parseFloat((el('pm-price') || {}).value),
            ivPct: parseFloat((el('pm-iv') || {}).value),
            rPct: parseFloat((el('pm-rate') || {}).value),
            spreadPct: clampSpread((el('pm-spread') || {}).value),
            perspective: readSide(),
        };
    }

    // Typing "0" (or clearing the field) is normalised on blur, not per
    // keystroke — rewriting the value mid-typing would fight the user.
    function normaliseSpreadInput() {
        const input = el('pm-spread');
        if (!input) return;
        input.addEventListener('change', function () {
            if (debounceTimer) { clearTimeout(debounceTimer); debounceTimer = null; }
            const text = String(clampSpread(input.value));
            if (input.value !== text) input.value = text;
            runWithCalendar();
        });
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
    function compute(expirations) {
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
        const payload = {
            spot: p.spot,
            ivPct: p.ivPct,
            rPct: p.rPct,
            spreadPct: p.spreadPct,
            perspective: p.perspective,
        };
        if (expirations) payload.expirations = expirations;
        const res = engine.buildPremiumMatrix(payload);
        const ms = ((window.performance && performance.now) ? performance.now() : Date.now()) - started;
        console.info(`[premium_matrix] ${res.rows.length}×${res.columns.length} grid built in ${ms.toFixed(2)}ms`);
        return res;
    }

    // Fetch the standard + daily expiry calendar from the API and use it as the
    // matrix columns. Fails loudly so the panel shows an error banner.
    async function loadCalendar() {
        if (!window.api || typeof window.api.get !== 'function') {
            throw new Error('api unavailable');
        }
        const params = new URLSearchParams({ standard: '12', daily: '10' });
        const resp = await window.api.get('/api/expiry_calendar?' + params.toString(), { key: 'pm-calendar' });
        if (!resp || resp.status !== 'ok' || !Array.isArray(resp.expirations)) {
            throw new Error('invalid calendar response');
        }
        return resp.expirations;
    }

    function finishRun(res) {
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

    // A missing price is not an error — the user is still typing. Bail out
    // BEFORE the calendar fetch, so the panel drops straight to idle.
    function ensureSpot() {
        const p = readInputs();
        if (!isFinite(p.spot) || p.spot <= 0) {
            window.appState.panels.set(PANEL, 'idle', { message: '请输入标的价格。' });
            return false;
        }
        return true;
    }

    function run() {
        if (!ensureSpot()) return;
        window.appState.panels.set(PANEL, 'loading', { message: '正在计算溢价率矩阵…' });
        loadCalendarThenRun();
    }

    // Only the four inputs and the fill side change what a cell WORTH is; the
    // expiry calendar is the same set of columns every time. Recomputing from
    // the cached calendar keeps a side flip or a spread edit synchronous — no
    // request, no abort race, no loading flash.
    function runWithCalendar() {
        if (!ensureSpot()) return;
        if (!calendar) { run(); return; }
        try {
            finishRun(compute(calendar));
        } catch (err) {
            console.error('[premium_matrix] build failed:', err);
            window.appState.panels.set(PANEL, 'error', { message: chineseMessage(err) });
        }
    }

    async function loadCalendarThenRun() {
        try {
            const expirations = await loadCalendar();
            calendar = expirations;
            finishRun(compute(expirations));
        } catch (err) {
            console.error('[premium_matrix] calendar load failed:', err);
            window.appState.panels.set(PANEL, 'error', { message: chineseMessage(err) });
        }
    }

    function scheduleRun() {
        if (debounceTimer) clearTimeout(debounceTimer);
        debounceTimer = setTimeout(function () {
            debounceTimer = null;
            // Typing changes what a cell is WORTH, never which columns exist,
            // so recompute locally instead of refetching the calendar.
            runWithCalendar();
        }, DEBOUNCE_MS);
    }

    /* -- rendering ------------------------------------------------------- */
    // The flex lives on a <span> INSIDE the <td>, never on the <td> itself:
    // `display: flex` on a table cell removes it from the table's column
    // layout, which stacks every data column on top of the first one.
    function cellMarkup(cell, j) {
        return '<td class="pm-cell" data-col="' + j + '">'
            + '<span class="pm-pair">'
            + halfMarkup(Object.assign({ kind: 'call' }, cell.call))
            + halfMarkup(Object.assign({ kind: 'put' }, cell.put))
            + '</span>'
            + '</td>';
    }

    function halfMarkup(side) {
        return '<span class="pm-half pm-half--' + side.kind + '">'
            + '<span class="pm-val pm-val--price">' + fmt(side.fill) + '</span>'
            + '<span class="pm-val pm-val--rate">' + fmtPct(side.premium_rate) + '</span>'
            + '</span>';
    }

    // One <col> per column. CSS paints the hovered column through its <col>,
    // so highlighting a column costs a single class write instead of 41.
    // <col> maps to columns BY POSITION, so the narrow-screen rule that hides
    // the sigma rail has to drop its <col> too — otherwise every highlight
    // would land one column to the right.
    function buildColgroupHtml() {
        let out = '<colgroup><col class="pm-col-rail">';
        if (!narrow) out += '<col class="pm-col-rail">';
        data.columns.forEach(function (col, i) {
            out += '<col class="pm-col-dte" data-col="' + i + '">';
        });
        return out + '</colgroup>';
    }

    // The header mirrors the data cell exactly: a DTE caption centred over the
    // whole column, then a CALL / PUT pair laid out by the same flex rules as
    // .pm-cell, so each label sits over the half it describes.
    function buildHeadHtml() {
        let out = '<thead><tr>'
            + '<th scope="col" class="pm-head-strike">Strike</th>'
            + '<th scope="col" class="pm-head-sigma" id="pm-head-sigma">σ</th>';

        data.columns.forEach(function (col, i) {
            const datePart = col.date ? col.date.slice(5) : '';
            out += '<th scope="col" data-col="' + i + '" class="pm-head-dte"'
                + ' title="' + col.dte + ' 天后到期 · 1σ 波动 ' + fmtPct(col.sigma_pct, 2)
                + (col.date ? ' · ' + col.date + (col.cycle ? ' (' + col.cycle + ')' : '') : '')
                + '">'
                + '<span class="pm-head-main">' + col.dte + 'D</span>'
                + '<span class="pm-head-sub">±' + fmtPct(col.sigma_pct, 1) + '</span>'
                + '<span class="pm-head-date">' + datePart + '</span>'
                + '<span class="pm-head-pair">'
                + '<span class="pm-head-half pm-head-half--call">Call</span>'
                + '<span class="pm-head-half pm-head-half--put">Put</span>'
                + '</span>'
                + '</th>';
        });
        return out + '</tr></thead>';
    }

    function buildTableHtml() {
        const decimals = data.decimals;

        const body = ['<tbody>'];
        data.rows.forEach(function (row, i) {
            const atm = i === data.atm_index ? ' pm-row-atm' : '';
            const cells = row.cells.map(cellMarkup).join('');
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
            + 'by strike (rows) and days to expiration (columns). Each expiration column is '
            + 'split into a CALL half and a PUT half.</caption>'
            + buildColgroupHtml()
            + buildHeadHtml()
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
            hoverCol = null;
            host.innerHTML = buildTableHtml();
            applyToggles();
            renderSigmaHeader();
            syncRailOffset();
            observeRail();
        });
    }

    // The sigma rail is sticky at `left: var(--pm-sigma-left)`. auto table
    // layout only treats `width` as a suggestion, so a strike like "9876543"
    // can stretch column one past the hard-coded 4.4rem and slide the rail out
    // of register with its own header. Measuring the real width closes that gap.
    function syncRailOffset() {
        const table = el('pm-matrix');
        if (!table) return;
        const strike = table.querySelector('tbody th[scope="row"]');
        if (!strike) return;
        const width = strike.getBoundingClientRect().width || strike.offsetWidth || 0;
        if (width > 0) table.style.setProperty('--pm-sigma-left', Math.round(width) + 'px');
    }

    // The panel is `display: none` until the panel state flips to 'loaded', so
    // the first render measures a zero-width column. Watching the cell means
    // the offset lands as soon as it is laid out — and re-lands on font swap,
    // zoom, or a strike long enough to widen column one.
    function observeRail() {
        const table = el('pm-matrix');
        if (!table) return;
        if (railObserver) { railObserver.disconnect(); railObserver = null; }
        if (typeof ResizeObserver === 'undefined') return;
        const strike = table.querySelector('tbody th[scope="row"]');
        if (!strike) return;
        railObserver = new ResizeObserver(syncRailOffset);
        railObserver.observe(strike);
    }

    // Crosshair: highlight exactly one column (the x axis). Rows are already
    // highlighted by :hover in CSS, so together they pin down the cell.
    function setHoverCol(idx) {
        const table = el('pm-matrix');
        if (!table) return;
        const next = (idx === null || !isFinite(idx)) ? null : Number(idx);
        if (next === hoverCol) return;
        clearHoverCol();
        hoverCol = next;
        if (hoverCol === null) return;
        const col = table.querySelector('col.pm-col-dte[data-col="' + hoverCol + '"]');
        const head = table.querySelector('th.pm-head-dte[data-col="' + hoverCol + '"]');
        if (col) col.classList.add('is-hover');
        if (head) head.classList.add('is-hover');
    }

    function clearHoverCol() {
        const table = el('pm-matrix');
        if (!table || hoverCol === null) return;
        const col = table.querySelector('col.pm-col-dte[data-col="' + hoverCol + '"]');
        const head = table.querySelector('th.pm-head-dte[data-col="' + hoverCol + '"]');
        if (col) col.classList.remove('is-hover');
        if (head) head.classList.remove('is-hover');
        hoverCol = null;
    }

    // Promote a column to the sigma reference. Explicit only (click or the
    // select) — hovering must never rewrite numbers the user is reading.
    function setRefCol(idx, syncSelect) {
        if (!data) return;
        const next = Math.min(Math.max(Number(idx) || 0, 0), data.columns.length - 1);
        if (next === refCol) return;
        refCol = next;
        // The hero band stays pinned to the 30D reference column, so changing
        // the row-header sigma reference must NOT re-render it.
        renderSigmaColumn();
        if (syncSelect) {
            const sel = el('pm-ref-dte');
            if (sel) sel.value = String(next);
        }
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

    // The hero band (ATM premium rate, 1σ move, ATM call, ATM put) is computed
    // from the matrix column CLOSEST TO 30D — `ref_column_index`, which the
    // engine sets to the column with the smallest |dte − 30|. Each label shows
    // the actual days used; it must never move when the user clicks a column to
    // change the row-header sigma reference.
    function renderHero() {
        if (!data) return;
        const row = data.rows[data.atm_index];
        const refIdx = data.ref_column_index;
        const cell = row.cells[refIdx];
        const col = data.columns[refIdx];
        const dteTag = col.dte + 'D';

        setText('pm-hero-label', 'ATM premium rate · ' + dteTag);
        setText('pm-kpi-sigma-label', '1σ move · ' + dteTag);
        setText('pm-kpi-call-label', 'ATM call · ' + dteTag);
        setText('pm-kpi-put-label', 'ATM put · ' + dteTag);

        const heroValue = el('pm-hero-value');
        if (heroValue) heroValue.textContent = fmtPct(cell.call.premium_rate);
        const heroSub = el('pm-hero-sub');
        if (heroSub) {
            heroSub.textContent = 'ATM ' + row.strike.toFixed(data.decimals)
                + ' · put ' + fmtPct(cell.put.premium_rate);
        }

        setText('pm-kpi-sigma', fmt(col.sigma_move));
        setText('pm-kpi-sigma-sub', fmtPct(col.sigma_pct, 2) + ' of ' + fmt(data.spot));
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

    /* -- fill side ------------------------------------------------------- */
    // Buy / sell are mutually exclusive — exactly one is pressed, and flipping
    // it reprices the grid (the engine memoises per side, so flipping back is
    // free). Unlike the four visibility toggles this one is NOT CSS-only.
    function wireSide() {
        SIDES.forEach(function (name) {
            const btn = document.querySelector('[data-pm-side="' + name + '"]');
            if (!btn) return;
            btn.addEventListener('click', function () {
                if (btn.getAttribute('aria-pressed') === 'true') return;
                SIDES.forEach(function (other) {
                    const node = document.querySelector('[data-pm-side="' + other + '"]');
                    if (!node) return;
                    const on = other === name;
                    node.setAttribute('aria-pressed', on ? 'true' : 'false');
                    node.classList.toggle('active', on);
                });
                runWithCalendar();
            });
        });
    }

    /* -- events ---------------------------------------------------------- */
    function wire() {
        if (wired) return;
        wired = true;
        narrow = isNarrow();

        ['pm-price', 'pm-iv', 'pm-rate', 'pm-spread'].forEach(function (id) {
            const node = el(id);
            if (node) node.addEventListener('input', scheduleRun);
        });
        normaliseSpreadInput();
        wireSide();

        const runBtn = document.querySelector('[data-action="pm-run"]');
        if (runBtn) runBtn.addEventListener('click', run);

        const refSel = el('pm-ref-dte');
        if (refSel) {
            refSel.addEventListener('change', function () {
                setRefCol(Number(refSel.value) || 0, false);
            });
        }

        // Crosshair only: hover / focus highlights a column, and a click is
        // what promotes it to the sigma reference. Values never move on hover.
        const host = el('pm-matrix-body');
        if (host) {
            host.addEventListener('mouseover', function (ev) {
                const target = ev.target.closest ? ev.target.closest('[data-col]') : null;
                if (!target) return;
                setHoverCol(Number(target.dataset.col));
            });
            host.addEventListener('mouseleave', function () {
                setHoverCol(null);
            });
            host.addEventListener('focusin', function (ev) {
                const target = ev.target.closest ? ev.target.closest('[data-col]') : null;
                if (!target) return;
                setHoverCol(Number(target.dataset.col) || 0);
            });
            host.addEventListener('click', function (ev) {
                const target = ev.target.closest ? ev.target.closest('[data-col]') : null;
                if (!target) return;
                setRefCol(Number(target.dataset.col) || 0, true);
            });
        }

        // Crossing the 720px breakpoint adds or removes a column, which
        // changes the <col> map, so the table has to be rebuilt. (Width
        // changes inside a breakpoint are already covered by railObserver.)
        window.addEventListener('resize', function () {
            if (resizeRaf) return;
            resizeRaf = true;
            requestAnimationFrame(function () {
                resizeRaf = false;
                if (isNarrow() === narrow) return;
                narrow = isNarrow();
                hoverCol = null;
                renderTable();
            });
        });

        wireToggles();
    }

    /* -- entry point ----------------------------------------------------- */
    window.loadPremiumMatrix = function loadPremiumMatrix() {
        wire();
        if (!data) run();
    };

    window.premiumMatrixDebug = function premiumMatrixDebug() {
        return { data, refCol, hoverCol, side: readSide(), spreadPct: clampSpread((el('pm-spread') || {}).value) };
    };
})();
