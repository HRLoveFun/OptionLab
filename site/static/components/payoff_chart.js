/**
 * payoff_chart.js — render strategy P&L curve via Chart.js using
 * /api/strategy/analyze (or /api/strategy/build_from_chain).
 *
 * Usage:
 *   import { renderPayoff, analyzeStrategy } from './components/payoff_chart.js';
 *   const data = await analyzeStrategy({ strategy: 'long_call', spot: 100, params: {...} });
 *   renderPayoff(canvasEl, data);
 *
 * Or, with build_from_chain:
 *   const data = await buildFromChain({ ticker:'AAPL', template:'long_call', expiry, strikes:{ k:170 } });
 *   renderPayoff(canvasEl, data.analytics);
 */

const API_BASE = '/api/v1';

async function _post(path, body) {
    const resp = await fetch(`${API_BASE}${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    const data = await resp.json();
    if (!resp.ok || data.status === 'error') {
        const msg = data.message || `HTTP ${resp.status}`;
        throw new Error(msg);
    }
    return data;
}

export function analyzeStrategy(body) {
    return _post('/strategy/analyze', body);
}

export function buildFromChain(body) {
    return _post('/strategy/build_from_chain', body);
}

/**
 * Render a P&L payoff curve into an existing <canvas> element.
 *
 * @param {HTMLCanvasElement} canvas
 * @param {object} analytics — payload with prices[], pnl[], breakevens[],
 *                             max_profit, max_loss, net_premium
 * @returns {Chart} the Chart.js instance (caller may destroy() to redraw)
 */
export function renderPayoff(canvas, analytics) {
    if (!window.Chart) {
        throw new Error('Chart.js not loaded — include cdn.jsdelivr.net/npm/chart.js@4');
    }
    if (!analytics || !Array.isArray(analytics.prices) || !Array.isArray(analytics.pnl)) {
        throw new Error('renderPayoff: invalid analytics payload');
    }

    // Highlight zero line + breakevens via point styling.
    const breakevens = analytics.breakevens || [];
    const annotations = breakevens.map((be) => ({
        x: be,
        y: 0,
    }));

    const data = {
        labels: analytics.prices,
        datasets: [
            {
                label: 'P&L at expiration',
                data: analytics.pnl,
                borderColor: '#2563eb',
                backgroundColor: 'rgba(37, 99, 235, 0.15)',
                borderWidth: 2,
                pointRadius: 0,
                fill: {
                    target: 'origin',
                    above: 'rgba(34, 197, 94, 0.20)',
                    below: 'rgba(239, 68, 68, 0.20)',
                },
                tension: 0,
            },
            {
                label: 'Breakeven',
                data: annotations.map((a) => ({ x: a.x, y: a.y })),
                type: 'scatter',
                backgroundColor: '#f59e0b',
                borderColor: '#f59e0b',
                pointRadius: 6,
                pointStyle: 'triangle',
                showLine: false,
            },
        ],
    };

    const config = {
        type: 'line',
        data,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: { position: 'top' },
                tooltip: {
                    callbacks: {
                        label(ctx) {
                            if (ctx.datasetIndex === 1) return `Breakeven @ ${Number(ctx.parsed.x).toFixed(2)}`;
                            const pnl = Number(ctx.parsed.y).toFixed(2);
                            return `P&L: ${pnl >= 0 ? '+' : ''}${pnl}`;
                        },
                    },
                },
                title: {
                    display: true,
                    text: _summaryTitle(analytics),
                },
            },
            scales: {
                x: {
                    type: 'linear',
                    title: { display: true, text: 'Underlying price at expiration' },
                    ticks: {
                        callback: (v) => Number(v).toFixed(2),
                    },
                },
                y: {
                    title: { display: true, text: 'P&L ($)' },
                    grid: {
                        color: (ctx) => (ctx.tick.value === 0 ? 'rgba(0,0,0,0.5)' : 'rgba(0,0,0,0.08)'),
                    },
                },
            },
        },
    };

    return new window.Chart(canvas.getContext('2d'), config);
}

function _summaryTitle(a) {
    const max_p = Number.isFinite(a.max_profit) ? a.max_profit.toFixed(2) : '∞';
    const max_l = Number.isFinite(a.max_loss) ? a.max_loss.toFixed(2) : '-∞';
    const np = Number.isFinite(a.net_premium) ? a.net_premium.toFixed(2) : '?';
    return `Net premium: ${np} | Max profit: ${max_p} | Max loss: ${max_l}`;
}
