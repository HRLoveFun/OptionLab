"""Market review domain constants and pure helpers.

This module is I/O-free: it only carries the benchmark symbol table and a
trivial ticker→display-name mapping. The L1/L2/L3 cache ladder that turns
these symbols into a close-price panel lives in ``services.market_review``.
"""

from __future__ import annotations

BENCHMARKS = {
    "USD": "DX-Y.NYB",
    "US10Y": "^TNX",
    "Gold": "GC=F",
    "SPX": "^SPX",
    "CSI300": "000300.SS",
    "HSI": "^HSI",
    "NKY": "^N225",
    "STOXX": "^STOXX",
}


def _canonicalize_instrument(instrument: str) -> str:
    """Map a benchmark ticker back to its display name when applicable."""
    inverse = {v: k for k, v in BENCHMARKS.items()}
    return inverse.get(instrument, instrument)
