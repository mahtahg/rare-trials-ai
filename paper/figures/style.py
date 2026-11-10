"""Shared figure style for the npj Digital Medicine submission.

Nature Portfolio / npj specifications: 183 mm (double-column) width, RGB, vector PDF/SVG plus 600 dpi TIFF,
Arial (or the metrically identical Liberation Sans where Arial is not installed), one size (7 pt) for all text,
all text black, lower-case bold panel labels, no titles inside the artwork, colour-blind-safe colours.
"""

from __future__ import annotations

import io
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "paper/figures"
MM = 1 / 25.4
BLACK, GREY, BLUE, LIGHTBLUE = "#000000", "#6b6b6b", "#0072B2", "#d9e8f5"
SIZE = 7

_have = {f.name for f in font_manager.fontManager.ttflist}
FONT = next((f for f in ("Arial", "Helvetica", "Liberation Sans") if f in _have), "DejaVu Sans")
plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": [FONT], "font.size": SIZE,
    "text.color": BLACK, "axes.labelcolor": BLACK, "axes.edgecolor": BLACK, "xtick.color": BLACK, "ytick.color": BLACK,
    "axes.titlesize": SIZE, "axes.labelsize": SIZE, "xtick.labelsize": SIZE, "ytick.labelsize": SIZE, "legend.fontsize": SIZE,
    "axes.linewidth": 0.5, "xtick.major.width": 0.5, "ytick.major.width": 0.5, "xtick.major.size": 2.5, "ytick.major.size": 2.5,
    "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none",
})


def panel_label(ax, letter: str, x: float = -0.12, y: float = 1.06) -> None:
    ax.text(x, y, letter, transform=ax.transAxes, fontweight="bold", va="bottom", ha="left", color=BLACK, fontsize=SIZE + 1)


def save(fig, name: str) -> None:
    """Write name.pdf, name.svg (editable text, Arial first), name.png (300 dpi) and name.tiff (600 dpi RGB)."""
    from PIL import Image

    OUT.mkdir(parents=True, exist_ok=True)
    for ext, kw in (("pdf", {}), ("svg", {}), ("png", {"dpi": 300})):
        fig.savefig(OUT / f"{name}.{ext}", facecolor="white", **kw)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=600, facecolor="white")
    Image.open(buf).convert("RGB").save(OUT / f"{name}.tiff", dpi=(600, 600), compression="tiff_lzw")
    svg = (OUT / f"{name}.svg").read_text()
    (OUT / f"{name}.svg").write_text(svg.replace(f"font-family: '{FONT}', sans-serif", f"font-family: Arial, Helvetica, '{FONT}', sans-serif"))
    print(f"{name}: font {FONT}; wrote pdf, svg, png, tiff")
