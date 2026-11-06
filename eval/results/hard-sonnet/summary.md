| model | condition | n | accuracy (95% CI) | mean score | abstain | invalid IDs | ungrounded IDs | ECE | API-equiv $/q (not billed) | median s | tool calls |
|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-sonnet-5-5 | biomcp | 50 | 0.980 (0.895–0.997) | 0.973 | 0.000 | 0.0 | 0.0 | 0.0976 | 0.0347 | 11.46 | 2.84 |
| claude-sonnet-5-5 | no_tools | 50 | 0.300 (0.191–0.438) | 0.276 | 0.440 | 0.0 | None | 0.126 | 0.0077 | 7.19 | 0.0 |
| claude-sonnet-5-5 | web_search | 50 | 0.760 (0.626–0.857) | 0.736 | 0.000 | 0.0 | None | 0.0956 | 0.0115 | 10.32 | 0.7 |

| comparison | n | biomcp-only correct | other-only correct | McNemar p | Δacc (95% CI) |
|---|---|---|---|---|---|
| claude-sonnet-5-5|biomcp_vs_no_tools | 50 | 35 | 1 | 0.0 | +0.680 (+0.540, +0.820) |
| claude-sonnet-5-5|biomcp_vs_web_search | 50 | 12 | 1 | 0.003418 | +0.220 (+0.100, +0.340) |

| template | claude-sonnet-5-5|biomcp | claude-sonnet-5-5|no_tools | claude-sonnet-5-5|web_search |
|---|---|---|---|
| h_eligibility_check | 1.00 | 0.00 | 1.00 |
| h_late_generic_boxed | 0.92 | 0.31 | 0.39 |
| h_recruitment_footprint | 1.00 | 0.08 | 1.00 |
| h_source_conflict | 1.00 | 0.58 | 0.58 |
| h_untested_target_drugs | 0.89 | 0.71 | 0.71 |
