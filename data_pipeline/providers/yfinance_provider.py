"""yfinance provider: historical bars, close panels, canonical mapping.

Domain:    Data Pipeline — yfinance Provider
Context:
  - This module (with ``yf_snapshot.py``) is the **only** place in the repo that
    imports ``yfinance``; batch B1 moved these calls here out of the old
    ``data_pipeline/yf_client.py`` and ``data_pipeline/downloader.py`` (now
    ``ingest/ohlcv.py``) without changing behaviour. See ADR 0002 (as amended by
    ADR 0011) and docs/plans/business_line_reorg.md §6.
  - ``YFinanceProvider`` is the canonical seam implementation (``history()`` /
    ``close_panel()`` / ``spot()`` / ``option_chain()``); it delegates the live
    snapshots to ``yf_snapshot.py``. The module-level ``fetch_*`` functions keep
    their original yfinance-shaped contracts so the ~11 existing importers keep
    working through the ``yf_client`` shim — new code should prefer the
    canonical shapes (ADR 0011).
Design rules:
  - CONSTRAINT: every public function calls ``yf_throttle()`` before each
    yfinance call — see docs/decisions/0005-token-bucket-throttle.md.
  - WHY (no caching here): caching is the caller's concern (e.g. ``app.py``
    option-chain cache, ``DataService`` 60s freshness window).
  - WHY (never raise on transient failure): callers receive an empty DataFrame
    and decide how to surface the error. Raising here would cascade into
    unhandled 500s from many different routes.
  - INVARIANT: returns plain Python types (float / DataFrame), never
    yfinance-specific objects — keeps the rest of the pipeline mockable.
  - CONSTRAINT: never pass ``session=requests.Session()`` — yfinance ≥0.2.50 uses
    curl_cffi and silently fails (ADR 0005 / docs/constraints.md §2).
Dependencies UPWARD:
  - utils.network (throttle), data_pipeline.store.quality_log (via providers._log)
Dependencies DOWNWARD:
  - providers/base, providers/_log, providers/yf_snapshot
"""

from __future__ import annotations

import datetime as dt
import logging
import time

import pandas as pd
import yfinance as yf

from data_pipeline.providers._log import _log_dq
from data_pipeline.providers.base import CANONICAL_BAR_COLUMNS, OptionChainSnapshot
from data_pipeline.providers.yf_snapshot import fetch_option_chain, fetch_spot, to_option_chain_snapshot
from utils.network import yf_throttle

logger = logging.getLogger(__name__)


# WHY: yfinance's Title-Case columns (as returned by ``yf.download``) mapped onto
# the canonical lowercase schema. ``Adj Close`` arrives with a space from
# ``yf.download`` and as ``Adj_Close`` from the test fixtures / upsert path.
_YF_TO_CANONICAL = {
    "Open": "open",
    "High": "high",
    "Low": "low",
    "Close": "close",
    "Adj Close": "adj_close",
    "Adj_Close": "adj_close",
    "Volume": "volume",
}


# ---------------------------------------------------------------------------
# Close-only panel (used by correlation matrix and market review)
# ---------------------------------------------------------------------------
def fetch_close_panel(
    tickers: list[str],
    period: str | None = "90d",
    *,
    start: str | None = None,
    end: str | None = None,
    max_retries: int = 2,
    retry_base_delay: float = 3.0,
) -> pd.DataFrame:
    """Return a wide DataFrame of Close prices for ``tickers``.

    Either pass ``period`` (e.g. ``"90d"``, ``"400d"``) OR ``start``/``end``
    date strings — when ``start`` is provided it takes precedence. On failure
    returns an empty DataFrame. One yfinance call total (yfinance natively
    supports multi-ticker download).

    WHY (retry loop): Yahoo occasionally returns an empty payload on the first
    call after a wake-from-sleep; one retry resolves it without escalating.
    """
    if not tickers:
        return pd.DataFrame()
    if start is not None:
        kwargs = {"start": start, "end": end}
    else:
        kwargs = {"period": period or "90d"}
    last_err: Exception | None = None
    for attempt in range(max_retries):
        try:
            yf_throttle()
            data = yf.download(tickers, auto_adjust=False, progress=False, **kwargs)
            if data is None or data.empty:
                if attempt < max_retries - 1:
                    logger.warning(
                        "fetch_close_panel empty payload, retrying in %.1fs (attempt %d)",
                        retry_base_delay * (attempt + 1),
                        attempt + 1,
                    )
                    time.sleep(retry_base_delay * (attempt + 1))
                    continue
                return pd.DataFrame()
            if isinstance(data.columns, pd.MultiIndex):
                if "Close" not in data.columns.get_level_values(0):
                    return pd.DataFrame()
                close = data["Close"]
                if isinstance(close.columns, pd.MultiIndex):
                    close.columns = close.columns.droplevel(1)
            else:
                if "Close" not in data.columns:
                    return pd.DataFrame()
                close = data[["Close"]]
            return close
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            is_rate_limit = "rate" in str(exc).lower() or "too many" in str(exc).lower()
            if is_rate_limit and attempt < max_retries - 1:
                time.sleep(retry_base_delay * (attempt + 1))
                continue
            break
    if last_err is not None:
        logger.warning("fetch_close_panel failed for %s: %s", tickers, last_err)
        is_rate_limit = "rate" in str(last_err).lower() or "too many" in str(last_err).lower()
        _log_dq(
            "yf_client.fetch_close_panel",
            "rate_limited" if is_rate_limit else "download_error",
            str(last_err),
            ticker=",".join(tickers),
        )
    return pd.DataFrame()


