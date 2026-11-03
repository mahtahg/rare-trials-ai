| model | condition | n | accuracy (95% CI) | mean score | abstain | invalid IDs | ungrounded IDs | ECE | API-equiv $/q (not billed) | median s | tool calls |
|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-sonnet-5-5 | biomcp | 254 | 0.779 (0.725–0.826) | 0.779 | 0.000 | 0.0 | 0.0654 | 0.0441 | 0.0123 | 7.44 | 0.81 |
| claude-sonnet-5-5 | no_tools | 254 | 0.315 (0.261–0.374) | 0.313 | 0.264 | 0.1667 | None | 0.0955 | 0.0112 | 5.41 | 0.0 |
| claude-sonnet-5-5 | web_search | 254 | 0.661 (0.601–0.717) | 0.661 | 0.024 | 0.0381 | None | 0.1229 | 0.0081 | 7.87 | 1.0 |

| comparison | n | biomcp-only correct | other-only correct | McNemar p | Δacc (95% CI) |
|---|---|---|---|---|---|
| claude-sonnet-5-5|biomcp_vs_no_tools | 254 | 119 | 1 | 0.0 | +0.465 (+0.402, +0.528) |
| claude-sonnet-5-5|biomcp_vs_web_search | 254 | 30 | 0 | 0.0 | +0.118 (+0.079, +0.158) |

| template | claude-sonnet-5-5|biomcp | claude-sonnet-5-5|no_tools | claude-sonnet-5-5|web_search |
|---|---|---|---|
| disease_late_stage_drugs | 0.99 | 0.47 | 0.48 |
| disease_rarity | 0.00 | 0.00 | 0.00 |
| disease_top_targets | 1.00 | 0.26 | 0.19 |
| drug_first_approval | 1.00 | 0.90 | 1.00 |
| drug_generic_us | 1.00 | 0.85 | 0.90 |
| drug_targets | 0.90 | 0.90 | 0.88 |
| multihop_generic_late_stage | 0.00 | 0.00 | 0.00 |
| not_found | 0.00 | 0.00 | 0.00 |
| trial_count | 1.00 | 0.25 | 0.95 |
| trial_enrollment | 1.00 | 0.00 | 1.00 |
| trial_has_sap | 1.00 | 0.35 | 1.00 |
| trial_n_sites | 1.00 | 0.00 | 1.00 |
| trial_why_stopped | 1.00 | 0.00 | 1.00 |
