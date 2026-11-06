"""Project 6, step 5: analysis (protocol sections 5 and 7).

Builds the analysis dataset from the ClinicalTrials.gov cohort, the ChEMBL drug map and (when present)
the LLM extraction, then reports:
  - flow (identified -> eligible window -> rare/NTD -> repurposed -> >=24 months follow-up)
  - stall proportion with Wilson 95% CIs, by stratum (non-oncology = headline, rare oncology, pooled)
    and by pre-specified subgroups (region, funder type, phase, disease group)
  - reasons for stopping (T3) when LLM labels exist
  - multivariable logistic regression (non-oncology stratum)
  - sensitivity analyses 1-5 (6 needs the human validation labels)
  - Rogan-Gladen misclassification correction when validation estimates are supplied

Repurposing is determined two ways and both are reported:
  det: deterministic rule from ChEMBL (protocol 4.2) -- approved parent (max_phase 4), first approval before
       the trial's start year, trial condition not among the drug's approved indications (MeSH), not a vaccine.
  llm: T2 label from the frozen LLM extraction (any drug judged repurposed = "true").
The pre-specified primary analysis uses the LLM labels once they pass the acceptance thresholds (6.4).
Until then everything here is PRELIMINARY and labelled as such.

    python project6/pipeline/analyze.py [--basis det|llm] [--out project6/results/<name>]
"""

from __future__ import annotations

import argparse
import gzip
import json
import math
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "project6/data"

ONC = re.compile(r"cancer|carcinoma|neoplasm|tumou?r|leuk(a)?emia|lymphoma|myeloma|sarcoma|glioma|blastoma|melanoma|"
                 r"malignan|myelodysplas|metasta", re.IGNORECASE)
VACCINE = re.compile(r"vaccin", re.IGNORECASE)
ACTIVE = {"NOT_YET_RECRUITING", "RECRUITING", "ENROLLING_BY_INVITATION", "ACTIVE_NOT_RECRUITING", "UNKNOWN"}
STOPPED = {"TERMINATED", "WITHDRAWN", "SUSPENDED"}

WHO_REGION = {
    "AFR": "Algeria Angola Benin Botswana Burkina_Faso Burundi Cameroon Cabo_Verde Central_African_Republic Chad Comoros Côte_d’Ivoire "
           "Democratic_Republic_of_the_Congo Equatorial_Guinea Eritrea Eswatini Ethiopia Gabon The_Gambia Ghana Guinea Guinea-Bissau Kenya "
           "Lesotho Liberia Madagascar Malawi Mali Mauritania Mauritius Mozambique Namibia Niger Nigeria Republic_of_the_Congo Rwanda "
           "Senegal Seychelles Sierra_Leone South_Africa South_Sudan Tanzania Togo Uganda Zambia Zimbabwe Reunion",
    "AMR": "Argentina Bahamas Barbados Belize Bolivia Brazil Canada Chile Colombia Costa_Rica Cuba Dominica Dominican_Republic Ecuador "
           "El_Salvador Grenada Guatemala Guyana Haiti Honduras Jamaica Mexico Nicaragua Panama Paraguay Peru Saint_Kitts_and_Nevis "
           "Saint_Lucia Suriname Trinidad_and_Tobago United_States Uruguay Venezuela Puerto_Rico French_Guiana Guadeloupe Martinique",
    "SEAR": "Bangladesh Bhutan North_Korea India Indonesia Maldives Burma Myanmar Nepal Sri_Lanka Thailand Timor-Leste",
    "EUR": "Albania Andorra Armenia Austria Azerbaijan Belarus Belgium Bosnia_and_Herzegovina Bulgaria Croatia Cyprus Czechia Denmark "
           "Estonia Finland France Georgia Germany Greece Hungary Iceland Ireland Israel Italy Kazakhstan Kyrgyzstan Latvia Lithuania "
           "Luxembourg Malta Monaco Montenegro Netherlands North_Macedonia Norway Poland Portugal Moldova Romania Russia San_Marino Serbia "
           "Slovakia Slovenia Spain Sweden Switzerland Tajikistan Turkey_(Türkiye) Turkmenistan Ukraine United_Kingdom Uzbekistan Kosovo "
           "Faroe_Islands Holy_See",
    "EMR": "Afghanistan Bahrain Djibouti Egypt Iran Iraq Jordan Kuwait Lebanon Libya Morocco Oman Pakistan Palestine Qatar Saudi_Arabia "
           "Somalia Sudan Syria Tunisia United_Arab_Emirates Yemen",
    "WPR": "Australia Brunei Cambodia China Cook_Islands Fiji Japan Kiribati Laos Malaysia Marshall_Islands Micronesia Mongolia Nauru "
           "New_Zealand Niue Palau Papua_New_Guinea Philippines South_Korea Samoa Singapore Solomon_Islands Tonga Tuvalu Vanuatu Vietnam "
           "Hong_Kong Taiwan Guam Christmas_Island",
}
C2R = {c.replace("_", " "): r for r, cs in WHO_REGION.items() for c in cs.split()}


