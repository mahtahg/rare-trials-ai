| model | condition | n | accuracy (95% CI) | mean score | abstain | invalid IDs | ungrounded IDs | ECE | API-equiv $/q (not billed) | median s | tool calls |
|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-sonnet-5-5 | biomcp | 50 | 0.880 (0.762–0.944) | 0.873 | 0.000 | 0.0 | 0.0 | 0.0472 | 0.0347 | 11.46 | 2.84 |
| claude-sonnet-5-5 | biomcp_go | 50 | 0.820 (0.692–0.902) | 0.799 | 0.000 | 0.0 | 0.0 | 0.1298 | 0.0619 | 15.66 | 6.64 |
| claude-sonnet-5-5 | no_tools | 50 | 0.360 (0.241–0.499) | 0.336 | 0.440 | 0.0 | None | 0.074 | 0.0077 | 7.19 | 0.0 |
| claude-sonnet-5-5 | web_search | 50 | 0.860 (0.738–0.930) | 0.836 | 0.000 | 0.0 | None | 0.1556 | 0.0115 | 10.32 | 0.7 |

| comparison | n | biomcp-only correct | other-only correct | McNemar p | Δacc (95% CI) |
|---|---|---|---|---|---|
| claude-sonnet-5-5|biomcp_vs_no_tools | 50 | 31 | 5 | 1.3e-05 | +0.520 (+0.320, +0.700) |
| claude-sonnet-5-5|biomcp_vs_web_search | 50 | 7 | 6 | 1.0 | +0.020 (-0.120, +0.160) |
| claude-sonnet-5-5|biomcp_vs_biomcp_go | 50 | 7 | 4 | 0.548828 | +0.060 (-0.060, +0.200) |

| template | claude-sonnet-5-5|biomcp | claude-sonnet-5-5|biomcp_go | claude-sonnet-5-5|no_tools | claude-sonnet-5-5|web_search |
|---|---|---|---|---|
| h_eligibility_check | 1.00 | 1.00 | 0.00 | 1.00 |
| h_late_generic_boxed | 0.92 | 0.42 | 0.31 | 0.39 |
| h_recruitment_footprint | 1.00 | 1.00 | 0.08 | 1.00 |
| h_source_conflict | 0.58 | 0.83 | 0.83 | 1.00 |
| h_untested_target_drugs | 0.89 | 0.66 | 0.71 | 0.71 |
