"""Figure 2: accuracy by condition, model and tier (from eval/results/V011_COMPARISON.json).

    python paper/figures/make_fig2.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from style import BLACK, BLUE, GREY, MM, ROOT, panel_label, save

CONDS = [("no_tools", "No tools"), ("web_search", "Web search"), ("biomcp_go", "BioMCP"),
         ("biomcp", "RareMCP\n0.1.0"), ("biomcp_v011", "RareMCP\n0.1.1*")]
TIERS = [("base", "Base tier (254 single-source questions)"), ("hard", "Hard tier (60 multi-step questions)")]
MODELS = [("sonnet", "o", -0.14), ("haiku", "s", 0.14)]


def main() -> int:
    rows = [r for r in json.loads((ROOT / "eval/results/V011_COMPARISON.json").read_text()) if "condition" in r]
    cell = {(r["tier"], r["model"], r["condition"]): r for r in rows}
    fig, axes = plt.subplots(1, 2, figsize=(183 * MM, 70 * MM), sharey=True)
    for ax, (tier, title), letter in zip(axes, TIERS, "ab"):
        for i, (cond, _) in enumerate(CONDS):
            col = BLUE if cond in ("biomcp", "biomcp_v011") else GREY
            for m, marker, dx in MODELS:
                r = cell[(tier, m, cond)]
                p, lo, hi = 100 * r["k"] / r["n"], 100 * r["ci"][0], 100 * r["ci"][1]
                ax.errorbar(i + dx, p, yerr=[[p - lo], [hi - p]], fmt="none", ecolor=col, elinewidth=0.8, capsize=1.8, capthick=0.8, zorder=2)
                ax.plot(i + dx, p, marker=marker, ms=4, mew=0.9, mec=col, mfc="white" if cond == "biomcp_v011" else col, ls="none", zorder=3)
        ax.set_xticks(range(len(CONDS)), [c for _, c in CONDS])
        ax.set_xlim(-0.55, len(CONDS) - 0.45)
        ax.set_ylim(0, 102)
        ax.set_yticks([0, 25, 50, 75, 100])
        ax.yaxis.grid(True, color="#d9d9d9", lw=0.4, zorder=0)
        ax.set_axisbelow(True)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        ax.set_title(title, loc="left", pad=6, color=BLACK)
        panel_label(ax, letter, x=-0.12 if letter == "a" else -0.04)
    axes[0].set_ylabel("Accuracy (%)")
    handles = [Line2D([], [], marker="o", ls="none", mfc=BLACK, mec=BLACK, ms=4, label="Claude Sonnet 5.5"),
               Line2D([], [], marker="s", ls="none", mfc=BLACK, mec=BLACK, ms=4, label="Claude Haiku 5.5"),
               Line2D([], [], marker="o", ls="none", mfc=BLUE, mec=BLUE, ms=4, label="RareMCP"),
               Line2D([], [], marker="o", ls="none", mfc=GREY, mec=GREY, ms=4, label="Comparator"),
               Line2D([], [], marker="o", ls="none", mfc="white", mec=BLUE, mew=0.9, ms=4, label="*Post hoc re-run")]
    fig.legend(handles=handles, loc="lower center", ncol=5, frameon=False, bbox_to_anchor=(0.5, 0.0), handletextpad=0.3, columnspacing=1.4)
    fig.subplots_adjust(left=0.07, right=0.99, top=0.86, bottom=0.26, wspace=0.12)
    save(fig, "Fig2")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
