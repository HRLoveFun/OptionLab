"""Option pricing and Greeks for European and American exercise.

Domain:    Option Simulation — Pricing
Context:
  - Pure, vectorized, network-free maths for the optsim scenario engine.
  - European: Black-Scholes-Merton with a continuous dividend yield q.
  - American: Cox-Ross-Rubinstein binomial tree vectorized over a batch of
    options, with the European tree as a control variate (price, delta,
    gamma and theta are corrected by the analytic European values).
  - Units match ``core.options.greeks.black_scholes.greeks_vectorized``:
    theta per calendar day, vega per 1 vol point (0.01).
  - Expired options (T <= 0) are worth intrinsic value with zero
    time-sensitivities.
  - Implied volatility inverts either style on [IV_MIN, IV_MAX]; NaN marks a
    price no volatility in that range reproduces (and every expired option).
Contracts:
  - european(kind, S, K, T, r, q, sigma) -> dict[str, np.ndarray]
  - american(kind, S, K, T, r, q, sigma, steps=200) -> dict[str, np.ndarray]
  - option_greeks(kind, S, K, T, r, q, sigma, style, steps=200) -> dict
  - implied_vol(kind, price, S, K, T, r, q, style, steps=200) -> np.ndarray
Dependencies UPWARD:
  - numpy, scipy.special
Dependencies DOWNWARD:
  - core.optsim.engine, core.optsim.models, core.optsim.market, tests
"""

from __future__ import annotations

import numpy as np
from scipy.special import ndtr

_SQRT_2PI = np.sqrt(2.0 * np.pi)

# CONSTRAINT: below ~1 minute to expiry the closed form divides by ~0; treat as expired.
_T_EXPIRED = 1e-6

# DOMAIN: 200 CRR steps with a European control variate keep American put prices
# within ~0.007 per 100 of strike (mean ~0.0013) of a 2000-step reference for
# 1-365 day options, calls within ~3e-4; 100 steps (the web path) ~0.02, mean ~0.003.
DEFAULT_STEPS = 200

# DOMAIN: vega is a central difference over +/- 1 vol point for American options.
_VEGA_BUMP = 0.01

KEYS = ("price", "delta", "gamma", "theta", "vega")

# DOMAIN: implied vols are searched between 0.5 and 300 vol points; 300 is also the
# ceiling the web form accepts for ATM IV.
IV_MIN, IV_MAX = 0.005, 3.0

# CONSTRAINT: halvings of [IV_MIN, IV_MAX] for the European inversion (~1e-14 in sigma).
_EU_BISECTIONS = 48
# CONSTRAINT: secant steps for the American inversion; most points converge in 3-4,
# and stragglers finish with bisection inside the bracket the secant kept.
_AM_SECANT_STEPS = 12
_AM_BISECTIONS = 30

# CONSTRAINT: a volatility reprices an option when the model is within this fraction
# of the strike (1e-5 per $100 of strike) of the target price.
_PRICE_TOL = 1e-7


def _arrays(*xs):
    return np.broadcast_arrays(*(np.asarray(x, dtype=float) for x in xs))


def _sign(kind: str) -> float:
    if kind not in ("call", "put"):
        raise ValueError(f"kind must be 'call' or 'put', got {kind!r}")
    return 1.0 if kind == "call" else -1.0


def _intrinsic(kind, S, K):
    return np.maximum(_sign(kind) * (S - K), 0.0)


def _expired(kind, S, K) -> dict[str, np.ndarray]:
    w = _sign(kind)
    itm = (w * (S - K)) > 0
    zero = np.zeros_like(S)
    return {"price": _intrinsic(kind, S, K), "delta": np.where(itm, w, 0.0), "gamma": zero, "theta": zero, "vega": zero}


def european(kind: str, S, K, T, r, q, sigma) -> dict[str, np.ndarray]:
    """Black-Scholes-Merton price and Greeks (theta per day, vega per vol point)."""
    S, K, T, r, q, sigma = _arrays(S, K, T, r, q, sigma)
    w = _sign(kind)
    live = T > _T_EXPIRED
    Tl = np.where(live, T, 1.0)
    sd = sigma * np.sqrt(Tl)
    d1 = (np.log(S / K) + (r - q + 0.5 * sigma**2) * Tl) / sd
    d2 = d1 - sd
    dq, dr = np.exp(-q * Tl), np.exp(-r * Tl)
    pdf = np.exp(-0.5 * d1 * d1) / _SQRT_2PI
    price = w * (S * dq * ndtr(w * d1) - K * dr * ndtr(w * d2))
    delta = w * dq * ndtr(w * d1)
    gamma = dq * pdf / (S * sd)
    theta_y = -S * dq * pdf * sigma / (2.0 * np.sqrt(Tl)) + w * (q * S * dq * ndtr(w * d1) - r * K * dr * ndtr(w * d2))
    vega = S * dq * pdf * np.sqrt(Tl)
    out = {"price": price, "delta": delta, "gamma": gamma, "theta": theta_y / 365.0, "vega": vega / 100.0}
    exp = _expired(kind, S, K)
    return {k: np.where(live, out[k], exp[k]) for k in KEYS}


