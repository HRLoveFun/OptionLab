"""Statistical analysis slice generation (scatter, correlation, volatility)."""

import gc
import logging

from core.correlation_validator import CorrelationValidator
from services.chart_service import ChartService
from utils.utils import DEFAULT_RISK_THRESHOLD, DEFAULT_ROLLING_WINDOW

logger = logging.getLogger(__name__)


def _chart_cache_key(form_data: dict, chart_name: str, *extra) -> tuple:
    """Build a stable LRU cache key for a deep matplotlib chart."""
    features = {
        "start": str(form_data.get("parsed_start_time")),
        "end": str(form_data.get("parsed_end_time")),
        "frequency": form_data.get("frequency"),
        "extra": extra,
    }
    return (form_data.get("ticker"), chart_name, ChartService.features_hash(features))


def _cached_or_build(key: tuple, builder):
    """Return a cached base64 chart for ``key`` or build → cache → return."""
    cached = ChartService.cache_get(key)
    if cached is not None:
        return cached
    result = builder()
    if isinstance(result, str) and result:
        ChartService.cache_put(key, result)
    return result


def _generate_statistical_analysis(analyzer, form_data):
    """Generate statistical analysis results."""
    ticker = form_data.get("ticker", "?")
    results = {
        "feat_ret_scatter_top_url": None,
        "high_low_scatter_url": None,
        "return_osc_high_low_url": None,
        "volatility_dynamic_url": None,
        "correlation_dynamics_chart": None,
    }
    try:
        rolling_window = form_data.get("rolling_window", DEFAULT_ROLLING_WINDOW)
        risk_threshold = form_data.get("risk_threshold", DEFAULT_RISK_THRESHOLD)

        chart_warnings = []

        top_plot = _cached_or_build(
            _chart_cache_key(form_data, "scatter_oscillation", rolling_window, risk_threshold),
            lambda: analyzer.generate_scatter_plots("Oscillation", rolling_window, risk_threshold),
        )
        if top_plot:
            results["feat_ret_scatter_top_url"] = top_plot
        else:
            chart_warnings.append("Oscillation scatter")
            logger.warning("Scatter plot generation returned None for %s", ticker)

        high_low_scatter = _cached_or_build(
            _chart_cache_key(form_data, "high_low_scatter"),
            lambda: analyzer.generate_high_low_scatter(),
        )
        if high_low_scatter:
            results["high_low_scatter_url"] = high_low_scatter
        else:
            chart_warnings.append("High-Low scatter")
            logger.warning("High-Low scatter plot returned None for %s", ticker)

        return_osc_plot = _cached_or_build(
            _chart_cache_key(form_data, "return_osc_high_low", rolling_window, risk_threshold),
            lambda: analyzer.generate_return_osc_high_low_chart(rolling_window, risk_threshold),
        )
        if return_osc_plot:
            results["return_osc_high_low_url"] = return_osc_plot
        else:
            chart_warnings.append("Return-Oscillation dynamics")
            logger.warning("Return-Osc plot returned None for %s", ticker)

        volatility_plot = _cached_or_build(
            _chart_cache_key(form_data, "volatility_dynamics"),
            lambda: analyzer.generate_volatility_dynamics(),
        )
        if volatility_plot:
            results["volatility_dynamic_url"] = volatility_plot
        else:
            chart_warnings.append("Volatility dynamics")
            logger.warning("Volatility dynamics plot generation failed for %s", ticker)

        # Generate correlation validation charts
        try:
            correlation_validator = CorrelationValidator(
                ticker=form_data["ticker"],
                start_date=form_data["parsed_start_time"],
                frequency=form_data["frequency"],
                end_date=form_data.get("parsed_end_time"),
                price_data=analyzer._ctx,
            )

            if correlation_validator.is_data_valid():
                corr_charts = correlation_validator.generate_all_correlation_charts()
                results.update(corr_charts)
            else:
                chart_warnings.append("Correlation dynamics")
                logger.warning("Correlation validator has no valid data for %s", ticker)
        except Exception as e:
            chart_warnings.append("Correlation dynamics")
            logger.error(f"Error generating correlation charts: {e}", exc_info=True)
        finally:
            gc.collect()

        # Surface per-chart failures
        all_none = all(v is None for k, v in results.items() if k != "statistical_error")
        if all_none and analyzer.is_data_valid():
            fdf = analyzer.features_df
            pdyn = getattr(analyzer, "price_dynamic", None)
            actual_min = actual_max = None
            if pdyn is not None and getattr(pdyn, "_data", None) is not None and not pdyn._data.empty:
                try:
                    actual_min = pdyn._data.index.min().date().isoformat()
                    actual_max = pdyn._data.index.max().date().isoformat()
                except Exception:
                    pass
            req_start = form_data.get("parsed_start_time")
            req_end = form_data.get("parsed_end_time")
            if fdf is not None and fdf.shape[0] == 0 and actual_min and actual_max:
                msg = (
                    f"No data points within the requested horizon "
                    f"({req_start} → {req_end}). DB only has {ticker} data "
                    f"from {actual_min} to {actual_max}. Either narrow the "
                    f"horizon to that window, or seed history via "
                    f"POST /api/data/seed with body "
                    f'{{"ticker":"{ticker}","years":5}} '
                    f"(note: /api/regime/backfill only repopulates VIX/SPY "
                    f"regime tags, NOT per-ticker price history)."
                )
            else:
                msg = f"All charts returned None. features_df shape: {fdf.shape if fdf is not None else 'None'}"
            logger.warning("Statistical analysis empty for %s: %s", ticker, msg)
            results["statistical_error"] = msg
        elif chart_warnings and not all_none:
            results["statistical_warning"] = (
                f"Some charts unavailable for {ticker}: {', '.join(chart_warnings)}. This may be due to insufficient data for the selected time range."
            )

    except Exception as e:
        logger.error(f"Error generating statistical analysis for {ticker}: {e}", exc_info=True)
        results["statistical_error"] = str(e)
    return results
