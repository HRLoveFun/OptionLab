"""Low-level helpers for option-chain row selection and pricing."""

import pandas as pd


def _row_for_strike(df: pd.DataFrame, strike: float) -> pd.Series | None:
    """Return the chain row whose strike is closest to ``strike`` (within $1)."""
    if df is None or df.empty or "strike" not in df.columns:
        return None
    diffs = (df["strike"] - strike).abs()
    idx = diffs.idxmin()
    if diffs.loc[idx] > 1.0:
        return None
    return df.loc[idx]


def _mid(bid: float | None, ask: float | None, last: float | None) -> float | None:
    """Mid of bid/ask; fall back to ``last`` only if both sides missing."""
    b = float(bid) if bid is not None and not pd.isna(bid) else None
    a = float(ask) if ask is not None and not pd.isna(ask) else None
    if b is not None and a is not None and b > 0 and a > 0:
        return (b + a) / 2.0
    if last is not None and not pd.isna(last) and float(last) > 0:
        return float(last)
    return None
