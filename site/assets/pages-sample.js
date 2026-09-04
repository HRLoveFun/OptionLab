/* pages-sample.js — fixture fallback for GitHub Pages (no backend).
 *
 * Static pages set `window.PAGES_SAMPLE = { base: '../fixtures' }` then call:
 *   PagesSample.getJSON(['/api/x', 'fixtures/x.json'])  — tries backend first,
 *   falls back through relative fixture candidates.
 * Pure fetch, no dependencies. Safe to load alongside Flask pages (no-op there).
 */
(function (root) {
  'use strict';

  function candidates(url) {
    // Absolute /api/* first (Flask local), then explicit fallbacks.
    if (Array.isArray(url)) return url;
    return [url];
  }

  async function getJSON(urls, opts) {
    const list = candidates(urls);
    let lastErr = null;
    for (const u of list) {
      try {
        const resp = await fetch(u, opts);
        if (!resp.ok) {
          lastErr = new Error('HTTP ' + resp.status + ' for ' + u);
          continue;
        }
        return await resp.json();
      } catch (e) {
        lastErr = e;
      }
    }
    throw lastErr || new Error('fetch failed');
  }

  // Resolve fixture paths relative to the current page depth.
  // Pages live at site/<page>/index.html, fixtures at site/fixtures/.
  function fixture(name) {
    const base = (root.PAGES_SAMPLE && root.PAGES_SAMPLE.base) || '../fixtures';
    return base.replace(/\/$/, '') + '/' + name;
  }

  root.PagesSample = { getJSON, fixture };
})(window);
