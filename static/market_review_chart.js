/* ============================================================
   Market Review – Interactive Time-Series Chart (Module 4A)
   ============================================================ */

const MR_CHART_CONFIG = {
    COLORS: {
        SPX: '#2196F3',
        USD: '#4CAF50',
        Gold: '#FFD700',
        US10Y: '#9C27B0',
        CSI300: '#F44336',
        HSI: '#00BCD4',
        NKY: '#FF9800',
        STOXX: '#795548',
    },
    DEFAULT_COLOR: '#FF6B35',
};

let mrChart = null;
let mrData = null;
let mrMode = 'return';
let mrPeriod = 'ETD';
let mrVisibleAssets = new Set();


async function loadMarketReviewChart(ticker, startDate) {
    const container = document.getElementById('market-review-chart-container');
    if (!container) return;
    container.innerHTML = '<div style="text-align:center;padding:4rem;color:#94a3b8;"><i class="fas fa-spinner fa-spin"></i> Loading time-series data...</div>';

    try {
        const resp = await fetch('/api/market_review_ts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ticker, start_date: startDate || null })
        });
        mrData = await resp.json();

        if (mrData.status !== 'ok') {
            container.innerHTML = `<div style="color:#ef4444;padding:2rem;">${mrData.message || 'Error loading data'}</div>`;
            return;
        }

        // Restore canvas
        container.innerHTML = '<canvas id="market-review-chart"></canvas>';
        mrVisibleAssets = new Set(Object.keys(mrData.assets));
        renderMarketReviewChart();
        renderAssetToggleButtons();
    } catch (e) {
        container.innerHTML = `<div style="color:#ef4444;padding:2rem;">Network error: ${e.message}</div>`;
    }
}