def _crr(kind: str, S, K, T, r, q, sigma, steps: int, american: bool) -> dict[str, np.ndarray]:
    """CRR tree on flat arrays; returns price, delta, gamma, theta (per year) from the lattice."""
    w = _sign(kind)
    dt = T / steps
    h = sigma * np.sqrt(dt)
    u = np.exp(h)
    p = ((np.exp((r - q) * dt) - 1.0 / u) / (u - 1.0 / u))[:, None]
    disc = np.exp(-r * dt)[:, None]
    j = np.arange(steps + 1)
    V = np.maximum(w * (S[:, None] * np.exp((2 * j - steps)[None, :] * h[:, None]) - K[:, None]), 0.0)
    level = {}
    for i in range(steps - 1, -1, -1):
        V = disc * (p * V[:, 1 : i + 2] + (1.0 - p) * V[:, : i + 1])
        if american or i <= 2:
            Si = S[:, None] * np.exp((2 * np.arange(i + 1) - i)[None, :] * h[:, None])
            if american:
                V = np.maximum(V, w * (Si - K[:, None]))
            if i <= 2:
                level[i] = (Si, V)
    (s1, v1), (s2, v2) = level[1], level[2]
    price = level[0][1][:, 0]
    delta = (v1[:, 1] - v1[:, 0]) / (s1[:, 1] - s1[:, 0])
    gamma = ((v2[:, 2] - v2[:, 1]) / (s2[:, 2] - s2[:, 1]) - (v2[:, 1] - v2[:, 0]) / (s2[:, 1] - s2[:, 0])) / (
        0.5 * (s2[:, 2] - s2[:, 0])
    )
    theta = (v2[:, 1] - price) / (2.0 * dt)
    return {"price": price, "delta": delta, "gamma": gamma, "theta": theta}


def _american_core(kind, S, K, T, r, q, sigma, steps):
    """Control-variate American price/delta/gamma/theta(per day) for live options (flat arrays)."""
    am = _crr(kind, S, K, T, r, q, sigma, steps, american=True)
    eu_tree = _crr(kind, S, K, T, r, q, sigma, steps, american=False)
    eu = european(kind, S, K, T, r, q, sigma)
    out = {k: eu[k] + am[k] - eu_tree[k] for k in ("price", "delta", "gamma")}
    out["theta"] = eu["theta"] + (am["theta"] - eu_tree["theta"]) / 365.0
    out["price"] = np.maximum(out["price"], np.maximum(_intrinsic(kind, S, K), eu["price"]))
    return out


def american(kind: str, S, K, T, r, q, sigma, steps: int = DEFAULT_STEPS) -> dict[str, np.ndarray]:
    """American price and Greeks via a control-variate CRR tree (theta per day, vega per vol point)."""
    S, K, T, r, q, sigma = _arrays(S, K, T, r, q, sigma)
    shape = S.shape
    flat = [x.ravel() for x in (S, K, T, r, q, sigma)]
    live = flat[2] > _T_EXPIRED
    out = {k: np.empty(flat[0].size) for k in KEYS}
    exp = _expired(kind, flat[0], flat[1])
    for k in KEYS:
        out[k][:] = exp[k]
    if live.any():
        s, k_, t, r_, q_, v = (x[live] for x in flat)
        core = _american_core(kind, s, k_, t, r_, q_, v, steps)
        up = _american_core(kind, s, k_, t, r_, q_, v + _VEGA_BUMP, steps)["price"]
        dn = _american_core(kind, s, k_, t, r_, q_, np.maximum(v - _VEGA_BUMP, 1e-4), steps)["price"]
        dv = v + _VEGA_BUMP - np.maximum(v - _VEGA_BUMP, 1e-4)
        core["vega"] = (up - dn) / dv / 100.0
        for key in KEYS:
            out[key][live] = core[key]
    return {k: out[k].reshape(shape) for k in KEYS}


def option_greeks(kind: str, S, K, T, r, q, sigma, style: str = "european", steps: int = DEFAULT_STEPS):
    """Dispatch on exercise style: 'european' (closed form) or 'american' (tree)."""
    if style == "european":
        return european(kind, S, K, T, r, q, sigma)
    if style == "american":
        return american(kind, S, K, T, r, q, sigma, steps=steps)
    raise ValueError(f"style must be 'european' or 'american', got {style!r}")


