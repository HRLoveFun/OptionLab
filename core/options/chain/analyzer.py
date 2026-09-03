"""Option-chain analyzer — canonical implementation.

Domain:    Options Analysis — Chain Orchestration
Context:
  - Encapsulates a fetched option-chain snapshot (spot + expiries + DataFrames).
  - Provides chart-rendering entry-points that delegate to core.options.charts.
  - Provides HTML-table helpers that delegate to core.options.chain.html_tables.
Contracts:
  - OptionsChainAnalyzer(ticker, snapshot=None)
  - get_odds_with_vol_context(spot, target_pct, chain, expiries) -> dict
Dependencies UPWARD:
  - core.options.chain.metrics, term_structure, liquidity, html_tables
  - core.options.charts.*
Dependencies DOWNWARD:
  - services.options.chain, services.options.preload
  - core.decision.candidate, core.decision.market_data
"""

from __future__ import annotations

import datetime as dt
import logging
import math

import numpy as np

from core.options.chain.html_tables import expected_move_table as _expected_move_table
from core.options.chain.html_tables import key_metrics_table as _key_metrics_table
from core.options.chain.liquidity import liquidity_score as _liquidity_score
from core.options.chain.term_structure import atm_iv_for_expiry
from core.options.charts.facade import (
    render_iv_smile,
    render_iv_surface,
    render_iv_term_structure,
    render_oi_volume,
    render_pcr,
    render_skew,
)

logger = logging.getLogger(__name__)

# Re-export for callers that do ``from core.options.chain.analyzer import liquidity_score``
liquidity_score = _liquidity_score


def _dte(expiry_str: str) -> int:
    """Days to expiry from today."""
    today = dt.date.today()
    exp = dt.datetime.strptime(expiry_str, "%Y-%m-%d").date()
    return max(0, (exp - today).days)


def _norm_cdf(x: float) -> float:
    """Approximate normal CDF using math.erf."""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def get_odds_with_vol_context(
    spot: float,
    target_pct: float,
    chain: dict,
    expiries: list,
) -> dict:
    """Return odds data enriched with nearest-expiry ATM IV context.

    Parameters
    ----------
    spot
        Current underlying price.
    target_pct
        Target percentage move (e.g. 10 for ±10%).
    chain
        Mapping expiry -> {"calls": DataFrame, "puts": DataFrame}.
    expiries
        Ordered list of expiry strings (YYYY-MM-DD).

    Returns
    -------
    dict
        ``{"spot", "target_pct", "nearest_expiry", "atm_iv_pct", "dte",
        "prob_touch", "odds": [...]}``.
    """
    if not expiries or not chain:
        return {"odds": [], "message": "no_chain_data"}

    nearest = expiries[0]
    if nearest not in chain:
        return {"odds": [], "message": "no_nearest_expiry"}

    puts = chain[nearest]["puts"]
    atm_iv = atm_iv_for_expiry(puts, spot)
    if atm_iv is None:
        return {"odds": [], "message": "no_atm_iv"}

    dte = max(_dte(nearest), 1)
    T = dte / 365
    sigma = atm_iv
    z = (target_pct / 100) / (sigma * (T**0.5))
    prob_touch = 2 * (1 - _norm_cdf(abs(z)))

    return {
        "spot": round(spot, 2),
        "target_pct": target_pct,
        "nearest_expiry": nearest,
        "atm_iv_pct": round(atm_iv * 100, 2),
        "dte": dte,
        "prob_touch": round(prob_touch, 4),
        "odds": [
            {
                "metric": "probability_of_touch",
                "value": round(prob_touch, 4),
                "description": f"Probability of {target_pct}% move by expiry",
            }
        ],
    }


