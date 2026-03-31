/* ============================================================
   Market Review – inline bars & sortable columns
   ============================================================ */
function enhanceMarketReviewTable() {
    const wrapper = document.querySelector('#tab-market-review .table-wrapper');
    if (!wrapper) return;
    const table = wrapper.querySelector('table');
    if (!table) return;

    const tbody = table.tBodies[0];
    if (!tbody) return;
    const rows = Array.from(tbody.rows);
    if (!rows.length) return;

    const colCount = rows[0].cells.length;

    // Parse a formatted value (e.g. "-5.3%", "0.7", "N/A") to float or null
    function parseVal(text) {
        if (!text) return null;
        const s = text.replace('%', '').trim();
        if (s === 'N/A' || s === '') return null;
        const v = parseFloat(s);
        return isNaN(v) ? null : v;
    }

    // Collect original text and build per-column stats BEFORE modifying DOM
    const cellVals = rows.map(r =>
        Array.from(r.cells).map(td => parseVal(td.textContent))
    );
    const colStats = [];
    for (let c = 0; c < colCount; c++) {
        const nums = cellVals.map(rv => rv[c]).filter(v => v !== null);
        const min = nums.length ? Math.min(...nums) : 0;
        const max = nums.length ? Math.max(...nums) : 0;
        colStats.push({ min, max, hasNeg: nums.some(v => v < 0) });
    }

    // Build set of column indices that belong to "Last Close" group (no bar)
    const noBarsSet = new Set();
    const theadRowsEarly = Array.from(table.tHead ? table.tHead.rows : []);
    if (theadRowsEarly.length >= 1) {
        let colCursor = 0;
        Array.from(theadRowsEarly[0].cells).forEach(th => {
            const span = parseInt(th.getAttribute('colspan') || '1', 10);
            if (th.textContent.trim() === 'Last Close') {
                for (let k = 0; k < span; k++) noBarsSet.add(colCursor + k);
            }
            colCursor += span;
        });
    }

    // Add inline bar to every data cell (skip the index column at c=0)
    rows.forEach((row, ri) => {
        Array.from(row.cells).forEach((td, ci) => {
            if (ci === 0) return;                         // row index (asset name)
            if (noBarsSet.has(ci)) {                      // no bar for Last Close
                td.innerHTML = `<div class="mr-cell-inner">${td.textContent.trim()}</div>`;
                return;
            }
            const val = cellVals[ri][ci];
            const stat = colStats[ci];
            const range = stat.max - stat.min;

            // Wrap existing text
            const origText = td.textContent.trim();
            td.innerHTML = `<div class="mr-cell-inner">${origText}</div>`;

            if (val === null || range === 0) {
                td.innerHTML += '<div class="mr-bar-wrap"></div>';
                return;
            }

            const wrapDiv = document.createElement('div');
            wrapDiv.className = 'mr-bar-wrap';

            const barDiv = document.createElement('div');
            barDiv.className = 'mr-bar';

            if (stat.hasNeg) {
                // Diverging bar centered at 0
                wrapDiv.classList.add('diverging');
                const absMax = Math.max(Math.abs(stat.min), Math.abs(stat.max)) || 1;
                const halfWidth = Math.min(Math.abs(val) / absMax * 50, 50);
                if (val >= 0) {
                    barDiv.classList.add('mr-bar-pos');
                    barDiv.style.left = '50%';
                    barDiv.style.width = halfWidth + '%';
                } else {
                    barDiv.classList.add('mr-bar-neg');
                    barDiv.style.left = (50 - halfWidth) + '%';
                    barDiv.style.width = halfWidth + '%';
                }
            } else {
                // Simple positive bar (0 → max)
                barDiv.classList.add('mr-bar-neutral');
                const pct = stat.max > 0 ? Math.min((val / stat.max) * 100, 100) : 0;
                barDiv.style.width = pct + '%';
            }

            wrapDiv.appendChild(barDiv);
            td.appendChild(wrapDiv);
        });
    });

    // ── Sortable column headers ──
    const theadRows = Array.from(table.tHead ? table.tHead.rows : []);
    if (!theadRows.length) return;
    const sortRow = theadRows[theadRows.length - 1];

    let sortColIdx = null;
    let sortDir = 'asc';

    const origVals = cellVals;

    Array.from(sortRow.cells).forEach((th, ci) => {
        if (ci === 0) return;
        th.classList.add('mr-sortable');
        const icon = document.createElement('span');
        icon.className = 'mr-sort-icon';
        icon.textContent = ' ⇅';
        th.appendChild(icon);

        th.addEventListener('click', () => {
            if (sortColIdx === ci) {
                sortDir = sortDir === 'asc' ? 'desc' : 'asc';
            } else {
                sortColIdx = ci;
                sortDir = 'asc';
            }

            Array.from(sortRow.cells).forEach((h, j) => {
                const ic = h.querySelector('.mr-sort-icon');
                if (!ic) return;
                h.classList.remove('sorted');
                ic.textContent = ' ⇅';
            });
            th.classList.add('sorted');
            icon.textContent = sortDir === 'asc' ? ' ↑' : ' ↓';

            const rowEntries = Array.from(tbody.rows).map(r => ({
                row: r,
                val: parseVal(r.cells[ci].querySelector('.mr-cell-inner')
                    ? r.cells[ci].querySelector('.mr-cell-inner').textContent
                    : r.cells[ci].textContent)
            }));

            rowEntries.sort((a, b) => {
                if (a.val === null && b.val === null) return 0;
                if (a.val === null) return 1;
                if (b.val === null) return -1;
                return sortDir === 'asc' ? a.val - b.val : b.val - a.val;
            });

            rowEntries.forEach(({ row }) => tbody.appendChild(row));
        });
    });
}
