| model | condition | n | accuracy (95% CI) | mean score | abstain | invalid IDs | ungrounded IDs | ECE | API-equiv $/q (not billed) | median s | tool calls |
|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-sonnet-5-5 | biomcp_go | 50 | 0.820 (0.692–0.902) | 0.799 | 0.000 | 0.0 | 0.0 | 0.1298 | 0.0619 | 15.66 | 6.64 |

| comparison | n | biomcp-only correct | other-only correct | McNemar p | Δacc (95% CI) |
|---|---|---|---|---|---|

| template | claude-sonnet-5-5|biomcp_go |
|---|---|
| h_eligibility_check | 1.00 |
| h_late_generic_boxed | 0.42 |
| h_recruitment_footprint | 1.00 |
| h_source_conflict | 0.83 |
| h_untested_target_drugs | 0.66 |
