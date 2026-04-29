/** @vitest-environment jsdom */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as payoff from '../../static/components/payoff_chart.js';

describe('payoff_chart.js', () => {
    beforeEach(() => {
        window.Chart = vi.fn(function (ctx, config) {
            this.ctx = ctx;
            this.config = config;
        });
    });

    it('analyzeStrategy posts to /api/v1/strategy/analyze', async () => {
        const fakePayload = { status: 'ok', prices: [1, 2], pnl: [0, 1], breakevens: [1.5] };
        const fetchMock = vi.fn().mockResolvedValue({
            ok: true,
            json: async () => fakePayload,
        });
        vi.stubGlobal('fetch', fetchMock);

        const out = await payoff.analyzeStrategy({ strategy: 'long_call', spot: 100, params: { strike: 100, premium: 3 } });

        expect(out).toEqual(fakePayload);
        expect(fetchMock).toHaveBeenCalledTimes(1);
        const [url, init] = fetchMock.mock.calls[0];
        expect(url).toBe('/api/v1/strategy/analyze');
        expect(init.method).toBe('POST');
        expect(JSON.parse(init.body).strategy).toBe('long_call');
    });

    it('analyzeStrategy throws on error response', async () => {
        vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
            ok: false,
            status: 400,
            json: async () => ({ status: 'error', message: 'nope' }),
        }));
        await expect(payoff.analyzeStrategy({})).rejects.toThrow('nope');
    });

    it('renderPayoff instantiates Chart with provided data', () => {
        const canvas = document.createElement('canvas');
        document.body.appendChild(canvas);
        const inst = payoff.renderPayoff(canvas, {
            prices: [90, 95, 100, 105, 110],
            pnl: [-5, -2, 0, 3, 6],
            breakevens: [100],
            max_profit: 10,
            max_loss: -5,
            net_premium: -3,
        });
        expect(window.Chart).toHaveBeenCalledTimes(1);
        expect(inst.config.type).toBe('line');
        expect(inst.config.data.datasets[0].data).toHaveLength(5);
        expect(inst.config.data.datasets[1].data[0].x).toBe(100);
    });

    it('renderPayoff rejects bad payloads', () => {
        expect(() => payoff.renderPayoff(document.createElement('canvas'), {})).toThrow(/invalid/);
    });
});
