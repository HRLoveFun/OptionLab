import atexit
import datetime as dt
import logging
import os
import re

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from data_pipeline.data_ops import DataService
from data_pipeline.db import close_thread_conn
from data_pipeline.job_cache import compute_or_get, create_job, get_job
from data_pipeline.scheduler import UpdateScheduler, acquire_scheduler_lock
from services.market_analysis import AnalysisService
from services.form_service import FormService
from services.market_service import MarketService
from services.options_chain_service import OptionsChainService
from services.validation_service import ValidationService
from utils.ticker_utils import normalize_ticker
from utils.utils import (
    DEFAULT_FREQUENCY,
    DEFAULT_RISK_THRESHOLD,
    DEFAULT_ROLLING_WINDOW,
    DEFAULT_SIDE_BIAS,
    DEFAULT_TICKER,
    init_yf_proxy,
)

load_dotenv()


app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Install unified error envelope (ApiError → JSON, /api/* 404 → JSON, etc.)
from utils.api_errors import install as _install_error_handlers  # noqa: E402

_install_error_handlers(app)


# `/api/v1/...` is an alias for legacy `/api/...`. Routes are still defined
# without the v1 prefix so existing tests / frontend keep working; this WSGI
# middleware rewrites the path before Flask's router matches it. When
# breaking changes are needed, define a new route at the explicit
# `/api/v2/...` path.
class _ApiV1AliasMiddleware:
    def __init__(self, wsgi):
        self.wsgi = wsgi

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "")
        if path.startswith("/api/v1/"):
            environ["PATH_INFO"] = "/api/" + path[len("/api/v1/") :]
        return self.wsgi(environ, start_response)


app.wsgi_app = _ApiV1AliasMiddleware(app.wsgi_app)


# ── In-memory rate limiter (token bucket) ────────────────────────
# WHY: yfinance-quota-burning routes (regime/backfill, manual update)
# can be triggered by an unauthenticated POST. Without a limiter, a
# scripted attacker can drain the daily Yahoo quota in seconds. This
# is a simple per-IP counter — adequate for a single-machine personal
# project; for multi-process production use a proper limiter (Redis
# or flask-limiter).
import threading as _rl_threading
import time as _rl_time

_rate_buckets: dict = {}
_rate_lock = _rl_threading.Lock()


def _rate_limit(key: str, max_calls: int, window_sec: int) -> tuple[bool, int]:
    """Allow up to ``max_calls`` per ``window_sec`` per key.

    Returns ``(allowed, retry_after_seconds)``. When throttled, retry_after
    is the number of seconds until the oldest call in the window expires.
    """
    now = _rl_time.monotonic()
    with _rate_lock:
        bucket = _rate_buckets.get(key, [])
        # Drop expired entries
        bucket = [t for t in bucket if (now - t) < window_sec]
        if len(bucket) >= max_calls:
            retry = int(window_sec - (now - bucket[0])) + 1
            _rate_buckets[key] = bucket
            return False, max(1, retry)
        bucket.append(now)
        _rate_buckets[key] = bucket
    return True, 0


def _client_ip() -> str:
    fwd = request.headers.get("X-Forwarded-For", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.remote_addr or "unknown"


@app.route("/api/_meta", methods=["GET"])
def api_v1_meta():
    """Lightweight discovery endpoint listing v1-stable routes.

    Reachable at both ``/api/_meta`` and ``/api/v1/_meta``.
    """
    return jsonify(
        {
            "status": "ok",
            "version": "v1",
            "routes": sorted(
                {
                    r.rule
                    for r in app.url_map.iter_rules()
                    if r.rule.startswith("/api/")
                }
            ),
        }
    )

# Rate limiting — defends Yahoo upstream and the local box from abusive
# clients. Disabled by setting RATE_LIMIT_DISABLED=1 (e.g. in tests).
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address

    if os.environ.get("RATE_LIMIT_DISABLED", "").strip() not in ("1", "true", "yes"):
        _default = os.environ.get("RATE_LIMIT_DEFAULT", "120 per minute")
        limiter = Limiter(
            key_func=get_remote_address,
            app=app,
            default_limits=[_default],
            storage_uri=os.environ.get("RATE_LIMIT_STORAGE", "memory://"),
        )
        logger.info("Rate limiter enabled: default=%s", _default)
    else:
        limiter = None
        logger.info("Rate limiter disabled via RATE_LIMIT_DISABLED")
except ImportError:
    limiter = None
    logger.warning("flask-limiter not installed; running without rate limiting")

# Propagate YF_PROXY → HTTP_PROXY/HTTPS_PROXY for curl_cffi (used by yfinance)
init_yf_proxy()

# Initialize DB
DataService.initialize()
_scheduler = None
# Hold the scheduler leader lock for the lifetime of this process. Under
# gunicorn --workers N this ensures only one worker actually runs the
# APScheduler triggers; the others quietly skip scheduler init.
_scheduler_lock_handle = acquire_scheduler_lock() if os.environ.get("AUTO_UPDATE_TICKERS", "").strip() else None
try:
    auto_update = os.environ.get("AUTO_UPDATE_TICKERS", "").strip()
    if auto_update and _scheduler_lock_handle is not None:
        tickers = [t.strip().upper() for t in auto_update.split(",") if t.strip()]
        if tickers:
            _scheduler = UpdateScheduler()
            _scheduler.start_daily_update(tickers)
            _scheduler.start_monthly_correlation_update(tickers)
            logger.info(f"Auto-update scheduler started for: {tickers}")
            logger.info(f"Monthly correlation update scheduler started for: {tickers}")
    elif auto_update and _scheduler_lock_handle is None:
        logger.info("Skipping scheduler init — leader lock held by another worker.")
except Exception as e:
    logger.warning(f"Scheduler init failed: {e}")

if _scheduler is not None:
    atexit.register(lambda: _scheduler.scheduler.shutdown(wait=False))


def parse_tickers(raw: str) -> list[str]:
    """Parse comma/newline separated tickers, deduplicate, max 6.

    Accepts both futu-format (US.NVDA) and yahoo-format (NVDA).
    Normalizes all to yahoo format for data pipeline consumption.
    """
    raw_parts = [t.strip().upper() for t in re.split(r"[,\n]+", raw) if t.strip()]
    tickers = []
    for t in raw_parts:
        try:
            yahoo, _futu = normalize_ticker(t)
            if yahoo and yahoo not in tickers:
                tickers.append(yahoo)
        except ValueError:
            # Skip invalid tickers silently
            logger.warning(f"Skipping invalid ticker: {t}")
    return tickers[:6]


def _filter_option_chain(
    result: dict, max_dte: int = 60, moneyness_low: float = 0.7, moneyness_high: float = 1.3, max_contracts: int = 1000
) -> dict:
    """Filter option chain result by DTE, moneyness range, and total contract count.

    If total contracts exceed max_contracts after DTE + moneyness filtering,
    progressively narrow the moneyness range until count ≤ max_contracts.
    """
    from datetime import datetime

    spot = result.get("spot")
    chain = result.get("chain", {})
    expirations = result.get("expirations", [])

    today = datetime.now().date()

    # Step 1: Filter expirations by DTE (always applies, does not need spot)
    filtered_exps = []
    for exp in expirations:
        try:
            exp_date = datetime.strptime(exp, "%Y-%m-%d").date()
            dte = (exp_date - today).days
            if 0 <= dte <= max_dte:
                filtered_exps.append(exp)
        except (ValueError, TypeError):
            continue

    # If spot is missing, skip moneyness filter — just apply DTE filter
    if not spot or spot <= 0:
        filtered_chain = {exp: chain[exp] for exp in filtered_exps if exp in chain}
        final_exps = [exp for exp in filtered_exps if exp in filtered_chain]
        return {
            "expirations": final_exps,
            "chain": filtered_chain,
            "spot": spot,
        }

    # Step 2: Filter by moneyness range
    def _filter_by_moneyness(chain_data, exps, m_low, m_high):
        filtered_chain = {}
        total_count = 0
        for exp in exps:
            if exp not in chain_data:
                continue
            exp_data = chain_data[exp]
            low_strike = spot * m_low
            high_strike = spot * m_high

            filtered_calls = [
                r for r in exp_data.get("calls", []) if r.get("strike") and low_strike <= r["strike"] <= high_strike
            ]
            filtered_puts = [
                r for r in exp_data.get("puts", []) if r.get("strike") and low_strike <= r["strike"] <= high_strike
            ]

            if filtered_calls or filtered_puts:
                filtered_chain[exp] = {"calls": filtered_calls, "puts": filtered_puts}
                total_count += len(filtered_calls) + len(filtered_puts)
        return filtered_chain, total_count

    filtered_chain, total_count = _filter_by_moneyness(chain, filtered_exps, moneyness_low, moneyness_high)

    # Step 3: If over max_contracts, progressively narrow moneyness
    if total_count > max_contracts:
        step = 0.05
        m_low = moneyness_low
        m_high = moneyness_high
        while total_count > max_contracts and (m_high - m_low) > 0.1:
            m_low += step
            m_high -= step
            filtered_chain, total_count = _filter_by_moneyness(chain, filtered_exps, m_low, m_high)
            logger.info(f"Narrowed moneyness to [{m_low:.2f}, {m_high:.2f}], contracts: {total_count}")

    # Build filtered expirations list (only those with data)
    final_exps = [exp for exp in filtered_exps if exp in filtered_chain]

    return {
        "expirations": final_exps,
        "chain": filtered_chain,
        "spot": spot,
    }


@app.route("/api/ping", methods=["GET"])
def api_ping():
    """Lightweight liveness probe used by the HTMX scaffold probe in index.html."""
    return jsonify({"ok": True})


@app.route("/", methods=["GET", "POST"])
def index():
    """
    Main dashboard route.

    GET:  render the empty form / skeleton.
    POST: validate form, register a JobCache entry, and immediately render the
          *skeleton* index.html with `streaming_mode=True`. Tab partials emit
          HTMX `hx-get="/render/<kind>?job=…&ticker=…"` placeholders that
          resolve in parallel after the browser receives the skeleton.

    No analysis runs in the POST handler — the time-to-first-byte is just the
    cost of form parsing + template rendering (well under 1s).
    """
    try:
        if request.method == "POST":
            # Extract and validate form data
            form_data = FormService.extract_form_data(request)
            validation_error = ValidationService.validate_input_data(form_data)

            if validation_error:
                return render_template("index.html", error=validation_error)

            # Parse multi-ticker input
            tickers_raw = form_data.get("ticker", "")
            tickers = parse_tickers(tickers_raw)
            if not tickers:
                return render_template("index.html", error="Please enter at least one ticker symbol.")

            # Register job and stream the skeleton. The render endpoints will
            # consume `form_data` from the JobCache when each tab loads.
            first_ticker = tickers[0]
            job_id = create_job({**form_data, "ticker": first_ticker}, tickers)

            template_data = {
                **form_data,
                "ticker": first_ticker,
                "tickers": tickers,
                "tickers_raw": ", ".join(tickers),
                "streaming_mode": True,
                "job_id": job_id,
                # Multi-ticker summary tab is computed on demand via its own
                # render endpoint (see /render/summary). Pass a flag so the
                # template knows whether to include the summary skeleton.
                "summary_pending": len(tickers) > 1,
            }
            return render_template("index.html", **template_data)

        return render_template(
            "index.html",
            ticker=DEFAULT_TICKER,
            tickers=[DEFAULT_TICKER],
            tickers_raw=DEFAULT_TICKER,
            start_time=(lambda today: f"{today.year - 5}-{today.month:02d}")(dt.date.today()),
            end_time="",
            frequency=DEFAULT_FREQUENCY,
            risk_threshold=DEFAULT_RISK_THRESHOLD,
            rolling_window=DEFAULT_ROLLING_WINDOW,
            side_bias=DEFAULT_SIDE_BIAS,
        )

    except Exception as e:
        logger.error(f"Unexpected error in main route: {e}", exc_info=True)
        return render_template("index.html", error=f"An unexpected error occurred: {str(e)}. Please try again.")


# ── HTMX streaming render endpoints ──────────────────────────────────────────
# Each endpoint returns an HTML *fragment* (no <html><body>) suitable for
# `hx-swap="outerHTML"`. They share form_data via the JobCache so duplicate
# triggers/refetches don't recompute.

_RENDER_KIND_SLICES = {
    # kind: (slice_fn_attr_name | None, fragment_template)
    # We store the attribute name (not the bound function) so that monkey-
    # patching AnalysisService methods in tests is honoured at call time.
    "market_review": ("generate_market_review_slice", "partials/fragments/market_review.html"),
    "statistical": ("generate_statistical_slice", "partials/fragments/statistical.html"),
    "assessment": ("generate_assessment_slice", "partials/fragments/assessment.html"),
    "options_chain": (None, "partials/fragments/options_chain.html"),  # special-cased below
}


def _render_error_fragment(kind: str, message: str, status: int = 500, recovery: bool = True) -> tuple[str, int]:
    """Uniform error fragment for any /render/* endpoint failure.

    The shape mirrors the empty-state block so styling matches the partials.
    When ``recovery`` is True, append a button that re-targets the user
    back to the home form so they can re-submit instead of being stuck.
    """
    recovery_html = (
        '<p style="margin-top:8px;">'
        '<a href="/" class="btn-link" style="color:#3b82f6;text-decoration:underline;">'
        '<i class="fas fa-arrow-left"></i> Return to form and re-submit'
        "</a></p>"
        if recovery
        else ""
    )
    html = (
        f'<div id="tab-{kind.replace("_", "-")}-content">'
        f'<div class="empty-state" style="color:#ef4444;">'
        f'<i class="fas fa-exclamation-circle empty-icon"></i>'
        f'<p>Failed to render {kind.replace("_", " ")}: {message}</p>'
        f"{recovery_html}"
        f"</div></div>"
    )
    return html, status


def _render_streaming_slice(kind: str):
    """Shared handler for /render/<kind>?job=…&ticker=….

    Looks up the job, dispatches to the slice fn, memoises the result in the
    JobCache, and renders the matching fragment template.

    WHY: When a user opens a /render/* URL directly (refresh, bookmark, copy
    link), there is no job in cache. Rather than show a dead-end error, we
    auto-create a job using DEFAULT_TICKER + default form params so the
    page is at least populated; users can then re-submit the form for a
    custom analysis.
    """
    job_id = request.args.get("job", "")
    ticker = (request.args.get("ticker", "") or "").upper()

    # WHY: missing job_id ⇒ direct access (refresh / bookmark / shared link).
    # Auto-bootstrap with default form params so the user lands on a
    # populated page instead of an error fragment. Fallback uses a synthetic
    # job entry held only for the duration of this request.
    fallback_form: dict | None = None
    if not job_id:
        from utils.utils import DEFAULT_TICKER as _DEF_T

        if not ticker:
            ticker = _DEF_T
        fallback_form = {
            "ticker": ticker,
            "frequency": DEFAULT_FREQUENCY,
            "start_time": "",
            "end_time": "",
            "parsed_start_time": dt.date.today() - dt.timedelta(days=365 * 2),
            "parsed_end_time": dt.date.today(),
            "rolling_window": DEFAULT_ROLLING_WINDOW,
            "risk_threshold": DEFAULT_RISK_THRESHOLD,
            "side_bias": DEFAULT_SIDE_BIAS,
            "target_bias": 0,
        }

    if not ticker:
        return _render_error_fragment(kind, "missing job or ticker", 400)

    job = None
    if fallback_form is None:
        job = get_job(job_id)
        if job is None:
            # Treat as a soft 200 so HTMX swaps a useful message instead of a
            # browser-default error toast — but include the job-expired hint so
            # the user knows to re-submit the form.
            return _render_error_fragment(
                kind, "session expired (job no longer cached); please re-submit the form", 200
            )

    slice_fn_name, template = _RENDER_KIND_SLICES[kind]

    # The form_data captured at POST time was for the first ticker. When the
    # user switches tickers via the sidebar we re-target by overriding
    # `ticker` in a per-call form_data copy.
    def _compute(form_data: dict) -> dict:
        # Worker-thread cleanup so we don't leak DB connections.
        try:
            local_form = {**form_data, "ticker": ticker}
            if kind == "options_chain":
                # Direct OptionsChainService call — no MarketAnalyzer needed.
                try:
                    return OptionsChainService.generate_options_chain_analysis(ticker) or {}
                except Exception as e:
                    logger.error("options_chain slice failed for %s: %s", ticker, e, exc_info=True)
                    return {"oc_error": str(e)}
            # Late-bind the slice attr so test monkey-patches are honoured.
            slice_fn = getattr(AnalysisService, slice_fn_name)
            return slice_fn(local_form)
        finally:
            close_thread_conn()

    try:
        if fallback_form is not None:
            # No job in cache — compute directly with the synthetic form.
            result = _compute(fallback_form)
        else:
            result = compute_or_get(job_id, ticker, kind, _compute)
    except KeyError:
        return _render_error_fragment(kind, "session expired", 200)
    except Exception as e:
        logger.error("/render/%s failed for ticker=%s: %s", kind, ticker, e, exc_info=True)
        return _render_error_fragment(kind, str(e), 500)

    # Build the template context. The fragment templates expect form-style
    # variables (frequency, start_time, etc.) so we merge job form_data with
    # the slice result.
    base_form = fallback_form if fallback_form is not None else (job.form_data or {})
    context = {**base_form, "ticker": ticker, **(result or {})}
    return render_template(template, **context)


@app.route("/render/market_review", methods=["GET"])
def render_market_review():
    return _render_streaming_slice("market_review")


@app.route("/render/statistical", methods=["GET"])
def render_statistical():
    return _render_streaming_slice("statistical")


@app.route("/render/assessment", methods=["GET"])
def render_assessment():
    return _render_streaming_slice("assessment")


@app.route("/render/options_chain", methods=["GET"])
def render_options_chain():
    return _render_streaming_slice("options_chain")


@app.route("/api/option_chain", methods=["GET"])
def option_chain():
    """
    API endpoint to fetch live option chain data via Yahoo Finance.
    Query params: ticker (required), max_dte (default 45),
                  moneyness_low (default 0.7), moneyness_high (default 1.3), max_contracts (default 1000)
    Response: { expirations: [...], chain: { date: { calls: [...], puts: [...] } }, spot: float }

    The route is intentionally thin: all heavy lifting (yfinance fetch,
    liquidity scoring, DataFrame -> records) is delegated to the
    `OptionsChainService.fetch_records` helper.
    """
    ticker_sym = request.args.get("ticker", "").strip().upper()
    if not ticker_sym:
        return jsonify({"status": "error", "code": "missing_ticker", "message": "ticker is required", "error": "ticker is required"}), 400

    try:
        ticker_sym, _ = normalize_ticker(ticker_sym)
    except ValueError:
        pass  # keep as-is

    max_dte = int(request.args.get("max_dte", 45))
    moneyness_low = float(request.args.get("moneyness_low", 0.7))
    moneyness_high = float(request.args.get("moneyness_high", 1.3))
    max_contracts = int(request.args.get("max_contracts", 1000))

    try:
        result = OptionsChainService.fetch_records(ticker_sym)
        if not result.get("expirations"):
            msg = f"No options available for {ticker_sym}"
            return jsonify({
                "status": "error",
                "code": "no_options",
                "message": msg,
                "error": msg,
            }), 404
        result = _filter_option_chain(result, max_dte, moneyness_low, moneyness_high, max_contracts)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error fetching option chain for {ticker_sym}: {e}", exc_info=True)
        msg = f"获取期权链失败: {str(e)}"
        return jsonify({
            "status": "error",
            "code": "option_chain_failed",
            "message": msg,
            "error": msg,
        }), 500


@app.route("/api/validate_ticker", methods=["POST"])
def validate_ticker():
    """
    API endpoint to validate ticker symbol.
    Request: JSON {"ticker": "AAPL"} or {"ticker": "US.AAPL"}
    Response: {"valid": true/false, "message": "..."}
    """
    try:
        data = request.get_json()
        raw_ticker = data.get("ticker", "").upper()

        if not raw_ticker:
            return jsonify({"valid": False, "message": "Please enter a ticker symbol"})

        yahoo_ticker, _futu = normalize_ticker(raw_ticker)
        is_valid, message = MarketService.validate_ticker(yahoo_ticker)

        return jsonify({"valid": is_valid, "message": message})

    except Exception as e:
        logger.error(f"Error validating ticker: {e}")
        return jsonify({"valid": False, "message": f"Error validating ticker: {str(e)}"})


# ── Module 0: Bulk ticker validation ──────────────────────────────
@app.route("/api/validate_tickers", methods=["POST"])
def validate_tickers_bulk():
    """Validate multiple tickers at once. Returns {status, results: {TICKER: {valid, price, message}}}.

    Accepts both futu-format (US.NVDA) and yahoo-format (NVDA) tickers.
    Results are keyed by the original input ticker for frontend mapping.
    """
    data = request.get_json(silent=True) or {}
    tickers = data.get("tickers", [])
    results = {}
    for raw_ticker in tickers[:10]:
        try:
            yahoo_ticker, _futu = normalize_ticker(raw_ticker)
            is_valid, message = MarketService.validate_ticker(yahoo_ticker)
            price = None
            if is_valid:
                try:
                    from data_pipeline.yf_client import fetch_spot

                    price = fetch_spot(yahoo_ticker)
                except Exception:
                    pass
            results[raw_ticker] = {"valid": is_valid, "price": price, "message": message}
        except Exception:
            results[raw_ticker] = {"valid": False, "price": None, "message": "validation error"}
    return jsonify({"status": "ok", "results": results})


# ── Module 1: Option chain preload & cache ────────────────────────
_option_chain_cache: dict = {}
CACHE_TTL_MINUTES = 15


@app.route("/api/preload_option_chain", methods=["POST"])
def preload_option_chain():
    """Pre-load option chain for Position module dropdowns."""
    data = request.get_json(silent=True) or {}
    raw_ticker = data.get("ticker", "").strip().upper()
    if not raw_ticker:
        return jsonify({"status": "error", "code": "missing_ticker", "message": "No ticker provided"}), 400

    # Normalize ticker to yahoo format
    try:
        ticker, _futu = normalize_ticker(raw_ticker)
    except ValueError:
        ticker = raw_ticker

    cached = _option_chain_cache.get(ticker)
    if cached:
        age = (dt.datetime.now() - cached["ts"]).total_seconds() / 60
        if age < CACHE_TTL_MINUTES:
            return jsonify({"status": "ok", **cached["data"]})

    try:
        from core.options_chain_analyzer import OptionsChainAnalyzer, _dte

        analyzer = OptionsChainAnalyzer(ticker)
        chain_out = {}
        for exp in analyzer.expiries:
            if exp not in analyzer.chain:
                continue
            calls_df = analyzer.chain[exp]["calls"]
            puts_df = analyzer.chain[exp]["puts"]

            def df_to_list(df, exp=exp):
                result = []
                for _, row in df.iterrows():
                    bid = float(row.get("bid", 0) or 0)
                    ask = float(row.get("ask", 0) or 0)
                    mid = (bid + ask) / 2 if bid > 0 and ask > 0 else float(row.get("lastPrice", 0) or 0)
                    result.append(
                        {
                            "strike": float(row["strike"]),
                            "bid": round(bid, 2),
                            "ask": round(ask, 2),
                            "mid": round(mid, 2),
                            "last": round(float(row.get("lastPrice", 0) or 0), 2),
                            "iv": round(float(row.get("impliedVolatility", 0) or 0), 4),
                            "iv_pct": round(float(row.get("impliedVolatility", 0) or 0) * 100, 1),
                            "oi": int(row.get("openInterest", 0) or 0),
                            "volume": int(row.get("volume", 0) or 0),
                            "dte": _dte(exp),
                        }
                    )
                return result

            chain_out[exp] = {
                "calls": df_to_list(calls_df),
                "puts": df_to_list(puts_df),
            }

        payload = {
            "ticker": analyzer.ticker,
            "spot": round(analyzer.spot, 2),
            "expiries": analyzer.expiries,
            "chain": chain_out,
        }
        _option_chain_cache[ticker] = {"ts": dt.datetime.now(), "data": payload}
        return jsonify({"status": "ok", **payload})

    except Exception as e:
        logger.error(f"preload_option_chain failed for {ticker}: {e}")
        return jsonify({"status": "error", "code": "option_chain_failed", "message": str(e)}), 500


# ── Module 3: Portfolio analysis  ─────────────────────────────────
@app.route("/api/portfolio_analysis", methods=["POST"])
def portfolio_analysis():
    """Analyse a multi-leg option portfolio."""
    data = request.get_json(silent=True) or {}
    positions = data.get("positions", [])
    account_size = data.get("account_size")
    max_risk_pct = data.get("max_risk_pct", 2.0)

    if not positions:
        return jsonify({"status": "error", "code": "no_positions", "message": "No positions provided"}), 400

    try:
        from services.portfolio_analysis import PortfolioAnalysisService

        result = PortfolioAnalysisService.run(positions, account_size, max_risk_pct)
        return jsonify(result)
    except Exception as e:
        logger.error(f"portfolio_analysis error: {e}", exc_info=True)
        return jsonify({"status": "error", "code": "portfolio_failed", "message": str(e)}), 500


# ── Multi-leg strategy analytics ──────────────────────────────────
@app.route("/api/strategies", methods=["GET"])
def list_strategies():
    """Return the catalog of supported multi-leg strategies."""
    from services.strategy_service import list_strategies as _list

    return jsonify({"status": "ok", "strategies": _list()})


@app.route("/api/strategy/analyze", methods=["POST"])
def analyze_strategy_route():
    """Analyse a multi-leg strategy: payoff, breakevens, Greeks, PoP.

    Body: ``{strategy: <name>, spot: float, params: {...}}``
    """
    data = request.get_json(silent=True) or {}
    try:
        from services.strategy_service import analyze

        return jsonify(analyze(data))
    except Exception as e:
        logger.error(f"analyze_strategy_route error: {e}", exc_info=True)
        return jsonify({"status": "error", "code": "strategy_failed", "message": str(e)}), 500


@app.route("/api/strategy/build_from_chain", methods=["POST"])
def build_strategy_from_chain():
    """Auto-fill a strategy template from the live option chain.

    Body: ``{ticker, template, expiry, strikes: {...}, qty?: int}``.
    Returns populated legs (with mid/bid/ask/IV/liquidity), full analytics,
    HV-based vol context, and slippage estimate.
    """
    from services.strategy_builder import build_from_chain

    data = request.get_json(silent=True) or {}
    raw_ticker = (data.get("ticker") or "").strip().upper()
    if not raw_ticker:
        from utils.api_errors import ApiError

        raise ApiError("ticker is required", code="ticker_required")
    try:
        ticker, _ = normalize_ticker(raw_ticker)
    except ValueError:
        ticker = raw_ticker
    return jsonify(
        build_from_chain(
            ticker=ticker,
            # WHY: Frontend code in static/ uses both `template` and `strategy`
            # interchangeably. Accept either rather than emitting a confusing
            # "unknown strategy template: " (empty string) error.
            template=(data.get("template") or data.get("strategy") or "").strip(),
            expiry=data.get("expiry", ""),
            strikes=data.get("strikes", {}) or {},
            qty=int(data.get("qty", 1) or 1),
        )
    )


# ── Portfolio: tracked positions, Greeks, P&L attribution ────────
@app.route("/api/portfolio/positions", methods=["GET", "POST"])
def portfolio_positions():
    """List open positions (GET) or create a new one (POST)."""
    from services.portfolio_service import create_position, list_positions

    if request.method == "POST":
        return jsonify(create_position(request.get_json(silent=True) or {}))
    status = request.args.get("status", "open") or None
    return jsonify({"status": "ok", "positions": list_positions(status=status)})


@app.route("/api/portfolio/positions/<int:position_id>/close", methods=["POST"])
def portfolio_close(position_id: int):
    from services.portfolio_service import close_position

    body = request.get_json(silent=True) or {}
    return jsonify(close_position(position_id, float(body.get("closed_value", 0.0))))


@app.route("/api/portfolio/snapshot", methods=["GET"])
def portfolio_snapshot_route():
    """Aggregate Greeks + per-position P&L attribution across all open positions."""
    from services.portfolio_service import portfolio_snapshot

    return jsonify(portfolio_snapshot())


# ── OHLCV-derived signals (HV, RSI, Bollinger, vol premium) ──────
@app.route("/api/signals", methods=["GET"])
def signals_route():
    raw_ticker = (request.args.get("ticker", "") or "").strip().upper()
    if not raw_ticker:
        return jsonify({"status": "error", "code": "missing_ticker", "message": "ticker is required"}), 400
    try:
        ticker, _ = normalize_ticker(raw_ticker)
    except ValueError:
        ticker = raw_ticker
    iv_pct = request.args.get("iv_pct")
    iv_pct_val = float(iv_pct) if iv_pct not in (None, "") else None
    try:
        from services.signals_service import get_signals

        return jsonify(get_signals(ticker, current_iv_pct=iv_pct_val))
    except Exception as e:
        logger.error(f"signals_route error: {e}", exc_info=True)
        return jsonify({"status": "error", "code": "signals_failed", "message": str(e)}), 500


# ── Data-quality health endpoint ──────────────────────────────────
@app.route("/health/data", methods=["GET"])
def health_data():
    """Return data-quality snapshot of the local SQLite cache.

    WHY: The full payload includes ticker names which can echo back
    historically-polluted strings. When ``HEALTH_TOKEN`` env var is set,
    require it as ``?token=`` or ``X-Health-Token`` header for the full
    payload; otherwise return only the public summary (status, counts,
    timestamps — no ticker names).
    """
    try:
        from services.health_service import overall_summary

        full = overall_summary()
        expected = os.environ.get("HEALTH_TOKEN", "").strip()
        provided = (request.args.get("token") or request.headers.get("X-Health-Token") or "").strip()
        if expected and provided != expected:
            # Public/redacted summary: keep counts and status, drop names.
            return jsonify({
                "status": full.get("status"),
                "generated_at": full.get("generated_at"),
                "ticker_count": full.get("ticker_count"),
                "total_rows": full.get("total_rows"),
                "stale_count": len(full.get("stale_tickers", [])),
                "nan_count": len(full.get("tickers_with_nan_close", [])),
                "failures_24h_total": sum(full.get("failures_24h_by_class", {}).values()),
                "freshness_threshold_days": full.get("freshness_threshold_days"),
                "redacted": True,
            })
        return jsonify(full)
    except Exception as e:
        logger.error(f"health_data error: {e}", exc_info=True)
        return jsonify({"status": "error", "code": "health_failed", "message": str(e)}), 500


@app.route("/health/status", methods=["GET"])
def health_status():
    """Public lightweight status endpoint for frontend degradation banner."""
    try:
        from services.health_service import overall_summary

        full = overall_summary()
        return jsonify({
            "status": full.get("status"),
            "stale_count": len(full.get("stale_tickers", [])),
            "nan_count": len(full.get("tickers_with_nan_close", [])),
            "failures_24h_total": sum(full.get("failures_24h_by_class", {}).values()),
            "generated_at": full.get("generated_at"),
        })
    except Exception as e:
        logger.error(f"health_status error: {e}", exc_info=True)
        return jsonify({"status": "error", "code": "health_failed", "message": str(e)}), 500


# ── JSON endpoints for client-side charts (IV smile, OI profile) ──
@app.route("/api/options_chart/iv_smile", methods=["GET"])
def iv_smile_json():
    """Return IV smile data points for client-side Chart.js rendering.

    Query: ``ticker`` (required), ``expiry`` (optional, default = nearest).
    """
    raw_ticker = (request.args.get("ticker", "") or "").strip().upper()
    if not raw_ticker:
        return jsonify({"status": "error", "code": "missing_ticker", "message": "ticker is required"}), 400
    try:
        ticker, _ = normalize_ticker(raw_ticker)
    except ValueError:
        ticker = raw_ticker
    expiry = request.args.get("expiry")
    try:
        from core.options_chain_analyzer import OptionsChainAnalyzer

        analyzer = OptionsChainAnalyzer(ticker)
        if not analyzer.expiries:
            return jsonify({"status": "error", "code": "no_expiries", "message": "no expiries"}), 404
        exp = expiry if expiry in analyzer.chain else analyzer.expiries[0]
        calls = analyzer.chain[exp]["calls"].dropna(subset=["impliedVolatility"])
        puts = analyzer.chain[exp]["puts"].dropna(subset=["impliedVolatility"])
        # WHY: Yahoo's reported IV for deep-ITM / deep-OTM contracts is
        # frequently nonsensical (e.g. 8.0 ⇒ 800%, or 0.000005 ⇒ 0.0005%).
        # Filter to a sane window so the chart isn't dominated by tail noise.
        # Range corresponds to 1%–500% annualised IV.
        _IV_LO, _IV_HI = 0.01, 5.0

        def _iv_ok(v):
            try:
                return _IV_LO <= float(v) <= _IV_HI
            except (TypeError, ValueError):
                return False

        calls = calls[calls["impliedVolatility"].apply(_iv_ok)]
        puts = puts[puts["impliedVolatility"].apply(_iv_ok)]
        return jsonify(
            {
                "status": "ok",
                "ticker": ticker,
                "expiry": exp,
                "spot": round(analyzer.spot, 2),
                "calls": [
                    {"strike": float(r.strike), "iv_pct": float(r.impliedVolatility) * 100}
                    for r in calls.itertuples()
                ],
                "puts": [
                    {"strike": float(r.strike), "iv_pct": float(r.impliedVolatility) * 100}
                    for r in puts.itertuples()
                ],
            }
        )
    except Exception as e:
        logger.error(f"iv_smile_json error: {e}", exc_info=True)
        return jsonify({"status": "error", "code": "iv_smile_failed", "message": str(e)}), 500


@app.route("/api/options_chart/oi_profile", methods=["GET"])
def oi_profile_json():
    """Return OI / Volume profile data for client-side rendering.

    Query: ``ticker`` (required), ``expiry`` (optional, default = nearest).
    """
    raw_ticker = (request.args.get("ticker", "") or "").strip().upper()
    if not raw_ticker:
        return jsonify({"status": "error", "code": "missing_ticker", "message": "ticker is required"}), 400
    try:
        ticker, _ = normalize_ticker(raw_ticker)
    except ValueError:
        ticker = raw_ticker
    expiry = request.args.get("expiry")
    try:
        from core.options_chain_analyzer import OptionsChainAnalyzer

        analyzer = OptionsChainAnalyzer(ticker)
        if not analyzer.expiries:
            return jsonify({"status": "error", "code": "no_expiries", "message": "no expiries"}), 404
        exp = expiry if expiry in analyzer.chain else analyzer.expiries[0]
        calls = analyzer.chain[exp]["calls"]
        puts = analyzer.chain[exp]["puts"]
        return jsonify(
            {
                "status": "ok",
                "ticker": ticker,
                "expiry": exp,
                "spot": round(analyzer.spot, 2),
                "calls": [
                    {
                        "strike": float(r.strike),
                        "oi": float(r.openInterest or 0),
                        "volume": float(r.volume or 0),
                    }
                    for r in calls.itertuples()
                ],
                "puts": [
                    {
                        "strike": float(r.strike),
                        "oi": float(r.openInterest or 0),
                        "volume": float(r.volume or 0),
                    }
                    for r in puts.itertuples()
                ],
            }
        )
    except Exception as e:
        logger.error(f"oi_profile_json error: {e}", exc_info=True)
        return jsonify({"status": "error", "code": "oi_profile_failed", "message": str(e)}), 500


# ── Module 4A: Market Review time-series ──────────────────────────
@app.route("/api/market_review_ts", methods=["POST"])
def market_review_ts():
    """Return time-series data for interactive Market Review chart."""
    data = request.get_json(silent=True) or {}
    raw_ticker = data.get("ticker", "").strip().upper()
    start_date = data.get("start_date")
    if not raw_ticker:
        return jsonify({"status": "error", "code": "missing_ticker", "message": "No ticker provided"}), 400
    try:
        ticker, _futu = normalize_ticker(raw_ticker)
    except ValueError:
        ticker = raw_ticker
    try:
        from core.market_review import market_review_timeseries

        result = market_review_timeseries(ticker, start_date=start_date)
        return jsonify({"status": "ok", **result})
    except Exception as e:
        logger.error(f"market_review_ts error: {e}", exc_info=True)
        return jsonify({"status": "error", "code": "market_review_failed", "message": str(e)}), 500


# ── Module 4B: Odds with vol context ─────────────────────────────
@app.route("/api/odds_with_vol", methods=["POST"])
def odds_with_vol():
    """Return odds data enriched with implied realized vol vs ATM IV."""
    data = request.get_json(silent=True) or {}
    raw_ticker = data.get("ticker", "").strip().upper()
    # WHY: target_pct is a DELTA in %, e.g. 5 ⇒ +5%. Default of 10 matches
    # the frontend input default in templates/partials/tab_odds.html.
    target_pct = float(data.get("target_pct", 10))
    if not raw_ticker:
        return jsonify({"status": "error", "code": "missing_ticker", "message": "No ticker provided"}), 400
    try:
        ticker, _futu = normalize_ticker(raw_ticker)
    except ValueError:
        ticker = raw_ticker
    try:
        from core.options_chain_analyzer import OptionsChainAnalyzer, get_odds_with_vol_context

        analyzer = OptionsChainAnalyzer(ticker)
        result = get_odds_with_vol_context(
            spot=analyzer.spot,
            target_pct=target_pct,
            chain=analyzer.chain,
            expiries=analyzer.expiries,
        )
        return jsonify({"status": "ok", **result})
    except Exception as e:
        logger.error(f"odds_with_vol error: {e}", exc_info=True)
        return jsonify({"status": "error", "code": "odds_failed", "message": str(e)}), 500


# ── Market Regime (Volatility × Direction labeling) ───────────────
@app.route("/api/regime/current", methods=["GET"])
def regime_current():
    """Current composite regime label (VIX / SPY)."""
    from services.regime_service import RegimeService

    persist = request.args.get("persist", "0").lower() in ("1", "true", "yes")
    try:
        result = (
            RegimeService.append_today() if persist else RegimeService.compute_current()
        )
        return jsonify({"status": "ok", **result})
    except Exception as e:
        logger.error(f"regime_current error: {e}", exc_info=True)
        return jsonify({"status": "error", "code": "regime_failed", "message": str(e)}), 500


@app.route("/api/regime/history", methods=["GET"])
def regime_history():
    """Regime history (persisted log, or live fallback if log is empty)."""
    from services.regime_service import RegimeService

    try:
        days = int(request.args.get("days", 180))
    except (TypeError, ValueError):
        days = 180
    # WHY: Without bounds an attacker can request days=-5 (returns empty
    # window with confusing ordering) or days=99999 (silently scans the
    # entire log table). Clamp to a sensible product range.
    days = max(1, min(days, 3650))
    try:
        result = RegimeService.history(days=days)
        return jsonify({"status": "ok", **result})
    except Exception as e:
        logger.error(f"regime_history error: {e}", exc_info=True)
        return jsonify({"status": "error", "code": "regime_history_failed", "message": str(e)}), 500


@app.route("/api/regime/backfill", methods=["POST"])
def regime_backfill():
    """Backfill regime log for the last N trading days."""
    from services.regime_service import RegimeService

    # WHY: yfinance-burning route — limit to 5 calls per IP per hour.
    allowed, retry = _rate_limit(f"backfill:{_client_ip()}", max_calls=5, window_sec=3600)
    if not allowed:
        return jsonify({
            "status": "error",
            "code": "rate_limited",
            "message": f"Too many backfill requests. Retry after {retry}s.",
            "retry_after": retry,
        }), 429

    data = request.get_json(silent=True) or {}
    try:
        days = int(data.get("days", 30))
    except (TypeError, ValueError):
        days = 30
    # Cap backfill window to keep yfinance traffic bounded.
    days = max(1, min(days, 365))
    try:
        result = RegimeService.backfill(days=days)
        return jsonify({"status": "ok", **result})
    except Exception as e:
        logger.error(f"regime_backfill error: {e}", exc_info=True)
        return jsonify({"status": "error", "code": "regime_backfill_failed", "message": str(e)}), 500


@app.route("/api/data/seed", methods=["POST"])
def data_seed():
    """Seed multi-year per-ticker price history.

    WHY: ensure_range's auto-backfill is capped at MAX_AUTO_BACKFILL_DAYS
    (~90d) per call and chunks longer ranges, which is fragile under
    yfinance rate-limit. This endpoint exposes DataService.seed_history
    so the user can populate years of history for a specific ticker in
    one bulk download — the correct remediation when the statistical
    analysis reports "DB only has {ticker} from X to Y".

    Body: {"ticker": "NVDA", "years": 5}
    """
    # WHY: yfinance-burning route — same 5/hour budget as regime/backfill.
    allowed, retry = _rate_limit(f"seed:{_client_ip()}", max_calls=5, window_sec=3600)
    if not allowed:
        return jsonify({
            "status": "error",
            "code": "rate_limited",
            "message": f"Too many seed requests. Retry after {retry}s.",
            "retry_after": retry,
        }), 429

    data = request.get_json(silent=True) or {}
    raw_ticker = (data.get("ticker") or "").strip()
    if not raw_ticker:
        return jsonify({
            "status": "error",
            "code": "invalid_ticker",
            "message": "Body must include non-empty 'ticker'.",
        }), 400
    try:
        # Normalise futu-format (US.NVDA → NVDA) to match clean_prices schema.
        yahoo_ticker, _ = normalize_ticker(raw_ticker)
        ticker = (yahoo_ticker or raw_ticker).upper()
    except (ValueError, ImportError):
        ticker = raw_ticker.upper()
    try:
        years = int(data.get("years", 5))
    except (TypeError, ValueError):
        years = 5
    # Cap years to keep yfinance traffic bounded; 1990 is the practical floor.
    years = max(1, min(years, 35))
    try:
        # WHY: clear any cached failure memo for this ticker so a previously
        # rate-limited backfill doesn't suppress the seed run.
        DataService.clear_ensure_range_memo(ticker)
        DataService.seed_history(ticker, years=years)
        return jsonify({"status": "ok", "ticker": ticker, "years": years})
    except Exception as e:
        logger.error(f"data_seed error for {ticker}: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "code": "seed_failed",
            "message": str(e),
        }), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=True)
