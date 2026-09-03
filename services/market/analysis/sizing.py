"""Position sizing calculation with full boundary handling."""

import numpy as np


def calculate_position_size(
    account_size: float, max_risk_pct: float, max_loss_per_contract: float, strategy_type: str
) -> dict | None:
    """Calculate position size with full boundary handling."""
    if not account_size or account_size <= 0:
        return None

    max_dollar_risk = account_size * (max_risk_pct / 100)

    if max_loss_per_contract is None or np.isinf(max_loss_per_contract):
        return {
            "max_contracts": None,
            "warning": "This portfolio has unlimited risk (naked short call). Add a hedge leg to calculate position limits.",
            "actual_risk": None,
        }

    abs_loss = abs(float(max_loss_per_contract))

    if abs_loss < 0.01:
        return {
            "max_contracts": None,
            "warning": "Max loss is near zero (pure premium collection). Position size is determined by margin requirements — consult your broker.",
            "actual_risk": None,
        }

    loss_per_contract = abs_loss * 100  # 1 contract = 100 shares

    max_contracts = max(1, int(max_dollar_risk / loss_per_contract))
    actual_risk = loss_per_contract * max_contracts

    margin_note = (
        "Credit spreads require margin — actual capital usage may exceed premium received. "
        "Check broker margin requirements."
        if strategy_type == "credit"
        else None
    )

    return {
        "max_contracts": max_contracts,
        "actual_risk": round(actual_risk, 2),
        "risk_pct": round(actual_risk / account_size * 100, 3),
        "margin_note": margin_note,
        "basis": f"Account ${account_size:,.0f} × {max_risk_pct}% risk / "
        f"${loss_per_contract:,.0f} max loss per contract",
    }
