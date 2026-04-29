"""Unified API error envelope.

Every JSON route should either:

* return a plain dict / response (treated as 200 OK), or
* raise :class:`ApiError` with a code, message, and HTTP status.

The Flask ``errorhandler`` registered in :mod:`app` translates ``ApiError``
into a uniform response shape so the frontend can rely on one error contract.

Response shape
--------------
``{"status": "error", "code": "<symbolic>", "message": "<human>", "details": {...}}``
"""

from __future__ import annotations

from typing import Any


class ApiError(Exception):
    """Structured API error.

    Parameters
    ----------
    message
        Human-readable message safe to show to end users.
    code
        Short symbolic identifier (e.g. ``"ticker_required"``,
        ``"yfinance_unavailable"``). Stable across versions; frontend may
        switch on it.
    status
        HTTP status code (default ``400``).
    details
        Optional structured payload echoed back to the client.
    """

    __slots__ = ("message", "code", "status", "details")

    def __init__(
        self,
        message: str,
        code: str = "bad_request",
        status: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status
        self.details = details or {}

    def to_payload(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "status": "error",
            "code": self.code,
            "message": self.message,
        }
        if self.details:
            out["details"] = self.details
        return out


def install(app) -> None:
    """Register error handlers on a Flask app.

    Catches both :class:`ApiError` and unhandled exceptions, returning a
    uniform JSON envelope. Non-API HTML routes are unaffected because the
    handler only fires for routes that raised — static templates render
    normally.
    """
    from flask import jsonify, request

    @app.errorhandler(ApiError)
    def _handle_api_error(err: ApiError):  # type: ignore[no-redef]
        return jsonify(err.to_payload()), err.status

    @app.errorhandler(404)
    def _handle_404(err):  # type: ignore[no-redef]
        # Only JSON-ify API paths; let HTML 404 fall through.
        if request.path.startswith("/api/"):
            return (
                jsonify(
                    {
                        "status": "error",
                        "code": "not_found",
                        "message": f"No route: {request.path}",
                    }
                ),
                404,
            )
        return err

    @app.errorhandler(Exception)
    def _handle_unexpected(err: Exception):  # type: ignore[no-redef]
        # Re-raise HTTPExceptions so Flask handles them normally.
        from werkzeug.exceptions import HTTPException

        if isinstance(err, HTTPException):
            return err
        app.logger.exception("Unhandled error: %s", err)
        if request.path.startswith("/api/"):
            return (
                jsonify(
                    {
                        "status": "error",
                        "code": "internal_error",
                        "message": str(err) or "internal server error",
                    }
                ),
                500,
            )
        raise err
