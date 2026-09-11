"""Provider-side hook into the pipeline's failure log.

Domain:    Data Pipeline — Providers (shared)
Context:
  - Every acquisition failure worth surfacing in ``/health/data`` lands in
    ``data_quality_log`` (see ``data_pipeline/store/quality_log.py``). Both option-chain
    and general yfinance provider modules need to record failures, and neither
    may import the other, so the best-effort wrapper lives here.
Why the ``source`` strings still read ``yf_client.*``:
  - Batch B1 moved these calls without changing the stored ``data_quality_log``
    rows; renaming the source labels is a separate, observable change and is
    deliberately deferred (see docs/plans/business_line_reorg.md §6 B1).
Dependencies UPWARD:
  - data_pipeline.store.quality_log (imported lazily — keeps package import cheap and
    avoids a cycle at import time)
"""

from __future__ import annotations


def _log_dq(source: str, error_class: str, message: str, *, ticker: str | None = None) -> None:
    """Best-effort write to ``data_quality_log``. Never raises."""
    try:
        from data_pipeline.store.quality_log import log_failure

        log_failure(source, error_class, message, ticker=ticker)
    except Exception:  # noqa: BLE001
        pass
