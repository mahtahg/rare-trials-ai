| model | condition | n | accuracy (95% CI) | mean score | abstain | invalid IDs | ungrounded IDs | ECE | API-equiv $/q (not billed) | median s | tool calls |
|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-sonnet-5-5 | biomcp | 55 | 1.000 (0.935–1.000) | 1.000 | 0.000 | 0.0 | 0.0 | 0.0229 | 0.0135 | 4.34 | 1.05 |
| claude-sonnet-5-5 | biomcp_go | 55 | 0.964 (0.877–0.990) | 0.973 | 0.000 | 0.0 | 0.0 | 0.136 | 0.0207 | 4.71 | 1.25 |
| claude-sonnet-5-5 | no_tools | 55 | 0.054 (0.019–0.148) | 0.054 | 0.727 | None | None | 0.0409 | 0.0052 | 4.23 | 0.0 |
| claude-sonnet-5-5 | web_search | 56 | 1.000 (0.936–1.000) | 0.999 | 0.000 | 0.0 | None | 0.0695 | 0.0079 | 5.48 | 1.23 |

| comparison | n | biomcp-only correct | other-only correct | McNemar p | Δacc (95% CI) |
|---|---|---|---|---|---|
| claude-sonnet-5-5|biomcp_vs_no_tools | 54 | 51 | 0 | 0.0 | +0.944 (+0.870, +1.000) |
| claude-sonnet-5-5|biomcp_vs_web_search | 55 | 0 | 0 | 1.0 | +0.000 (+0.000, +0.000) |
| claude-sonnet-5-5|biomcp_vs_biomcp_go | 55 | 2 | 0 | 0.5 | +0.036 (+0.000, +0.091) |

| template | claude-sonnet-5-5|biomcp | claude-sonnet-5-5|biomcp_go | claude-sonnet-5-5|no_tools | claude-sonnet-5-5|web_search |
|---|---|---|---|---|
| trial_enrollment | 1.00 | 0.97 | 0.00 | 1.00 |
| trial_has_sap | 1.00 | 0.93 | 0.20 | 1.00 |
| trial_why_stopped | 1.00 | 1.00 | 0.00 | 1.00 |
