"""Option-chain HTML table generation.

Domain:    Options Analysis — Chain Presentation
Context:
  - Stateless functions that produce HTML tables from pre-fetched chain data.
  - No yfinance calls, no matplotlib.
Contracts:
  - expected_move_table(chain, expiries, spot) -> str | None
  - key_metrics_table(chain, expiries, spot) -> str | None
Dependencies UPWARD:
  - pandas, numpy
Dependencies DOWNWARD:
  - core.options_chain_analyzer (backward-compat adapter)
"""

from __future__ import annotations

import datetime as dt
import logging

import numpy as np
import pandas as pd

from core.options.chain.metrics import expected_move, max_pain, skew_25d
from core.options.chain.term_structure import atm_iv_for_expiry

logger = logging.getLogger(__name__)


def _dte(expiry_str: str) -> int:
    """Days to expiry from today."""
    today = dt.date.today()
    exp = dt.datetime.strptime(expiry_str, "%Y-%m-%d").date()
    return max(0, (exp - today).days)


def expected_move_table(chain: dict, expiries: list, spot: float) -> str | None:
    """HTML table of expected move per expiry."""
    try:
        rows = []
        for exp in expiries:
            if exp not in chain:
                continue
            calls = chain[exp]["calls"]
            puts = chain[exp]["puts"]
            dte = _dte(exp)
            em = expected_move(calls, puts, spot)
            if em is None:
                continue
            em_pct = em / spot * 100
            upper = spot + em
            lower = spot - em
            rows.append({
                "Expiry": exp,
                "DTE": dte,
                "ATM Straddle": f"${em:.2f}",
                "Exp Move": f"${em:.2f}",
                "Exp Move %": f"{em_pct:.2f}%",
                "Upper Bound": f"{upper:.2f}",
                "Lower Bound": f"{lower:.2f}",
            })
        if not rows:
            return "<p>No expected move data available.</p>"
        df = pd.DataFrame(rows)
        return df.to_html(index=False, classes="table table-striped", border=0, justify="center")
    except Exception as e:
        logger.error("expected_move_table failed: %s", e, exc_info=True)
        return None


def key_metrics_table(chain: dict, expiries: list, spot: float) -> str | None:
    """HTML table of key option metrics (nearest + second expiry)."""
    try:
        nearest = expiries[0] if expiries else None
        second = expiries[1] if len(expiries) > 1 else None

        # Nearest expiry ATM IV
        near_atm_iv = None
        if nearest and nearest in chain:
            iv = atm_iv_for_expiry(chain[nearest]["puts"], spot)
            near_atm_iv = iv

        # 25Δ Skew
        skew_25 = None
        if nearest and nearest in chain:
            s = skew_25d(chain[nearest]["puts"], chain[nearest]["calls"], spot)
            skew_25 = s * 100 if s is not None else None

        # Term structure slope
        ts_slope = None
        second_iv = None
        if second and second in chain:
            second_iv = atm_iv_for_expiry(chain[second]["puts"], spot)
        if near_atm_iv is not None and second_iv is not None:
            ts_slope = near_atm_iv - second_iv

        # PCR near month
        near_pcr = None
        if nearest and nearest in chain:
            calls = chain[nearest]["calls"]
            puts = chain[nearest]["puts"]
            c_vol = calls["volume"].sum()
            p_vol = puts["volume"].sum()
            near_pcr = p_vol / c_vol if c_vol > 0 else None

        # Expected move near month
        near_em = None
        if nearest and nearest in chain:
            near_em = expected_move(chain[nearest]["calls"], chain[nearest]["puts"], spot)

        # Max Pain near month
        max_pain_val = None
        if nearest and nearest in chain:
            try:
                max_pain_val = max_pain(chain[nearest]["calls"], chain[nearest]["puts"])
            except Exception:
                pass

        def _fmt(v, fmt=".2f", suffix=""):
            return f"{v:{fmt}}{suffix}" if v is not None else "N/A"

        rows = [
            ("Spot Price", _fmt(spot, ".2f")),
            ("Nearest Expiry", nearest or "N/A"),
            ("Nearest ATM IV", _fmt(near_atm_iv, ".2f", "%")),
            ("25Δ Put Skew (near)", _fmt(skew_25, ".2f", "%")),
            ("Term Structure Slope", _fmt(ts_slope, ".2f", "%")),
            ("PCR — near month (Vol)", _fmt(near_pcr, ".3f")),
            ("Expected Move (near)", _fmt(near_em, ".2f", " pts") if near_em else "N/A"),
            ("Max Pain (near)", _fmt(max_pain_val, ".0f")),
        ]
        df = pd.DataFrame(rows, columns=["Metric", "Value"])
        return df.to_html(index=False, classes="table table-striped", border=0, justify="center")
    except Exception as e:
        logger.error("key_metrics_table failed: %s", e, exc_info=True)
        return None
