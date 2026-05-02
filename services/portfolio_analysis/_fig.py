"""Matplotlib figure → base64 encoding with explicit lifecycle management."""

import base64
import io

import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Agg")


def _fig_to_base64(fig) -> str:
    """Encode a matplotlib Figure as a base64 PNG string and explicitly close it."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    buf.seek(0)
    result = base64.b64encode(buf.getvalue()).decode()
    plt.close(fig)
    return result
