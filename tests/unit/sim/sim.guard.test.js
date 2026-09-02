// sim.guard.test.js — the sim core MUST stay I/O-free so it can run on GitHub
// Pages (public, no backend). Fail the build if any network/global-IO call
// sneaks into static/sim/.
import { describe, it, expect } from 'vitest';
import { readdirSync, readFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const simDir = resolve(__dirname, '../../../static/sim');

const FORBIDDEN = [
  /\bfetch\s*\(/,            // network requests
  /XMLHttpRequest/,          // network requests
  /WebSocket/,               // network sockets
  /\bimport\.meta\.url\b/,    // fragile cross-origin URL construction
];

describe('static/sim is I/O-free (Pages-safe)', () => {
  const files = readdirSync(simDir).filter((f) => f.endsWith('.js'));
  it('has the expected modules', () => {
    expect(files.sort()).toEqual(
      ['analyze.js', 'black_scholes.js', 'grid.js', 'norm.js', 'payoff.js', 'stats.js'].sort(),
    );
  });

  for (const f of files) {
    it(`"${f}" contains no forbidden I/O`, () => {
      const src = readFileSync(resolve(simDir, f), 'utf-8');
      for (const re of FORBIDDEN) {
        expect(re.test(src)).toBe(false);
      }
    });
  }
});
