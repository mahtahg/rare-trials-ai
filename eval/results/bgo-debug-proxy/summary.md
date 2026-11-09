| model | condition | n | accuracy (95% CI) | mean score | abstain | invalid IDs | ungrounded IDs | ECE | API-equiv $/q (not billed) | median s | tool calls |
|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-haiku-5-5 | biomcp_go | 9 | 0.667 (0.354–0.879) | 0.667 | 0.000 | 0.0 | 0.0 | 0.24 | 0.0430 | 37.69 | 13.11 |

| comparison | n | biomcp-only correct | other-only correct | McNemar p | Δacc (95% CI) |
|---|---|---|---|---|---|

| template | claude-haiku-5-5|biomcp_go |
|---|---|
| h_eligibility_check | 1.00 |
| h_late_generic_boxed | 0.50 |
| h_recruitment_footprint | 0.50 |
| h_source_conflict | 1.00 |
| h_untested_target_drugs | 0.00 |
