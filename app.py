"""OptionLab Flask application — Thin Adapter entry-point.

This module is intentionally thin.  All route logic lives in ``routes/``
blueprints; all business logic lives in ``core/`` and ``services/``.
"""

from __future__ import annotations

import atexit
import logging
import os

from dotenv import load_dotenv
from flask import Flask

from data_pipeline.orchestrate.scheduler import UpdateScheduler, acquire_scheduler_lock
from data_pipeline.read import DataService
from utils.network import init_yf_proxy

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
# middleware rewrites the path before Flask's router matches it.
class _ApiV1AliasMiddleware:
    def __init__(self, wsgi):
        self.wsgi = wsgi

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "")
        if path.startswith("/api/v1/"):
            environ["PATH_INFO"] = "/api/" + path[len("/api/v1/") :]
        return self.wsgi(environ, start_response)


app.wsgi_app = _ApiV1AliasMiddleware(app.wsgi_app)


# ── Rate limiting — global per-IP throttle defending this process (not the
# Yahoo upstream; that one lives in utils/network.py::yf_throttle).
# Implemented in-house so 429s use the same JSON envelope as every other API
# error. Disabled by setting RATE_LIMIT_DISABLED=1 (e.g. in tests).
from utils.rate_limit import install as _install_rate_limit  # noqa: E402

_install_rate_limit(app)

# Propagate YF_PROXY → HTTP_PROXY/HTTPS_PROXY for curl_cffi (used by yfinance)
init_yf_proxy()

# Initialize DB
DataService.initialize()
_scheduler = None
# APScheduler is imported lazily inside UpdateScheduler, so a missing package
# only matters when the operator actually asked for auto-updates.
_scheduler_lock_handle = acquire_scheduler_lock() if os.environ.get("AUTO_UPDATE_TICKERS", "").strip() else None
try:
    auto_update = os.environ.get("AUTO_UPDATE_TICKERS", "").strip()
    if auto_update and _scheduler_lock_handle is not None:
        tickers = [t.strip().upper() for t in auto_update.split(",") if t.strip()]
        if tickers:
            _scheduler = UpdateScheduler()
            _scheduler.start_daily_update(tickers)
            _scheduler.start_monthly_correlation_update(tickers)
            logger.info("Auto-update scheduler started for: %s", tickers)
            logger.info("Monthly correlation update scheduler started for: %s", tickers)
    elif auto_update and _scheduler_lock_handle is None:
        logger.info("Skipping scheduler init — leader lock held by another worker.")
except ModuleNotFoundError as e:
    logger.warning("Auto-update scheduler disabled — %s", e)
except Exception as e:
    logger.warning("Scheduler init failed: %s", e)

if _scheduler is not None:
    atexit.register(lambda: _scheduler.scheduler.shutdown(wait=False))


# ── Register Blueprints ────────────────────────────────────────────────────
from routes import (  # noqa: E402
    core_bp,
    data_bp,
    market_bp,
    options_bp,
    portfolio_bp,
    regime_bp,
    strategies_bp,
)

app.register_blueprint(core_bp)
app.register_blueprint(options_bp)
app.register_blueprint(portfolio_bp)
app.register_blueprint(strategies_bp)
app.register_blueprint(market_bp)
app.register_blueprint(regime_bp)
app.register_blueprint(data_bp)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    # WHY: bind address via the HOST env var (default 0.0.0.0 for LAN access).
    # Binding to 0.0.0.0 makes werkzeug's HTTPServer.server_bind call
    # socket.getfqdn, which does a reverse-DNS lookup — on a flaky network
    # (hotspot / dead proxy) this can block startup for 10s+ per resolver
    # timeout. Bind to 127.0.0.1 (resolved via /etc/hosts, no DNS) for
    # instant local startup.
    # CONSTRAINT: Werkzeug's debugger (/console) can execute arbitrary Python.
    # Never enable it implicitly on a 0.0.0.0 bind — opt in via FLASK_DEBUG.
    host = os.environ.get("HOST", "0.0.0.0").strip() or "0.0.0.0"
    debug = os.environ.get("FLASK_DEBUG", "").strip().lower() in ("1", "true", "yes")
    app.run(host=host, port=port, debug=debug)
