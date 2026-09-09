#!/usr/bin/env python3
"""Regenerate the raster favicon set from the vector source geometry.

Source of truth for the artwork is ``static/favicon.svg``; this script
redraws the same shapes with Pillow (no SVG rasteriser needed) and writes
every derivative that ``templates/index.html`` and ``static/site.webmanifest``
reference:

    favicon-16x16.png  favicon-32x32.png  favicon.ico (16/32/48)
    apple-touch-icon.png (180)  icon-192.png  icon-512.png

Pillow is an on-demand tool dependency (like ruff / playwright) and is
deliberately not in requirements.txt::

    pip install Pillow
    python scripts/gen_favicons.py

Keep the constants below in sync with static/favicon.svg if the art changes.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

REPO_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = REPO_ROOT / "static"

# --- artwork constants (viewBox 0..512), mirrored from static/favicon.svg ---
VB = 512
CORNER_R = 112
ONYX = (10, 10, 10, 255)  # --slate-100
GOLD = (212, 175, 55, 255)  # --blue
GOLD_BRIGHT = (245, 200, 66, 255)  # --blue-dark

BORDER_INSET = 12
BORDER_R = 100
BORDER_W = 7
BORDER_ALPHA = 0.28

FLOOR = ((108, 350), (236, 350))
FLOOR_W = 40
FLOOR_ALPHA = 0.45
UPSIDE = ((236, 350), (412, 146))
UPSIDE_W = 46
STRIKE = (236, 350)
STRIKE_R = 27

SS = 8  # supersample factor for antialiasing

# size -> filename(s); .ico bundles several resolutions
PNG_TARGETS = {
    "favicon-16x16.png": 16,
    "favicon-32x32.png": 32,
    "apple-touch-icon.png": 180,
    "icon-192.png": 192,
    "icon-512.png": 512,
}
ICO_SIZES = [16, 32, 48]


def _round_line(draw: ImageDraw.ImageDraw, p0, p1, width, fill) -> None:
    """A line with round caps (Pillow has no cap style of its own)."""
    draw.line([p0, p1], fill=fill, width=width)
    r = width / 2
    for cx, cy in (p0, p1):
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill)


def _layer(size: int):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)


def _with_alpha(img: Image.Image, alpha: float) -> Image.Image:
    a = img.getchannel("A").point(lambda v: int(v * alpha))
    img.putalpha(a)
    return img


def render(target: int) -> Image.Image:
    size = target * SS
    scale = size / VB

    def s(v):
        return v * scale

    def sp(pt):
        return (pt[0] * scale, pt[1] * scale)

    # onyx tile
    base, d = _layer(size)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=s(CORNER_R), fill=ONYX)

    # gold hairline
    border, bd = _layer(size)
    bd.rounded_rectangle(
        [s(BORDER_INSET), s(BORDER_INSET), size - 1 - s(BORDER_INSET), size - 1 - s(BORDER_INSET)],
        radius=s(BORDER_R),
        outline=GOLD,
        width=max(1, round(s(BORDER_W))),
    )
    base.alpha_composite(_with_alpha(border, BORDER_ALPHA))

    # payoff floor (dim gold)
    floor, fd = _layer(size)
    _round_line(fd, sp(FLOOR[0]), sp(FLOOR[1]), round(s(FLOOR_W)), GOLD)
    base.alpha_composite(_with_alpha(floor, FLOOR_ALPHA))

    # payoff upside (bright gold) + strike node
    up, ud = _layer(size)
    _round_line(ud, sp(UPSIDE[0]), sp(UPSIDE[1]), round(s(UPSIDE_W)), GOLD_BRIGHT)
    r = s(STRIKE_R)
    cx, cy = sp(STRIKE)
    ud.ellipse([cx - r, cy - r, cx + r, cy + r], fill=GOLD_BRIGHT)
    base.alpha_composite(up)

    return base.resize((target, target), Image.LANCZOS)


def main() -> None:
    master = render(512)
    for name, px in PNG_TARGETS.items():
        img = master if px == 512 else render(px)
        img.save(STATIC_DIR / name)
        print(f"wrote static/{name} ({px}x{px})")

    ico = render(max(ICO_SIZES))
    ico.save(STATIC_DIR / "favicon.ico", sizes=[(n, n) for n in ICO_SIZES])
    print(f"wrote static/favicon.ico ({'/'.join(map(str, ICO_SIZES))})")


if __name__ == "__main__":
    main()
