| model | condition | n | accuracy (95% CI) | mean score | abstain | invalid IDs | ungrounded IDs | ECE | API-equiv $/q (not billed) | median s | tool calls |
|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-sonnet-5-5 | biomcp | 198 | 1.000 (0.981–1.000) | 1.000 | 0.000 | None | 0.0654 | 0.0441 | 0.0158 | 8.28 | 1.04 |
| claude-sonnet-5-5 | no_tools | 199 | 0.402 (0.336–0.471) | 0.399 | 0.337 | None | None | 0.0955 | 0.0142 | 5.88 | 0.0 |
| claude-sonnet-5-5 | web_search | 198 | 0.849 (0.792–0.892) | 0.849 | 0.030 | None | None | 0.1229 | 0.0103 | 10.02 | 1.28 |

| comparison | n | biomcp-only correct | other-only correct | McNemar p | Δacc (95% CI) |
|---|---|---|---|---|---|
| claude-sonnet-5-5|biomcp_vs_no_tools | 198 | 119 | 0 | 0.0 | +0.601 (+0.530, +0.672) |
| claude-sonnet-5-5|biomcp_vs_web_search | 198 | 30 | 0 | 0.0 | +0.151 (+0.106, +0.202) |

| template | claude-sonnet-5-5|biomcp | claude-sonnet-5-5|no_tools | claude-sonnet-5-5|web_search |
|---|---|---|---|
| disease_late_stage_drugs | 0.99 | 0.47 | 0.48 |
| disease_top_targets | 1.00 | 0.26 | 0.19 |
| drug_first_approval | 1.00 | 0.90 | 1.00 |
| drug_generic_us | 1.00 | 0.85 | 0.90 |
| drug_targets | 1.00 | 0.94 | 0.98 |
| trial_count | 1.00 | 0.25 | 0.95 |
| trial_enrollment | 1.00 | 0.00 | 1.00 |
| trial_has_sap | 1.00 | 0.35 | 1.00 |
| trial_n_sites | 1.00 | 0.00 | 1.00 |
| trial_why_stopped | 1.00 | 0.00 | 1.00 |