function renderMarketReviewChart() {
    if (!mrData || !mrData.dates) return;

    const startDate = mrData.periods[mrPeriod] || mrData.periods['ETD'];
    const startIdx = mrData.dates.findIndex(d => d >= startDate);
    const filteredDates = mrData.dates.slice(Math.max(0, startIdx));

    const datasets = [];
    for (const [asset, series] of Object.entries(mrData.assets)) {
        if (!mrVisibleAssets.has(asset)) continue;

        let yData;
        if (mrMode === 'return') {
            const prices = series.prices.slice(Math.max(0, startIdx));
            const basePrice = prices.find(p => p !== null);
            yData = prices.map(p => p !== null && basePrice ? ((p / basePrice) - 1) * 100 : null);
        } else if (mrMode === 'vol') {
            yData = series.rolling_vol.slice(Math.max(0, startIdx));
        } else {
            yData = series.rolling_corr.slice(Math.max(0, startIdx));
        }

        const color = asset === mrData.instrument
            ? MR_CHART_CONFIG.DEFAULT_COLOR
            : (MR_CHART_CONFIG.COLORS[asset] || '#999');

        datasets.push({
            label: asset,
            data: filteredDates.map((d, i) => ({ x: d, y: yData[i] })),
            borderColor: color,
            backgroundColor: 'transparent',
            borderWidth: asset === mrData.instrument ? 2.5 : 1.5,
            pointRadius: 0,
            tension: 0.3,
        });
    }

    const ctx = document.getElementById('market-review-chart');
    if (!ctx) return;
    if (mrChart) mrChart.destroy();

    mrChart = new Chart(ctx, {
        type: 'line',
        data: { datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: { display: true, position: 'top', labels: { font: { size: 11 }, boxWidth: 14 } },
                tooltip: {
                    callbacks: {
                        label: function (ctx) {
                            const v = ctx.parsed.y;
                            if (v === null || v === undefined) return null;
                            if (mrMode === 'return') return `${ctx.dataset.label}: ${v.toFixed(2)}%`;
                            if (mrMode === 'vol') return `${ctx.dataset.label}: ${v.toFixed(1)}%`;
                            return `${ctx.dataset.label}: ${v.toFixed(3)}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    type: 'time',
                    time: { unit: 'month' },
                    grid: { display: false },
                    ticks: { font: { size: 10 } }
                },
                y: {
                    title: {
                        display: true,
                        text: mrMode === 'return' ? 'Cumulative Return (%)'
                            : mrMode === 'vol' ? 'Rolling 20d Vol (%)'
                                : 'Rolling 20d Correlation',
                        font: { size: 12 }
                    },
                    grid: { color: 'rgba(200,200,200,0.2)' },
                    ticks: { font: { size: 10 } }
                }
            }
        }
    });
}


function renderAssetToggleButtons() {
    const container = document.getElementById('asset-toggle-container');
    if (!container || !mrData) return;
    container.innerHTML = '';

    for (const asset of Object.keys(mrData.assets)) {
        const btn = document.createElement('button');
        const color = asset === mrData.instrument
            ? MR_CHART_CONFIG.DEFAULT_COLOR
            : (MR_CHART_CONFIG.COLORS[asset] || '#999');
        btn.className = 'btn-toggle btn-sm' + (mrVisibleAssets.has(asset) ? ' active' : '');
        btn.style.borderColor = color;
        btn.style.color = mrVisibleAssets.has(asset) ? '#fff' : color;
        btn.style.backgroundColor = mrVisibleAssets.has(asset) ? color : 'transparent';
        btn.textContent = asset;
        btn.addEventListener('click', function () {
            if (mrVisibleAssets.has(asset)) {
                mrVisibleAssets.delete(asset);
                this.classList.remove('active');
                this.style.color = color;
                this.style.backgroundColor = 'transparent';
            } else {
                mrVisibleAssets.add(asset);
                this.classList.add('active');
                this.style.color = '#fff';
                this.style.backgroundColor = color;
            }
            renderMarketReviewChart();
        });
        container.appendChild(btn);
    }
}


function setMrMode(mode) {
    mrMode = mode;
    document.querySelectorAll('#mr-mode-btns .btn-toggle').forEach(b => {
        b.classList.toggle('active', b.textContent.toLowerCase().startsWith(mode.slice(0, 3)));
    });
    renderMarketReviewChart();
}

function setMrPeriod(period) {
    mrPeriod = period;
    document.querySelectorAll('#mr-period-btns .btn-toggle').forEach(b => {
        b.classList.toggle('active', b.textContent === period);
    });
    renderMarketReviewChart();
}

function toggleSummaryTable() {
    const wrapper = document.getElementById('market-review-table-wrapper');
    if (wrapper) {
        wrapper.style.display = wrapper.style.display === 'none' ? 'block' : 'none';
    }
}


/* ============================================================
   Module 5: Correlation Heatmap (SVG)
   ============================================================ */

function renderCorrelationHeatmap(corrData) {
    const container = document.getElementById('correlation-heatmap-container');
    if (!container || !corrData) return;
    const { labels, values } = corrData;
    const n = labels.length;
    const cellSize = 60;
    const margin = 80;
    const totalSize = cellSize * n + margin + 20;

    let svgCells = '';
    for (let i = 0; i < n; i++) {
        for (let j = 0; j < n; j++) {
            const corr = values[i][j];
            const color = corrToColor(corr);
            const x = margin + j * cellSize;
            const y = margin + i * cellSize;
            svgCells += `<rect x="${x}" y="${y}" width="${cellSize}" height="${cellSize}" fill="${color}" stroke="white" stroke-width="1"/>`;
            svgCells += `<text x="${x + cellSize / 2}" y="${y + cellSize / 2 + 5}" text-anchor="middle" font-size="12" fill="${Math.abs(corr) > 0.5 ? 'white' : 'black'}">${corr.toFixed(2)}</text>`;
        }
    }

    let axisLabels = labels.map((label, i) => {
        const cx = margin + i * cellSize + cellSize / 2;
        return `<text x="${cx}" y="${margin - 10}" text-anchor="middle" font-size="11" transform="rotate(-30,${cx},${margin - 10})">${label}</text>` +
            `<text x="${margin - 10}" y="${margin + i * cellSize + cellSize / 2 + 5}" text-anchor="end" font-size="11">${label}</text>`;
    }).join('');

    container.innerHTML = `<svg viewBox="0 0 ${totalSize} ${totalSize}" xmlns="http://www.w3.org/2000/svg" style="max-width:${totalSize}px;">${axisLabels}${svgCells}</svg>`;
}

function corrToColor(corr) {
    if (corr > 0) {
        const r = Math.round(255 * (1 - corr));
        const g = Math.round(255 * (1 - corr));
        return `rgb(${r},${g},255)`;
    } else {
        const intensity = Math.abs(corr);
        const g = Math.round(255 * (1 - intensity));
        const b = Math.round(255 * (1 - intensity));
        return `rgb(255,${g},${b})`;
    }
}


/* ============================================================
   Multi-ticker context switcher
   ============================================================ */

function switchTickerContext(ticker) {
    document.querySelectorAll('.ticker-tab-btn').forEach(b => {
        b.classList.toggle('active', b.dataset.ticker === ticker);
    });
    // Reload Market Review chart for selected ticker
    if (window._mrLoaded) {
        loadMarketReviewChart(ticker);
    }
}