class OptionsChainAnalyzer:
    """Analyses an option chain snapshot.

    INVARIANT: this class performs no I/O. Callers fetch the snapshot upstream
    (``data_pipeline.yf_client.fetch_option_chain``) and inject it via
    ``snapshot=``. WHY: keeping ``core/`` pure means the analyzer can be driven
    entirely by fixture data in tests, and every network call stays behind the
    single yfinance exit point where proxy setup and throttling are enforced.
    """

    def __init__(self, ticker: str = "^SPX", *, snapshot: dict):
        if snapshot is None:
            raise ValueError(
                "OptionsChainAnalyzer requires snapshot=... — fetch it upstream via "
                "data_pipeline.yf_client.fetch_option_chain (core/ must stay pure)"
            )
        self.ticker = ticker
        self._init_from_snapshot(snapshot)

    def _init_from_snapshot(self, snap: dict):
        spot = snap.get("spot")
        if spot is None:
            raise RuntimeError(f"Unable to fetch spot price for {self.ticker}")
        self.spot: float = float(spot)
        self.expiries: list = list(snap.get("expiries", []))
        self.chain: dict = dict(snap.get("chain", {}))

    def get_snapshot_summary(self) -> dict:
        nearest = self.expiries[0] if self.expiries else None
        if nearest and nearest in self.chain:
            calls = self.chain[nearest]["calls"]
            atm = min(calls["strike"].tolist(), key=lambda x: abs(x - self.spot))
        else:
            atm = None
        return {
            "spot": round(self.spot, 2),
            "expiries": self.expiries,
            "nearest_expiry": nearest,
            "atm_strike": atm,
            "timestamp": dt.datetime.now(dt.UTC).strftime("%Y-%m-%d %H:%M UTC"),
        }

    # ------------------------------------------------------------------
    # Charts — delegate to core.options.charts
    # ------------------------------------------------------------------

    def plot_iv_smile(self, expiry: str) -> str | None:
        try:
            if expiry not in self.chain:
                return None
            calls = self.chain[expiry]["calls"]
            puts = self.chain[expiry]["puts"]
            return render_iv_smile(calls, puts, self.spot, expiry)
        except Exception as e:
            logger.error("plot_iv_smile failed for %s: %s", expiry, e, exc_info=True)
            return None

    def plot_iv_term_structure(self) -> str | None:
        try:
            dates, atm_ivs = [], []
            for exp in self.expiries:
                if exp not in self.chain:
                    continue
                puts = self.chain[exp]["puts"].dropna(subset=["impliedVolatility"])
                if puts.empty:
                    continue
                iv = atm_iv_for_expiry(puts, self.spot)
                if iv is not None:
                    atm_ivs.append(iv)
                    dates.append(exp)
            return render_iv_term_structure(dates, atm_ivs, self.spot)
        except Exception as e:
            logger.error("plot_iv_term_structure failed: %s", e, exc_info=True)
            return None

    def plot_iv_surface(self) -> str | None:
        try:
            records = []
            for exp in self.expiries:
                if exp not in self.chain:
                    continue
                dte = _dte(exp)
                puts = self.chain[exp]["puts"].dropna(subset=["impliedVolatility"])
                for _, row in puts.iterrows():
                    moneyness = float(row["strike"]) / self.spot
                    iv = float(row["impliedVolatility"]) * 100
                    if 0.7 <= moneyness <= 1.3 and iv > 0:
                        records.append({"moneyness": moneyness, "dte": dte, "iv": iv})
            return render_iv_surface(records, self.spot, self.ticker)
        except Exception as e:
            logger.error("plot_iv_surface failed: %s", e, exc_info=True)
            return None

    def plot_skew_analysis(self, expiry: str) -> str | None:
        try:
            if expiry not in self.chain:
                return None
            calls = self.chain[expiry]["calls"].dropna(subset=["impliedVolatility"])
            puts = self.chain[expiry]["puts"].dropna(subset=["impliedVolatility"])
            return render_skew(calls, puts, self.spot, expiry)
        except Exception as e:
            logger.error("plot_skew_analysis failed for %s: %s", expiry, e, exc_info=True)
            return None

    def plot_oi_volume_profile(self, expiry: str) -> str | None:
        try:
            if expiry not in self.chain:
                return None
            calls = self.chain[expiry]["calls"]
            puts = self.chain[expiry]["puts"]
            return render_oi_volume(calls, puts, self.spot, expiry)
        except Exception as e:
            logger.error("plot_oi_volume_profile failed for %s: %s", expiry, e, exc_info=True)
            return None

    def plot_pcr_summary(self) -> str | None:
        try:
            rows = []
            for exp in self.expiries[:12]:
                if exp not in self.chain:
                    continue
                calls = self.chain[exp]["calls"]
                puts = self.chain[exp]["puts"]
                c_vol = calls["volume"].sum()
                p_vol = puts["volume"].sum()
                c_oi = calls["openInterest"].sum()
                p_oi = puts["openInterest"].sum()
                rows.append(
                    {
                        "expiry": exp,
                        "vol_pcr": (p_vol / c_vol) if c_vol > 0 else np.nan,
                        "oi_pcr": (p_oi / c_oi) if c_oi > 0 else np.nan,
                    }
                )
            return render_pcr(rows, self.ticker)
        except Exception as e:
            logger.error("plot_pcr_summary failed: %s", e, exc_info=True)
            return None

    # ------------------------------------------------------------------
    # HTML tables — delegates to core.options.chain.html_tables
    # ------------------------------------------------------------------

    def get_expected_move_table(self) -> str | None:
        """Render expected-move table via core.options.chain.html_tables."""
        return _expected_move_table(self.chain, self.expiries, self.spot)

    def get_key_metrics_table(self) -> str | None:
        """Render key-metrics table via core.options.chain.html_tables."""
        return _key_metrics_table(self.chain, self.expiries, self.spot)
