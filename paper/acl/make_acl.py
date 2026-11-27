"""Build the generated parts of the ACL paper: figures, tables and the open-model results paragraph.

Claude results come from the saved comparisons (all_COMPARISON.json for RareMCP 0.1.0 as run, V011_COMPARISON.json
for the post hoc 0.1.1 composite). Open-model results come from eval/results/open-*: shards are merged and scored
against gold v1.1 on all questions (the primary analysis), and a model enters the tables only when every one of
its runs is present. Until then its cells read "pending" and the paragraph says so in red, so a draft can never
be mistaken for a finished one.

    python paper/acl/make_acl.py            # writes paper/acl/generated/* and paper/acl/fig_*.pdf
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "paper/figures"))
sys.path.insert(0, str(ROOT / "eval"))
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from score import mcnemar_exact, paired_bootstrap, wilson
from style import BLACK, BLUE, GREY, MM

RES = ROOT / "eval/results"
GEN = HERE / "generated"
TIERS = {"base": ("eval/questions.jsonl", 254), "hard": ("eval/questions_hard.jsonl", 60)}
CONDS = ["no_tools", "web_search", "biomcp_go", "biomcp"]
CLAUDE = [("sonnet", "claude-sonnet-5-5", "Claude Sonnet 5.5"), ("haiku", "claude-haiku-5-5", "Claude Haiku 5.5")]
OPEN = [("gemma", "Gemma 4 26B-A4B", {"base": "open-gemma4", "hard": "open-gemma4-hard"}),
        ("gptoss", "gpt-oss-20b", {"base": "open-gptoss", "hard": "open-gptoss-hard"})]
MARK = {"sonnet": "o", "haiku": "s", "gemma": "^", "gptoss": "D"}
CLAIM = re.compile(  # same screen as eval/process_fabrication.py
    r"\b(I (queried|ran|retrieved|fetched|looked up|pulled|called|searched)|(query|lookup|call|search|request|response|API)s? "
    r"(returned|reported|came back|showed|gave)|returned \d+ (rows|results|trials|records|hits)|my (query|search|lookup|follow-up))",
    re.IGNORECASE)


def pct(x: float) -> str:
    return f"{100 * x:.1f}"


def fmt_p(p: float) -> str:
    if p >= 0.001:
        return f"{p:.2f}" if p >= 0.01 else f"{p:.3f}"
    m, e = f"{p:.1e}".split("e")
    return f"${m}\\times10^{{{int(e)}}}$"


# ---------------------------------------------------------------- Claude (saved comparisons)

def claude_cells() -> dict:
    out = {}
    allc = json.loads((RES / "all_COMPARISON.json").read_text())
    for r in allc["cells"]:
        out[(r["tier"], r["model"].replace("claude-", "").replace("-5-5", ""), r["condition"])] = (round(r["acc"] * r["n"]), r["n"])
    for r in json.loads((RES / "V011_COMPARISON.json").read_text()):
        if r.get("condition") == "biomcp_v011":
            out[(r["tier"], r["model"], "biomcp_v011")] = (r["k"], r["n"])
    return out


def claude_paired() -> dict:
    out = {}
    for r in json.loads((RES / "all_COMPARISON.json").read_text())["benefit"]:
        out[(r["tier"], r["model"].replace("claude-", "").replace("-5-5", ""), r["vs"])] = r
    return out


# ---------------------------------------------------------------- open models (raw shards)

def open_run(run: str, tier: str) -> dict | None:
    d = RES / run
    if not d.exists():
        return None
    shards = sorted(d.glob("raw.shard*of*.jsonl"))
    if shards:
        subprocess.run([sys.executable, str(ROOT / "eval/merge_shards.py"), str(d)], check=True, capture_output=True)
    if not (d / "raw.jsonl").exists():
        return None
    subprocess.run([sys.executable, str(ROOT / "eval/score.py"), "--questions", str(ROOT / TIERS[tier][0]), "--run", str(d),
                    "--exclude", "", "--prefix", "all_"], check=True, capture_output=True)
    raw = {}
    for line in (d / "raw.jsonl").read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            if not r.get("error"):
                raw[(r["qid"], r["condition"])] = r
    cells: dict = {}
    for line in (d / "all_scored.jsonl").read_text().splitlines():
        x = json.loads(line)
        cells.setdefault(x["condition"], {})[x["qid"]] = x
    nt = [r for (q, c), r in raw.items() if c == "no_tools"]
    fab = sum(1 for r in nt if not r["tool_calls"] and CLAIM.search(r.get("final_text") or ""))
    stops = Counter(r.get("stop_reason") for r in raw.values() if r.get("stop_reason"))
    complete = all(len(cells.get(c, {})) == TIERS[tier][1] for c in CONDS)
    return {"cells": cells, "complete": complete, "n": {c: len(cells.get(c, {})) for c in CONDS}, "fab": (fab, len(nt)),
            "stops": dict(stops), "parse_fail": sum(1 for c in cells.values() for x in c.values() if x.get("parse_fail")),
            "provenance": sorted({p.read_text().strip() for p in d.glob("provenance.shard*.json")})}


def open_results() -> dict:
    out = {}
    for key, _, runs in OPEN:
        for tier, run in runs.items():
            r = open_run(run, tier)
            if r:
                out[(key, tier)] = r
    return out


def acc_open(o: dict, cond: str) -> tuple[int, int]:
    v = o["cells"].get(cond, {})
    return sum(x["correct"] for x in v.values()), len(v)


def paired_open(o: dict, other: str) -> dict:
    a, b = o["cells"]["biomcp"], o["cells"][other]
    q = sorted(set(a) & set(b))
    x, y = [a[i]["correct"] for i in q], [b[i]["correct"] for i in q]
    bb, cc = sum(p and not r for p, r in zip(x, y)), sum(r and not p for p, r in zip(x, y))
    d = paired_bootstrap([float(v) for v in x], [float(v) for v in y], iters=10000, seed=7)
    return {"n": len(q), "b": bb, "c": cc, "p": mcnemar_exact(bb, cc), "delta": d}


def ready(op: dict, key: str) -> bool:
    return all(op.get((key, t), {}).get("complete") for t in TIERS)


# ---------------------------------------------------------------- tables

def tab_accuracy(cc: dict, op: dict) -> str:
    head = ["\\begin{table*}[t]", "\\centering\\small", "\\begin{tabular}{llccccc}", "\\toprule",
            "Tier & Model & No tools & Web search & BioMCP & RareMCP 0.1.0 & RareMCP 0.1.1 \\\\", "\\midrule"]
    rows = []
    for tier in TIERS:
        for m, _, name in CLAUDE:
            vals = [pct(cc[(tier, m, c)][0] / cc[(tier, m, c)][1]) for c in CONDS]
            v11 = cc[(tier, m, "biomcp_v011")]
            rows.append(f"{tier.capitalize()} & {name} & " + " & ".join(vals[:3]) + f" & \\textbf{{{vals[3]}}} & {pct(v11[0] / v11[1])}$^\\dagger$ \\\\")
        for key, name, _ in OPEN:
            o = op.get((key, tier))
            if ready(op, key):
                vals = [pct(k / n) for k, n in (acc_open(o, c) for c in CONDS)]
                rows.append(f"{tier.capitalize()} & {name} & " + " & ".join(vals[:3]) + f" & -- & \\textbf{{{vals[3]}}} \\\\")
            else:
                rows.append(f"{tier.capitalize()} & {name} & \\pend & \\pend & \\pend & -- & \\pend \\\\")
        rows.append("\\midrule" if tier == "base" else "\\bottomrule")
    foot = ["\\end{tabular}",
            "\\caption{Accuracy (\\%) by tool condition against the audited gold answers (v1.1), one run per question, model and "
            "condition. Base tier: 254 single-source questions; hard tier: 60 multi-step questions. Bold: RareMCP version as run. "
            "Claude models were run with RareMCP 0.1.0; $^\\dagger$post hoc composite in which the 58 Drugs@FDA-dependent "
            "questions were re-run with 0.1.1 and all other answers kept (\\S\\ref{sec:shared}). Open-weight models were run "
            "once, with 0.1.1 throughout. Open-model web search is DuckDuckGo search plus page fetch rather than Claude Code's "
            "built-in tools (\\S\\ref{sec:setup}). 95\\% Wilson intervals are in Figure~\\ref{fig:acc}.}",
            "\\label{tab:acc}", "\\end{table*}"]
    return "\n".join(head + rows + foot) + "\n"


def tab_paired(cp: dict, op: dict) -> str:
    head = ["\\begin{table}[t]", "\\centering", "\\setlength{\\tabcolsep}{3pt}", "\\resizebox{\\columnwidth}{!}{%", "\\begin{tabular}{llrrrr}", "\\toprule",
            "& & \\multicolumn{2}{c}{vs web search} & \\multicolumn{2}{c}{vs BioMCP} \\\\",
            "\\cmidrule(lr){3-4}\\cmidrule(lr){5-6}", "Tier & Model & $\\Delta$ & $P$ & $\\Delta$ & $P$ \\\\", "\\midrule"]
    rows = []
    for tier in TIERS:
        for m, _, name in CLAUDE:
            w, b = cp[(tier, m, "web_search")], cp[(tier, m, "biomcp_go")]
            rows.append(f"{tier.capitalize()} & {name.replace('Claude ', '')} & {100 * w['delta'][0]:+.1f} & {fmt_p(w['p'])} & "
                        f"{100 * b['delta'][0]:+.1f} & {fmt_p(b['p'])} \\\\")
        for key, name, _ in OPEN:
            if ready(op, key):
                o = op[(key, tier)]
                w, b = paired_open(o, "web_search"), paired_open(o, "biomcp_go")
                rows.append(f"{tier.capitalize()} & {name} & {100 * w['delta'][0]:+.1f} & {fmt_p(w['p'])} & "
                            f"{100 * b['delta'][0]:+.1f} & {fmt_p(b['p'])} \\\\")
            else:
                rows.append(f"{tier.capitalize()} & {name} & \\pend & & \\pend & \\\\")
        rows.append("\\midrule" if tier == "base" else "\\bottomrule")
    foot = ["\\end{tabular}}",
            "\\caption{RareMCP minus comparator, accuracy in percentage points, paired on identical questions (gold v1.1); "
            "exact two-sided McNemar $P$. Claude: RareMCP 0.1.0 as run; open models: 0.1.1. Bootstrap intervals for every "
            "row are in Appendix~\\ref{app:paired}.}", "\\label{tab:paired}", "\\end{table}"]
    return "\n".join(head + rows + foot) + "\n"


def tab_paired_full(cp: dict, op: dict) -> str:
    rows = ["\\begin{table*}[h]", "\\centering", "\\resizebox{\\textwidth}{!}{%", "\\begin{tabular}{lllrrrrl}", "\\toprule",
            "Tier & Model & Comparator & $n$ & RareMCP only & Comparator only & $P$ & $\\Delta$ (95\\% CI) \\\\", "\\midrule"]
    names = {"web_search": "Web search", "biomcp_go": "BioMCP", "no_tools": "No tools"}
    for tier in TIERS:
        for m, _, name in CLAUDE:
            for vs in names:
                r = cp[(tier, m, vs)]
                d = r["delta"]
                rows.append(f"{tier.capitalize()} & {name} & {names[vs]} & {r['n']} & {r['b']} & {r['c']} & {fmt_p(r['p'])} & "
                            f"{100 * d[0]:+.1f} ({100 * d[1]:.1f} to {100 * d[2]:.1f}) \\\\")
        for key, name, _ in OPEN:
            if not ready(op, key):
                rows.append(f"{tier.capitalize()} & {name} & all & \\multicolumn{{5}}{{c}}{{\\pend}} \\\\")
                continue
            for vs in names:
                r = paired_open(op[(key, tier)], vs)
                d = r["delta"]
                rows.append(f"{tier.capitalize()} & {name} & {names[vs]} & {r['n']} & {r['b']} & {r['c']} & {fmt_p(r['p'])} & "
                            f"{100 * d[0]:+.1f} ({100 * d[1]:.1f} to {100 * d[2]:.1f}) \\\\")
    rows += ["\\bottomrule", "\\end{tabular}}",
             "\\caption{Paired comparisons of RareMCP with each comparator (gold v1.1). RareMCP only / Comparator only: "
             "discordant questions. $P$: exact two-sided McNemar. $\\Delta$: accuracy difference in points with a "
             "question-level paired bootstrap interval (10,000 resamples). Claude rows use RareMCP 0.1.0 as run.}",
             "\\label{tab:pairedfull}", "\\end{table*}"]
    return "\n".join(rows) + "\n"


# ---------------------------------------------------------------- open-model paragraph

def open_paragraph(op: dict) -> str:
    done = [(k, n) for k, n, _ in OPEN if ready(op, k)]
    if len(done) < len(OPEN):
        have = ", ".join(f"{n} {t} {sum(op[(k, t)]['n'].values())}/{4 * TIERS[t][1]}" for k, n, _ in OPEN for t in TIERS if (k, t) in op)
        return ("\\textcolor{red}{[Open-weight runs pending; this paragraph and the open-model rows of "
                "Tables~\\ref{tab:acc} and~\\ref{tab:paired} are generated by \\texttt{paper/acl/make\\_acl.py} once every run "
                "is present" + (f". Progress: {have}" if have else "") + ".]}\n")
    parts = []
    for key, name in done:
        b, h = op[(key, "base")], op[(key, "hard")]
        a = {c: acc_open(b, c) for c in CONDS}
        ah = {c: acc_open(h, c) for c in CONDS}
        pw, pb = paired_open(b, "web_search"), paired_open(b, "biomcp_go")
        parts.append(
            f"{name} answered {pct(a['biomcp'][0] / a['biomcp'][1])}\\% of base-tier questions with RareMCP, "
            f"{pct(a['web_search'][0] / a['web_search'][1])}\\% with web search, {pct(a['biomcp_go'][0] / a['biomcp_go'][1])}\\% "
            f"with BioMCP and {pct(a['no_tools'][0] / a['no_tools'][1])}\\% without tools (RareMCP minus web search "
            f"{100 * pw['delta'][0]:+.1f} points, $P={fmt_p(pw['p']).strip('$')}$; minus BioMCP {100 * pb['delta'][0]:+.1f}, "
            f"$P={fmt_p(pb['p']).strip('$')}$); on the hard tier the figures were {pct(ah['biomcp'][0] / 60)}\\%, "
            f"{pct(ah['web_search'][0] / 60)}\\%, {pct(ah['biomcp_go'][0] / 60)}\\% and {pct(ah['no_tools'][0] / 60)}\\%.")
    fabs = "; ".join(f"{n}: {op[(k, 'base')]['fab'][0] + op[(k, 'hard')]['fab'][0]} of "
                     f"{op[(k, 'base')]['fab'][1] + op[(k, 'hard')]['fab'][1]}" for k, n in done)
    stops = Counter()
    for k, _ in done:
        for t in TIERS:
            stops.update(op[(k, t)]["stops"])
    return (" ".join(parts) + f" The fabricated-tool-use screen flagged no-tools answers as follows ({fabs}); "
            "\\textcolor{red}{[read and confirm each flag before submission]}. "
            + (f"Model-side stops, scored incorrect: {', '.join(f'{v} {k.replace(chr(95), chr(32))}' for k, v in stops.items())}." if stops else "")
            + "\n")


# ---------------------------------------------------------------- figures

def fig_accuracy(cc: dict, op: dict) -> None:
    models = [(m, n, "claude") for m, _, n in CLAUDE] + [(k, n, "open") for k, n, _ in OPEN if ready(op, k)]
    conds = [("no_tools", "No tools"), ("web_search", "Web search"), ("biomcp_go", "BioMCP"), ("biomcp", "RareMCP\n(as run)")]
    fig, axes = plt.subplots(1, 2, figsize=(160 * MM, 58 * MM), sharey=True)
    width = 0.62
    for ax, tier, title, letter in zip(axes, TIERS, ("Base tier (254 single-source questions)", "Hard tier (60 multi-step questions)"), "ab"):
        for i, (cond, _) in enumerate(conds):
            for j, (m, _, kind) in enumerate(models):
                dx = -width / 2 + width * (j + 0.5) / len(models)
                k, n = cc[(tier, m, cond)] if kind == "claude" else acc_open(op[(m, tier)], cond)
                p = 100 * k / n
                lo, hi = (100 * v for v in wilson(k, n))
                col = BLUE if cond == "biomcp" else GREY
                ax.errorbar(i + dx, p, yerr=[[p - lo], [hi - p]], fmt="none", ecolor=col, elinewidth=0.7, capsize=1.5, capthick=0.7, zorder=2)
                ax.plot(i + dx, p, marker=MARK[m], ms=3.6, mew=0.8, mec=col, mfc=col if kind == "claude" else "white", ls="none", zorder=3)
        ax.set_xticks(range(len(conds)), [c for _, c in conds])
        ax.set_xlim(-0.55, len(conds) - 0.45)
        ax.set_ylim(0, 102)
        ax.set_yticks([0, 25, 50, 75, 100])
        ax.yaxis.grid(True, color="#d9d9d9", lw=0.4, zorder=0)
        ax.set_axisbelow(True)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        ax.set_title(title, loc="left", pad=5, color=BLACK)
        ax.text(-0.1 if letter == "a" else -0.03, 1.04, letter, transform=ax.transAxes, fontweight="bold", fontsize=8, va="bottom")
    axes[0].set_ylabel("Accuracy (%)")
    handles = [Line2D([], [], marker=MARK[m], ls="none", mfc=BLACK if kind == "claude" else "white", mec=BLACK, mew=0.8, ms=3.6, label=n)
               for m, n, kind in models]
    handles += [Line2D([], [], marker="s", ls="none", mfc=BLUE, mec=BLUE, ms=3.6, label="RareMCP"),
                Line2D([], [], marker="s", ls="none", mfc=GREY, mec=GREY, ms=3.6, label="Comparator")]
    fig.legend(handles=handles, loc="lower center", ncol=len(handles), frameon=False, bbox_to_anchor=(0.5, 0.0), handletextpad=0.2, columnspacing=1.0)
    fig.subplots_adjust(left=0.07, right=0.995, top=0.86, bottom=0.27, wspace=0.08)
    fig.savefig(HERE / "fig_accuracy.pdf")
    plt.close(fig)


def fig_shared_error() -> None:
    """Same data and encoding as paper/figures/make_fig3.py, laid out for the ACL text width."""
    import make_fig3 as f3

    rows = []
    for template in ("h_source_conflict", None):
        pr = []
        for cond, cname in f3.CONDS:
            for m, mname in f3.MODELS:
                pr.append((f"{cname}, {mname}", BLUE if cond == "biomcp" else GREY,
                           f3.acc(f"hard-{m}", "v1gold_all_", cond, template), f3.acc(f"hard-{m}", "all_", cond, template)))
        for m, mname in f3.MODELS:
            v = f3.acc(f"fda011-{m}", "all_", "biomcp", template) if template else f3.v011_hard(m)
            pr.append((f"RareMCP 0.1.1*, {mname}", BLUE, None, v))
        rows.append(pr)
    fig, axes = plt.subplots(1, 2, figsize=(160 * MM, 66 * MM), sharey=True)
    titles = ("Approval-year questions (12; ChEMBL vs FDA)", "Hard tier (60 multi-step questions)")
    for ax, pr, title, letter in zip(axes, rows, titles, "ab"):
        n = len(pr)
        for i, (_, col, old, new) in enumerate(pr):
            y = n - 1 - i
            if old is not None:
                if abs(new - old) > 0.5:
                    ax.annotate("", xy=(new, y), xytext=(old, y),
                                arrowprops={"arrowstyle": "-|>", "color": col, "lw": 0.8, "shrinkA": 3, "shrinkB": 3, "mutation_scale": 6})
                ax.plot(old, y, marker="o", ms=3.6, mfc="white", mec=col, mew=0.8, ls="none", zorder=3)
            ax.plot(new, y, marker="o", ms=3.6, mfc=col, mec=col, ls="none", zorder=4)
        ax.set_yticks(range(n), [p[0] for p in reversed(pr)])
        ax.set_xlim(0, 104)
        ax.set_xticks([0, 25, 50, 75, 100])
        ax.set_ylim(-0.7, n - 0.3)
        ax.xaxis.grid(True, color="#d9d9d9", lw=0.4, zorder=0)
        ax.set_axisbelow(True)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        ax.set_xlabel("Accuracy (%)")
        ax.set_title(title, loc="left", pad=5, color=BLACK)
    handles = [Line2D([], [], marker="o", ls="none", mfc="white", mec=BLACK, mew=0.8, ms=3.6, label="Original gold (v1.0)"),
               Line2D([], [], marker="o", ls="none", mfc=BLACK, mec=BLACK, ms=3.6, label="Audited gold (v1.1)"),
               Line2D([], [], marker="s", ls="none", mfc=BLUE, mec=BLUE, ms=3.6, label="RareMCP"),
               Line2D([], [], marker="s", ls="none", mfc=GREY, mec=GREY, ms=3.6, label="Comparator"),
               Line2D([], [], ls="none", label="*Post hoc re-run, corrected search")]
    fig.legend(handles=handles, loc="lower center", ncol=5, frameon=False, bbox_to_anchor=(0.5, 0.0), handletextpad=0.2, columnspacing=1.0)
    fig.subplots_adjust(left=0.2, right=0.99, top=0.88, bottom=0.25, wspace=0.08)
    for ax, letter in zip(axes, "ab"):
        fig.text(0.005 if letter == "a" else ax.get_position().x0 - 0.025, 0.955, letter, fontweight="bold", fontsize=8, va="top")
    fig.savefig(HERE / "fig_shared_error.pdf")
    plt.close(fig)


def main() -> int:
    GEN.mkdir(exist_ok=True)
    cc, cp, op = claude_cells(), claude_paired(), open_results()
    (GEN / "tab_accuracy.tex").write_text(tab_accuracy(cc, op))
    (GEN / "tab_paired.tex").write_text(tab_paired(cp, op))
    (GEN / "tab_paired_full.tex").write_text(tab_paired_full(cp, op))
    (GEN / "open_results.tex").write_text(open_paragraph(op))
    fig_accuracy(cc, op)
    fig_shared_error()
    status = {f"{k}/{t}": {"complete": v["complete"], "n": v["n"], "stops": v["stops"], "fab": v["fab"], "provenance": v["provenance"]}
              for (k, t), v in op.items()}
    (GEN / "open_status.json").write_text(json.dumps(status, indent=1))
    print(json.dumps(status, indent=1) if status else "open-model results: none yet (tables show 'pending')")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
