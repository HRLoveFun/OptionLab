// Helper to load IIFE/script-style static JS files into the current jsdom
// window.
//
// Two mechanisms are exposed:
//
// 1. `loadScript(rel)` — sync, runs source via indirect `eval` so top-level
//    `function`/`var` decls attach to globalThis. Used by all tests today.
//    Trade-off: V8 coverage cannot attribute `eval`'d sources back to the
//    original file, so the coverage report shows 0% for these modules.
//
// 2. `staticImports` — static `import` statements pointing at the real
//    sources. Importing this module triggers each IIFE once *with*
//    coverage instrumentation. Used by `coverage.test.js` to make every
//    line of the suite executed appear in the V8 coverage report.

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '..', '..');

const _cache = new Map();

function _read(rel) {
    if (!_cache.has(rel)) {
        const abs = path.join(REPO_ROOT, rel);
        let src = fs.readFileSync(abs, 'utf8');
        if (!/\/\/[#@]\s*sourceURL=/.test(src)) {
            src += `\n//# sourceURL=${abs}\n`;
        }
        _cache.set(rel, src);
    }
    return _cache.get(rel);
}

export function loadScript(relPath) {
    const src = _read(relPath);
    (0, eval)(src);
}

export function loadStateBundle() {
    loadScript('static/eventBus.js');
    loadScript('static/state/store.js');
    loadScript('static/state/abortRegistry.js');
    loadScript('static/state/chainCacheState.js');
    loadScript('static/state/optionChainState.js');
    loadScript('static/state/oddsChainState.js');
    loadScript('static/state/tabFlagsState.js');
    loadScript('static/state/panelState.js');
}

