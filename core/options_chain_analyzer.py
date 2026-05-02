"""Options Chain Analyzer — BACKWARD-COMPAT ADAPTER over core.options.*.

This module is a thin facade.  All heavy lifting has been moved to:
  - core.options.chain.metrics      (max_pain, expected_move, skew_25d)
  - core.options.chain.term_structure (atm_iv, iv_rank, iv_percentile)
  - core.options.chain.liquidity    (liquidity_score)
  - core.options.charts.*           (matplotlib rendering)

New code should import those submodules directly; this class exists only
to satisfy existing callers during the transition.
"""

from __future__ import annotations

import datetime as dt
import logging

import numpy as np
import pandas as pd

from core.options.chain.html_tables import expected_move_table as _expected_move_table
from core.options.chain.html_tables import key_metrics_table as _key_metrics_table
from core.options.chain.liquidity import liquidity_score as _liquidity_score
from core.options.chain.metrics import expected_move, max_pain, skew_25d
from core.options.chain.term_structure import atm_iv_for_expiry, iv_percentile, iv_rank
from core.options.charts.iv_smile import render_iv_smile
from core.options.charts.iv_surface import render_iv_surface
from core.options.charts.iv_term import render_iv_term_structure
from core.options.charts.oi_volume import render_oi_volume
from core.options.charts.pcr import render_pcr
from core.options.charts.skew import render_skew
from data_pipeline.yf_client import fetch_option_chain

logger = logging.getLogger(__name__)

# Re-export for callers that do ``from core.options_chain_analyzer import liquidity_score``
liquidity_score = _liquidity_score


def _dte(expiry_str: str) -> int:
    """Days to expiry from today."""
    today = dt.date.today()
    exp = dt.datetime.strptime(expiry_str, "%Y-%m-%d").date()
    return max(0, (exp - today).days)


class OptionsChainAnalyzer:
    """Analyses an option chain snapshot.

    New code should fetch data upstream (e.g. via ``data_pipeline.yf_client``)
    and pass the raw snapshot here.  The legacy ``ticker``-only constructor
    still works for backward compatibility but triggers a network call.
    """

    def __init__(self, ticker: str = "^SPX", *, snapshot: dict | None = None):
        self.ticker = ticker
        if snapshot is not None:
            self._init_from_snapshot(snapshot)
        else:
            self._init_from_yfinance(ticker)

    def _init_from_snapshot(self, snap: dict):
        spot = snap.get("spot")
        if spot is None:
            raise RuntimeError(f"Unable to fetch spot price for {self.ticker}")
        self.spot: float = float(spot)
        self.expiries: list = list(snap.get("expiries", []))
        self.chain: dict = dict(snap.get("chain", {}))

    def _init_from_yfinance(self, ticker: str):
        snap = fetch_option_chain(ticker)
        self._init_from_snapshot(snap)

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
            "timestamp": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
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
                rows.append({
                    "expiry": exp,
                    "vol_pcr": (p_vol / c_vol) if c_vol > 0 else np.nan,
                    "oi_pcr": (p_oi / c_oi) if c_oi > 0 else np.nan,
                })
            return render_pcr(rows, self.ticker)
        except Exception as e:
            logger.error("plot_pcr_summary failed: %s", e, exc_info=True)
            return None

    # ------------------------------------------------------------------
    # HTML tables — pure computation kept here for backward-compat
    # ------------------------------------------------------------------

    def get_expected_move_table(self) -> str | None:
        """Backward-compat: delegates to core.options.chain.html_tables."""
        return _expected_move_table(self.chain, self.expiries, self.spot)

    def get_key_metrics_table(self) -> str | None:
        """Backward-compat: delegates to core.options.chain.html_tables."""
        return _key_metrics_table(self.chain, self.expiries, self.spot)
