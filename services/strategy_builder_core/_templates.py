"""Strategy templates: map user-facing names to leg specifications."""

from typing import Any

TEMPLATES: dict[str, dict[str, Any]] = {
    "long_call": {
        "factory": "long_call",
        "legs": [("call", "long", "k")],
        "strikes": ["k"],
    },
    "long_put": {
        "factory": "long_put",
        "legs": [("put", "long", "k")],
        "strikes": ["k"],
    },
    "short_call": {
        "factory": "short_call",
        "legs": [("call", "short", "k")],
        "strikes": ["k"],
    },
    "short_put": {
        "factory": "short_put",
        "legs": [("put", "short", "k")],
        "strikes": ["k"],
    },
    "bull_call_spread": {
        "factory": "bull_call_spread",
        "legs": [("call", "long", "k_long"), ("call", "short", "k_short")],
        "strikes": ["k_long", "k_short"],
    },
    "bear_put_spread": {
        "factory": "bear_put_spread",
        "legs": [("put", "long", "k_long"), ("put", "short", "k_short")],
        "strikes": ["k_long", "k_short"],
    },
    "iron_condor": {
        "factory": "iron_condor",
        "legs": [
            ("put", "long", "k_put_long"),
            ("put", "short", "k_put_short"),
            ("call", "short", "k_call_short"),
            ("call", "long", "k_call_long"),
        ],
        "strikes": ["k_put_long", "k_put_short", "k_call_short", "k_call_long"],
    },
    "long_straddle": {
        "factory": "long_straddle",
        "legs": [("call", "long", "k"), ("put", "long", "k")],
        "strikes": ["k"],
    },
}
