/* Market Regime tab — renders current regime, history strip, and coverage.
 * Consumes /api/regime/current, /api/regime/history, /api/regime/backfill.
 */
(function () {
    'use strict';

    // Regime palettes are sourced from CSS custom properties defined in
    // static/styles.css (`--regime-*`) so the design tokens stay in one
    // place. Keep these maps in sync with that token group.
    function cssVar(name, fallback) {
        try {
            const v = getComputedStyle(document.documentElement)
                .getPropertyValue(name).trim();
            return v || fallback;
        } catch (_e) {
            return fallback;
        }
    }
    const VOL_COLORS = {
        LOW_VOL: cssVar('--regime-low-vol', '#10b981'),
        MID_VOL: cssVar('--regime-mid-vol', '#3b82f6'),
        HIGH_VOL: cssVar('--regime-high-vol', '#f59e0b'),
        STRESS_VOL: cssVar('--regime-stress-vol', '#ef4444'),
        UNKNOWN_VOL: cssVar('--regime-unknown', '#94a3b8')
    };
    const DIR_COLORS = {
        UP_TREND: cssVar('--regime-up-trend', '#10b981'),
        DOWN_TREND: cssVar('--regime-down-trend', '#ef4444'),
        CHOP: cssVar('--regime-chop', '#f59e0b'),
        UNKNOWN_DIR: cssVar('--regime-unknown', '#94a3b8')
    };
    const REGIME_UNKNOWN_COLOR = cssVar('--regime-unknown', '#94a3b8');
    const REGIME_BADGE_FALLBACK = cssVar('--regime-badge-fallback', '#64748b');

    let stripChart = null;
    let currentDays = 180;

    function fmtPct(v) {
        if (v === null || v === undefined || isNaN(v)) return '—';
        return (v * 100).toFixed(2) + '%';
    }
    function fmtNum(v, digits) {
        if (v === null || v === undefined || isNaN(v)) return '—';
        return Number(v).toFixed(digits === undefined ? 2 : digits);
    }
    function regimeBadge(value, palette) {
        const color = palette[value] || REGIME_BADGE_FALLBACK;
        return `<span class="regime-badge" style="background:${color};">${value || '—'}</span>`;
    }

    /* Compose a human-readable composite regime label, e.g.
       "Mid-Vol · Up-Trend".  Pure formatting — no inference. */
    function composeRegimeTitle(volRegime, dirRegime) {
        const pretty = (v) => {
            if (!v) return '—';
            return v
                .replace('_VOL', '-Vol')
                .replace('_TREND', '-Trend')
                .toLowerCase()
                .replace(/(^|[\s-])\w/g, c => c.toUpperCase());
        };
        return `${pretty(volRegime)} · ${pretty(dirRegime)}`;
    }

    async function fetchJSON(url, opts) {
        const resp = await fetch(url, opts);
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        return resp.json();
    }

    function renderCurrent(data) {
        const container = document.getElementById('regime-current-body');
        if (!container) return;
        if (!data || !data.label) {
            container.innerHTML =
                '<div class="regime-hero regime-hero--placeholder"><span>No data.</span></div>';
            return;
        }
        const L = data.label;
        const volColor = VOL_COLORS[L.vol_regime] || REGIME_UNKNOWN_COLOR;
        const dirColor = DIR_COLORS[L.dir_regime] || REGIME_UNKNOWN_COLOR;
        const incomplete = !data.data_complete;
        const incompleteNote = incomplete
            ? '<div class="semantic-warn" style="margin-top:.5rem;font-size:.85rem;">' +
            '<i class="fas fa-exclamation-triangle" aria-hidden="true"></i> ' +
            'Data incomplete — regime may be UNKNOWN.</div>'
            : '';
        // Hero layout — Design Principle P1.
        container.innerHTML = `
            <div class="regime-hero">
                <div class="regime-hero__primary">
                    <div class="regime-hero__date">As of ${L.date || '—'}</div>
                    <div class="regime-hero__label">${composeRegimeTitle(L.vol_regime, L.dir_regime)}</div>
                    <div class="regime-hero__badges">
                        <span class="regime-badge" style="background:${volColor};">${L.vol_regime || '—'}</span>
                        <span class="regime-badge" style="background:${dirColor};">${L.dir_regime || '—'}</span>
                    </div>
                    ${incompleteNote}
                </div>
                <div class="regime-hero__metrics" role="list" aria-label="Regime supporting metrics">
                    <div class="regime-hero__metric" role="listitem">
                        <div class="regime-hero__metric-label">VIX</div>
                        <div class="regime-hero__metric-value">${fmtNum(L.vix_value)}</div>
                    </div>
                    <div class="regime-hero__metric" role="listitem">
                        <div class="regime-hero__metric-label">SPY 20-day SMA</div>
                        <div class="regime-hero__metric-value">${fmtNum(L.sma_20)}</div>
                    </div>
                    <div class="regime-hero__metric" role="listitem">
                        <div class="regime-hero__metric-label">5-day SMA Slope</div>
                        <div class="regime-hero__metric-value">${fmtPct(L.sma_slope_5d)}</div>
                    </div>
                    <div class="regime-hero__metric" role="listitem">
                        <div class="regime-hero__metric-label">Close vs SMA</div>
                        <div class="regime-hero__metric-value">${fmtPct(L.close_vs_sma_pct)}</div>
                    </div>
                </div>
            </div>
            ${L.notes ? `<div class="muted" style="margin-top:.5rem;font-size:.8rem;">Notes: ${L.notes}</div>` : ''}
        `;
    }

    function renderStrip(rows) {
        const canvas = document.getElementById('regime-strip-chart');
        if (!canvas || typeof Chart === 'undefined') return;
        if (!rows || rows.length === 0) {
            if (stripChart) { stripChart.destroy(); stripChart = null; }
            const ctx = canvas.getContext('2d');
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            return;
        }
        const volData = rows.map(r => ({ x: r.date, y: 1, _regime: r.vol_regime }));
        const dirData = rows.map(r => ({ x: r.date, y: 0, _regime: r.dir_regime }));
        const volColors = rows.map(r => VOL_COLORS[r.vol_regime] || REGIME_UNKNOWN_COLOR);
        const dirColors = rows.map(r => DIR_COLORS[r.dir_regime] || REGIME_UNKNOWN_COLOR);
        const vixLine = rows
            .filter(r => r.vix_value !== null && r.vix_value !== undefined)
            .map(r => ({ x: r.date, y: r.vix_value }));
        const smaLine = rows
            .filter(r => r.sma_20 !== null && r.sma_20 !== undefined)
            .map(r => ({ x: r.date, y: r.sma_20 }));

        if (stripChart) { stripChart.destroy(); }
        stripChart = new Chart(canvas.getContext('2d'), {
            data: {
                datasets: [
                    {
                        type: 'scatter',
                        label: 'Volatility regime',
                        data: volData,
                        backgroundColor: volColors,
                        borderColor: volColors,
                        pointRadius: 4,
                        pointStyle: 'rect',
                        yAxisID: 'yRegime'
                    },
                    {
                        type: 'scatter',
                        label: 'Direction regime',
                        data: dirData,
                        backgroundColor: dirColors,
                        borderColor: dirColors,
                        pointRadius: 4,
                        pointStyle: 'rect',
                        yAxisID: 'yRegime'
                    },
                    {
                        type: 'line',
                        label: 'VIX',
                        data: vixLine,
                        borderColor: '#ef4444',
                        backgroundColor: 'rgba(239,68,68,.08)',
                        borderWidth: 1.5,
                        pointRadius: 0,
                        tension: 0.15,
                        yAxisID: 'yVix'
                    },
                    {
                        type: 'line',
                        label: 'SPY 20-day SMA',
                        data: smaLine,
                        borderColor: '#3b82f6',
                        backgroundColor: 'rgba(59,130,246,.08)',
                        borderWidth: 1.5,
                        pointRadius: 0,
                        tension: 0.15,
                        yAxisID: 'ySma'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                parsing: false,
                interaction: { mode: 'index', intersect: false },
                scales: {
                    x: { type: 'time', time: { unit: 'month' } },
                    yRegime: {
                        position: 'left',
                        min: -0.5, max: 1.5,
                        ticks: {
                            stepSize: 1,
                            callback: v => v === 1 ? 'Vol' : (v === 0 ? 'Dir' : '')
                        },
                        grid: { display: false }
                    },
                    yVix: {
                        position: 'right',
                        title: { display: true, text: 'VIX' },
                        grid: { drawOnChartArea: false }
                    },
                    ySma: {
                        position: 'right',
                        title: { display: true, text: 'SPY SMA20' },
                        grid: { drawOnChartArea: false },
                        offset: true
                    }
                },
                plugins: {
                    legend: { display: true, position: 'bottom' },
                    tooltip: {
                        callbacks: {
                            label: ctx => {
                                const p = ctx.raw || {};
                                if (ctx.dataset.type === 'scatter') {
                                    const kind = ctx.datasetIndex === 0 ? 'Vol' : 'Dir';
                                    return `${kind}: ${p._regime}`;
                                }
                                return `${ctx.dataset.label}: ${p.y?.toFixed?.(2) ?? p.y}`;
                            }
                        }
                    }
                }
            }
        });
    }

    function renderCoverage(coverage) {
        const el = document.getElementById('regime-coverage-body');
        if (!el) return;
        if (!coverage) { el.innerHTML = '<span class="muted">—</span>'; return; }
        const met = coverage.charter_exit_condition_met
            ? '<span style="color:#10b981;font-weight:600;"><i class="fas fa-check"></i> Met</span>'
            : '<span style="color:#ef4444;font-weight:600;"><i class="fas fa-times"></i> Not met</span>';
        el.innerHTML = `
            <div style="display:flex;gap:2rem;flex-wrap:wrap;">
                <div><div class="muted" style="font-size:.8rem;">Vol regimes observed</div>
                    <div>${(coverage.vol_regimes_observed || []).map(v => regimeBadge(v, VOL_COLORS)).join(' ') || '—'}</div>
                </div>
                <div><div class="muted" style="font-size:.8rem;">Dir regimes observed</div>
                    <div>${(coverage.dir_regimes_observed || []).map(v => regimeBadge(v, DIR_COLORS)).join(' ') || '—'}</div>
                </div>
                <div><div class="muted" style="font-size:.8rem;">Unique composite regimes</div>
                    <div style="font-weight:600;">${coverage.unique_composite_regimes ?? 0}</div></div>
                <div><div class="muted" style="font-size:.8rem;">Days with UNKNOWN</div>
                    <div style="font-weight:600;">${coverage.days_with_unknown ?? 0}</div></div>
                <div><div class="muted" style="font-size:.8rem;">Charter §6 (≥2 regimes)</div>
                    <div>${met}</div></div>
            </div>
        `;
    }

    function renderTransitions(transitions) {
        const el = document.getElementById('regime-transitions-body');
        if (!el) return;
        if (!transitions || !transitions.length) {
            el.innerHTML = '<span class="muted">No transitions in window.</span>';
            return;
        }
        const recent = transitions.slice(-20).reverse();
        let html = '<table class="table table-striped"><thead><tr><th>Date</th><th>From</th><th>To</th></tr></thead><tbody>';
        for (const t of recent) {
            html += `<tr><td>${t.date}</td><td><code>${t.from}</code></td><td><code>${t.to}</code></td></tr>`;
        }
        html += '</tbody></table>';
        el.innerHTML = html;
    }

    async function loadHistory() {
        try {
            const data = await fetchJSON(`/api/regime/history?days=${currentDays}`);
            if (data.status !== 'ok') throw new Error(data.message || 'history error');
            renderStrip(data.rows || []);
            renderCoverage(data.coverage);
            renderTransitions((data.coverage && data.coverage.regime_transitions) || []);
            const tag = document.getElementById('regime-source-tag');
            if (tag) {
                tag.innerHTML = `<i class="fas fa-${data.source === 'log' ? 'database' : 'bolt'}"></i> source: ${data.source}`;
            }
        } catch (e) {
            console.error('regime history failed', e);
            const el = document.getElementById('regime-coverage-body');
            if (el) el.innerHTML = `<span class="semantic-neg">Failed to load history: ${e.message}</span>`;
        }
    }

    async function loadCurrent() {
        try {
            const data = await fetchJSON('/api/regime/current');
            if (data.status !== 'ok') throw new Error(data.message || 'current error');
            renderCurrent(data);
        } catch (e) {
            console.error('regime current failed', e);
            const el = document.getElementById('regime-current-body');
            if (el) el.innerHTML = `<span class="semantic-neg">Failed to load current regime: ${e.message}</span>`;
        }
    }

    async function doBackfill() {
        const btn = document.getElementById('regime-backfill-btn');
        if (btn) { btn.disabled = true; btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Backfilling…'; }
        try {
            const data = await fetchJSON('/api/regime/backfill', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ days: Math.max(currentDays, 90) })
            });
            if (data.status !== 'ok') throw new Error(data.message || 'backfill error');
            await loadHistory();
        } catch (e) {
            alert('Backfill failed: ' + e.message);
        } finally {
            if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fas fa-database"></i> Backfill &amp; Persist'; }
        }
    }

    function wireControls() {
        document.querySelectorAll('#regime-range-btns .btn-toggle').forEach(b => {
            b.addEventListener('click', () => {
                document.querySelectorAll('#regime-range-btns .btn-toggle').forEach(x => x.classList.remove('active'));
                b.classList.add('active');
                currentDays = parseInt(b.dataset.days, 10) || 180;
                loadHistory();
            });
        });
        const refresh = document.getElementById('regime-refresh-btn');
        if (refresh) refresh.addEventListener('click', () => { loadCurrent(); loadHistory(); });
        const backfill = document.getElementById('regime-backfill-btn');
        if (backfill) backfill.addEventListener('click', doBackfill);
    }

    let wired = false;
    window.loadRegimeTab = function () {
        if (!wired) { wireControls(); wired = true; }
        loadCurrent();
        loadHistory();
    };
})();
