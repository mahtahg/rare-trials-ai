"""Figure 1 for the npj Digital Medicine submission, built from eval/results/V011_COMPARISON.json.

Nature Portfolio / npj specifications: 183 mm (double-column) width, RGB, vector PDF/SVG plus 600 dpi TIFF,
Arial (or the metrically identical Liberation Sans where Arial is not installed), 8 pt text, all text black,
lower-case bold panel labels, no figure title inside the artwork, colour-blind-safe colours (Okabe-Ito blue,
grey), no red-green contrast.

    python paper/figures/make_fig1.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "paper/figures"
MM = 1 / 25.4
BLACK = "#000000"
GREY = "#6b6b6b"
BLUE = "#0072B2"

have = {f.name for f in font_manager.fontManager.ttflist}
FONT = next((f for f in ("Arial", "Helvetica", "Liberation Sans") if f in have), "DejaVu Sans")
plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": [FONT], "font.size": 8,
    "text.color": BLACK, "axes.labelcolor": BLACK, "axes.edgecolor": BLACK, "xtick.color": BLACK, "ytick.color": BLACK,
    "axes.titlesize": 8, "axes.labelsize": 8, "xtick.labelsize": 8, "ytick.labelsize": 8, "legend.fontsize": 8,
    "axes.linewidth": 0.5, "xtick.major.width": 0.5, "ytick.major.width": 0.5, "xtick.major.size": 2.5, "ytick.major.size": 2.5,
    "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none",
})

CONDS = [("no_tools", "No tools"), ("web_search", "Web search"), ("biomcp_go", "BioMCP"),
         ("biomcp", "RareMCP\n0.1.0"), ("biomcp_v011", "RareMCP\n0.1.1*")]
TIERS = [("base", "Base tier (254 single-source questions)"), ("hard", "Hard tier (60 multi-step questions)")]
MODELS = [("sonnet", "o", -0.14), ("haiku", "s", 0.14)]


def main() -> int:
    rows = [r for r in json.loads((ROOT / "eval/results/V011_COMPARISON.json").read_text()) if "condition" in r]
    cell = {(r["tier"], r["model"], r["condition"]): r for r in rows}
    fig, axes = plt.subplots(1, 2, figsize=(183 * MM, 72 * MM), sharey=True)
    for ax, (tier, title), letter in zip(axes, TIERS, "ab"):
        for i, (cond, _) in enumerate(CONDS):
            rare = cond.startswith("biomcp") and cond != "biomcp_go"
            col = BLUE if rare else GREY
            for m, marker, dx in MODELS:
                r = cell[(tier, m, cond)]
                p, lo, hi = 100 * r["k"] / r["n"], 100 * r["ci"][0], 100 * r["ci"][1]
                ax.errorbar(i + dx, p, yerr=[[p - lo], [hi - p]], fmt="none", ecolor=col, elinewidth=0.8, capsize=1.8, capthick=0.8, zorder=2)
                ax.plot(i + dx, p, marker=marker, ms=4.2, mew=0.9, mec=col, mfc="white" if cond == "biomcp_v011" else col, ls="none", zorder=3)
        ax.set_xticks(range(len(CONDS)), [c for _, c in CONDS])
        ax.set_xlim(-0.55, len(CONDS) - 0.45)
        ax.set_ylim(0, 102)
        ax.set_yticks([0, 25, 50, 75, 100])
        ax.yaxis.grid(True, color="#d9d9d9", lw=0.4, zorder=0)
        ax.set_axisbelow(True)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        ax.set_title(title, loc="left", pad=6, color=BLACK)
        ax.text(-0.13 if letter == "a" else -0.04, 1.06, letter, transform=ax.transAxes, fontweight="bold", va="bottom", ha="left", color=BLACK)
    axes[0].set_ylabel("Accuracy (%)")
    handles = [Line2D([], [], marker="o", ls="none", mfc=BLACK, mec=BLACK, ms=4.2, label="Claude Sonnet 5.5"),
               Line2D([], [], marker="s", ls="none", mfc=BLACK, mec=BLACK, ms=4.2, label="Claude Haiku 5.5"),
               Line2D([], [], marker="o", ls="none", mfc=BLUE, mec=BLUE, ms=4.2, label="RareMCP"),
               Line2D([], [], marker="o", ls="none", mfc=GREY, mec=GREY, ms=4.2, label="Comparator"),
               Line2D([], [], marker="o", ls="none", mfc="white", mec=BLUE, mew=0.9, ms=4.2, label="*Post hoc re-run")]
    fig.legend(handles=handles, loc="lower center", ncol=5, frameon=False, bbox_to_anchor=(0.5, 0.0), handletextpad=0.3, columnspacing=1.4)
    fig.subplots_adjust(left=0.075, right=0.99, top=0.86, bottom=0.27, wspace=0.12)
    OUT.mkdir(parents=True, exist_ok=True)
    for ext, kw in (("pdf", {}), ("svg", {}), ("png", {"dpi": 300})):
        fig.savefig(OUT / f"Fig1.{ext}", facecolor="white", **kw)
    # TIFF: flattened RGB (no alpha), 600 dpi, LZW
    import io

    from PIL import Image
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=600, facecolor="white")
    Image.open(buf).convert("RGB").save(OUT / "Fig1.tiff", dpi=(600, 600), compression="tiff_lzw")
    # SVG text stays editable; declare Arial first so it renders in Arial wherever Arial is installed
    svg = (OUT / "Fig1.svg").read_text()
    (OUT / "Fig1.svg").write_text(svg.replace(f"font-family: '{FONT}', sans-serif", f"font-family: Arial, Helvetica, '{FONT}', sans-serif"))
    print(f"font: {FONT}; wrote {', '.join(f'Fig1.{e}' for e in ('pdf', 'svg', 'tiff', 'png'))} to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
