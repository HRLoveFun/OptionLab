/* Position Simulator tab — value, Greeks and margin of a hypothetical
 * multi-leg position over spot × time × IV.
 *
 * Consumes POST /api/optsim (services/options/optsim.py → core.optsim). Both
 * margin regimes come back in every response, so the margin switch only
 * re-renders; the exercise switch re-runs, because American legs are priced
 * on a binomial tree server-side.
 */
(function () {
    'use strict';

    const PANEL = 'optsim';
    const MAX_LEGS = 6;
    const DEFAULT_PRESET = 'short_strangle';

    function leg(type, side, dte, by, value) {
        return { type, side, qty: 1, dte, by, value };
    }

    // Presets are rules, not contracts: the server resolves |Δ| against the smile.
    // A null strike means "at the money" (the Spot input, rounded).
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

    const GREEK_AXIS = {
        delta: 'Delta (shares)',
        gamma: 'Gamma (shares per $1)',
        theta: 'Theta ($ per day)',
        vega: 'Vega ($ per vol point)',
    };

    let legs = [];
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

    // Small numbers need decimals, large ones do not: theta +$6.33 vs +$193.
    function adaptiveMoney(v) {
        return fmtMoney(v, Math.abs(v) >= 100 ? 0 : 2);
    }

    function cap(s) {
        return s ? s.charAt(0).toUpperCase() + s.slice(1) : '';
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

    /* -- legs editor -------------------------------------------------------- */
    function spotInput() {
        const v = parseFloat((el('optsim-spot') || {}).value);
        return Number.isFinite(v) && v > 0 ? v : null;
    }

    function atmStrike() {
        const s = spotInput();
        return s === null ? null : Math.round(s);
    }

    function applyPreset(name) {
        const preset = PRESETS[name];
        if (!preset) return false;
        legs = preset.map((l) => ({ ...l, value: l.value === null ? atmStrike() : l.value }));
        renderLegEditor();
        return true;
    }

    function option(value, label, current) {
        return `<option value="${value}"${value === current ? ' selected' : ''}>${label}</option>`;
    }

    function legRow(l, i) {
        const n = i + 1;
        const valueLabel = l.by === 'delta' ? 'absolute delta' : 'strike';
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
            + `<td><input type="number" data-field="value" min="0" step="any" value="${l.value === null ? '' : l.value}"`
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
        } else {
            l[field] = raw;
        }
        if (field === 'by') {
            // A delta is not a strike: switching the selector resets the value.
            l.value = raw === 'delta' ? 0.16 : atmStrike();
            renderLegEditor();
        }
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
        const v = parseFloat((el(id) || {}).value);
        return Number.isFinite(v) ? v : null;
    }

    function buildPayload() {
        return {
            spot: numberOf('optsim-spot'),
            rate: numberOf('optsim-rate'),
            div_yield: numberOf('optsim-div'),
            atm_iv: numberOf('optsim-atm-iv'),
            skew: numberOf('optsim-skew'),
            curvature: numberOf('optsim-curvature'),
            multiplier: numberOf('optsim-multiplier'),
            spot_range: numberOf('optsim-spot-range'),
            iv_shift: numberOf('optsim-iv-shift'),
            product: (el('optsim-product') || {}).value || 'etf',
            style,
            legs: legs.map((l) => ({
                type: l.type,
                side: l.side,
                qty: l.qty,
                dte: l.dte,
                [l.by === 'delta' ? 'delta' : 'strike']: l.value,
            })),
        };
    }

    async function run() {
        window.appState.panels.set(PANEL, 'loading', {
            message: style === 'american'
                ? 'Pricing American exercise on a binomial tree…'
                : 'Revaluing the position…',
        });
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
    function renderAll() {
        if (!data) return;
        renderSummary();
        renderResolved();
        renderCharts();
        renderProfile();
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

    function renderResolved() {
        const host = el('optsim-resolved');
        if (!host) return;
        const rows = data.legs.map((l, i) => '<tr>'
            + `<td>${i + 1}</td><td>${cap(l.side)} ${l.qty} ${cap(l.type)}</td><td>${l.dte}</td>`
            + `<td>${fmtNum(l.strike, 2)}</td><td>${fmtPct(l.iv, 2)}</td>`
            + `<td>${fmtNum(l.premium, 2)}</td><td>${fmtNum(l.delta, 3)}</td>`
            + '</tr>').join('');
        host.innerHTML = '<table class="sim-detail" aria-label="Resolved legs at entry"><thead><tr>'
            + '<th scope="col">Leg</th><th scope="col">Position</th><th scope="col">DTE</th>'
            + '<th scope="col">Strike</th><th scope="col">IV</th>'
            + '<th scope="col">Premium / share</th><th scope="col">Delta / share</th>'
            + `</tr></thead><tbody>${rows}</tbody></table>`;
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

    function dayLabel(day) {
        const lastExpiry = Math.max(...data.legs.map((l) => l.dte));
        if (day === 0) return 'Entry';
        return `Day ${fmtNum(day, 0)}${day === lastExpiry ? ' (expiry)' : ''}`;
    }

    // Spot marker plus a hover guide, drawn on the canvas so neither joins the
    // legend or the index-mode tooltip.
    const guides = {
        id: 'optsimGuides',
        afterDatasetsDraw(chart, _args, opts) {
            const { ctx, chartArea } = chart;
            const x = chart.scales.x;
            const line = (px, color, dash) => {
                ctx.save();
                ctx.strokeStyle = color;
                ctx.lineWidth = 1;
                ctx.setLineDash(dash);
                ctx.beginPath();
                ctx.moveTo(px, chartArea.top);
                ctx.lineTo(px, chartArea.bottom);
                ctx.stroke();
                ctx.restore();
            };
            if (Number.isFinite(opts.spot)) line(x.getPixelForValue(opts.spot), opts.color, [5, 4]);
            const active = chart.tooltip && chart.tooltip.getActiveElements
                ? chart.tooltip.getActiveElements() : [];
            if (active.length) line(active[0].element.x, opts.color, []);
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
                    x: {
                        type: 'linear',
                        min: data.spots[0],
                        max: data.spots[data.spots.length - 1],
                        title: { display: true, text: 'Spot', color: pal.muted },
                        ticks: {
                            color: pal.muted,
                            includeBounds: false,
                            callback: (v, _i, ticks) => fmtNum(v, tickDigits(ticks)),
                        },
                        grid: { color: pal.grid },
                    },
                    y: {
                        title: { display: true, text: yTitle, color: pal.muted },
                        ticks: { color: pal.muted, callback: (v, _i, ticks) => axisText(kind, v, ticks) },
                        grid: { color: (ctx) => (ctx.tick && ctx.tick.value === 0 ? pal.axis : pal.grid) },
                    },
                },
                plugins: {
                    optsimGuides: { spot: data.spot, color: pal.muted },
                    legend: {
                        position: 'bottom',
                        labels: { color: pal.ink, boxWidth: 16, boxHeight: 2 },
                    },
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

    function renderCharts() {
        const pal = palette();
        renderPnlChart(pal);
        renderIvChart(pal);
        renderGreekChart(pal);
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
            else if (t.hasAttribute('data-optsim-style')) setStyle(t.getAttribute('data-optsim-style'));
            else if (t.hasAttribute('data-optsim-margin')) setMargin(t.getAttribute('data-optsim-margin'));
            else if (t.hasAttribute('data-optsim-greek')) setGreek(t.getAttribute('data-optsim-greek'));
        });
        const body = el('optsim-legs-body');
        if (body) {
            body.addEventListener('change', onLegChange);
            body.addEventListener('click', onLegClick);
        }
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
        }
    }

    window.loadOptsimTab = function () {
        if (!wired) {
            wire();
            applyPreset(DEFAULT_PRESET);
            wired = true;
        }
        if (!data) run();
    };

    window.runOptsim = run;
    window.optsimDebug = () => ({ legs, style, margin, greek, data, buildPayload, charts });
})();
