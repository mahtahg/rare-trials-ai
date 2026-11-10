"""Figure 3: a search error shared by RareMCP 0.1.0 and the original gold answers.

Accuracy against the original gold (v1.0) and the audited gold (v1.1) for (a) the approval-year template
(h_source_conflict, 12 questions) and (b) the hard tier (60 questions), with the RareMCP 0.1.1 re-run (v1.1 only).
Values are read from the saved summaries (v1gold_all_summary.json, all_summary.json, fda011-*).

    python paper/figures/make_fig3.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from style import BLACK, BLUE, GREY, MM, ROOT, save

RES = ROOT / "eval/results"
CONDS = [("no_tools", "No tools"), ("web_search", "Web search"), ("biomcp_go", "BioMCP"), ("biomcp", "RareMCP 0.1.0")]
MODELS = [("sonnet", "Sonnet"), ("haiku", "Haiku")]


def acc(run: str, prefix: str, cond: str, template: str | None) -> float:
    s = json.loads((RES / run / f"{prefix}summary.json").read_text())
    block = s["by_template"][template] if template else s["by_condition"]
    return next(100 * v["accuracy"] for k, v in block.items() if k.split("|")[1] == cond)


def v011_hard(model: str) -> float:
    r = next(x for x in json.loads((RES / "V011_COMPARISON.json").read_text())
             if x.get("condition") == "biomcp_v011" and x["tier"] == "hard" and x["model"] == model)
    return 100 * r["k"] / r["n"]


def main() -> int:
    rows = []  # (label, colour, v1.0 or None, v1.1) per panel
    for template, name in (("h_source_conflict", "a"), (None, "b")):
        pr = []
        for cond, cname in CONDS:
            for m, mname in MODELS:
                pr.append((f"{cname}, {mname}", BLUE if cond == "biomcp" else GREY,
                           acc(f"hard-{m}", "v1gold_all_", cond, template), acc(f"hard-{m}", "all_", cond, template)))
        for m, mname in MODELS:
            v = acc(f"fda011-{m}", "all_", "biomcp", template) if template else v011_hard(m)
            pr.append((f"RareMCP 0.1.1*, {mname}", BLUE, None, v))
        rows.append((name, pr))
    fig, axes = plt.subplots(1, 2, figsize=(183 * MM, 72 * MM), sharey=True)
    titles = {"a": "Approval-year questions (12; ChEMBL versus FDA)", "b": "Hard tier (60 multi-step questions)"}
    for ax, (letter, pr) in zip(axes, rows):
        n = len(pr)
        for i, (label, col, old, new) in enumerate(pr):
            y = n - 1 - i
            if old is not None:
                if abs(new - old) > 0.5:
                    ax.annotate("", xy=(new, y), xytext=(old, y),
                                arrowprops={"arrowstyle": "-|>", "color": col, "lw": 0.8, "shrinkA": 3, "shrinkB": 3, "mutation_scale": 6})
                ax.plot(old, y, marker="o", ms=4, mfc="white", mec=col, mew=0.9, ls="none", zorder=3)
            ax.plot(new, y, marker="o", ms=4, mfc=col, mec=col, ls="none", zorder=4)
        ax.set_yticks(range(n), [p[0] for p in reversed(pr)])
        ax.set_xlim(0, 104)
        ax.set_xticks([0, 25, 50, 75, 100])
        ax.set_ylim(-0.7, n - 0.3)
        ax.xaxis.grid(True, color="#d9d9d9", lw=0.4, zorder=0)
        ax.set_axisbelow(True)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        ax.set_xlabel("Accuracy (%)")
        ax.set_title(titles[letter], loc="left", pad=6, color=BLACK)
    handles = [Line2D([], [], marker="o", ls="none", mfc="white", mec=BLACK, mew=0.9, ms=4, label="Original gold (v1.0)"),
               Line2D([], [], marker="o", ls="none", mfc=BLACK, mec=BLACK, ms=4, label="Audited gold (v1.1)"),
               Line2D([], [], marker="o", ls="none", mfc=BLUE, mec=BLUE, ms=4, label="RareMCP"),
               Line2D([], [], marker="o", ls="none", mfc=GREY, mec=GREY, ms=4, label="Comparator"),
               Line2D([], [], ls="none", label="*Post hoc re-run with the corrected search")]
    fig.legend(handles=handles, loc="lower center", ncol=5, frameon=False, bbox_to_anchor=(0.55, 0.0), handletextpad=0.3, columnspacing=1.4)
    fig.subplots_adjust(left=0.16, right=0.99, top=0.88, bottom=0.24, wspace=0.08)
    for ax, letter in zip(axes, "ab"):
        x = 0.005 if letter == "a" else ax.get_position().x0 - 0.02
        fig.text(x, 0.955, letter, fontweight="bold", fontsize=8, color=BLACK, va="top")
    save(fig, "Fig3")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
