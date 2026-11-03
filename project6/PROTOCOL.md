# Stalled drug-repurposing trials in rare and neglected tropical diseases: a cross-registry meta-research study with validated LLM-assisted data extraction

**Status:** draft protocol for OSF pre-registration (v0.1, 2026-11-03). Not yet registered.
**Lead:** Mahta Haghighat Ghahfarokhi (King's College London). Second reviewer: TBC. Senior advisor: TBC.
**Code and data:** github.com/mahtahg/rare-trials-ai (`project6/`), released under MIT/CC-BY at publication.

---

## 1. Background and rationale

Drug repurposing (testing an already-approved medicine for a new indication) is the main route to treatments for rare diseases and neglected tropical diseases (NTDs), where commercial incentives are weak. These trials are often investigator-led or nonprofit-funded, small, and multi-country. Registry studies show that a large share of trials are discontinued or never report, with poor recruitment the leading stated reason. However, evidence specific to *repurposing* trials in rare diseases and NTDs is limited, and existing studies mostly use ClinicalTrials.gov alone, under-representing trials registered in low- and middle-income countries.

Large language models (LLMs) could make this kind of registry-scale meta-research cheap and repeatable. They are only usable as research instruments if their extraction is validated against human reviewers and their error is propagated into the estimates. This study does both.

## 2. Objectives

**Primary.** Estimate the proportion of interventional drug-repurposing trials in rare diseases and NTDs, registered 2010–2026, that stall (definition §5.1). Report it overall and by region, funder type, phase and disease group.

**Secondary.**
1. Describe the stated reasons for stopping, using a pre-specified taxonomy (§5.3).
2. Estimate associations between trial characteristics and stalling (§7.3).
3. Quantify enrolment shortfall (actual vs anticipated enrolment).
4. Validate LLM-assisted extraction against blinded dual human extraction. Report inter-rater agreement and LLM accuracy, and correct prevalence estimates for measured misclassification.
5. Release a reusable, versioned dataset and pipeline.

## 3. Design

Cross-sectional meta-research study of trial registry records. No human participants and no patient-level data, so ethics approval is not required (public registry data). Reporting follows STROBE where applicable; LLM components follow TRIPOD-LLM reporting items.

## 4. Data sources and eligibility

### 4.1 Sources (snapshot date fixed at download and reported)
- **ClinicalTrials.gov:** API v2, full download of interventional studies.
- **WHO ICTRP:** full dataset covering all primary registries, obtained as WHO's weekly ZIP-compressed CSV by institutional request (requested November 2026). If access is not granted in time, the fallback is per-query CSV/XML export from the ICTRP Search Portal for the disease lexicon, with coverage reported.
- **Orphanet/Orphadata:**
  - Product 9: point prevalence.
  - Product 1: cross-references to MeSH, ICD-10, OMIM and MONDO.
  - Release version recorded.
- **WHO list of NTDs:** the current list of disease groups, version recorded.
- **ChEMBL:** release recorded. Supplies drug normalisation, approval status and first approval year.
- **US FDA Drugs@FDA (openFDA):** marketed-generic availability, used as the off-patent proxy.

### 4.2 Inclusion
- Interventional study, registered (first submitted) between 2010-01-01 and the snapshot date.
- At least one condition is (a) a rare disease (Orphanet point prevalence ≤5 per 10,000, the EU definition) or (b) a WHO-listed NTD.
- At least one drug intervention is a **repurposed drug**: an active ingredient with any regulatory approval (ChEMBL max_phase = 4) whose first approval year is earlier than the trial's start year, tested for an indication other than one it was approved for at trial start.

### 4.3 Exclusion
- Biologics or medicines whose only approval is for the trial condition (not repurposing).
- Vaccines.
- Non-drug interventions only (devices, behavioural).
- Dietary supplements without regulatory drug approval.
- Expanded-access records.

### 4.4 Deduplication
Cross-registry duplicates are linked using secondary IDs (registry cross-references, EudraCT/CTIS numbers, sponsor protocol IDs). For records without IDs, fuzzy matching on title, sponsor and start date is used and then confirmed manually. The record with the most complete status history is retained; linkage decisions are logged.

## 5. Outcomes and definitions

### 5.1 Primary outcome: stalled (binary)
A trial is **stalled** if any of the following holds at the snapshot date:
- (a) Overall status is Terminated, Withdrawn or Suspended.
- (b) **Overdue without completion.** Status is Not yet recruiting, Recruiting, Enrolling by invitation, Active not recruiting or Unknown, and the anticipated primary completion date is ≥12 months before the snapshot date.

The primary analysis is restricted to trials with ≥24 months between registration and snapshot, so that recent trials have had time to stall. Trials registered within 24 months are described but not included in stall estimates.

### 5.2 Secondary outcomes
- **Enrolment shortfall:** actual enrolment below 50% of the originally anticipated enrolment (from record history where available). Applies to Completed/Terminated trials with ACTUAL enrolment.
- **Results posted:** results posted in the registry (ClinicalTrials.gov only; descriptive).

### 5.3 Reason-for-stopping taxonomy (pre-specified; adapted from prior registry studies)
1. Insufficient accrual / recruitment
2. Funding / financial
3. Sponsor or business decision (non-scientific)
4. Drug or supply issues
5. Efficacy / futility (including interim analysis)
6. Safety / toxicity
7. Regulatory, ethics or contractual
8. Logistics, site or investigator (e.g. PI left)
9. COVID-19 pandemic
10. Scientific landscape changed (new evidence, standard of care changed)
11. Other
12. Not stated

Multiple categories may be assigned. The **primary reason** is the first stated.

### 5.4 Covariates
- Region of sites (WHO region; multi-region flag)
- Lead sponsor / funder type: industry, academic/hospital, government, nonprofit/foundation, mixed
- Phase
- Anticipated enrolment
- Number of sites
- Randomisation, masking
- Disease group (rare vs NTD) and prevalence class
- Paediatric inclusion
- Start year
- Off-patent proxy (marketed US generic at trial start)
- Registry of origin

## 6. Data extraction

### 6.1 Deterministic extraction
Status, dates, enrolment, phase, sites, countries and sponsor fields come directly from structured registry data via versioned code. The only exception is an ICTRP field that requires normalisation.

### 6.2 LLM-assisted extraction (four tasks)
- **T1 Condition mapping:** maps free-text conditions to an ORPHA code or a WHO NTD group, or "neither".
- **T2 Repurposed-drug determination:** normalises each drug intervention to a ChEMBL ID and judges whether it is repurposed under §4.2, given ChEMBL approval and indication data supplied in the prompt.
- **T3 Reason-for-stopping classification:** classifies free-text why-stopped statements into the §5.3 taxonomy.
- **T4 Funder-type classification:** classifies lead sponsor and collaborators.

All four tasks share the same set-up:
- **Model:** a pinned model ID (`claude-sonnet-5-5`), recorded with the date range of calls.
- **Output:** a JSON schema enforced through tool use.
- **Prompts:** version-controlled, frozen before the validation sample is drawn.
- **Uncertainty:** each output carries a self-reported confidence. A separate abstention option ("cannot determine") is permitted.

The model is given only registry text and the supplied reference data, never the human labels.

### 6.3 Human validation
- **Sample:** stratified random sample of **n = 350** candidate records, drawn by a seeded script after prompts are frozen. Strata are registry source × status × disease group. Records near the inclusion boundary (LLM confidence < 0.7) are over-sampled at a ratio of 2:1, and estimates are re-weighted.
- **Calibration:** 30 records extracted jointly by both reviewers to align on definitions. These are excluded from agreement statistics.
- **Independent extraction:** the remaining **320 records** are extracted independently by two reviewers using a web form. Reviewers are blinded to each other and to LLM output. Blinding is enforced by the form's access rules: each reviewer writes only their own extraction subtree, and a second reviewer with Contributor access cannot read the first reviewer's entries. The study lead, as owner, could technically read both, so the form never displays the other reviewer's entries or any LLM output, and the lead will not query them before adjudication.
- **Adjudication:** disagreements are resolved by discussion. Persisting disagreements go to a senior advisor. The adjudicated label is the reference standard.
- **Sample-size rationale:** 320 records give a 95% CI half-width of about ±0.04 for LLM accuracy near 0.90, and about ±0.07 for Cohen's κ near 0.75 on binary items.

### 6.4 Pre-specified acceptance thresholds
LLM extraction is used for the full dataset only if, for each task, accuracy against adjudicated labels has a lower 95% CI bound ≥ 0.85, with κ(LLM, reference) ≥ 0.70. Tasks failing the threshold fall back to human extraction of all records for that field. If the volume makes this infeasible, the field is reported as exploratory.

## 7. Analysis

### 7.1 Descriptive
- Counts by registry, year, disease group, region, phase and funder.
- Flow diagram: records identified → deduplicated → screened → included.

### 7.2 Primary
- Proportion stalled, with Wilson 95% CIs, overall and by pre-specified subgroups: region, funder type, phase and disease group.
- **Misclassification correction:** inclusion and stall prevalence are adjusted for LLM misclassification. Sensitivity and specificity estimated in the validation sample are applied with the Rogan–Gladen estimator, and CIs are bootstrapped over both the full and validation samples.

### 7.3 Associations
- **Model:** multivariable logistic regression for stalled vs not, with covariates from §5.4. Firth penalisation is used if separation occurs. Continuous predictors use restricted cubic splines.
- **Reporting:** odds ratios with 95% CIs. Associations are interpreted as descriptive, not causal.

### 7.4 Sensitivity analyses
1. Follow-up threshold changed to ≥12 and ≥36 months.
2. Overdue window changed to ≥6 and ≥24 months.
3. Stalled = Terminated/Withdrawn/Suspended only, dropping the overdue criterion.
4. Trials starting 2020–2021 excluded (COVID-19).
5. ClinicalTrials.gov records only.
6. Human labels in place of LLM labels, restricted to the validation sample.

### 7.5 Missing data
Reasons for stopping that are missing are reported as "Not stated", not imputed. Missing covariates are handled by multiple imputation with chained equations (m = 20) if >5% are missing, with complete-case analysis as a sensitivity analysis.

## 8. Reproducibility and openness
- **Release:** all code, prompts, model IDs, registry snapshot dates and release versions, raw LLM outputs, validation labels and analysis outputs.
- **Re-running:** the pipeline is re-runnable from a single command against a new snapshot.
- **Deviations:** any deviation from this protocol is logged with a date and rationale in `project6/DEVIATIONS.md`.

## 9. Limitations (anticipated)
- **Registry staleness:** non-US registries often do not update status, so the "overdue" criterion may misclassify completed-but-unupdated trials as stalled. Sensitivity analysis 3 addresses this.
- **Approval data:** ChEMBL approval data are not jurisdiction-specific, and the US generic-availability proxy does not represent all markets.
- **Time-varying approvals:** repurposing status depends on time-varying approved indications, which ChEMBL does not fully capture historically. This is mitigated by human validation of T2.
- **Self-reported reasons:** stated reasons for stopping are self-reported and often vague.

## 10. Timeline
| Weeks | Task |
|---|---|
| 1–2 | Pre-register; download snapshots; build cohort |
| 3–4 | Freeze prompts; run LLM extraction; draw validation sample |
| 5–8 | Calibration, dual extraction, adjudication |
| 9–10 | Analysis |
| 11–12 | Write-up; submit (target: BMJ Global Health or Orphanet Journal of Rare Diseases) |
