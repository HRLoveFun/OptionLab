/* Position Simulator tab — value, Greeks and margin of a multi-leg position
 * over spot × time × IV.
 *
 * Consumes POST /api/optsim (services/options/optsim.py → core.optsim). Both
 * margin regimes come back in every response, so the margin switch only
 * re-renders; the market and exercise switches re-run, because ticker mode
 * reprices on the option chain and American legs are priced on a binomial
 * tree server-side.
 *
 * Market: "hypothetical" prices on the inputs typed here; "ticker" sends the
 * header ticker, and the server takes spot, listed expiries and strikes and
 * each leg's IV from its option chain, the rate from ^IRX, a dividend yield of
 * 0 and the margin class from the underlying's type. In ticker mode those
 * fields are read-only (showing what the server used); the request still
 * carries the typed values (the typed rate is the fallback when ^IRX is
 * missing), and the fields get them back when the switch returns to
 * Hypothetical. A ticker change re-runs a ticker-mode tab: at once when it is
 * on screen, else on the next visit (both ticker-change paths reset the
 * 'optsim' tab flag).
 *
 * The tab keeps its own state across reloads under one localStorage key: the
 * legs, the typed inputs and the market / exercise / margin switches. Storage
 * that throws (private windows, blocked site data) only means no persistence.
 */
