/* pages-shim.js — GitHub Pages demo backend (fetch-level stub).
 *
 * The Pages build renders the REAL templates/index.html + REAL static/*.js,
 * so the UI is identical to the Flask app. This file is the ONLY Pages-only
 * code: it answers the backend endpoints the JS calls with committed
 * snapshot fixtures (site/fixtures/*.json), and disables the analysis form
 * submit (no server to POST to).
 *
 * Everything else (styles, tab logic, charts, state machines) is untouched
 * app code — users learn exactly one UI.
 *
 * Load order: AFTER all app scripts (end of <body>), BEFORE NOTHING else.
 * Safe no-op when a real backend answers (it only intercepts requests that
 * would otherwise fail — and same-origin /api/* on Pages always fails).
 */
(function () {
    'use strict';

    window.PAGES_DEMO = true;

    var JSON_HDR = { 'Content-Type': 'application/json' };
    var fixtureCache = {};

    function jsonResponse(obj, status) {
        return new Response(JSON.stringify(obj), {
            status: status || 200,
            headers: JSON_HDR,
        });
    }

    function loadFixture(name) {
        if (fixtureCache[name]) return Promise.resolve(fixtureCache[name]);
        return fetch('./fixtures/' + name).then(function (r) {
            if (!r.ok) throw new Error('fixture missing: ' + name);
            return r.json();
        }).then(function (j) {
            fixtureCache[name] = j;
            return j;
        });
    }

    function checkAbort(signal) {
        if (signal && signal.aborted) {
            var e = new DOMException('aborted', 'AbortError');
            e.name = 'AbortError';
            throw e;
        }
    }

    /* -- regime history: slice rows to the requested window + recompute -- */
    function sliceRegimeHistory(full, days) {
        var rows = (full.rows || []).slice().sort(function (a, b) {
            return a.date < b.date ? -1 : 1;
        });
        var end = rows.length ? rows[rows.length - 1].date : null;
        var cutoff = null;
        if (end && isFinite(days)) {
            var d = new Date(end + 'T00:00:00');
            d.setDate(d.getDate() - days);
            cutoff = d.toISOString().slice(0, 10);
        }
        var win = cutoff ? rows.filter(function (r) { return r.date >= cutoff; }) : rows;
        var vols = {}, dirs = {}, composites = {}, unknown = 0, transitions = [];
        var prev = null;
        win.forEach(function (r) {
            vols[r.vol_regime] = 1;
            dirs[r.dir_regime] = 1;
            composites[r.vol_regime + '|' + r.dir_regime] = 1;
            if (/^UNKNOWN/.test(r.vol_regime || '') || /^UNKNOWN/.test(r.dir_regime || '')) unknown++;
            if (prev && (prev.vol_regime !== r.vol_regime || prev.dir_regime !== r.dir_regime)) {
                transitions.push({
                    date: r.date,
                    from: prev.vol_regime + ' / ' + prev.dir_regime,
                    to: r.vol_regime + ' / ' + r.dir_regime,
                });
            }
            prev = r;
        });
        return {
            status: 'ok',
            rows: win,
            coverage: {
                vol_regimes_observed: Object.keys(vols).sort(),
                dir_regimes_observed: Object.keys(dirs).sort(),
                unique_composite_regimes: Object.keys(composites).length,
                regime_transitions: transitions,
                days_with_unknown: unknown,
                charter_exit_condition_met: Object.keys(composites).length >= 2,
            },
            source: (full.source || 'log') + '+demo-slice',
        };
    }

    /* -- preload payload derived from the option-chain snapshot fixture -- */
    function toPreload(chain) {
        function dte(exp) {
            var ms = new Date(exp + 'T00:00:00') - new Date();
            return Math.max(0, Math.round(ms / 86400000));
        }
        function rec(c, exp) {
            var bid = +c.bid || 0, ask = +c.ask || 0;
            var mid = bid > 0 && ask > 0 ? (bid + ask) / 2 : (+c.lastPrice || 0);
            var ivPct = +c.iv || 0; // chain fixture stores IV as percent
            return {
                strike: +c.strike,
                bid: Math.round(bid * 100) / 100,
                ask: Math.round(ask * 100) / 100,
                mid: Math.round(mid * 100) / 100,
                last: Math.round((+c.lastPrice || 0) * 100) / 100,
                iv: Math.round(ivPct * 100) / 10000,
                iv_pct: Math.round(ivPct * 10) / 10,
                oi: +c.openInterest || 0,
                volume: +c.volume || 0,
                dte: dte(exp),
            };
        }
        var out = { status: 'ok', ticker: chain.ticker, spot: chain.spot, expiries: chain.expirations || [], chain: {} };
        Object.keys(chain.chain || {}).forEach(function (exp) {
            var ch = chain.chain[exp] || {};
            out.chain[exp] = {
                calls: (ch.calls || []).map(function (c) { return rec(c, exp); }),
                puts: (ch.puts || []).map(function (c) { return rec(c, exp); }),
            };
        });
        return out;
    }

    function validateTickers(body) {
        return loadFixture('validate_tickers.json').then(function (known) {
            var results = {};
            ((body && body.tickers) || []).slice(0, 10).forEach(function (t) {
                var key = String(t || '').trim().toUpperCase();
                if (known.results && known.results[key]) {
                    results[t] = known.results[key];
                } else {
                    results[t] = { valid: false, price: null, message: 'demo snapshot only covers ' + Object.keys(known.results || {}).join(', ') };
                }
            });
            return { status: 'ok', results: results };
        });
    }

    function route(path, method, url, opts) {
        // Liveness / health
        if (path === '/api/ping') return jsonResponse({ ok: true });
        if (path === '/health/status' || path === '/health/data') {
            return jsonResponse({ status: 'ok', demo: true });
        }
        if (path === '/api/_meta') {
            return jsonResponse({ status: 'ok', version: 'v1', demo: true, routes: [] });
        }
        // Ticker validation
        if (path === '/api/validate_tickers' && method === 'POST') {
            var body = {};
            try { body = JSON.parse((opts && opts.body) || '{}'); } catch (e) { /* ignore */ }
            return validateTickers(body).then(jsonResponse);
        }
        if (path === '/api/validate_ticker' && method === 'POST') {
            var b2 = {};
            try { b2 = JSON.parse((opts && opts.body) || '{}'); } catch (e) { /* ignore */ }
            return validateTickers({ tickers: [b2.ticker] }).then(function (r) {
                var k = Object.keys(r.results)[0];
                var info = r.results[k] || { valid: false };
                return jsonResponse({ valid: !!info.valid, message: info.message || '' });
            });
        }
        // Option chain snapshot (same file the static fallbacks use)
        if (path === '/api/option_chain') {
            return loadFixture('option_chain.nvda.json').then(jsonResponse);
        }
        if (path === '/api/preload_option_chain' && method === 'POST') {
            return loadFixture('option_chain.nvda.json').then(function (c) { return jsonResponse(toPreload(c)); });
        }
        if (path === '/api/odds_with_vol') {
            return loadFixture('odds_with_vol.nvda.json').then(jsonResponse);
        }
        if (path === '/api/expiry_calendar') {
            return loadFixture('expiry_calendar.json').then(jsonResponse);
        }
        if (path === '/api/market_review_ts') {
            return loadFixture('market_review_ts.nvda.json').then(jsonResponse);
        }
        // Regime (from local regime_log snapshot)
        if (path === '/api/regime/current') {
            return loadFixture('regime_current.json').then(jsonResponse);
        }
        if (path === '/api/regime/history') {
            var days = parseInt((url.searchParams.get('days') || '180'), 10) || 180;
            return loadFixture('regime_history.json').then(function (f) { return jsonResponse(sliceRegimeHistory(f, days)); });
        }
        if (path === '/api/regime/backfill' && method === 'POST') {
            return jsonResponse({ status: 'ok', persisted_rows: 0, demo: true, note: 'demo site: history is a read-only snapshot' });
        }
        // Portfolio analysis needs live pricing — honest failure on the same
        // code path the app shows when the backend errors.
        if (path === '/api/portfolio_analysis') {
            return jsonResponse({ status: 'error', code: 'demo_unavailable', message: 'Portfolio Analysis 需要本地 Flask（实时定价）。本站为静态演示快照。' }, 200);
        }
        return null;
    }

    var nativeFetch = window.fetch.bind(window);
    window.fetch = function (url, opts) {
        var method = ((opts && opts.method) || 'GET').toUpperCase();
        var path;
        try {
            path = new URL(String(url), window.location.href).pathname;
        } catch (e) {
            return nativeFetch(url, opts);
        }
        var handled;
        try {
            handled = route(path, method,
                new URL(String(url), window.location.href), opts || {});
        } catch (e) {
            return Promise.reject(e);
        }
        if (!handled) return nativeFetch(url, opts);
        try { checkAbort(opts && opts.signal); } catch (e) { return Promise.reject(e); }
        return Promise.resolve(handled);
    };

    /* -- analysis form: no server to POST to — explain, don't navigate -- */
    function toast(msg) {
        var el = document.getElementById('pages-demo-toast');
        if (!el) {
            el = document.createElement('div');
            el.id = 'pages-demo-toast';
            el.setAttribute('role', 'status');
            el.style.cssText = 'position:fixed;left:50%;bottom:24px;transform:translateX(-50%);' +
                'background:#1f2937;color:#f9fafb;padding:.7rem 1.1rem;border-radius:10px;' +
                'font-size:.85rem;z-index:10000;box-shadow:0 8px 24px rgba(0,0,0,.35);max-width:min(92vw,560px);';
            document.body.appendChild(el);
        }
        el.textContent = msg;
        el.style.display = 'block';
        clearTimeout(el._t);
        el._t = setTimeout(function () { el.style.display = 'none'; }, 4500);
    }

    document.addEventListener('submit', function (ev) {
        var form = ev.target;
        if (form && form.id === 'analysis-form') {
            ev.preventDefault();
            ev.stopPropagation();
            toast('静态演示站：分析运行需要本地 Flask（python app.py）。当前展示 NVDA 快照，交互方式与本地版一致。');
        }
    }, true);

    /* -- hash deep-links: #tab-option-chain etc. activate the same tab -- */
    function activateFromHash() {
        var id = (window.location.hash || '').replace('#', '');
        if (!id) return;
        var btn = document.querySelector('.tab-btn[data-tab="' + id + '"]');
        if (btn) btn.click();
    }
    document.addEventListener('DOMContentLoaded', activateFromHash);
    window.addEventListener('hashchange', activateFromHash);
    document.addEventListener('click', function (ev) {
        var btn = ev.target && ev.target.closest ? ev.target.closest('.tab-btn') : null;
        if (btn && btn.dataset && btn.dataset.tab) {
            try { history.replaceState(null, '', '#' + btn.dataset.tab); } catch (e) { /* ignore */ }
        }
    });
})();
