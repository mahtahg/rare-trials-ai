| model | condition | n | accuracy (95% CI) | mean score | abstain | invalid IDs | ungrounded IDs | ECE | API-equiv $/q (not billed) | median s | tool calls |
|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-sonnet-5-5 | biomcp | 22 | 0.955 (0.782–0.992) | 0.955 | 0.000 | 0.0 | 0.0 | 0.1332 | 0.0546 | 8.42 | 3.27 |
| claude-sonnet-5-5 | biomcp_go | 22 | 0.818 (0.615–0.927) | 0.818 | 0.000 | 0.0 | 0.0 | 0.2136 | 0.0883 | 21.93 | 12.05 |
| claude-sonnet-5-5 | no_tools | 22 | 0.318 (0.164–0.527) | 0.303 | 0.318 | 0.0 | None | 0.331 | 0.0095 | 6.88 | 0.0 |
| claude-sonnet-5-5 | web_search | 23 | 0.696 (0.491–0.844) | 0.681 | 0.000 | 0.0 | None | 0.2326 | 0.0145 | 8.98 | 0.74 |

| comparison | n | biomcp-only correct | other-only correct | McNemar p | Δacc (95% CI) |
|---|---|---|---|---|---|
| claude-sonnet-5-5|biomcp_vs_no_tools | 21 | 14 | 1 | 0.000977 | +0.619 (+0.333, +0.857) |
| claude-sonnet-5-5|biomcp_vs_biomcp_go | 22 | 4 | 1 | 0.375 | +0.136 (-0.045, +0.318) |
| claude-sonnet-5-5|biomcp_vs_web_search | 22 | 6 | 1 | 0.125 | +0.227 (+0.000, +0.455) |

| template | claude-sonnet-5-5|biomcp | claude-sonnet-5-5|biomcp_go | claude-sonnet-5-5|no_tools | claude-sonnet-5-5|web_search |
|---|---|---|---|---|
| h_late_generic_boxed | 0.90 | 0.60 | 0.33 | 0.33 |
| h_recruitment_footprint | 1.00 | 1.00 | 0.27 | 1.00 |
