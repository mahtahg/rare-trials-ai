"""Score an eval run deterministically and compute paired statistics.

python eval/score.py --run eval/results/<run_id> [--validate-ids]

Writes scored.jsonl, summary.json and summary.md into the run directory.
--validate-ids checks every NCT/CHEMBL/PMID the model emitted against the live
source (needs network; run in CI) to measure the hallucinated-identifier rate.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

ID_PATTERNS = {
    "nct": re.compile(r"\bNCT\d{8}\b"),
    "chembl": re.compile(r"\bCHEMBL\d+\b"),
    "pmid": re.compile(r"\bPMID:?\s*(\d{5,9})\b", re.IGNORECASE),
}

YES = {"yes", "true", "y", "1"}
NO = {"no", "false", "n", "0"}


def norm_token(s) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(s).lower()).strip()


def token_f1(pred: str, gold: str) -> float:
    p, g = norm_token(pred).split(), norm_token(gold).split()
    if not p or not g:
        return 0.0
    common = defaultdict(int)
    for t in g:
        common[t] += 1
    hit = 0
    for t in p:
        if common[t] > 0:
            hit += 1
            common[t] -= 1
    if hit == 0:
        return 0.0
    prec, rec = hit / len(p), hit / len(g)
    return 2 * prec * rec / (prec + rec)


def to_bool(x):
    if isinstance(x, bool):
        return x
    s = norm_token(x)
    if s in YES or s.startswith("yes"):
        return True
    if s in NO or s.startswith("no"):
        return False
    return None


def to_num(x):
    if isinstance(x, bool):
        return None
    if isinstance(x, (int, float)):
        return float(x)
    m = re.search(r"-?\d[\d,]*\.?\d*", str(x))
    return float(m.group().replace(",", "")) if m else None


SALT_RE = re.compile(r"\b(HYDROCHLORIDE|HYDROBROMIDE|HCL|SODIUM|POTASSIUM|CALCIUM|MAGNESIUM|MESYLATE|MESILATE|SULFATE|SULPHATE|"
                     r"ACETATE|MALEATE|TARTRATE|BITARTRATE|CITRATE|PHOSPHATE|FUMARATE|SUCCINATE|BESYLATE|TOSYLATE|"
                     r"DIHYDRATE|MONOHYDRATE|HYDRATE|ANHYDROUS|DISODIUM|DIPROPIONATE|PROPIONATE|BROMIDE|CHLORIDE|NITRATE)\b")


def drug_norm(k: str) -> str:
    return re.sub(r"\s+", " ", SALT_RE.sub(" ", k)).strip()


def to_set(x, aliases: dict[str, str] | None = None, drug: bool = False) -> set[str]:
    if x is None:
        return set()
    items = x if isinstance(x, list) else re.split(r"[,;\n]| and ", str(x))
    out = set()
    for it in items:
        if isinstance(it, dict):
            it = it.get("name") or it.get("symbol") or it.get("id") or ""
        k = norm_token(it).upper()
        if drug:
            k = drug_norm(k)
        if k:
            out.add((aliases or {}).get(k, k))
    return out


def score_answer(q: dict, parsed: dict | None) -> dict:
    """Returns {'score': 0..1, 'correct': bool, 'abstained': bool, ...}."""
    kind = q["answer_type"]
    gold = q["gold"]
    if parsed is None:
        return {"score": 0.0, "correct": False, "abstained": False, "parse_fail": True}
    ans = parsed.get("answer")
    nf = bool(parsed.get("not_found")) or ans in (None, "", "not found", "unknown")
    if kind == "notfound":
        return {"score": float(nf), "correct": nf, "abstained": nf}
    if nf:
        return {"score": 0.0, "correct": False, "abstained": True}
    if kind == "bool":
        b = to_bool(ans)
        ok = b is not None and b == gold
        return {"score": float(ok), "correct": ok, "abstained": False}
    if kind in {"int", "count", "year"}:
        v = to_num(ans)
        if v is None:
            return {"score": 0.0, "correct": False, "abstained": False}
        tol_abs = q.get("tol_abs", 0)
        tol_rel = q.get("tol_rel", 0)
        err = abs(v - gold)
        ok = err <= max(tol_abs, tol_rel * abs(gold))
        return {"score": float(ok), "correct": ok, "abstained": False, "abs_err": err}
    if kind == "enrollment":
        v = to_num(ans.get("count") if isinstance(ans, dict) else ans)
        t = (ans.get("type") if isinstance(ans, dict) else str(ans)).upper() if ans else ""
        ok_n = v is not None and v == gold["count"]
        ok_t = gold["type"] in t
        return {"score": (ok_n + ok_t) / 2, "correct": ok_n and ok_t, "abstained": False}
    if kind == "set":
        aliases = q.get("aliases", {})
        drug = q.get("template") in {"disease_late_stage_drugs", "multihop_generic_late_stage"}
        p, g = to_set(ans, aliases, drug), to_set(gold, aliases, drug)
        if not g:
            ok = not p
            return {"score": float(ok), "correct": ok, "abstained": False}
        tp = len(p & g)
        prec = tp / len(p) if p else 0.0
        rec = tp / len(g)
        f1 = 0.0 if tp == 0 else 2 * prec * rec / (prec + rec)
        return {"score": f1, "correct": f1 >= q.get("f1_threshold", 0.5), "abstained": False,
                "precision": prec, "recall": rec, "f1": f1}
    if kind == "text":
        f1 = token_f1(str(ans), str(gold))
        return {"score": f1, "correct": f1 >= q.get("f1_threshold", 0.5), "abstained": False, "f1": f1}
    raise ValueError(f"unknown answer_type {kind}")


def extract_ids(rec: dict) -> dict[str, set[str]]:
    text = rec.get("final_text") or ""
    ids = {k: set() for k in ID_PATTERNS}
    blob = text + " " + " ".join(map(str, (rec.get("parsed") or {}).get("identifiers") or []))
    for k, pat in ID_PATTERNS.items():
        for m in pat.finditer(blob):
            ids[k].add(m.group(1) if m.groups() else m.group())
    # bare PMIDs listed in identifiers
    for x in (rec.get("parsed") or {}).get("identifiers") or []:
        if re.fullmatch(r"\d{5,9}", str(x)):
            ids["pmid"].add(str(x))
    return ids


def grounded_ids(rec: dict) -> set[str]:
    """IDs that appeared in tool outputs during the run (i.e. not produced from memory)."""
    seen = set()
    for c in rec.get("tool_outputs") or []:
        if isinstance(c, str):
            for pat in ID_PATTERNS.values():
                seen |= {m.group(1) if m.groups() else m.group() for m in pat.finditer(c)}
            seen |= set(re.findall(r'"pmid":\s*"(\d+)"', c))
    return seen


async def validate_ids(all_ids: dict[str, set[str]]) -> dict[str, bool]:
    from biomcp.core.http import HttpClient, set_shared_client
    from biomcp.sources import chembl, ctgov, europepmc

    c = HttpClient(cassette_mode="off")
    set_shared_client(c)
    out: dict[str, bool] = {}
    sem = asyncio.Semaphore(4)

    async def chk(kind, i):
        async with sem:
            try:
                if kind == "nct":
                    r = await ctgov.get_trial(i, include_eligibility=False)
                elif kind == "chembl":
                    r = await chembl.get_molecule(i)
                else:
                    r = await europepmc.get_article(i)
                out[i] = r["data"] is not None
            except Exception:  # noqa: BLE001 - malformed IDs count as invalid
                out[i] = False

    await asyncio.gather(*(chk(k, i) for k, s in all_ids.items() for i in s))
    await c.aclose()
    return out


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(c - h, 4), round(c + h, 4))


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar p-value for discordant counts b, c."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = sum(math.comb(n, i) for i in range(k + 1)) / 2**n
    return min(1.0, 2 * p)


def paired_bootstrap(a: list[float], b: list[float], iters: int = 5000, seed: int = 1) -> tuple[float, float, float]:
    rng = random.Random(seed)
    n = len(a)
    diffs = []
    for _ in range(iters):
        idx = [rng.randrange(n) for _ in range(n)]
        diffs.append(sum(a[i] - b[i] for i in idx) / n)
    diffs.sort()
    return (round(sum(x - y for x, y in zip(a, b)) / n, 4), round(diffs[int(0.025 * iters)], 4), round(diffs[int(0.975 * iters)], 4))


def ece(conf: list[float], corr: list[bool], bins: int = 10) -> float:
    if not conf:
        return float("nan")
    tot = 0.0
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        idx = [i for i, c in enumerate(conf) if (lo <= c < hi) or (b == bins - 1 and c == 1.0)]
        if idx:
            acc = sum(corr[i] for i in idx) / len(idx)
            cf = sum(conf[i] for i in idx) / len(idx)
            tot += len(idx) / len(conf) * abs(acc - cf)
    return round(tot, 4)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--questions", default=str(ROOT / "eval/questions.jsonl"))
    ap.add_argument("--validate-ids", action="store_true")
    ap.add_argument("--exclude", default=str(ROOT / "eval/excluded_questions.json"), help="JSON list of question ids dropped in review")
    a = ap.parse_args()
    run = Path(a.run)
    qs = {json.loads(line)["id"]: json.loads(line) for line in Path(a.questions).read_text().splitlines() if line.strip()}
    recs = [json.loads(line) for line in (run / "raw.jsonl").read_text().splitlines() if line.strip()]
    # keep the last successful record per job
    dedup = {}
    for r in recs:
        dedup[(r["qid"], r["model"], r["condition"], r["rep"])] = r
    recs = [r for r in dedup.values() if r["qid"] in qs]
    errored = [r for r in recs if r.get("error")]
    recs = [r for r in recs if not r.get("error")]  # infrastructure failures (usage limits, timeouts) are not model answers
    excluded = set()
    if a.exclude and Path(a.exclude).exists():
        excluded = set(json.loads(Path(a.exclude).read_text()))
        recs = [r for r in recs if r["qid"] not in excluded]

    all_ids: dict[str, set[str]] = {k: set() for k in ID_PATTERNS}
    for r in recs:
        r["ids"] = {k: sorted(v) for k, v in extract_ids(r).items()}
        for k, v in r["ids"].items():
            all_ids[k] |= set(v)
    valid = asyncio.run(validate_ids(all_ids)) if a.validate_ids else {}

    scored = []
    for r in recs:
        q = qs[r["qid"]]
        s = score_answer(q, r["parsed"])
        qtext = q["question"]
        ids = [i for v in r["ids"].values() for i in v if i not in qtext]  # IDs given in the question don't count
        g = grounded_ids(r)
        s.update({
            "n_ids": len(ids),
            "n_ids_invalid": sum(1 for i in ids if valid.get(i) is False) if valid else None,
            "n_ids_ungrounded": sum(1 for i in ids if i not in g) if r["condition"] == "biomcp" else None,
            "confidence": (r["parsed"] or {}).get("confidence"),
        })
        scored.append({k: r[k] for k in ("qid", "template", "model", "condition", "rep", "latency_s", "n_web_searches", "error")}
                      | {"cost_usd": r.get("api_equivalent_cost_usd") or 0.0, "num_turns": r.get("num_turns")}
                      | {"n_tool_calls": len(r["tool_calls"]), "n_tool_errors": sum(t["is_error"] for t in r["tool_calls"]), **s,
                         "difficulty": q.get("difficulty")})
    (run / "scored.jsonl").write_text("\n".join(json.dumps(x) for x in scored) + "\n")

    summary: dict = {"by_condition": {}, "by_template": {}, "paired": {}, "id_validation": bool(valid),
                     "n_errored_runs_excluded": len(errored), "n_questions_excluded_by_review": len(excluded)}
    groups = defaultdict(list)
    for s in scored:
        groups[(s["model"], s["condition"])].append(s)
    for (m, c), xs in sorted(groups.items()):
        n = len(xs)
        k = sum(x["correct"] for x in xs)
        conf = [(float(x["confidence"]), x["correct"]) for x in xs if isinstance(x["confidence"], (int, float))]
        nid = sum(x["n_ids"] for x in xs)
        summary["by_condition"][f"{m}|{c}"] = {
            "n": n, "accuracy": round(k / n, 4), "accuracy_ci95": wilson(k, n),
            "mean_score": round(sum(x["score"] for x in xs) / n, 4),
            "abstain_rate": round(sum(x["abstained"] for x in xs) / n, 4),
            "parse_fail_rate": round(sum(bool(x.get("parse_fail")) for x in xs) / n, 4),
            "ids_emitted": nid,
            "invalid_id_rate": round(sum(x["n_ids_invalid"] or 0 for x in xs) / nid, 4) if (valid and nid) else None,
            "ungrounded_id_rate": round(sum(x["n_ids_ungrounded"] or 0 for x in xs) / nid, 4) if (c == "biomcp" and nid) else None,
            "ece": ece([cf for cf, _ in conf], [ok for _, ok in conf]),
            "brier": round(sum((cf - ok) ** 2 for cf, ok in conf) / len(conf), 4) if conf else None,
            "mean_api_equiv_cost_usd": round(sum(x["cost_usd"] for x in xs) / n, 5),
            "total_api_equiv_cost_usd": round(sum(x["cost_usd"] for x in xs), 3),
            "median_latency_s": sorted(x["latency_s"] for x in xs)[n // 2],
            "mean_tool_calls": round(sum(x["n_tool_calls"] for x in xs) / n, 2),
            "tool_error_rate": round(sum(x["n_tool_errors"] for x in xs) / max(1, sum(x["n_tool_calls"] for x in xs)), 4),
        }
        tmpl = defaultdict(list)
        for x in xs:
            tmpl[x["template"]].append(x)
        for t, ys in sorted(tmpl.items()):
            summary["by_template"].setdefault(t, {})[f"{m}|{c}"] = {
                "n": len(ys), "accuracy": round(sum(y["correct"] for y in ys) / len(ys), 4),
                "mean_score": round(sum(y["score"] for y in ys) / len(ys), 4)}

    # paired comparisons on rep 0: biomcp vs each other condition, per model
    for m in {s["model"] for s in scored}:
        r0 = {(s["qid"], s["condition"]): s for s in scored if s["model"] == m and s["rep"] == 0}
        for other in {s["condition"] for s in scored} - {"biomcp"}:
            qids = sorted({q for q, c in r0 if c == "biomcp"} & {q for q, c in r0 if c == other})
            if not qids:
                continue
            a_ = [r0[(q, "biomcp")]["correct"] for q in qids]
            b_ = [r0[(q, other)]["correct"] for q in qids]
            b = sum(x and not y for x, y in zip(a_, b_))
            c = sum(y and not x for x, y in zip(a_, b_))
            summary["paired"][f"{m}|biomcp_vs_{other}"] = {
                "n": len(qids), "biomcp_only_correct": b, "other_only_correct": c,
                "mcnemar_p": round(mcnemar_exact(b, c), 6),
                "acc_diff_ci95": paired_bootstrap([float(x) for x in a_], [float(y) for y in b_]),
                "score_diff_ci95": paired_bootstrap([r0[(q, "biomcp")]["score"] for q in qids], [r0[(q, other)]["score"] for q in qids]),
            }
    (run / "summary.json").write_text(json.dumps(summary, indent=1))

    lines = ["| model | condition | n | accuracy (95% CI) | mean score | abstain | invalid IDs | ungrounded IDs | ECE | API-equiv $/q (not billed) | median s | tool calls |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for key, v in summary["by_condition"].items():
        m, c = key.split("|")
        lines.append(f"| {m} | {c} | {v['n']} | {v['accuracy']:.3f} ({v['accuracy_ci95'][0]:.3f}–{v['accuracy_ci95'][1]:.3f}) | "
                     f"{v['mean_score']:.3f} | {v['abstain_rate']:.3f} | {v['invalid_id_rate']} | {v['ungrounded_id_rate']} | "
                     f"{v['ece']} | {v['mean_api_equiv_cost_usd']:.4f} | {v['median_latency_s']} | {v['mean_tool_calls']} |")
    lines += ["", "| comparison | n | biomcp-only correct | other-only correct | McNemar p | Δacc (95% CI) |", "|---|---|---|---|---|---|"]
    for key, v in summary["paired"].items():
        d = v["acc_diff_ci95"]
        lines.append(f"| {key} | {v['n']} | {v['biomcp_only_correct']} | {v['other_only_correct']} | {v['mcnemar_p']} | {d[0]:+.3f} ({d[1]:+.3f}, {d[2]:+.3f}) |")
    lines += ["", "| template | " + " | ".join(summary["by_condition"]) + " |", "|---|" + "---|" * len(summary["by_condition"])]
    for t, v in summary["by_template"].items():
        lines.append(f"| {t} | " + " | ".join(f"{v.get(k, {}).get('mean_score', float('nan')):.2f}" for k in summary["by_condition"]) + " |")
    (run / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
