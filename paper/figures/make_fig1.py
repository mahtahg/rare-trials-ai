"""Figure 1: study design. Questions are answered by two Claude models under four tool conditions; answers are
scored against gold answers computed from the same public sources by separate code, then audited.

    python paper/figures/make_fig1.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from style import BLACK, BLUE, LIGHTBLUE, MM, SIZE, save

W, H = 183, 98  # mm
LH = 3.5  # line height, mm


def box(ax, x, y, w, h, title, lines, fill="white", edge=BLACK, lw=0.6):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.2", fc=fill, ec=edge, lw=lw))
    ax.text(x + 2, y + h - 2.2, title, fontweight="bold", va="top", ha="left", color=BLACK)
    for i, t in enumerate(lines):
        ax.text(x + 2, y + h - 6.4 - LH * i, t, va="top", ha="left", color=BLACK)


def arrow(ax, p, q, style="-|>", ls="-", rad=0.0, col=BLACK):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle=style, mutation_scale=7, lw=0.7, color=col, ls=ls,
                                 connectionstyle=f"arc3,rad={rad}", shrinkA=0, shrinkB=0))


def main() -> int:
    fig = plt.figure(figsize=(W * MM, H * MM))
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")

    # top row: question set -> client and models -> tool conditions -> answer and scoring
    box(ax, 2, 61, 42, 31, "Question set (314)",
        ["18 templates", "Base tier: 254 single-source", "Hard tier: 60 multi-step", "246 rare disease, 48 NTD",
         "20 EU-rarity items", "20 non-existent identifiers"])
    box(ax, 50, 61, 38, 31, "Headless Claude Code",
        ["Claude Sonnet 5.5", "Claude Haiku 5.5", "One shared system prompt", "One run per question,", "model and condition"])
    cx, cw = 94, 48
    conds = [("No tools", [], "white", BLACK, 86, 6),
             ("Web search", ["WebSearch and WebFetch"], "white", BLACK, 74, 10.5),
             ("BioMCP 0.9.3", ["GenomOncology server, via proxy"], "white", BLACK, 61.5, 10.5),
             ("RareMCP 0.1.0", ["17 read-only tools, 6 servers;", "provenance on every response"], LIGHTBLUE, BLUE, 46, 14)]
    for t, ls_, fill, edge, y, h in conds:
        box(ax, cx, y, cw, h, t, ls_, fill=fill, edge=edge)
    ax.text(cx + cw / 2, 93.5, "Tool condition (2,512 runs in all)", ha="center", va="bottom", fontweight="bold", color=BLACK)
    box(ax, 146, 61, 35, 31, "Answer and scoring",
        ["Final JSON block: answer,", "identifiers, not-found flag,", "confidence", "Accuracy (template rules)",
         "Identifier validity", "Grounding in tool outputs", "Calibration (ECE, Brier)"])

    # bottom row: public sources -> tools (live queries); sources -> gold answers (audited) -> scoring
    box(ax, 2, 4, 72, 28, "Public sources",
        ["ClinicalTrials.gov", "Open Targets", "ChEMBL", "openFDA (Drugs@FDA, labels)", "Europe PMC", "Orphadata (Orphanet)"])
    box(ax, 94, 4, 87, 28, "Gold answers",
        ["Computed on 3\u20134 November 2026 from raw source responses",
         "by deterministic code that does not import the servers (v1.0)",
         "Audit: 41-question re-derivation from archived records;",
         "all 58 Drugs@FDA-dependent answers re-derived with a",
         "broader search; 8 corrected (v1.1). The original search",
         "had also been used inside RareMCP 0.1.0 (shared error)"])

    arrow(ax, (44, 76.5), (50, 76.5))                    # questions -> client
    arrow(ax, (88, 89), (94, 89), style="<|-|>")          # client <-> tools
    arrow(ax, (142, 76.5), (146, 76.5))                  # tools -> answer
    # live queries: bus from the sources to web search, BioMCP and RareMCP
    ax.plot([74, 90.5, 90.5], [26, 26, 79], color=BLACK, lw=0.7)
    for y, col in ((79, BLACK), (66.75, BLACK), (53, BLUE)):
        arrow(ax, (90.5, y), (94, y), col=col)
    ax.text(89.5, 40, "queried\nlive", ha="right", va="center", color=BLACK)
    arrow(ax, (74, 12), (94, 12))                        # sources -> gold
    ax.text(84, 13.2, "separate\ncode", ha="center", va="bottom", color=BLACK)
    arrow(ax, (163.5, 32), (163.5, 61))                      # gold -> scoring
    save(fig, "Fig1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
