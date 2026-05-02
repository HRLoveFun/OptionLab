"""Assessment slice generation (projections, option analysis, position sizing)."""

import logging

from ._sizing import calculate_position_size

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

        # Option analysis is now optional
        if form_data.get("option_data") and len(form_data["option_data"]) > 0:
            valid_options = [
                option
                for option in form_data["option_data"]
                if (
                    option.get("strike")
                    and option.get("quantity")
                    and option.get("premium")
                    and float(option["strike"]) > 0
                    and int(option["quantity"]) != 0
                    and float(option["premium"]) > 0
                )
            ]
            if valid_options:
                try:
                    option_analysis = analyzer.analyze_options(valid_options)
                    if option_analysis:
                        results["plot_url"] = option_analysis
                    else:
                        logger.info("Option analysis returned None - no chart generated")
                except Exception as e:
                    logger.error(f"Error in option analysis: {e}", exc_info=True)
            else:
                logger.info("No valid option positions found - skipping option analysis")
        else:
            logger.info("No option data provided - skipping option analysis")
    except Exception as e:
        logger.error(f"Error generating assessment for {ticker}: {e}", exc_info=True)
        results["assessment_error"] = str(e)

    # Position sizing
    try:
        account_size = form_data.get("account_size")
        max_risk_pct = form_data.get("max_risk_pct")
        if account_size is not None and max_risk_pct is not None:
            max_loss_per_contract = None
            if form_data.get("option_data"):
                current_price = analyzer._get_current_price() if analyzer.is_data_valid() else None
                if current_price is not None:
                    matrix = analyzer._calculate_option_matrix(current_price, form_data["option_data"])
                    if matrix is not None:
                        max_loss_per_contract = float(matrix["PnL"].min())

            strategy_type = (
                "credit" if (max_loss_per_contract is not None and max_loss_per_contract < 0) else "debit"
            )
            ps_result = calculate_position_size(
                float(account_size), float(max_risk_pct), max_loss_per_contract, strategy_type
            )
            if ps_result:
                results["position_sizing"] = ps_result
    except Exception as e:
        logger.warning(f"Position sizing failed: {e}")

    return results