# ---------- statistics ----------
def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return (None, None, None)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(p, 4), round(c - h, 4), round(c + h, 4))


def rogan_gladen(p_obs: float, se: float, sp: float) -> float:
    """Prevalence corrected for misclassification (Rogan & Gladen 1978), clipped to [0, 1]."""
    if se + sp - 1 <= 0:
        return float("nan")
    return min(1.0, max(0.0, (p_obs + sp - 1) / (se + sp - 1)))


def kappa(a: list[bool], b: list[bool]) -> float | None:
    n = len(a)
    if not n:
        return None
    po = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return round((po - pe) / (1 - pe), 4) if pe < 1 else None


# ---------- derivation ----------
def ym(s: str | None) -> date | None:
    if not s:
        return None
    p = s.split("-")
    return date(int(p[0]), int(p[1]) if len(p) > 1 else 6, int(p[2]) if len(p) > 2 else 15)


def months(a: date, b: date) -> float:
    return (b - a).days / 30.4375


def phase_group(ph: list[str]) -> str:
    s = set(ph or [])
    if s & {"PHASE3", "PHASE4"}:
        return "phase 3/4" if "PHASE2" not in s else "phase 2/3"
    if "PHASE2" in s:
        return "phase 1/2" if "PHASE1" in s else "phase 2"
    if s & {"PHASE1", "EARLY_PHASE1"}:
        return "phase 1"
    return "not applicable"


def funder(r: dict) -> str:
    c = r["lead_sponsor_class"]
    return {"INDUSTRY": "industry", "NIH": "government", "FED": "government", "OTHER_GOV": "government",
            "NETWORK": "academic/hospital network", "OTHER": "academic/hospital/nonprofit", "INDIV": "other"}.get(c, "other")


def region(r: dict) -> str:
    rs = {C2R.get(c, "unmapped") for c in r["countries"]}
    rs.discard("unmapped")
    if not rs:
        return "no sites listed"
    return next(iter(rs)) if len(rs) == 1 else "multi-region"


def years_txt(t: str | None) -> float | None:
    m = re.search(r"(\d+)\s*(Year|Month|Week|Day)", t or "", re.IGNORECASE)
    return None if not m else int(m.group(1)) / {"year": 1, "month": 12, "week": 52.1775, "day": 365.25}[m.group(2).lower()]


