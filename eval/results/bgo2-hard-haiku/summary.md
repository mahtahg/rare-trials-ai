| model | condition | n | accuracy (95% CI) | mean score | abstain | invalid IDs | ungrounded IDs | ECE | API-equiv $/q (not billed) | median s | tool calls |
|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-haiku-5-5 | biomcp_go | 50 | 0.760 (0.626–0.857) | 0.769 | 0.040 | 0.0 | 0.0 | 0.1032 | 0.0165 | 17.62 | 10.86 |

| comparison | n | biomcp-only correct | other-only correct | McNemar p | Δacc (95% CI) |
|---|---|---|---|---|---|

| template | claude-haiku-5-5|biomcp_go |
|---|---|
| h_eligibility_check | 1.00 |
| h_late_generic_boxed | 0.58 |
| h_recruitment_footprint | 1.00 |
| h_source_conflict | 0.67 |
| h_untested_target_drugs | 0.15 |
