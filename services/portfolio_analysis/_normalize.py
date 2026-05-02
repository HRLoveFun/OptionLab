"""Position normalization: tolerate legacy keys and produce a strict schema."""


_OPT_TYPE_ALIASES = {
    "lc": "LC", "long_call": "LC", "buy_call": "LC",
    "sc": "SC", "short_call": "SC", "sell_call": "SC",
    "lp": "LP", "long_put": "LP", "buy_put": "LP",
    "sp": "SP", "short_put": "SP", "sell_put": "SP",
}


def _normalize_position(pos: dict) -> dict:
    """Accept legacy / colloquial keys and produce the strict schema.

    Strict schema: ticker, option_type ∈ {LC,SC,LP,SP}, strike, quantity, price
    Tolerated aliases:
      - kind/type + side/action → option_type
      - contracts → quantity
      - premium → price
    """
    if not isinstance(pos, dict):
        raise ValueError(f"position must be a dict, got {type(pos).__name__}")
    out = dict(pos)

    # option_type derivation
    if "option_type" not in out:
        kind = (out.get("kind") or out.get("type") or "").strip().lower()
        side = (out.get("side") or out.get("action") or "").strip().lower()
        combined = (out.get("opt_type") or "").strip().lower()
        if combined in _OPT_TYPE_ALIASES:
            out["option_type"] = _OPT_TYPE_ALIASES[combined]
        elif kind and side:
            key = f"{side}_{kind}"  # e.g. "buy_call"
            if key in _OPT_TYPE_ALIASES:
                out["option_type"] = _OPT_TYPE_ALIASES[key]
    # final upper-case sanity
    if "option_type" in out and isinstance(out["option_type"], str):
        ot = out["option_type"].upper()
        if ot in {"LC", "SC", "LP", "SP"}:
            out["option_type"] = ot
        elif ot.lower() in _OPT_TYPE_ALIASES:
            out["option_type"] = _OPT_TYPE_ALIASES[ot.lower()]

    # quantity / price aliases
    if "quantity" not in out and "contracts" in out:
        out["quantity"] = out["contracts"]
    if "price" not in out and "premium" in out:
        out["price"] = out["premium"]

    # Required-field guard with a clear, structured error
    required = ("ticker", "option_type", "strike", "quantity", "price")
    missing = [k for k in required if k not in out or out[k] in (None, "")]
    if missing:
        raise ValueError(
            f"position missing required fields: {missing}. "
            f"Got keys: {sorted(out.keys())}"
        )
    return out