def repurposed_det(r: dict, dm: dict, start_year: int) -> tuple[bool, list[dict], bool]:
    mesh = {m.lower() for m in r["condition_mesh"]} | {c.lower() for c in r["conditions"]}
    parents = {}
    for n in r["drugs"] + r["drug_other_names"]:
        h = dm["names"].get(n.strip()) or {}
        if not h.get("unmatched") and h.get("parent_chembl_id"):
            parents[h["parent_chembl_id"]] = n
    out, generic = [], False
    for pid, n in parents.items():
        p = dm["parents"].get(pid) or {}
        appr = float(p.get("max_phase") or 0) >= 4
        fa = p.get("first_approval")
        ind = {x.lower() for x in p.get("approved_indications") or []}
        vac = bool(VACCINE.search((p.get("pref_name") or "") + " " + n)) or p.get("molecule_type") == "Vaccine component"
        ok = appr and fa is not None and int(fa) < start_year and not (ind & mesh) and not vac
        out.append({"parent": pid, "name": p.get("pref_name"), "approved": appr, "first_approval": fa, "repurposed": ok})
        generic |= ok and bool(p.get("generic_available_us"))
    return any(d["repurposed"] for d in out), out, generic


def build(snapshot: date, follow_up: float = 24, overdue: float = 12) -> list[dict]:
    dm = json.loads((D / "drug_map.json").read_text())
    llm = {}
    lp = D / "llm_extract_v1.jsonl"
    if lp.exists():
        for line in lp.read_text().splitlines():
            if line.strip():
                x = json.loads(line)
                llm[x["trial_id"]] = x
    rows = []
    with gzip.open(D / "cohort_ctgov.jsonl.gz", "rt") as f:
        for line in f:
            r = json.loads(line)
            reg = ym(r["first_submitted"])
            start = ym(r["start_date"]) or reg
            pcd = ym(r["primary_completion_date"])
            sy = start.year if start else reg.year
            rep, drugs, generic = repurposed_det(r, dm, sy)
            st = r["overall_status"]
            stalled_tws = st in STOPPED
            fu = months(reg, snapshot)
            lx = llm.get(r["trial_id"])
            rows.append({
                "id": r["trial_id"], "status": st, "registered": reg.isoformat(), "start_year": sy, "followup_m": round(fu, 1),
                "pcd_months_ago": round(months(pcd, snapshot), 1) if pcd else None,
                "stalled_tws": stalled_tws,
                "oncology": bool(ONC.search(" ".join(r["conditions"] + r["condition_mesh"]))),
                "rare": bool(r["match"]["rare"]), "ntd": bool(r["match"]["ntd"]),
                "rep_det": rep, "drugs_det": drugs, "generic_us": generic,
                "rep_llm": (any(d.get("repurposed") == "true" for d in lx["drugs"]) if lx else None),
                "cond_llm": lx["condition_category"] if lx else None,
                "stop_primary_llm": lx["primary_stop_reason"] if lx else None,
                "stop_all_llm": lx["stop_reasons"] if lx else None,
                "funder_llm": lx["funder_type"] if lx else None,
                "why_stopped": r["why_stopped"],
                "phase": phase_group(r["phases"]), "funder": funder(r), "region": region(r),
                "enrollment": r["enrollment"], "n_sites": r["n_sites"],
                "randomised": r["allocation"] == "RANDOMIZED", "masked": (r["masking"] or "NONE") != "NONE",
                "paediatric": (years_txt(r["min_age"]) or 0) < 18,
                "prevalence_basis": (r["match"]["rare"][0]["rarity_basis"] if r["match"]["rare"] else None),
            })
    return rows


def stalled(x: dict, overdue: float = 12, tws_only: bool = False) -> bool:
    if x["status"] in STOPPED:
        return True
    if tws_only:
        return False
    return x["status"] in ACTIVE and x["pcd_months_ago"] is not None and x["pcd_months_ago"] >= overdue


def disease_group(x):
    return "rare + NTD" if x["rare"] and x["ntd"] else ("NTD" if x["ntd"] else "rare")


def included(x, basis: str) -> bool:
    if basis == "llm":
        return bool(x["rep_llm"]) and x["cond_llm"] in ("rare", "ntd", "both")
    return x["rep_det"]


def prop_table(xs, key, overdue=12, tws_only=False):
    g = defaultdict(list)
    for x in xs:
        g[key(x)].append(stalled(x, overdue, tws_only))
    return {k: {"n": len(v), "stalled": sum(v), "p_ci": wilson(sum(v), len(v))} for k, v in sorted(g.items(), key=lambda kv: -len(kv[1]))}


