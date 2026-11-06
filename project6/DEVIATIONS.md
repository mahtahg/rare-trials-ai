# Deviations from protocol

Logged with date and rationale. The protocol (PROTOCOL.md v0.1) is **not yet registered on OSF**; entries below
record decisions made after any data were viewed, so the registration can state them openly.

| date | change | rationale | data viewed before the change? |
|---|---|---|---|
| 2026-11-06 | Preliminary ClinicalTrials.gov analysis run (`project6/pipeline/analyze.py --basis det`) before OSF registration, using a deterministic repurposing rule (ChEMBL approved parent, first approval before start year, condition not an approved indication, not a vaccine). | Pipeline testing at the lead's request ("complete all projects now"). Outputs are labelled PRELIMINARY. | Yes: stall proportions and subgroup estimates were viewed. The OSF registration must disclose this; the pre-specified primary analysis (LLM labels meeting §6.4 thresholds, then misclassification-corrected) is unchanged. |
| 2026-11-06 | Deterministic rule reported as a secondary comparator for T2, with agreement (Cohen's κ) against LLM labels. | Gives a transparent, model-free baseline for the repurposing determination. | Yes (as above). |
| 2026-11-06 | Sensitivity analysis S7 (exclude Withdrawn) and a regression refit without Withdrawn trials added. | Withdrawn trials never enrol, so they list no sites by construction; "no sites listed" and site count are partly outcome-defined. | Yes: the "no sites listed" region level showed a high stall proportion (63%), which prompted the check. |
| 2026-11-06 | Region level "no sites listed" kept as its own category; WHO region assigned only when all listed countries fall in one region, else "multi-region". | Protocol §5.4 lists region and a multi-region flag without specifying trials with no sites. | Yes. |
| 2026-11-06 | Until T4 labels pass validation, funder type is mapped from ClinicalTrials.gov `lead_sponsor_class` (OTHER → academic/hospital/nonprofit, which cannot separate nonprofits). | Fallback only; the T4 LLM label is primary. | Yes. |