# ---------------------------------------------------------------------------
# Daily OHLCV
# ---------------------------------------------------------------------------
def fetch_daily_ohlcv(
    ticker: str,
    start,
    end,
    *,
    auto_adjust: bool = False,
    max_retries: int = 2,
    retry_base_delay: float = 3.0,
) -> pd.DataFrame:
    """Download daily OHLCV bars for ``ticker`` in ``[start, end)``.

    Returns a DataFrame indexed by Date with columns
    ``[Open, High, Low, Close, Adj Close, Volume]``. Empty DataFrame on
    failure. Includes simple retry loop for transient empty responses.
    """
    last_err: Exception | None = None
    for attempt in range(max_retries):
        try:
            yf_throttle()
            df = yf.download(
                ticker,
                start=start,
                end=end,
                interval="1d",
                progress=False,
                auto_adjust=auto_adjust,
            )
            if df is None or df.empty:
                if attempt < max_retries - 1:
                    time.sleep(retry_base_delay * (attempt + 1))
                    continue
                return pd.DataFrame()
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(1)
            df.index = pd.DatetimeIndex(df.index)
            return df
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            is_rate_limit = "rate" in str(exc).lower() or "too many" in str(exc).lower()
            if is_rate_limit and attempt < max_retries - 1:
                time.sleep(retry_base_delay * (attempt + 1))
                continue
            break
    if last_err is not None:
        logger.warning("fetch_daily_ohlcv failed for %s: %s", ticker, last_err)
        is_rate_limit = "rate" in str(last_err).lower() or "too many" in str(last_err).lower()
        _log_dq(
            "yf_client.fetch_daily_ohlcv",
            "rate_limited" if is_rate_limit else "download_error",
            str(last_err),
            ticker=ticker,
        )
    return pd.DataFrame()


def download_daily_frame(ticker: str, start: dt.date, end: dt.date) -> pd.DataFrame:
    """Download daily OHLCV for ``[start, end]`` (inclusive) from yfinance.

    Returns a frame with Title-Case columns plus ``Adj_Close`` — the shape
    ``data_pipeline.ingest.ohlcv.upsert_raw_prices`` consumes. ``history()`` on
    ``YFinanceProvider`` is the canonical equivalent.
    """
    # yfinance 'end' is exclusive, so pass end + 1 day to include the requested end date
    yf_end = end + dt.timedelta(days=1)
    yf_throttle()
    df = yf.download(ticker, start=start, end=yf_end, interval="1d", progress=False, auto_adjust=False)
    if df is None or df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
    cols = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]
    for c in cols:
        if c not in df.columns:
            df[c] = pd.NA
    return df[cols].rename(columns={"Adj Close": "Adj_Close"})


# ---------------------------------------------------------------------------
# Canonical mapping
# ---------------------------------------------------------------------------
def to_canonical_bars(frame: pd.DataFrame | None) -> pd.DataFrame:
    """Map a yfinance OHLCV frame onto the canonical lower-case schema."""
    if frame is None or frame.empty:
        return pd.DataFrame(columns=list(CANONICAL_BAR_COLUMNS))
    out = pd.DataFrame(index=pd.DatetimeIndex(frame.index))
    for source, target in _YF_TO_CANONICAL.items():
        if source in frame.columns:
            out[target] = pd.to_numeric(frame[source], errors="coerce")
    for col in CANONICAL_BAR_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA
    return out[list(CANONICAL_BAR_COLUMNS)].sort_index()


# ---------------------------------------------------------------------------
# Provider implementation
# ---------------------------------------------------------------------------
class YFinanceProvider:
    """yfinance implementation of ``MarketDataProvider`` (the only one today)."""

    name = "yfinance"

    def history(self, symbol: str, start: dt.date, end: dt.date) -> pd.DataFrame:
        """Canonical daily bars for ``[start, end]`` (inclusive)."""
        return to_canonical_bars(download_daily_frame(symbol, start, end))

    def close_panel(
        self,
        symbols: list[str],
        *,
        start: dt.date | str | None = None,
        end: dt.date | str | None = None,
        period: str | None = None,
    ) -> pd.DataFrame:
        """Wide Close-price panel for ``symbols``."""
        return fetch_close_panel(symbols, period or "90d", start=start, end=end)

    def spot(self, symbol: str) -> float | None:
        """Latest traded price for ``symbol``."""
        return fetch_spot(symbol)

    def option_chain(self, symbol: str) -> OptionChainSnapshot:
        """Canonical live option-chain snapshot for ``symbol``."""
        return to_option_chain_snapshot(fetch_option_chain(symbol), provider=self.name)