def logistic(xs: list[dict]):
    try:
        import numpy as np
        import pandas as pd
        import statsmodels.formula.api as smf
    except ImportError:
        return {"error": "statsmodels not installed"}
    df = pd.DataFrame([{
        "y": int(stalled(x)), "funder": x["funder"], "phase": x["phase"], "region": x["region"],
        "log_enrol": math.log1p(x["enrollment"] or 0), "log_sites": math.log1p(x["n_sites"] or 0),
        "randomised": int(x["randomised"]), "masked": int(x["masked"]), "paediatric": int(x["paediatric"]),
        "ntd": int(x["ntd"]), "generic": int(x["generic_us"]), "start_year": x["start_year"]} for x in xs])
    # collapse sparse levels so every level has >= 30 trials (pre-specified to avoid separation)
    for c in ("funder", "phase", "region"):
        vc = df[c].value_counts()
        df[c] = df[c].where(df[c].map(vc) >= 30, "other/sparse")
    f = ("y ~ C(funder, Treatment('academic/hospital/nonprofit')) + C(phase, Treatment('phase 2')) + C(region, Treatment('AMR')) "
         "+ cr(log_enrol, df=4) + log_sites + randomised + masked + paediatric + ntd + generic + cr(start_year, df=4)")
    try:
        m = smf.logit(f, data=df).fit(disp=0, maxiter=200)
    except Exception as e:  # noqa: BLE001 - separation or singular design: report, Firth fallback documented
        return {"error": f"fit failed ({e!r}); protocol 7.3: refit with Firth penalisation"}
    ci = m.conf_int()
    out = {}
    for k in m.params.index:
        if k.startswith("cr(") or k == "Intercept":
            continue
        out[k] = {"or": round(float(np.exp(m.params[k])), 3), "ci": [round(float(np.exp(ci.loc[k, 0])), 3), round(float(np.exp(ci.loc[k, 1])), 3)],
                  "p": float(m.pvalues[k])}
    return {"n": int(m.nobs), "events": int(df.y.sum()), "pseudo_r2": round(float(m.prsquared), 4),
            "converged": bool(m.mle_retvals.get("converged")), "terms": out,
            "note": "splines (restricted cubic, 4 df) for log enrolment and start year; ORs for spline terms omitted"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--basis", choices=["det", "llm"], default="det")
    ap.add_argument("--out", default=None)
    ap.add_argument("--validation", default=None, help="JSON with sensitivity/specificity of inclusion and stall labels (from the validation sample)")
    a = ap.parse_args()
    man = json.loads((D / "cohort_ctgov.manifest.json").read_text())
    snap = date.fromisoformat(man["ctgov_version"]["dataTimestamp"][:10])
    out = Path(a.out or ROOT / f"project6/results/prelim_ctgov_{a.basis}")
    out.mkdir(parents=True, exist_ok=True)
    rows = build(snap)
    n_llm = sum(x["rep_llm"] is not None for x in rows)
    if a.basis == "llm" and n_llm < len(rows):
        print(f"warning: LLM labels for {n_llm}/{len(rows)} trials only; LLM basis restricted to labelled trials")
        rows = [x for x in rows if x["rep_llm"] is not None]
    inc = [x for x in rows if included(x, a.basis)]
    fu24 = [x for x in inc if x["followup_m"] >= 24]
    strata = {"non-oncology (headline)": [x for x in fu24 if not x["oncology"]], "rare oncology": [x for x in fu24 if x["oncology"]], "pooled": fu24}
    res = {"status": "PRELIMINARY: before human validation of LLM/deterministic labels (protocol 6.3-6.4)", "basis": a.basis,
           "snapshot": snap.isoformat(), "registry": "ClinicalTrials.gov only (ICTRP pending)",
           "flow": {"rare_or_ntd_candidates_ctgov": len(rows), "repurposed": len(inc), "followup_ge_24m": len(fu24),
                    "registered_lt_24m_described_only": len(inc) - len(fu24),
                    "non_oncology": len(strata["non-oncology (headline)"]), "rare_oncology": len(strata["rare oncology"])},
           "primary": {}, "subgroups": {}, "sensitivity": {}, "reasons": {}, "agreement_det_vs_llm": None}
    for name, xs in strata.items():
        k = sum(stalled(x) for x in xs)
        res["primary"][name] = {"n": len(xs), "stalled": k, "p_ci": wilson(k, len(xs)),
                                "components": dict(Counter(("stopped (T/W/S)" if x["status"] in STOPPED else "overdue without completion")
                                                           for x in xs if stalled(x)))}
        res["subgroups"][name] = {"region": prop_table(xs, lambda x: x["region"]), "funder": prop_table(xs, lambda x: x["funder"]),
                                  "phase": prop_table(xs, lambda x: x["phase"]), "disease group": prop_table(xs, disease_group)}
    hx = strata["non-oncology (headline)"]
    allinc = [x for x in inc if not x["oncology"]]
    sens = {
        "S1 follow-up >=12 months": [x for x in allinc if x["followup_m"] >= 12],
        "S1 follow-up >=36 months": [x for x in allinc if x["followup_m"] >= 36],
    }
    for k, xs in sens.items():
        s = sum(stalled(x) for x in xs)
        res["sensitivity"][k] = {"n": len(xs), "p_ci": wilson(s, len(xs))}
    for ov in (6, 24):
        s = sum(stalled(x, overdue=ov) for x in hx)
        res["sensitivity"][f"S2 overdue window {ov} months"] = {"n": len(hx), "p_ci": wilson(s, len(hx))}
    s = sum(stalled(x, tws_only=True) for x in hx)
    res["sensitivity"]["S3 terminated/withdrawn/suspended only"] = {"n": len(hx), "p_ci": wilson(s, len(hx))}
    xs = [x for x in hx if x["start_year"] not in (2020, 2021)]
    res["sensitivity"]["S4 excluding 2020-2021 starts"] = {"n": len(xs), "p_ci": wilson(sum(stalled(x) for x in xs), len(xs))}
    xs = [x for x in hx if x["status"] != "WITHDRAWN"]
    res["sensitivity"]["S7 excluding withdrawn (post hoc; see DEVIATIONS)"] = {"n": len(xs), "p_ci": wilson(sum(stalled(x) for x in xs), len(xs))}
    res["regression_non_oncology_excl_withdrawn"] = logistic(xs)
    res["sensitivity"]["S5 ClinicalTrials.gov only"] = {"note": "identical to primary until ICTRP records are added"}
    res["sensitivity"]["S6 human labels"] = {"note": "requires the adjudicated validation sample"}
    stopped = [x for x in hx if x["status"] in STOPPED]
    lab = [x for x in stopped if x["stop_primary_llm"]]
    res["reasons"] = {"stopped_trials": len(stopped), "with_llm_label": len(lab),
                      "why_stopped_missing": sum(not x["why_stopped"] for x in stopped),
                      "primary_reason": dict(Counter(x["stop_primary_llm"] for x in lab).most_common()),
                      "any_reason": dict(Counter(r for x in lab for r in x["stop_all_llm"] or []).most_common())}
    both = [x for x in rows if x["rep_llm"] is not None]
    if both:
        res["agreement_det_vs_llm"] = {"n": len(both), "agree": sum(x["rep_det"] == x["rep_llm"] for x in both),
                                       "kappa": kappa([x["rep_det"] for x in both], [bool(x["rep_llm"]) for x in both]),
                                       "det_only": sum(x["rep_det"] and not x["rep_llm"] for x in both),
                                       "llm_only": sum(x["rep_llm"] and not x["rep_det"] for x in both)}
    res["regression_non_oncology"] = logistic(hx)
    if a.validation:
        v = json.loads(Path(a.validation).read_text())
        p = res["primary"]["non-oncology (headline)"]["p_ci"][0]
        res["misclassification_corrected"] = {"stall_rg": rogan_gladen(p, v["stall_se"], v["stall_sp"]), "inputs": v}
    (out / "results.json").write_text(json.dumps(res, indent=1, default=str))
    with (out / "analysis_dataset.jsonl").open("w") as f:
        for x in rows:
            f.write(json.dumps({k: v for k, v in x.items() if k != "drugs_det"}) + "\n")
    write_md(res, out / "results.md")
    print((out / "results.md").read_text()[:4000])
    return 0


TERM_RE = re.compile(r"C\((\w+), Treatment\(.+?\)\)\[T\.(.+)\]")


def term_label(k: str) -> str:
    m = TERM_RE.fullmatch(k)
    return f"{m.group(1)}: {m.group(2)}" if m else k


def fmt(pc):
    return "–" if pc[0] is None else f"{100 * pc[0]:.1f}% ({100 * pc[1]:.1f}–{100 * pc[2]:.1f})"


def write_md(res, p: Path):
    L = [f"# Stalled repurposing trials: {res['status']}", "", f"Basis for repurposing: **{res['basis']}**. Snapshot {res['snapshot']}. {res['registry']}.", "",
         "## Flow", "", "| step | n |", "|---|---|"] + [f"| {k} | {v} |" for k, v in res["flow"].items()] + [
         "", "## Primary: proportion stalled (Wilson 95% CI)", "", "| stratum | n | stalled | % (95% CI) | stopped / overdue |", "|---|---|---|---|---|"]
    for k, v in res["primary"].items():
        L.append(f"| {k} | {v['n']} | {v['stalled']} | {fmt(v['p_ci'])} | {v['components']} |")
    for k, sg in res["subgroups"].items():
        L += ["", f"## Subgroups: {k}"]
        for name, t in sg.items():
            L += ["", f"**{name}**", "", "| level | n | % stalled (95% CI) |", "|---|---|---|"] + [f"| {lv} | {d['n']} | {fmt(d['p_ci'])} |" for lv, d in t.items()]
    L += ["", "## Sensitivity analyses (non-oncology)", "", "| analysis | n | % stalled (95% CI) |", "|---|---|---|"]
    for k, v in res["sensitivity"].items():
        L.append(f"| {k} | {v.get('n', '')} | {fmt(v['p_ci']) if 'p_ci' in v else v.get('note')} |")
    r = res["reasons"]
    L += ["", "## Reasons for stopping (non-oncology, LLM T3 labels)", "", (f"{r['stopped_trials']} stopped trials; {r['with_llm_label']} labelled; "
           f"{r['why_stopped_missing']} with no stated reason in the registry."), "", "| primary reason | n |", "|---|---|"] + [
          f"| {k} | {v} |" for k, v in r["primary_reason"].items()]
    if res.get("agreement_det_vs_llm"):
        a = res["agreement_det_vs_llm"]
        L += ["", "## Repurposing label agreement: deterministic rule vs LLM (T2)", "",
              f"n={a['n']}; agreement {a['agree']}/{a['n']}; kappa {a['kappa']}; rule-only {a['det_only']}; LLM-only {a['llm_only']}."]
    for key, title in (("regression_non_oncology", "Multivariable logistic regression (non-oncology; descriptive associations)"),
                       ("regression_non_oncology_excl_withdrawn", "Same model excluding withdrawn trials (post hoc: withdrawn trials list no sites by construction)")):
        g = res.get(key)
        if not g:
            continue
        L += ["", f"## {title}", ""]
        if "error" in g:
            L.append(g["error"])
            continue
        L += [f"n={g['n']}, events={g['events']}, pseudo-R²={g['pseudo_r2']}, converged={g['converged']}. {g['note']}.", "",
              "| term | OR (95% CI) | p |", "|---|---|---|"] + [
              f"| {term_label(k)} | {v['or']} ({v['ci'][0]}–{v['ci'][1]}) | {v['p']:.3g} |"
              for k, v in g["terms"].items()]
    p.write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
