"""Error-fragment helpers for the streaming /render/* endpoints.

Domain:    Utils — Render Helpers
Context:
  - Pure HTML builders for the async-state contract. No request handling, no
    service access, no data access.
  - WHY: utils is a leaf layer. The slice-dispatch logic that used to live here
    needed Flask, the job cache and two service facades, which made utils
    depend *upward* on services; it now lives in ``services/market/dispatch.py``.
Contracts:
  - render_error_fragment(kind, message, status, recovery) -> tuple[str, int]
Dependencies UPWARD:
  - (none — stdlib only)
Dependencies DOWNWARD:
  - services/market/dispatch.py
"""

from __future__ import annotations


def render_error_fragment(kind: str, message: str, status: int = 500, recovery: bool = True) -> tuple[str, int]:
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
        f"<p>Failed to render {kind.replace('_', ' ')}: {message}</p>"
        f"{recovery_html}"
        f"</div></div>"
    )
    return html, status
