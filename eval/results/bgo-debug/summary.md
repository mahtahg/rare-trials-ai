| model | condition | n | accuracy (95% CI) | mean score | abstain | invalid IDs | ungrounded IDs | ECE | API-equiv $/q (not billed) | median s | tool calls |
|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-haiku-5-5 | biomcp_go | 8 | 0.750 (0.409–0.928) | 0.750 | 0.000 | 0.0 | 0.0 | 0.2225 | 0.0165 | 25.9 | 10.75 |

| comparison | n | biomcp-only correct | other-only correct | McNemar p | Δacc (95% CI) |
|---|---|---|---|---|---|

| template | claude-haiku-5-5|biomcp_go |
|---|---|
| h_eligibility_check | 1.00 |
| h_late_generic_boxed | 1.00 |
| h_recruitment_footprint | 1.00 |
| h_source_conflict | 0.50 |
| h_untested_target_drugs | 0.00 |
