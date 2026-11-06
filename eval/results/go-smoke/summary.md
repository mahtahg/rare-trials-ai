| model | condition | n | accuracy (95% CI) | mean score | abstain | invalid IDs | ungrounded IDs | ECE | API-equiv $/q (not billed) | median s | tool calls |
|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-sonnet-5-5 | biomcp_go | 13 | 0.769 (0.497–0.918) | 0.710 | 0.077 | 0.0 | 0.0 | 0.1323 | 0.0234 | 9.22 | 2.46 |

| comparison | n | biomcp-only correct | other-only correct | McNemar p | Δacc (95% CI) |
|---|---|---|---|---|---|

| template | claude-sonnet-5-5|biomcp_go |
|---|---|
| disease_late_stage_drugs | 0.73 |
| disease_rarity | 1.00 |
| disease_top_targets | 1.00 |
| drug_first_approval | 1.00 |
| drug_generic_us | 0.00 |
| drug_targets | 1.00 |
| multihop_generic_late_stage | 0.50 |
| not_found | 1.00 |
| trial_count | 0.00 |
| trial_enrollment | 1.00 |
| trial_has_sap | 0.00 |
| trial_n_sites | 1.00 |
| trial_why_stopped | 1.00 |