def _european_iv(kind, price, S, K, T, r, q, lo, hi):
    """Bisection on the closed form; NaN where [lo, hi] does not bracket ``price`` (flat arrays)."""
    a, b = np.full_like(S, lo), np.full_like(S, hi)
    brackets = (european(kind, S, K, T, r, q, a)["price"] <= price) & (
        european(kind, S, K, T, r, q, b)["price"] >= price
    )
    for _ in range(_EU_BISECTIONS):
        mid = 0.5 * (a + b)
        above = european(kind, S, K, T, r, q, mid)["price"] > price
        b = np.where(above, mid, b)
        a = np.where(above, a, mid)
    return np.where(brackets, 0.5 * (a + b), np.nan)


def _american_iv(kind, price, S, K, T, r, q, lo, hi, steps):
    """American implied vol, searched below the European root (flat arrays).

    An American option is never worth less than the European one, so the European
    root bounds the American one from above. A safeguarded secant starts there with
    the European vega as the first slope; points it leaves unsettled finish with
    bisection inside the bracket it kept. NaN where even ``lo`` overprices the option.
    Deep in the money, where exercising now is optimal, the price is flat in vol and
    every vol of that flat stretch reprices it; the search returns the highest.
    """
    out = np.full_like(S, np.nan)
    upper = _european_iv(kind, price, S, K, T, r, q, lo, hi)
    idx = np.flatnonzero(np.isfinite(upper))
    if idx.size == 0:
        return out
    p, s, k, t, rr, qq = (x[idx] for x in (price, S, K, T, r, q))
    tol = _PRICE_TOL * np.maximum(k, 1.0)

    def excess(sel, sigma):
        return _american_core(kind, s[sel], k[sel], t[sel], rr[sel], qq[sel], sigma, steps)["price"] - p[sel]

    every = np.arange(idx.size)
    a, b = np.full(idx.size, lo), upper[idx].copy()
    x = b.copy()
    fx = excess(every, x)  # >= 0: the American value at the European root
    slope = european(kind, s, k, t, rr, qq, x)["vega"] * 100.0  # dV/dsigma
    todo = np.abs(fx) > tol
    for _ in range(_AM_SECANT_STEPS):
        if not todo.any():
            break
        i = np.flatnonzero(todo)
        b[i] = np.where(fx[i] > 0, x[i], b[i])
        a[i] = np.where(fx[i] > 0, a[i], x[i])
        xn = x[i] - fx[i] / np.maximum(slope[i], 1e-12)
        xn = np.where((xn > a[i]) & (xn < b[i]), xn, 0.5 * (a[i] + b[i]))
        fn = excess(i, xn)
        dx = xn - x[i]
        secant = (fn - fx[i]) / np.where(dx != 0.0, dx, 1.0)
        slope[i] = np.where((dx != 0.0) & (secant > 1e-12), secant, slope[i])
        x[i], fx[i] = xn, fn
        todo[i] = np.abs(fn) > tol[i]
    i = np.flatnonzero(todo)
    if i.size:
        b[i] = np.where(fx[i] > 0, x[i], b[i])
        a[i] = np.where(fx[i] > 0, a[i], x[i])
        for _ in range(_AM_BISECTIONS):
            mid = 0.5 * (a[i] + b[i])
            fm = excess(i, mid)
            b[i] = np.where(fm > 0, mid, b[i])
            a[i] = np.where(fm > 0, a[i], mid)
            x[i], fx[i] = mid, fm
    out[idx] = np.where(np.abs(fx) <= tol, x, np.nan)
    return out


def implied_vol(
    kind: str, price, S, K, T, r, q, style: str = "european", steps: int = DEFAULT_STEPS, lo=IV_MIN, hi=IV_MAX
) -> np.ndarray:
    """Volatility in ``[lo, hi]`` at which the option is worth ``price`` per share; NaN where none does.

    Vectorized over the broadcast inputs. European: bisection on the closed form.
    American: searched below the European root (see ``_american_iv``); a price only
    an American option above ``hi`` reaches is reported as NaN as well. Expired
    options and non-positive prices have no implied vol.
    """
    _sign(kind)
    if style not in ("european", "american"):
        raise ValueError(f"style must be 'european' or 'american', got {style!r}")
    price, S, K, T, r, q = _arrays(price, S, K, T, r, q)
    shape = S.shape
    p, s, k, t, rr, qq = (x.ravel() for x in (price, S, K, T, r, q))
    out = np.full(s.size, np.nan)
    live = (t > _T_EXPIRED) & np.isfinite(p) & (p > 0.0)
    if live.any():
        args = [x[live] for x in (p, s, k, t, rr, qq)]
        if style == "european":
            out[live] = _european_iv(kind, *args, lo, hi)
        else:
            out[live] = _american_iv(kind, *args, lo, hi, steps)
    return out.reshape(shape)