(function () {
    'use strict';

    const PANEL = 'optsim';
    const MAX_LEGS = 6;
    const DEFAULT_PRESET = 'short_strangle';
    // Inputs ticker mode supplies itself; their typed values are kept aside meanwhile.
    const MARKET_FIELDS = [
        'optsim-spot', 'optsim-rate', 'optsim-div', 'optsim-product',
        'optsim-atm-iv', 'optsim-skew', 'optsim-curvature',
    ];
    // Inputs saved with the legs: the typed market fields plus the grid.
    const SAVED_FIELDS = MARKET_FIELDS.concat(['optsim-multiplier', 'optsim-spot-range', 'optsim-iv-shift']);
    const STORE_KEY = 'optsim.v1';
    // What a locked field shows until the server answers.
    const TICKER_PLACEHOLDER = {
        'optsim-spot': 'from chain',
        'optsim-atm-iv': 'from chain',
        'optsim-rate': 'from ^IRX',
        'optsim-skew': 'not used',
        'optsim-curvature': 'not used',
    };

    function leg(type, side, dte, by, value) {
        return { type, side, qty: 1, dte, by, value };
    }

    // Presets are rules, not contracts: the server resolves |Δ| against the smile.
    // A null strike means "at the money" (the Spot input, rounded; the nearest
    // listed strike in ticker mode).
    const PRESETS = {
        short_put: [leg('put', 'short', 45, 'delta', 0.30)],
        short_strangle: [leg('put', 'short', 45, 'delta', 0.16), leg('call', 'short', 45, 'delta', 0.16)],
        iron_condor: [
            leg('put', 'short', 45, 'delta', 0.16),
            leg('put', 'long', 45, 'delta', 0.08),
            leg('call', 'short', 45, 'delta', 0.16),
            leg('call', 'long', 45, 'delta', 0.08),
        ],
        put_spread: [leg('put', 'short', 45, 'delta', 0.30), leg('put', 'long', 45, 'delta', 0.16)],
        call_calendar: [leg('call', 'short', 30, 'strike', null), leg('call', 'long', 60, 'strike', null)],
        long_call: [leg('call', 'long', 45, 'delta', 0.50)],
    };

    const PRODUCT_LABEL = {
        index: 'broad index',
        etf: 'broad-index ETF',
        index_small: 'other broad index',
        equity: 'single stock',
    };

    const TYPE_LABEL = { index: 'index', etf: 'ETF', equity: 'stock', other: 'other instrument' };

    const GREEK_AXIS = {
        delta: 'Delta (shares)',
        gamma: 'Gamma (shares per $1)',
        theta: 'Theta ($ per day)',
        vega: 'Vega ($ per vol point)',
    };

    let legs = [];
    let marketMode = 'hypothetical';
    let typed = null;         // typed values of MARKET_FIELDS while ticker mode is on
    let lastTicker = null;    // the ticker the last ticker-mode run asked for
    let style = 'european';
    let margin = 'regt';
    let greek = 'delta';
    let data = null;          // last /api/optsim payload
    const charts = {};        // canvas id -> Chart
    let wired = false;

    const el = (id) => document.getElementById(id);

    /* -- formatting -------------------------------------------------------- */
    // Values that round to zero print without a sign: "$0", not "−$0" or "-0.0".
    function rounded(v, digits) {
        return Math.abs(v) < 0.5 * Math.pow(10, -digits) ? 0 : v;
    }

    function fmtNum(v, digits) {
        if (v === null || v === undefined || !Number.isFinite(v)) return '—';
        const d = digits === undefined ? 2 : digits;
        return rounded(v, d).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });
    }

    function fmtMoney(v, digits) {
        if (v === null || v === undefined || !Number.isFinite(v)) return '—';
        const d = digits === undefined ? 0 : digits;
        const x = rounded(v, d);
        const sign = x > 0 ? '+' : (x < 0 ? '−' : '');
        return sign + '$' + fmtNum(Math.abs(x), d);
    }

    function fmtUsd(v) {
        return Number.isFinite(v) ? '$' + fmtNum(v, 0) : '—';
    }

    function fmtPct(v, digits) {
        return Number.isFinite(v) ? (v * 100).toFixed(digits === undefined ? 1 : digits) + '%' : '—';
    }

    // Spot relative to the entry spot, signed: "+2.5%", "−5.0%", "0.0%".
    function fmtRel(spot) {
        if (!data || !Number.isFinite(spot) || !(data.spot > 0)) return '';
        const x = rounded((spot / data.spot - 1) * 100, 1);
        return (x > 0 ? '+' : (x < 0 ? '−' : '')) + Math.abs(x).toFixed(1) + '%';
    }

    // Small numbers need decimals, large ones do not: theta +$6.33 vs +$193.
    function adaptiveMoney(v) {
        return fmtMoney(v, Math.abs(v) >= 100 ? 0 : 2);
    }

    function cap(s) {
        return s ? s.charAt(0).toUpperCase() + s.slice(1) : '';
    }

    // Expiry dates come from the option chain: print only well-formed ones.
    function safeDate(s) {
        return typeof s === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(s) ? s : '—';
    }

    function fmtAsOf(iso) {
        const t = new Date(iso);
        if (Number.isNaN(t.getTime())) return '';
        return t.toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    }

    function setText(id, text) {
        const node = el(id);
        if (node) node.textContent = text;
    }

    function cssVar(name, fallback) {
        try {
            const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
            return v || fallback;
        } catch (_e) {
            return fallback;
        }
    }

    /* -- market mode -------------------------------------------------------- */
    // The first symbol of the header's ticker box — the one the Option Chain tab uses.
    function currentTicker() {
        if (typeof getValidTickers === 'function') return getValidTickers()[0] || '';
        const raw = ((el('ticker') || {}).value || '').toUpperCase();
        return raw.split(/[,\n]+/)[0].trim();
    }

    function tickerMode() {
        return marketMode === 'ticker';
    }

    // A ticker-mode result is stale once the header ticker moved on.
    function stale() {
        return tickerMode() && currentTicker() !== lastTicker;
    }

    function applyMarketFields() {
        const on = tickerMode();
        if (on && typed === null) typed = MARKET_FIELDS.map((id) => (el(id) || {}).value);
        MARKET_FIELDS.forEach((id, i) => {
            const node = el(id);
            if (!node) return;
            node.disabled = on;
            if (node.tagName === 'SELECT') {
                if (!on && typed) node.value = typed[i];
            } else if (on) {
                node.value = id === 'optsim-div' ? '0' : '';
                node.placeholder = TICKER_PLACEHOLDER[id] || '';
            } else {
                node.placeholder = '';
                if (typed) node.value = typed[i];
            }
        });
        if (!on) typed = null;
        const hint = el('optsim-market-hint');
        if (hint) hint.hidden = !on;
    }

    // The value a field stands for in the request: in ticker mode, what was typed before.
    function fieldValue(id) {
        const at = MARKET_FIELDS.indexOf(id);
        if (tickerMode() && typed && at >= 0) return typed[at];
        return (el(id) || {}).value;
    }

    // Show what the server used in the read-only fields (plain numbers: they are <input type=number>).
    function fillMarketFields(m) {
        const set = (id, v) => { const node = el(id); if (node && v !== null) node.value = v; };
        set('optsim-spot', Number.isFinite(m.spot) ? String(Math.round(m.spot * 100) / 100) : null);
        set('optsim-atm-iv', Number.isFinite(m.atm_iv) ? (m.atm_iv * 100).toFixed(1) : null);
        set('optsim-rate', Number.isFinite(m.rate) ? (m.rate * 100).toFixed(2) : null);
        set('optsim-div', '0');
        set('optsim-product', PRODUCT_LABEL[m.product] ? m.product : null);
    }

    function setMarket(next) {
        if (next === marketMode) return;
        marketMode = next;
        syncToggles('data-optsim-market', marketMode);
        applyMarketFields();
        // ATM legs show "ATM" in ticker mode and the rounded typed spot otherwise.
        if (!tickerMode()) legs.forEach((l) => { if (l.atm) l.value = atmStrike(); });
        renderLegEditor();
        run();
    }

    /* -- legs editor -------------------------------------------------------- */
    function spotInput() {
        const v = parseFloat((el('optsim-spot') || {}).value);
        return Number.isFinite(v) && v > 0 ? v : null;
    }

    function atmStrike() {
        const s = spotInput();
        return s === null ? null : Math.round(s);
    }

    // The value an "at the money" strike starts with: none in ticker mode (the server picks
    // the listed strike nearest spot), else the rounded Spot input.
    function atmValue() {
        return tickerMode() ? null : atmStrike();
    }

    function applyPreset(name) {
        const preset = PRESETS[name];
        if (!preset) return false;
        legs = preset.map((l) => ({ ...l, atm: l.value === null, value: l.value === null ? atmValue() : l.value }));
        renderLegEditor();
        return true;
    }

    function option(value, label, current) {
        return `<option value="${value}"${value === current ? ' selected' : ''}>${label}</option>`;
    }

    function legRow(l, i) {
        const n = i + 1;
        const valueLabel = l.by === 'delta' ? 'absolute delta' : 'strike';
        const shown = (tickerMode() && l.atm) || l.value === null ? '' : l.value;
        const placeholder = l.by === 'delta' ? '' : ' placeholder="ATM"';
        return `<tr data-leg="${i}">`
            + `<td><select data-field="type" aria-label="Leg ${n} type">`
            + option('put', 'Put', l.type) + option('call', 'Call', l.type) + '</select></td>'
            + `<td><select data-field="side" aria-label="Leg ${n} side">`
            + option('long', 'Long', l.side) + option('short', 'Short', l.side) + '</select></td>'
            + `<td><input type="number" data-field="qty" min="1" max="1000" step="1" value="${l.qty}"`
            + ` aria-label="Leg ${n} quantity"></td>`
            + `<td><input type="number" data-field="dte" min="1" max="730" step="1" value="${l.dte}"`
            + ` aria-label="Leg ${n} days to expiry"></td>`
            + `<td><select data-field="by" aria-label="Leg ${n} strike selection">`
            + option('delta', '|Δ|', l.by) + option('strike', 'Strike', l.by) + '</select></td>'
            + `<td><input type="number" data-field="value" min="0" step="any" value="${shown}"${placeholder}`
            + ` aria-label="Leg ${n} ${valueLabel}"></td>`
            + `<td><button type="button" class="btn-delete" data-action="optsim-remove-leg"`
            + ` aria-label="Remove leg ${n}"${legs.length <= 1 ? ' disabled' : ''}>Remove</button></td>`
            + '</tr>';
    }

    function renderLegEditor() {
        const body = el('optsim-legs-body');
        if (body) body.innerHTML = legs.map(legRow).join('');
        const add = document.querySelector('[data-action="optsim-add-leg"]');
        if (add) add.disabled = legs.length >= MAX_LEGS;
        save();
    }

    /* -- persistence ---------------------------------------------------------- */
    function save() {
        const state = {
            v: 1,
            legs: legs.map((l) => ({
                type: l.type, side: l.side, qty: l.qty, dte: l.dte, by: l.by, value: l.value, atm: Boolean(l.atm),
            })),
            inputs: Object.fromEntries(SAVED_FIELDS.map((id) => [id, fieldValue(id)])),
            market: marketMode,
            style,
            margin,
        };
        try {
            window.localStorage.setItem(STORE_KEY, JSON.stringify(state));
        } catch (_e) { /* no storage: the tab just forgets on reload */ }
    }

    function validLeg(l) {
        return Boolean(l) && ['put', 'call'].includes(l.type) && ['long', 'short'].includes(l.side)
            && Number.isInteger(l.qty) && l.qty >= 1 && Number.isInteger(l.dte) && l.dte >= 1
            && ['delta', 'strike'].includes(l.by) && (l.value === null || Number.isFinite(l.value));
    }

    function readSaved() {
        let state = null;
        try {
            state = JSON.parse(window.localStorage.getItem(STORE_KEY) || 'null');
        } catch (_e) {
            return null;
        }
        if (!state || state.v !== 1 || !Array.isArray(state.legs)) return null;
        const saved = state.legs.filter(validLeg).slice(0, MAX_LEGS);
        return saved.length ? { ...state, legs: saved } : null;
    }

    // Inputs go back first, so ticker mode can set them aside as the typed values.
    function restore() {
        const state = readSaved();
        if (!state) return false;
        const inputs = state.inputs || {};
        SAVED_FIELDS.forEach((id) => {
            const node = el(id);
            const v = inputs[id];
            if (!node || typeof v !== 'string') return;
            if (node.tagName === 'SELECT' && ![...node.options].some((o) => o.value === v)) return;
            node.value = v;
        });
        if (['european', 'american'].includes(state.style)) style = state.style;
        if (['regt', 'pm'].includes(state.margin)) margin = state.margin;
        syncToggles('data-optsim-style', style);
        syncToggles('data-optsim-margin', margin);
        if (state.market === 'ticker') {
            marketMode = 'ticker';
            syncToggles('data-optsim-market', marketMode);
            applyMarketFields();
        }
        legs = state.legs.map((l) => ({ ...l, atm: Boolean(l.atm) }));
        renderLegEditor();
        return true;
    }

    function onLegChange(ev) {
        const row = ev.target.closest('tr[data-leg]');
        const field = ev.target.getAttribute('data-field');
        if (!row || !field) return;
        const l = legs[parseInt(row.getAttribute('data-leg'), 10)];
        if (!l) return;
        const raw = ev.target.value;
        if (field === 'qty' || field === 'dte') {
            l[field] = parseInt(raw, 10);
        } else if (field === 'value') {
            const v = parseFloat(raw);
            l.value = Number.isFinite(v) ? v : null;
            // A cleared strike means "at the money" again; a typed one is the user's.
            l.atm = l.by === 'strike' && l.value === null;
        } else {
            l[field] = raw;
        }
        if (field === 'by') {
            // A delta is not a strike: switching the selector resets the value.
            l.atm = raw === 'strike';
            l.value = raw === 'delta' ? 0.16 : atmValue();
            renderLegEditor();
        }
        save();
    }

    function onLegClick(ev) {
        const btn = ev.target.closest('[data-action="optsim-remove-leg"]');
        if (!btn || legs.length <= 1) return;
        const row = btn.closest('tr[data-leg]');
        legs.splice(parseInt(row.getAttribute('data-leg'), 10), 1);
        renderLegEditor();
    }

    function addLeg() {
        if (legs.length >= MAX_LEGS) return;
        const last = legs[legs.length - 1];
        legs.push(last ? { ...last } : leg('put', 'short', 45, 'delta', 0.16));
        renderLegEditor();
    }

    /* -- request ------------------------------------------------------------ */
    function numberOf(id) {
        const v = parseFloat(fieldValue(id));
        return Number.isFinite(v) ? v : null;
    }

    function legStrike(l) {
        if (l.value === null || (tickerMode() && l.atm)) return 'atm';
        return l.value;
    }

    function buildPayload() {
        const body = {
            market: marketMode,
            spot: numberOf('optsim-spot'),
            rate: numberOf('optsim-rate'),
            div_yield: numberOf('optsim-div'),
            atm_iv: numberOf('optsim-atm-iv'),
            skew: numberOf('optsim-skew'),
            curvature: numberOf('optsim-curvature'),
            multiplier: numberOf('optsim-multiplier'),
            spot_range: numberOf('optsim-spot-range'),
            iv_shift: numberOf('optsim-iv-shift'),
            product: fieldValue('optsim-product') || 'etf',
            style,
            legs: legs.map((l) => ({
                type: l.type,
                side: l.side,
                qty: l.qty,
                dte: l.dte,
                ...(l.by === 'delta' ? { delta: l.value } : { strike: legStrike(l) }),
            })),
        };
        if (tickerMode()) body.ticker = currentTicker();
        return body;
    }

    async function run() {
        let message = style === 'american'
            ? 'Pricing American exercise on a binomial tree…'
            : 'Revaluing the position…';
        if (tickerMode()) {
            const ticker = currentTicker();
            lastTicker = ticker;
            if (!ticker) {
                if (window.api.abort) window.api.abort('optsim');
                window.appState.panels.set(PANEL, 'empty', {
                    message: 'Ticker mode needs a ticker: enter one in the header, or switch Market to Hypothetical.',
                });
                return;
            }
            message = `Loading the ${ticker} option chain…`;
        }
        save();
        window.appState.panels.set(PANEL, 'loading', { message });
        try {
            const res = await window.api.post('/api/optsim', { body: buildPayload(), key: 'optsim' });
            data = res;
            window.appState.panels.set(PANEL, 'loaded', { data: res });
            renderAll();
        } catch (err) {
            if (err && err.name === 'AbortError') return;
            window.appState.panels.set(PANEL, 'error', {
                message: (err && err.message) || 'Simulation failed.',
            });
        }
    }

    /* -- rendering ---------------------------------------------------------- */
    function listedMarket() {
        return Boolean(data && data.market && data.market.source === 'ticker');
    }

    function renderAll() {
        if (!data) return;
        if (listedMarket()) fillMarketFields(data.market);
        renderMarketNote();
        renderSummary();
        renderResolved();
        renderCharts();
        renderProfile();
    }

    function renderMarketNote() {
        const node = el('optsim-market-note');
        if (!node) return;
        if (!listedMarket()) {
            node.hidden = true;
            node.textContent = '';
            return;
        }
        const m = data.market;
        const parts = [`${m.ticker} option chain`, `spot ${fmtNum(m.spot, 2)}`];
        const asOf = m.as_of ? fmtAsOf(m.as_of) : '';
        if (asOf) parts.push(`as of ${asOf}`);
        parts.push(`ATM IV ${fmtPct(m.atm_iv, 1)} on ${safeDate(m.atm_expiry)}`);
        parts.push(`rate ${fmtPct(m.rate, 2)} (${m.rate_source === '^IRX' ? '^IRX' : 'typed: ^IRX unavailable'})`);
        parts.push('dividend 0%');
        const kind = TYPE_LABEL[m.instrument_type] || 'type unknown';
        parts.push(`${kind} → ${PRODUCT_LABEL[m.product] || m.product} margin`);
        node.textContent = parts.join(' · ');
        node.hidden = false;
    }

    function bindingMargin(row) {
        return margin === 'pm' ? row.pm : row.regt;
    }

    function renderSummary() {
        const credit = data.entry_value < 0;
        setText('optsim-hero-label', credit ? 'Net credit' : 'Net debit');
        setText('optsim-hero-value', fmtUsd(Math.abs(data.entry_value)));
        const n = data.legs.length;
        const sub = [`${n} leg${n > 1 ? 's' : ''}`, cap(data.style), PRODUCT_LABEL[data.product] || data.product];
        if (listedMarket()) sub.unshift(data.market.ticker);
        if (data.tree_steps) sub.push(`${data.tree_steps}-step tree`);
        setText('optsim-hero-sub', sub.join(' · '));

        const entry = data.profile[0];
        const bind = bindingMargin(entry);
        setText('optsim-kpi-margin-label', margin === 'pm' ? 'Portfolio margin' : 'Reg-T margin');
        setText('optsim-kpi-margin', fmtUsd(bind));
        const note = [margin === 'pm' ? 'worst loss over the PM range' : entry.regt_method.replace('_', ' ')];
        if (credit && bind > 0) note.push(`max-profit ROM ${fmtPct(-data.entry_value / bind)}`);
        setText('optsim-kpi-margin-sub', note.join(' · '));

        const lastDay = data.days[data.days.length - 1];
        setText('optsim-kpi-be-label', `Breakevens at day ${fmtNum(lastDay, 0)}`);
        setText('optsim-kpi-be', data.breakevens.length
            ? data.breakevens.map((b) => fmtNum(b, 2)).join(' / ')
            : 'none in range');
        setText('optsim-kpi-theta', adaptiveMoney(entry.theta));
        setText('optsim-kpi-vega', adaptiveMoney(entry.vega));
    }

    function legName(l) {
        return `${cap(l.side)} ${l.qty} ${cap(l.type)}`;
    }

    function renderResolved() {
        const host = el('optsim-resolved');
        if (!host) return;
        const listed = listedMarket();
        const head = ['Leg', 'Position'].concat(
            listed ? ['Expiry'] : [],
            ['DTE', 'Strike', 'IV', 'Premium / share'],
            listed ? ['Bid / ask'] : [],
            ['Delta / share'],
        );
        const rows = data.legs.map((l, i) => {
            const cells = [String(i + 1), legName(l)];
            if (listed) cells.push(safeDate(l.expiry));
            cells.push(String(l.dte), fmtNum(l.strike, 2), fmtPct(l.iv, 2) + (l.iv_source === 'curve' ? '*' : ''),
                fmtNum(l.premium, 2));
            if (listed) {
                cells.push(Number.isFinite(l.bid) && Number.isFinite(l.ask)
                    ? `${fmtNum(l.bid, 2)} / ${fmtNum(l.ask, 2)}` : 'no quote');
            }
            cells.push(fmtNum(l.delta, 3));
            return '<tr>' + cells.map((c) => `<td>${c}</td>`).join('') + '</tr>';
        }).join('');
        const note = listed && data.legs.some((l) => l.iv_source === 'curve')
            ? '<p class="optsim-table-note">* No two-sided quote: the IV is read off the expiry\'s IV curve.</p>'
            : '';
        host.innerHTML = '<table class="sim-detail" aria-label="Resolved legs at entry"><thead><tr>'
            + head.map((h) => `<th scope="col">${h}</th>`).join('')
            + `</tr></thead><tbody>${rows}</tbody></table>${note}`;
    }

    function renderProfile() {
        const host = el('optsim-profile');
        if (!host) return;
        const bindCls = (key) => (key === margin ? ' class="optsim-binding"' : '');
        const lastExpiry = Math.max(...data.legs.map((l) => l.dte));
        const rows = data.profile.map((r) => {
            const tone = r.pnl > 0 ? 'semantic-pos' : (r.pnl < 0 ? 'semantic-neg' : '');
            return '<tr>'
                + `<td>${fmtNum(r.day, 0)}${r.day === lastExpiry ? ' (expiry)' : ''}</td>`
                + `<td>${fmtMoney(r.value)}</td>`
                + `<td class="${tone}">${fmtMoney(r.pnl)}</td>`
                + `<td>${fmtNum(r.delta, 2)}</td><td>${fmtNum(r.gamma, 4)}</td>`
                + `<td>${fmtNum(r.theta, 1)}</td><td>${fmtNum(r.vega, 1)}</td>`
                + `<td${bindCls('regt')}>${fmtUsd(r.regt)}</td><td${bindCls('pm')}>${fmtUsd(r.pm)}</td>`
                + '</tr>';
        }).join('');
        host.innerHTML = '<table class="sim-detail" aria-label="Position over time at the entry spot"><thead><tr>'
            + '<th scope="col">Day</th><th scope="col">Value</th><th scope="col">P&amp;L</th>'
            + '<th scope="col">Delta</th><th scope="col">Gamma</th>'
            + '<th scope="col">Theta / day</th><th scope="col">Vega / vol pt</th>'
            + `<th scope="col"${bindCls('regt')}>Reg-T</th><th scope="col"${bindCls('pm')}>PM</th>`
            + `</tr></thead><tbody>${rows}</tbody></table>`;
    }

    /* -- charts --------------------------------------------------------------- */
    function palette() {
        const fallback = ['#86b6ef', '#5598e7', '#2a78d6', '#1c5cab', '#104281'];
        return {
            ramp: fallback.map((hex, i) => cssVar(`--optsim-day-${i + 1}`, hex)),
            iv: {
                down: cssVar('--optsim-iv-down', '#2a78d6'),
                flat: cssVar('--optsim-iv-flat', '#1f2937'),
                up: cssVar('--optsim-iv-up', '#d97706'),
            },
            ink: cssVar('--slate-700', '#334155'),
            muted: cssVar('--slate-500', '#64748b'),
            grid: cssVar('--slate-200', '#e2e8f0'),
            axis: cssVar('--slate-300', '#cbd5e1'),
        };
    }

    // Evenly spaced steps of the 5-step ramp for n ordered lines.
    function rampColors(ramp, n) {
        if (n <= 1) return [ramp[ramp.length - 1]];
        return Array.from({ length: n }, (_, i) => ramp[Math.round((i * (ramp.length - 1)) / (n - 1))]);
    }

    // The color a date wears in every chart: its place among the chart dates.
    function dayColor(pal, day) {
        const colors = rampColors(pal.ramp, data.chart_days.length);
        const at = data.chart_days.findIndex((d) => data.days[d] === day);
        return at >= 0 ? colors[at] : colors[colors.length - 1];
    }

    function dayLabel(day) {
        const lastExpiry = Math.max(...data.legs.map((l) => l.dte));
        if (day === 0) return 'Entry';
        return `Day ${fmtNum(day, 0)}${day === lastExpiry ? ' (expiry)' : ''}`;
    }

    // Spot marker, optional reference lines and a hover guide, drawn on the
    // canvas so none of them joins the legend or the index-mode tooltip.
    const guides = {
        id: 'optsimGuides',
        afterDatasetsDraw(chart, _args, opts) {
            const { ctx, chartArea } = chart;
            const x = chart.scales.x;
            const y = chart.scales.y;
            const stroke = (x0, y0, x1, y1, color, dash, width) => {
                ctx.save();
                ctx.strokeStyle = color;
                ctx.lineWidth = width || 1;
                ctx.setLineDash(dash || []);
                ctx.beginPath();
                ctx.moveTo(x0, y0);
                ctx.lineTo(x1, y1);
                ctx.stroke();
                ctx.restore();
            };
            const vline = (v, color, dash, width) => {
                if (!Number.isFinite(v) || v < x.min || v > x.max) return;
                const px = x.getPixelForValue(v);
                stroke(px, chartArea.top, px, chartArea.bottom, color, dash, width);
            };
            const hline = (v, color, dash, width) => {
                if (!Number.isFinite(v) || v < y.min || v > y.max) return;
                const py = y.getPixelForValue(v);
                stroke(chartArea.left, py, chartArea.right, py, color, dash, width);
            };
            vline(opts.spot, opts.color, [5, 4]);
            (opts.vlines || []).forEach((l) => vline(l.x, l.color, l.dash, l.width));
            (opts.hlines || []).forEach((l) => hline(l.y, l.color, l.dash, l.width));
            const active = chart.tooltip && chart.tooltip.getActiveElements
                ? chart.tooltip.getActiveElements() : [];
            if (active.length) {
                stroke(active[0].element.x, chartArea.top, active[0].element.x, chartArea.bottom, opts.color, []);
            }
        },
    };

    function series(values, color, label) {
        return {
            label,
            data: data.spots.map((s, j) => ({ x: s, y: values[j] })),
            borderColor: color,
            backgroundColor: color,
            borderWidth: 2,
            pointRadius: 0,
            pointHoverRadius: 3,
            tension: 0,
        };
    }

    // A dataset with no points: it only puts a canvas-drawn line in the legend.
    function legendOnly(label, color) {
        return { label, data: [], borderColor: color, backgroundColor: color, borderWidth: 2, pointRadius: 0 };
    }

    // One format per axis: the decimals follow the tick step, not each value.
    function tickDigits(ticks) {
        let step = Infinity;
        for (let i = 1; i < ticks.length; i += 1) {
            const gap = Math.abs(ticks[i].value - ticks[i - 1].value);
            if (gap > 0 && gap < step) step = gap;
        }
        if (!Number.isFinite(step) || step >= 1) return 0;
        return step >= 0.1 ? 1 : (step >= 0.01 ? 2 : 3);
    }

    // kind: 'money' (P&L, theta, vega), 'delta' (shares) or 'gamma' (shares per $1).
    function axisText(kind, v, ticks) {
        const d = tickDigits(ticks);
        return kind === 'money' ? fmtMoney(v, d) : fmtNum(v, d);
    }

    function valueText(kind, v) {
        if (kind === 'money') return adaptiveMoney(v);
        return fmtNum(v, kind === 'gamma' ? 4 : 2);
    }

    function spotAxis(pal, ticks) {
        return {
            type: 'linear',
            min: data.spots[0],
            max: data.spots[data.spots.length - 1],
            title: { display: true, text: 'Spot', color: pal.muted },
            ticks: { color: pal.muted, includeBounds: false, ...ticks },
            grid: { color: pal.grid },
        };
    }

    function legendOptions(pal) {
        return { position: 'bottom', labels: { color: pal.ink, boxWidth: 16, boxHeight: 2 } };
    }

    function drawChart(id, datasets, yTitle, kind) {
        const canvas = el(id);
        if (!canvas || typeof Chart === 'undefined') return;
        if (charts[id]) { charts[id].destroy(); delete charts[id]; }
        const pal = palette();
        charts[id] = new Chart(canvas.getContext('2d'), {
            type: 'line',
            data: { datasets },
            plugins: [guides],
            options: {
                responsive: true,
                maintainAspectRatio: false,
                parsing: false,
                animation: false,
                interaction: { mode: 'index', intersect: false },
                scales: {
                    x: spotAxis(pal, { callback: (v, _i, ticks) => fmtNum(v, tickDigits(ticks)) }),
                    y: {
                        title: { display: true, text: yTitle, color: pal.muted },
                        ticks: { color: pal.muted, callback: (v, _i, ticks) => axisText(kind, v, ticks) },
                        grid: { color: (ctx) => (ctx.tick && ctx.tick.value === 0 ? pal.axis : pal.grid) },
                    },
                },
                plugins: {
                    optsimGuides: { spot: data.spot, color: pal.muted },
                    legend: legendOptions(pal),
                    tooltip: {
                        callbacks: {
                            title: (items) => 'Spot ' + fmtNum(items[0] ? items[0].parsed.x : NaN, 2),
                            label: (ctx) => `${ctx.dataset.label}: ${valueText(kind, ctx.parsed.y)}`,
                        },
                    },
                },
            },
        });
    }

    function renderPnlChart(pal) {
        const colors = rampColors(pal.ramp, data.chart_days.length);
        const sets = data.chart_days.map((d, i) => series(data.pnl_by_day[d], colors[i], dayLabel(data.days[d])));
        drawChart('optsim-chart-pnl', sets, 'P&L ($)', 'money');
    }

    function renderIvChart(pal) {
        const sets = data.iv_shifts.map((shift, i) => {
            const pts = Math.round(Math.abs(shift) * 100);
            const color = shift < 0 ? pal.iv.down : (shift > 0 ? pal.iv.up : pal.iv.flat);
            const label = shift === 0 ? 'IV unchanged' : `IV ${shift < 0 ? '−' : '+'}${pts} vol pts`;
            return series(data.pnl_by_iv_at_entry[i], color, label);
        });
        drawChart('optsim-chart-iv', sets, 'P&L ($)', 'money');
    }

    function renderGreekChart(pal) {
        const colors = rampColors(pal.ramp, data.chart_days.length);
        const values = data.greeks_by_day[greek];
        const sets = data.chart_days.map((d, i) => series(values[d], colors[i], dayLabel(data.days[d])));
        const kind = greek === 'theta' || greek === 'vega' ? 'money' : greek;
        drawChart('optsim-chart-greek', sets, GREEK_AXIS[greek], kind);
    }

    /* -- break-even IV: one chart per leg, on one IV scale -------------------- */
    function beivScaleMax() {
        const top = Math.max(...data.legs.map((l) => l.iv)) * 100;
        return Math.min(300, Math.max(30, Math.ceil((3 * top) / 10) * 10));
    }

    function drawBeivChart(canvas, l, be, pal, yMax) {
        const days = data.breakeven_iv.days;
        const sets = [];
        days.forEach((day, t) => {
            const row = be.iv[t] || [];
            if (!row.some((v) => v !== null)) return; // expired by this date
            const pct = row.map((v) => (v === null ? null : v * 100));
            sets.push(series(pct, dayColor(pal, day), dayLabel(day)));
        });
        const expiryColor = dayColor(pal, l.dte);
        sets.push(legendOnly(`Expiry, day ${fmtNum(l.dte, 0)}: ${fmtNum(be.expiry_breakeven, 2)}`, expiryColor));
        sets.push(legendOnly(`Entry IV ${fmtPct(l.iv, 1)}`, pal.muted));
        charts[canvas.id] = new Chart(canvas.getContext('2d'), {
            type: 'line',
            data: { datasets: sets },
            plugins: [guides],
            options: {
                responsive: true,
                maintainAspectRatio: false,
                parsing: false,
                animation: false,
                interaction: { mode: 'index', intersect: false },
                scales: {
                    // Two-line ticks: the price, then its distance from the entry spot.
                    x: spotAxis(pal, { callback: (v, _i, ticks) => [fmtNum(v, tickDigits(ticks)), fmtRel(v)] }),
                    y: {
                        min: 0,
                        max: yMax,
                        title: { display: true, text: 'Break-even IV (%)', color: pal.muted },
                        ticks: { color: pal.muted, callback: (v) => `${fmtNum(v, 0)}%` },
                        grid: { color: pal.grid },
                    },
                },
                plugins: {
                    optsimGuides: {
                        spot: data.spot,
                        color: pal.muted,
                        hlines: [{ y: l.iv * 100, color: pal.muted, dash: [5, 4] }],
                        vlines: [{ x: be.expiry_breakeven, color: expiryColor, width: 2 }],
                    },
                    legend: legendOptions(pal),
                    tooltip: {
                        filter: (item) => Number.isFinite(item.parsed.y),
                        callbacks: {
                            title: (items) => (items[0]
                                ? `Spot ${fmtNum(items[0].parsed.x, 2)} (${fmtRel(items[0].parsed.x)})` : ''),
                            label: (ctx) => `${ctx.dataset.label}: ${fmtNum(ctx.parsed.y, 1)}%`,
                        },
                    },
                },
            },
        });
    }

    function renderBeivCharts(pal) {
        const host = el('optsim-beiv-grid');
        if (!host || !data.breakeven_iv) return;
        Object.keys(charts).filter((id) => id.startsWith('optsim-chart-beiv-')).forEach((id) => {
            charts[id].destroy();
            delete charts[id];
        });
        host.textContent = '';
        const yMax = beivScaleMax();
        data.legs.forEach((l, i) => {
            const fig = document.createElement('figure');
            fig.className = 'optsim-beiv-cell';
            const caption = document.createElement('figcaption');
            const expiry = l.expiry ? ` · ${safeDate(l.expiry)}` : '';
            caption.textContent = `Leg ${i + 1} · ${legName(l)} ${fmtNum(l.strike, 2)}${expiry} · ${l.dte} DTE`;
            const wrap = document.createElement('div');
            wrap.className = 'chart-wrapper optsim-chart-wrapper optsim-chart-wrapper--beiv';
            const canvas = document.createElement('canvas');
            canvas.id = `optsim-chart-beiv-${i}`;
            canvas.setAttribute('role', 'img');
            canvas.setAttribute('aria-label', `Break-even IV of leg ${i + 1} versus spot on several dates`);
            wrap.appendChild(canvas);
            fig.append(caption, wrap);
            host.appendChild(fig);
            if (typeof Chart !== 'undefined') drawBeivChart(canvas, l, data.breakeven_iv.legs[i], pal, yMax);
        });
    }

    // The table view of the charts: each leg's break-even IV at the entry spot.
    function renderBeivTable() {
        const host = el('optsim-beiv-table');
        const be = data.breakeven_iv;
        if (!host || !be) return;
        const head = '<th scope="col">Leg</th><th scope="col">Entry IV</th>'
            + be.days.map((d) => `<th scope="col">Day ${fmtNum(d, 0)}</th>`).join('')
            + '<th scope="col">Expiry break-even</th>';
        const rows = data.legs.map((l, i) => {
            const b = be.legs[i];
            const cells = be.days.map((d, t) => {
                if (d >= l.dte) return '<td>—</td>';
                return `<td>${b.at_spot[t] === null ? 'none' : fmtPct(b.at_spot[t], 1)}</td>`;
            }).join('');
            return `<tr><td>${i + 1} · ${legName(l)} ${fmtNum(l.strike, 2)}</td><td>${fmtPct(l.iv, 1)}</td>${cells}`
                + `<td>${fmtNum(b.expiry_breakeven, 2)} (day ${fmtNum(l.dte, 0)})</td></tr>`;
        }).join('');
        host.innerHTML = '<table class="sim-detail" aria-label="Break-even IV at the entry spot by date">'
            + `<thead><tr>${head}</tr></thead><tbody>${rows}</tbody></table>`
            + '<p class="optsim-table-note">At the entry spot. “—”: the leg has expired by that date;'
            + ' “none”: no IV between 0.5% and 300% brings the leg back to its premium.</p>';
    }

    function renderCharts() {
        const pal = palette();
        renderPnlChart(pal);
        renderIvChart(pal);
        renderGreekChart(pal);
        renderBeivCharts(pal);
        renderBeivTable();
    }

    /* -- switches ------------------------------------------------------------- */
    function syncToggles(attr, value) {
        document.querySelectorAll(`[${attr}]`).forEach((btn) => {
            const on = btn.getAttribute(attr) === value;
            btn.classList.toggle('active', on);
            btn.setAttribute('aria-pressed', String(on));
        });
    }

    function setStyle(next) {
        if (next === style) return;
        style = next;
        syncToggles('data-optsim-style', style);
        run();
    }

    function setMargin(next) {
        margin = next;
        syncToggles('data-optsim-margin', margin);
        save();
        if (data) { renderSummary(); renderProfile(); }
    }

    function setGreek(next) {
        greek = next;
        syncToggles('data-optsim-greek', greek);
        if (data) renderGreekChart(palette());
    }

    function wire() {
        const tab = el('tab-optsim');
        if (!tab) return;
        tab.addEventListener('click', (ev) => {
            const t = ev.target.closest('button');
            if (!t) return;
            if (t.matches('[data-action="optsim-run"]')) run();
            else if (t.matches('[data-action="optsim-add-leg"]')) addLeg();
            else if (t.hasAttribute('data-optsim-market')) setMarket(t.getAttribute('data-optsim-market'));
            else if (t.hasAttribute('data-optsim-style')) setStyle(t.getAttribute('data-optsim-style'));
            else if (t.hasAttribute('data-optsim-margin')) setMargin(t.getAttribute('data-optsim-margin'));
            else if (t.hasAttribute('data-optsim-greek')) setGreek(t.getAttribute('data-optsim-greek'));
        });
        const body = el('optsim-legs-body');
        if (body) {
            body.addEventListener('change', onLegChange);
            body.addEventListener('click', onLegClick);
        }
        tab.addEventListener('change', (ev) => { if (SAVED_FIELDS.includes(ev.target.id)) save(); });
        const preset = el('optsim-preset');
        if (preset) {
            preset.addEventListener('change', () => {
                if (applyPreset(preset.value)) run();
                preset.value = '';
            });
        }
        if (window.bus && window.bus.on) {
            // Chart colors are read from CSS tokens, which the theme toggle swaps.
            window.bus.on('theme:changed', () => { if (data) renderCharts(); });
            // Both ticker-change paths reset this tab's flag: re-check it now if it is
            // on screen (an off-screen tab re-checks on its next visit).
            window.bus.on('tab_flags:changed', (ev) => {
                if (!ev || ev.tab !== PANEL || ev.loaded) return;
                if (!tab.classList.contains('active')) return;
                window.loadOptsimTab();
                window.appState.tabFlags.markLoaded(PANEL);
            });
        }
    }

    window.loadOptsimTab = function () {
        if (!wired) {
            wire();
            if (!restore()) applyPreset(DEFAULT_PRESET);
            wired = true;
        }
        if (!data || stale()) run();
    };

    window.runOptsim = run;
    window.optsimDebug = () => ({ legs, marketMode, style, margin, greek, data, buildPayload, charts });
})();
