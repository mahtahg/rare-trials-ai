| model | condition | n | accuracy (95% CI) | mean score | abstain | invalid IDs | ungrounded IDs | ECE | API-equiv $/q (not billed) | median s | tool calls |
|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-sonnet-5-5 | biomcp_go | 109 | 0.945 (0.885–0.975) | 0.949 | 0.000 | 0.0 | 0.0 | 0.1085 | 0.0214 | 5.37 | 1.74 |

| comparison | n | biomcp-only correct | other-only correct | McNemar p | Δacc (95% CI) |
|---|---|---|---|---|---|

| template | claude-sonnet-5-5|biomcp_go |
|---|---|
| disease_top_targets | 0.82 |
| trial_count | 0.95 |
| trial_enrollment | 1.00 |
| trial_has_sap | 0.85 |
| trial_n_sites | 1.00 |
| trial_why_stopped | 1.00 |
