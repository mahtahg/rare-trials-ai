| model | condition | n | accuracy (95% CI) | mean score | abstain | invalid IDs | ungrounded IDs | ECE | API-equiv $/q (not billed) | median s | tool calls |
|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-haiku-5-5 | biomcp | 58 | 0.879 (0.771–0.940) | 0.876 | 0.000 | None | 0.0 | 0.1014 | 0.0017 | 8.65 | 3.98 |

| comparison | n | biomcp-only correct | other-only correct | McNemar p | Δacc (95% CI) |
|---|---|---|---|---|---|

| template | claude-haiku-5-5|biomcp |
|---|---|
| drug_generic_us | 0.90 |
| h_late_generic_boxed | 1.00 |
| h_source_conflict | 0.58 |
| multihop_generic_late_stage | 0.99 |
