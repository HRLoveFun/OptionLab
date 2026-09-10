"""Assessment slice generation (projections, option analysis, position sizing)."""

import logging

from .sizing import calculate_position_size

logger = logging.getLogger(__name__)


def _generate_assessment(analyzer, form_data):
    """Generate assessment results including projections and option analysis."""
    ticker = form_data.get("ticker", "?")
    results = {
        "feat_projection_url": None,
        "feat_projection_table": None,
    }
    try:
        percentile = form_data["risk_threshold"] / 100.0
        target_bias = form_data["target_bias"]
        projection_plot, projection_table = analyzer.generate_oscillation_projection(
            percentile=percentile, target_bias=target_bias
        )
        if projection_plot:
            results["feat_projection_url"] = projection_plot
        else:
            logger.warning("Oscillation projection plot returned None for %s", ticker)
        if projection_table:
            results["feat_projection_table"] = projection_table
    except Exception as e:
        logger.error(f"Error generating assessment for {ticker}: {e}", exc_info=True)
        results["assessment_error"] = "评估图表生成失败，请稍后重试"

    # Position sizing. WHY debit-only: batch B7 moved option positions to the
    # Portfolio tab, so the Assessment slice no longer sees a position list to
    # derive a per-contract max loss from — sizing here uses account_size /
    # max_risk_pct against a debit (defined-risk) assumption. Position-aware
    # sizing lives in the Portfolio tab.
    try:
        account_size = form_data.get("account_size")
        max_risk_pct = form_data.get("max_risk_pct")
        if account_size is not None and max_risk_pct is not None:
            ps_result = calculate_position_size(float(account_size), float(max_risk_pct), None, "debit")
            if ps_result:
                results["position_sizing"] = ps_result
    except Exception as e:
        # WHY (deliberate degradation, confirmed with the owner): position
        # sizing is auxiliary info on a page whose subject is the statistical
        # charts — surfacing a dedicated error fragment for a failed sizing
        # calc would be more disruptive than the missing panel. Contrast with
        # the other failures in this function, which DO set assessment_error.
        logger.warning(f"Position sizing failed: {e}")

    return results
