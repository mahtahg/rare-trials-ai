| model | condition | n | accuracy (95% CI) | mean score | abstain | invalid IDs | ungrounded IDs | ECE | API-equiv $/q (not billed) | median s | tool calls |
|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-sonnet-5-5 | biomcp | 58 | 0.983 (0.909–0.997) | 0.983 | 0.000 | 0.0 | 0.0 | 0.0798 | 0.0228 | 8.11 | 3.0 |

| comparison | n | biomcp-only correct | other-only correct | McNemar p | Δacc (95% CI) |
|---|---|---|---|---|---|

| template | claude-sonnet-5-5|biomcp |
|---|---|
| drug_generic_us | 1.00 |
| h_late_generic_boxed | 0.92 |
| h_source_conflict | 1.00 |
| multihop_generic_late_stage | 1.00 |
