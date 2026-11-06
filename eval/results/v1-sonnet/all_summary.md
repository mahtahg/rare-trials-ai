| model | condition | n | accuracy (95% CI) | mean score | abstain | invalid IDs | ungrounded IDs | ECE | API-equiv $/q (not billed) | median s | tool calls |
|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-sonnet-5-5 | biomcp | 254 | 1.000 (0.985–1.000) | 1.000 | 0.079 | 0.0 | 0.0 | 0.0544 | 0.0159 | 8.14 | 1.34 |
| claude-sonnet-5-5 | no_tools | 254 | 0.469 (0.408–0.530) | 0.460 | 0.343 | 0.0 | None | 0.1339 | 0.0125 | 5.74 | 0.0 |
| claude-sonnet-5-5 | web_search | 254 | 0.819 (0.767–0.861) | 0.815 | 0.102 | 0.0 | None | 0.0861 | 0.0101 | 8.71 | 1.15 |

| comparison | n | biomcp-only correct | other-only correct | McNemar p | Δacc (95% CI) |
|---|---|---|---|---|---|
| claude-sonnet-5-5|biomcp_vs_web_search | 254 | 46 | 0 | 0.0 | +0.181 (+0.134, +0.232) |
| claude-sonnet-5-5|biomcp_vs_no_tools | 254 | 135 | 0 | 0.0 | +0.531 (+0.469, +0.595) |

| template | claude-sonnet-5-5|biomcp | claude-sonnet-5-5|no_tools | claude-sonnet-5-5|web_search |
|---|---|---|---|
| disease_late_stage_drugs | 0.99 | 0.47 | 0.48 |
| disease_rarity | 1.00 | 0.50 | 0.50 |
| disease_top_targets | 1.00 | 0.26 | 0.19 |
| drug_first_approval | 1.00 | 0.90 | 1.00 |
| drug_generic_us | 1.00 | 0.85 | 0.90 |
| drug_targets | 1.00 | 0.95 | 0.98 |
| multihop_generic_late_stage | 1.00 | 0.45 | 0.50 |
| not_found | 1.00 | 1.00 | 1.00 |
| trial_count | 1.00 | 0.25 | 0.95 |
| trial_enrollment | 1.00 | 0.00 | 1.00 |
| trial_has_sap | 1.00 | 0.35 | 1.00 |
| trial_n_sites | 1.00 | 0.00 | 1.00 |
| trial_why_stopped | 1.00 | 0.00 | 1.00 |
