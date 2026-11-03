| model | condition | n | accuracy (95% CI) | mean score | abstain | invalid IDs | ungrounded IDs | ECE | API-equiv $/q (not billed) | median s | tool calls |
|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-sonnet-5-5 | biomcp | 5 | 1.000 (0.566–1.000) | 1.000 | 0.200 | 0.5 | 0.0 | 0.024 | 0.0164 | 7.21 | 1.2 |
| claude-sonnet-5-5 | no_tools | 5 | 1.000 (0.566–1.000) | 1.000 | 0.200 | 0.5 | None | 0.232 | 0.0057 | 5.58 | 0.0 |
| claude-sonnet-5-5 | web_search | 5 | 1.000 (0.566–1.000) | 1.000 | 0.200 | 0.5 | None | 0.052 | 0.0066 | 6.41 | 0.4 |

| comparison | n | biomcp-only correct | other-only correct | McNemar p | Δacc (95% CI) |
|---|---|---|---|---|---|
| claude-sonnet-5-5|biomcp_vs_web_search | 5 | 0 | 0 | 1.0 | +0.000 (+0.000, +0.000) |
| claude-sonnet-5-5|biomcp_vs_no_tools | 5 | 0 | 0 | 1.0 | +0.000 (+0.000, +0.000) |

| template | claude-sonnet-5-5|biomcp | claude-sonnet-5-5|no_tools | claude-sonnet-5-5|web_search |
|---|---|---|---|
| smoke | 1.00 | 1.00 | 1.00 |
