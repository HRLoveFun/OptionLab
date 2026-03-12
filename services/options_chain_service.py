"""
Options Chain Service - Orchestrates OptionsChainAnalyzer and returns
all charts / tables as a single result dictionary for the Flask route.
"""

import logging
from core.options_chain_analyzer import OptionsChainAnalyzer

logger = logging.getLogger(__name__)


class OptionsChainService:
    """Thin orchestration layer around OptionsChainAnalyzer."""

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
            'oc_snapshot':           None,
            'oc_iv_smile':           None,
            'oc_iv_term_structure':  None,
            'oc_iv_surface':         None,
            'oc_skew_analysis':      None,
            'oc_oi_volume':          None,
            'oc_pcr_summary':        None,
            'oc_expected_move':      None,
            'oc_key_metrics':        None,
        }

        # --- Initialise analyzer (fetches chain on construction) ----------
        try:
            analyzer = OptionsChainAnalyzer(ticker)
        except Exception as e:
            logger.warning(f"OptionsChainAnalyzer init failed for {ticker}: {e}")
            return result

        nearest = analyzer.expiries[0] if analyzer.expiries else None

        # --- Snapshot summary -------------------------------------------
        try:
            result['oc_snapshot'] = analyzer.get_snapshot_summary()
        except Exception as e:
            logger.warning(f"get_snapshot_summary failed: {e}")

        # --- IV Smile (nearest expiry) ------------------------------------
        if nearest:
            try:
                result['oc_iv_smile'] = analyzer.plot_iv_smile(nearest)
            except Exception as e:
                logger.warning(f"plot_iv_smile failed: {e}")

        # --- IV Term Structure --------------------------------------------
        try:
            result['oc_iv_term_structure'] = analyzer.plot_iv_term_structure()
        except Exception as e:
            logger.warning(f"plot_iv_term_structure failed: {e}")

        # --- IV Surface ---------------------------------------------------
        try:
            result['oc_iv_surface'] = analyzer.plot_iv_surface()
        except Exception as e:
            logger.warning(f"plot_iv_surface failed: {e}")

        # --- Skew Analysis (nearest expiry) -------------------------------
        if nearest:
            try:
                result['oc_skew_analysis'] = analyzer.plot_skew_analysis(nearest)
            except Exception as e:
                logger.warning(f"plot_skew_analysis failed: {e}")

        # --- OI / Volume Profile (nearest expiry) -------------------------
        if nearest:
            try:
                result['oc_oi_volume'] = analyzer.plot_oi_volume_profile(nearest)
            except Exception as e:
                logger.warning(f"plot_oi_volume_profile failed: {e}")

        # --- PCR Summary --------------------------------------------------
        try:
            result['oc_pcr_summary'] = analyzer.plot_pcr_summary()
        except Exception as e:
            logger.warning(f"plot_pcr_summary failed: {e}")

        # --- Expected Move Table ------------------------------------------
        try:
            result['oc_expected_move'] = analyzer.get_expected_move_table()
        except Exception as e:
            logger.warning(f"get_expected_move_table failed: {e}")

        # --- Key Metrics Table --------------------------------------------
        try:
            result['oc_key_metrics'] = analyzer.get_key_metrics_table()
        except Exception as e:
            logger.warning(f"get_key_metrics_table failed: {e}")

        return result
