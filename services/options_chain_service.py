"""
Options Chain Service - Orchestrates OptionsChainAnalyzer and returns
all charts / tables as a single result dictionary for the Flask route.
"""

import logging
import math

from core.options_chain_analyzer import OptionsChainAnalyzer, liquidity_score
from data_pipeline.yf_client import fetch_option_chain

logger = logging.getLogger(__name__)


def _clean_num(v) -> float | None:
    """Coerce a value to a JSON-safe rounded float, or None."""
    try:
        if v is None:
            return None
        fv = float(v)
        if math.isnan(fv) or math.isinf(fv):
            return None
        return round(fv, 4)
    except (TypeError, ValueError):
        return None


class OptionsChainService:
    """Thin orchestration layer around OptionsChainAnalyzer."""

    # ------------------------------------------------------------------
    # Lightweight records endpoint (used by /api/option_chain)
    # ------------------------------------------------------------------
    @staticmethod
    def fetch_records(ticker: str) -> dict:
        """Return a JSON-friendly option chain payload.

        Shape::

            {
                "expirations": [...],
                "chain": {expiry: {"calls": [row, ...], "puts": [row, ...]}},
                "spot": float | None,
            }

        Each row carries strike/bid/ask/last/iv/oi/volume + a liquidity score.
        Heavy DataFrame work and yfinance access stay out of the route.
        """
        snap = fetch_option_chain(ticker)
        spot = _clean_num(snap.get("spot"))
        chain_dfs = snap.get("chain", {}) or {}
        expirations = list(chain_dfs.keys())

        chain_records: dict = {}
        for exp, frames in chain_dfs.items():
            calls_df = frames.get("calls")
            puts_df = frames.get("puts")
            chain_records[exp] = {
                "calls": OptionsChainService._df_to_records(calls_df, spot),
                "puts": OptionsChainService._df_to_records(puts_df, spot),
            }

        return {"expirations": expirations, "chain": chain_records, "spot": spot}

    @staticmethod
    def _df_to_records(df, spot):
        if df is None or df.empty:
            return []
        # Sort by strike for stable output across expiries
        try:
            df = df.sort_values("strike")
        except Exception:
            pass
        rows = []
        for _, r in df.iterrows():
            strike = _clean_num(r.get("strike"))
            bid_ = _clean_num(r.get("bid"))
            ask_ = _clean_num(r.get("ask"))
            last_ = _clean_num(r.get("lastPrice"))
            oi_ = _clean_num(r.get("openInterest"))
            vol_ = _clean_num(r.get("volume"))
            iv_raw = r.get("impliedVolatility")
            iv_pct = _clean_num((iv_raw or 0) * 100)
            score, reason = liquidity_score(strike or 0, bid_, ask_, last_, oi_, vol_, spot)
            rows.append(
                {
                    "strike": strike,
                    "lastPrice": last_,
                    "bid": bid_,
                    "ask": ask_,
                    "volume": vol_,
                    "openInterest": oi_,
                    "iv": iv_pct,
                    "itm": bool(r.get("inTheMoney", False)),
                    "liq_score": score,
                    "liq_reason": reason,
                }
            )
        return rows

    # ------------------------------------------------------------------
    # Full analysis (used by /render/options_chain)
    # ------------------------------------------------------------------
    @staticmethod
    def generate_options_chain_analysis(ticker: str) -> dict:
        """
        Build an OptionsChainAnalyzer snapshot and generate all charts /
        tables.  Each individual step is wrapped in try/except so a single
        failure does not prevent the rest from rendering.

        Returns a dict with keys:
            oc_snapshot          – dict (get_snapshot_summary)
            oc_iv_smile          – base64 PNG str | None
            oc_iv_term_structure – base64 PNG str | None
            oc_iv_surface        – base64 PNG str | None
            oc_skew_analysis     – base64 PNG str | None
            oc_oi_volume         – base64 PNG str | None
            oc_pcr_summary       – base64 PNG str | None
            oc_expected_move     – HTML str | None
            oc_key_metrics       – HTML str | None
        """
        result = {
            "oc_snapshot": None,
            "oc_iv_smile": None,
            "oc_iv_term_structure": None,
            "oc_iv_surface": None,
            "oc_skew_analysis": None,
            "oc_oi_volume": None,
            "oc_pcr_summary": None,
            "oc_expected_move": None,
            "oc_key_metrics": None,
            "oc_vol_premium": None,
        }

        # --- Fetch snapshot upstream and inject into analyzer -------------
        try:
            snap = fetch_option_chain(ticker)
            analyzer = OptionsChainAnalyzer(ticker, snapshot=snap)
        except Exception as e:
            logger.warning(f"OptionsChainAnalyzer init failed for {ticker}: {e}")
            return result

        nearest = analyzer.expiries[0] if analyzer.expiries else None

        # --- Snapshot summary -------------------------------------------
        try:
            result["oc_snapshot"] = analyzer.get_snapshot_summary()
        except Exception as e:
            logger.warning(f"get_snapshot_summary failed: {e}")

        # --- IV Smile (nearest expiry) ------------------------------------
        if nearest:
            try:
                result["oc_iv_smile"] = analyzer.plot_iv_smile(nearest)
            except Exception as e:
                logger.warning(f"plot_iv_smile failed: {e}")

        # --- IV Term Structure --------------------------------------------
        try:
            result["oc_iv_term_structure"] = analyzer.plot_iv_term_structure()
        except Exception as e:
            logger.warning(f"plot_iv_term_structure failed: {e}")

        # --- IV Surface ---------------------------------------------------
        try:
            result["oc_iv_surface"] = analyzer.plot_iv_surface()
        except Exception as e:
            logger.warning(f"plot_iv_surface failed: {e}")

        # --- Skew Analysis (nearest expiry) -------------------------------
        if nearest:
            try:
                result["oc_skew_analysis"] = analyzer.plot_skew_analysis(nearest)
            except Exception as e:
                logger.warning(f"plot_skew_analysis failed: {e}")

        # --- OI / Volume Profile (nearest expiry) -------------------------
        if nearest:
            try:
                result["oc_oi_volume"] = analyzer.plot_oi_volume_profile(nearest)
            except Exception as e:
                logger.warning(f"plot_oi_volume_profile failed: {e}")

        # --- PCR Summary --------------------------------------------------
        try:
            result["oc_pcr_summary"] = analyzer.plot_pcr_summary()
        except Exception as e:
            logger.warning(f"plot_pcr_summary failed: {e}")

        # --- Expected Move Table ------------------------------------------
        try:
            result["oc_expected_move"] = analyzer.get_expected_move_table()
        except Exception as e:
            logger.warning(f"get_expected_move_table failed: {e}")

        # --- Key Metrics Table --------------------------------------------
        try:
            result["oc_key_metrics"] = analyzer.get_key_metrics_table()
        except Exception as e:
            logger.warning(f"get_key_metrics_table failed: {e}")

        # --- Vol Premium context (HV vs IV) --------------------------------
        try:
            import datetime as dt

            from core.market.data_context import build_data_context
            from core.signals.hv import vol_premium_context

            ctx = build_data_context(ticker, dt.date.today() - dt.timedelta(days=365), "D")
            if ctx.is_valid() and ctx.daily_bars is not None:
                # Get nearest-expiry ATM IV
                atm_iv = None
                nearest_exp = analyzer.expiries[0] if analyzer.expiries else None
                if nearest_exp and nearest_exp in analyzer.chain:
                    puts = analyzer.chain[nearest_exp]["puts"].dropna(subset=["impliedVolatility"])
                    if not puts.empty:
                        idx = (puts["strike"] - analyzer.spot).abs().idxmin()
                        atm_iv = float(puts.loc[idx, "impliedVolatility"]) * 100

                vol_ctx = vol_premium_context(ctx.daily_bars.get("Adj Close"), atm_iv)
                if vol_ctx:
                    result["oc_vol_premium"] = vol_ctx
        except Exception as e:
            logger.warning(f"Vol premium context failed: {e}")

        return result
