| model | condition | n | accuracy (95% CI) | mean score | abstain | invalid IDs | ungrounded IDs | ECE | API-equiv $/q (not billed) | median s | tool calls |
|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-haiku-5-5 | biomcp | 58 | 1.000 (0.938–1.000) | 1.000 | 0.000 | 0.0 | 0.0 | 0.1141 | 0.0017 | 8.65 | 3.98 |

| comparison | n | biomcp-only correct | other-only correct | McNemar p | Δacc (95% CI) |
|---|---|---|---|---|---|

| template | claude-haiku-5-5|biomcp |
|---|---|
| drug_generic_us | 1.00 |
| h_late_generic_boxed | 1.00 |
| h_source_conflict | 1.00 |
| multihop_generic_late_stage | 1.00 |
