| model | condition | n | accuracy (95% CI) | mean score | abstain | invalid IDs | ungrounded IDs | ECE | API-equiv $/q (not billed) | median s | tool calls |
|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-haiku-5-5 | biomcp | 214 | 0.991 (0.967–0.997) | 0.988 | 0.000 | 0.0 | 0.0 | 0.0758 | 0.0012 | 6.25 | 1.6 |
| claude-haiku-5-5 | no_tools | 214 | 0.332 (0.272–0.397) | 0.315 | 0.495 | 0.5 | None | 0.1018 | 0.0059 | 5.66 | 0.0 |
| claude-haiku-5-5 | web_search | 214 | 0.790 (0.730–0.839) | 0.779 | 0.164 | 0.0 | None | 0.1438 | 0.0094 | 16.27 | 3.17 |

| comparison | n | biomcp-only correct | other-only correct | McNemar p | Δacc (95% CI) |
|---|---|---|---|---|---|
| claude-haiku-5-5|biomcp_vs_web_search | 214 | 45 | 2 | 0.0 | +0.201 (+0.145, +0.257) |
| claude-haiku-5-5|biomcp_vs_no_tools | 213 | 141 | 0 | 0.0 | +0.662 (+0.596, +0.728) |

| template | claude-haiku-5-5|biomcp | claude-haiku-5-5|no_tools | claude-haiku-5-5|web_search |
|---|---|---|---|
| disease_late_stage_drugs | 0.99 | 0.35 | 0.16 |
| disease_top_targets | 0.98 | 0.06 | 0.02 |
| drug_first_approval | 1.00 | 0.80 | 1.00 |
| drug_generic_us | 1.00 | 0.85 | 0.95 |
| drug_targets | 1.00 | 0.92 | 0.93 |
| multihop_generic_late_stage | 1.00 | 0.37 | 0.47 |
| trial_count | 0.90 | 0.00 | 0.95 |
| trial_enrollment | 1.00 | 0.05 | 1.00 |
| trial_has_sap | 1.00 | 0.00 | 1.00 |
| trial_n_sites | 1.00 | 0.05 | 1.00 |
| trial_why_stopped | 1.00 | 0.00 | 1.00 |
| not_found | nan | 1.00 | nan |
