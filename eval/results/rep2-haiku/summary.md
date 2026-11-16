| model | condition | n | accuracy (95% CI) | mean score | abstain | invalid IDs | ungrounded IDs | ECE | API-equiv $/q (not billed) | median s | tool calls |
|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-haiku-5-5 | biomcp | 25 | 1.000 (0.867–1.000) | 1.000 | 0.000 | 0.0 | 0.0 | 0.0372 | 0.0008 | 4.07 | 1.0 |
| claude-haiku-5-5 | biomcp_go | 25 | 0.960 (0.805–0.993) | 0.980 | 0.000 | 0.0 | 0.0 | 0.108 | 0.0011 | 3.92 | 1.24 |
| claude-haiku-5-5 | no_tools | 25 | 0.000 (0.000–0.133) | 0.004 | 0.880 | None | None | 0.0413 | 0.0075 | 4.57 | 0.0 |
| claude-haiku-5-5 | web_search | 25 | 1.000 (0.867–1.000) | 0.997 | 0.000 | 0.0 | None | 0.072 | 0.0014 | 8.08 | 1.8 |

| comparison | n | biomcp-only correct | other-only correct | McNemar p | Δacc (95% CI) |
|---|---|---|---|---|---|
| claude-haiku-5-5|biomcp_vs_biomcp_go | 25 | 1 | 0 | 1.0 | +0.040 (+0.000, +0.120) |
| claude-haiku-5-5|biomcp_vs_no_tools | 24 | 24 | 0 | 0.0 | +1.000 (+1.000, +1.000) |
| claude-haiku-5-5|biomcp_vs_web_search | 25 | 0 | 0 | 1.0 | +0.000 (+0.000, +0.000) |

| template | claude-haiku-5-5|biomcp | claude-haiku-5-5|biomcp_go | claude-haiku-5-5|no_tools | claude-haiku-5-5|web_search |
|---|---|---|---|---|
| trial_enrollment | 1.00 | 0.90 | 0.00 | 1.00 |
| trial_why_stopped | 1.00 | 1.00 | 0.00 | 1.00 |
