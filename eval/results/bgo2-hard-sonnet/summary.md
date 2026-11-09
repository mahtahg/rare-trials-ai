| model | condition | n | accuracy (95% CI) | mean score | abstain | invalid IDs | ungrounded IDs | ECE | API-equiv $/q (not billed) | median s | tool calls |
|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-sonnet-5-5 | biomcp_go | 29 | 0.759 (0.579–0.878) | 0.759 | 0.000 | 0.0 | 0.0 | 0.1859 | 0.0860 | 22.25 | 9.55 |

| comparison | n | biomcp-only correct | other-only correct | McNemar p | Δacc (95% CI) |
|---|---|---|---|---|---|

| template | claude-sonnet-5-5|biomcp_go |
|---|---|
| h_eligibility_check | 1.00 |
| h_late_generic_boxed | 0.42 |
| h_recruitment_footprint | 1.00 |
