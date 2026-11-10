| model | condition | n | accuracy (95% CI) | mean score | abstain | invalid IDs | ungrounded IDs | ECE | API-equiv $/q (not billed) | median s | tool calls |
|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-sonnet-5-5 | biomcp_go | 254 | 0.874 (0.828–0.909) | 0.853 | 0.079 | 0.0 | 0.0 | 0.0924 | 0.0207 | 7.23 | 2.33 |

| comparison | n | biomcp-only correct | other-only correct | McNemar p | Δacc (95% CI) |
|---|---|---|---|---|---|

| template | claude-sonnet-5-5|biomcp_go |
|---|---|
| disease_late_stage_drugs | 0.61 |
| disease_rarity | 0.50 |
| disease_top_targets | 0.87 |
| drug_first_approval | 0.80 |
| drug_generic_us | 0.90 |
| drug_targets | 0.94 |
| multihop_generic_late_stage | 0.60 |
| not_found | 1.00 |
| trial_count | 0.95 |
| trial_enrollment | 1.00 |
| trial_has_sap | 0.85 |
| trial_n_sites | 1.00 |
| trial_why_stopped | 1.00 |
