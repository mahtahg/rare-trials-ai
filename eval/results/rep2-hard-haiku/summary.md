| model | condition | n | accuracy (95% CI) | mean score | abstain | invalid IDs | ungrounded IDs | ECE | API-equiv $/q (not billed) | median s | tool calls |
|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-haiku-5-5 | biomcp | 16 | 0.938 (0.717–0.989) | 0.938 | 0.000 | 0.0 | 0.0 | 0.1844 | 0.0041 | 9.4 | 4.19 |
| claude-haiku-5-5 | biomcp_go | 16 | 0.812 (0.570–0.934) | 0.781 | 0.000 | 0.0 | 0.0 | 0.2656 | 0.0367 | 26.59 | 17.69 |
| claude-haiku-5-5 | no_tools | 16 | 0.125 (0.035–0.360) | 0.104 | 0.562 | None | None | 0.0846 | 0.0006 | 4.36 | 0.0 |
| claude-haiku-5-5 | web_search | 17 | 0.824 (0.590–0.938) | 0.824 | 0.000 | 0.0 | None | 0.2971 | 0.0136 | 17.67 | 3.65 |

| comparison | n | biomcp-only correct | other-only correct | McNemar p | Δacc (95% CI) |
|---|---|---|---|---|---|
| claude-haiku-5-5|biomcp_vs_biomcp_go | 16 | 3 | 1 | 0.625 | +0.125 (-0.125, +0.375) |
| claude-haiku-5-5|biomcp_vs_no_tools | 15 | 13 | 1 | 0.001831 | +0.800 (+0.467, +1.000) |
| claude-haiku-5-5|biomcp_vs_web_search | 16 | 2 | 1 | 1.0 | +0.062 (-0.125, +0.250) |

| template | claude-haiku-5-5|biomcp | claude-haiku-5-5|biomcp_go | claude-haiku-5-5|no_tools | claude-haiku-5-5|web_search |
|---|---|---|---|---|
| h_late_generic_boxed | 0.75 | 0.62 | 0.42 | 0.40 |
| h_recruitment_footprint | 1.00 | 0.83 | 0.00 | 1.00 |
