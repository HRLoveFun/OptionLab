"""Form parsing + default-injection service.

Context:
- Centralises the rules that translate raw HTML form payloads into typed
  parameters with project defaults applied. Keeps Flask routes free of
  ad-hoc parsing logic.
"""

import logging

from utils.constants import (
    DEFAULT_FREQUENCY,
    DEFAULT_RISK_THRESHOLD,
    DEFAULT_ROLLING_WINDOW,
    DEFAULT_SIDE_BIAS,
)
from utils.date_helpers import parse_month_str

logger = logging.getLogger(__name__)


class FormService:
    """
    Service for handling form data extraction and processing from Flask request.
    - extract_form_data: Extracts and parses all dashboard form fields.
    - extract_modules: Modules the client asked for (readiness planning).
    - extract_module_params: One module's own query args → partial form_data.
    """

    @staticmethod
    def extract_modules(request) -> list[str]:
        """Return the module tokens the client requested (ADR 0012 / batch B5).

        Accepts either repeated fields (``modules=market_review&modules=statistical``)
        or one comma-separated value. Unknown tokens are dropped rather than
        rejected: an unrecognised module simply has no datasets to plan, and
        failing the whole submit for a typo would be hostile.

        WHY default to every known module: the frontend does not send this field
        until batch B7, and the streaming tabs are rendered unconditionally — so
        "everything" is the honest interpretation of a request that omits it.
        """
        from data_pipeline.orchestrate.readiness import ALL_MODULES

        raw = request.form.getlist("modules")
        tokens: list[str] = []
        for item in raw:
            tokens.extend(part.strip() for part in item.split(",") if part.strip())
        if not tokens:
            return list(ALL_MODULES)
        known = [t for t in tokens if t in ALL_MODULES]
        unknown = sorted(set(tokens) - set(ALL_MODULES))
        if unknown:
            logger.warning("extract_modules: ignoring unknown module token(s) %s", unknown)
        # De-duplicate while preserving the caller's order.
        return list(dict.fromkeys(known))

    #: Module token → the query args its own toolbar sends (batch B7 / §8 Q1).
    #: INVARIANT: `/render/<kind>` reads only these keys, so a hand-crafted query
    #: string cannot inject arbitrary keys into the slice's form_data.
    MODULE_PARAM_KEYS: dict[str, tuple[str, ...]] = {
        "market_review": ("from", "to"),
        "statistical": ("from", "to", "frequency"),
        "assessment": (
            "from",
            "to",
            "frequency",
            "side_bias",
            "risk_threshold",
            "rolling_window",
            "account_size",
            "max_risk_pct",
        ),
        # The volatility slice needs the ticker only; its chain comes live.
        "options_chain": (),
    }

    _FREQUENCIES = ("D", "W", "ME", "QE")

    @staticmethod
    def extract_module_params(module: str, args) -> dict:
        """Parse one module's own query args into a partial ``form_data``.

        Only the keys declared in ``MODULE_PARAM_KEYS[module]`` are read. Blank or
        malformed values are skipped rather than defaulted, so a missing param
        falls back to whatever the job recorded at POST time.
        """
        out: dict = {}
        for key in FormService.MODULE_PARAM_KEYS.get(module, ()):
            raw = args.get(key)
            if raw is None or str(raw).strip() == "":
                continue
            text = str(raw).strip()
            if key == "from":
                parsed = parse_month_str(text)
                if parsed is not None:
                    out["start_time"] = text
                    out["parsed_start_time"] = parsed
            elif key == "to":
                out["end_time"] = text
                out["parsed_end_time"] = parse_month_str(text)
            elif key == "frequency":
                if text in FormService._FREQUENCIES:
                    out["frequency"] = text
            elif key == "side_bias":
                out["side_bias"] = text
                out["target_bias"] = None if text == "Natural" else 0
            elif key in ("risk_threshold", "rolling_window"):
                try:
                    out[key] = int(text)
                except (TypeError, ValueError):
                    pass
            elif key in ("account_size", "max_risk_pct"):
                try:
                    out[key] = float(text)
                except (TypeError, ValueError):
                    pass
        return out

    @staticmethod
    def extract_form_data(request):
        """
        Extract and process form data from request.
        Accepts futu-format (US.NVDA) or yahoo-format (NVDA) tickers.
        Normalizes ticker to yahoo format for data pipeline consumption.
        Args:
            request (flask.Request): Incoming request
        Returns:
            dict: Parsed form data (ticker, frequency, start_time/end_time, etc.)
        """
        raw_ticker = request.form.get("ticker", "").upper()
        # normalize_ticker handled in app.py parse_tickers for multi-ticker;
        # here we just pass through the raw value for parse_tickers to handle
        ticker = raw_ticker
        frequency = request.form.get("frequency", DEFAULT_FREQUENCY)
        start_time = request.form.get("start_time", "")
        end_time = request.form.get("end_time", "")

        parsed_start_time = parse_month_str(start_time)
        parsed_end_time = parse_month_str(end_time) if end_time else None

        # Apply defaults when fields are blank
        rt_raw = request.form.get("risk_threshold", "")
        rw_raw = request.form.get("rolling_window", "")

        try:
            risk_threshold = int(rt_raw) if str(rt_raw).strip() != "" else DEFAULT_RISK_THRESHOLD
        except (ValueError, TypeError):
            risk_threshold = DEFAULT_RISK_THRESHOLD

        try:
            rolling_window = int(rw_raw) if str(rw_raw).strip() != "" else DEFAULT_ROLLING_WINDOW
        except (ValueError, TypeError):
            rolling_window = DEFAULT_ROLLING_WINDOW
        side_bias = request.form.get("side_bias", DEFAULT_SIDE_BIAS)
        target_bias = None if side_bias == "Natural" else 0

        # Position sizing (optional)
        acct_raw = request.form.get("account_size", "").strip()
        risk_raw = request.form.get("max_risk_pct", "").strip()
        account_size = None
        max_risk_pct = None
        if acct_raw:
            try:
                account_size = float(acct_raw)
            except (ValueError, TypeError):
                pass
        if risk_raw:
            try:
                max_risk_pct = float(risk_raw)
            except (ValueError, TypeError):
                pass

        return {
            "ticker": ticker,
            "frequency": frequency,
            "start_time": start_time,
            "end_time": end_time,
            "parsed_start_time": parsed_start_time,
            "parsed_end_time": parsed_end_time,
            "risk_threshold": risk_threshold,
            "rolling_window": rolling_window,
            "side_bias": side_bias,
            "target_bias": target_bias,
            "account_size": account_size,
            "max_risk_pct": max_risk_pct,
        }
