/* Market Regime tab — renders current regime, history strip, and coverage.
 * Consumes /api/regime/current, /api/regime/history, /api/regime/backfill.
 */
(function () {
    'use strict';

    const VOL_COLORS = {
        LOW_VOL: '#10b981',
        MID_VOL: '#3b82f6',
        HIGH_VOL: '#f59e0b',
        STRESS_VOL: '#ef4444',
        UNKNOWN_VOL: '#94a3b8'
    };
    const DIR_COLORS = {
        UP_TREND: '#10b981',
        DOWN_TREND: '#ef4444',
        CHOP: '#f59e0b',
        UNKNOWN_DIR: '#94a3b8'
    };

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
        const color = palette[value] || '#64748b';
        return `<span style="display:inline-block;padding:.15rem .55rem;border-radius:999px;background:${color};color:#fff;font-weight:600;font-size:.85rem;">${value || '—'}</span>`;
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
            container.innerHTML = '<span class="muted">No data.</span>';
            return;
        }
        const L = data.label;
        const complete = data.data_complete ? '' :
            '<div style="color:#f59e0b;margin-top:.5rem;font-size:.9rem;"><i class="fas fa-exclamation-triangle"></i> Data incomplete — regime may be UNKNOWN.</div>';
        container.innerHTML = `
            <div style="display:flex;gap:2rem;flex-wrap:wrap;align-items:center;">
                <div><div class="muted" style="font-size:.8rem;">Date</div><div style="font-weight:600;">${L.date}</div></div>
                <div><div class="muted" style="font-size:.8rem;">Volatility</div><div>${regimeBadge(L.vol_regime, VOL_COLORS)}</div></div>
                <div><div class="muted" style="font-size:.8rem;">Direction</div><div>${regimeBadge(L.dir_regime, DIR_COLORS)}</div></div>
                <div><div class="muted" style="font-size:.8rem;">VIX</div><div>${fmtNum(L.vix_value)}</div></div>
                <div><div class="muted" style="font-size:.8rem;">SPY 20-day SMA</div><div>${fmtNum(L.sma_20)}</div></div>
                <div><div class="muted" style="font-size:.8rem;">5-day SMA slope</div><div>${fmtPct(L.sma_slope_5d)}</div></div>
                <div><div class="muted" style="font-size:.8rem;">Close vs SMA</div><div>${fmtPct(L.close_vs_sma_pct)}</div></div>
            </div>
            ${L.notes ? `<div class="muted" style="margin-top:.5rem;font-size:.8rem;">Notes: ${L.notes}</div>` : ''}
            ${complete}
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
        const volColors = rows.map(r => VOL_COLORS[r.vol_regime] || '#94a3b8');
        const dirColors = rows.map(r => DIR_COLORS[r.dir_regime] || '#94a3b8');
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
            if (el) el.innerHTML = `<span style="color:#ef4444;">Failed to load history: ${e.message}</span>`;
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
            if (el) el.innerHTML = `<span style="color:#ef4444;">Failed to load current regime: ${e.message}</span>`;
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
