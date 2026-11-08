| model | condition | n | accuracy (95% CI) | mean score | abstain | invalid IDs | ungrounded IDs | ECE | API-equiv $/q (not billed) | median s | tool calls |
|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-sonnet-5-5 | biomcp | 58 | 0.862 (0.751–0.928) | 0.859 | 0.000 | None | 0.0 | 0.0795 | 0.0228 | 8.11 | 3.0 |

| comparison | n | biomcp-only correct | other-only correct | McNemar p | Δacc (95% CI) |
|---|---|---|---|---|---|

| template | claude-sonnet-5-5|biomcp |
|---|---|
| drug_generic_us | 0.90 |
| h_late_generic_boxed | 0.92 |
| h_source_conflict | 0.58 |
| multihop_generic_late_stage | 0.99 |
