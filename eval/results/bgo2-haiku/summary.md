| model | condition | n | accuracy (95% CI) | mean score | abstain | invalid IDs | ungrounded IDs | ECE | API-equiv $/q (not billed) | median s | tool calls |
|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-haiku-5-5 | biomcp_go | 254 | 0.791 (0.737–0.837) | 0.785 | 0.138 | 0.0 | 0.0 | 0.0904 | 0.0025 | 10.1 | 4.49 |

| comparison | n | biomcp-only correct | other-only correct | McNemar p | Δacc (95% CI) |
|---|---|---|---|---|---|

| template | claude-haiku-5-5|biomcp_go |
|---|---|
| disease_late_stage_drugs | 0.38 |
| disease_rarity | 0.25 |
| disease_top_targets | 0.87 |
| drug_first_approval | 0.85 |
| drug_generic_us | 1.00 |
| drug_targets | 0.94 |
| multihop_generic_late_stage | 0.51 |
| not_found | 1.00 |
| trial_count | 0.80 |
| trial_enrollment | 0.97 |
| trial_has_sap | 0.55 |
| trial_n_sites | 1.00 |
| trial_why_stopped | 1.00 |
