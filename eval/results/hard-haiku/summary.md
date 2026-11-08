| model | condition | n | accuracy (95% CI) | mean score | abstain | invalid IDs | ungrounded IDs | ECE | API-equiv $/q (not billed) | median s | tool calls |
|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-haiku-5-5 | biomcp | 50 | 0.860 (0.738–0.930) | 0.847 | 0.000 | 0.0 | 0.0 | 0.1048 | 0.0026 | 9.73 | 3.98 |
| claude-haiku-5-5 | biomcp_go | 50 | 0.680 (0.542–0.792) | 0.693 | 0.020 | 0.0 | 0.0 | 0.1224 | 0.0120 | 19.28 | 11.52 |
| claude-haiku-5-5 | no_tools | 50 | 0.320 (0.208–0.458) | 0.313 | 0.480 | None | None | 0.1298 | 0.0042 | 5.87 | 0.0 |
| claude-haiku-5-5 | web_search | 50 | 0.880 (0.762–0.944) | 0.863 | 0.040 | 0.0 | None | 0.2018 | 0.0194 | 20.03 | 3.94 |

| comparison | n | biomcp-only correct | other-only correct | McNemar p | Δacc (95% CI) |
|---|---|---|---|---|---|
| claude-haiku-5-5|biomcp_vs_web_search | 50 | 6 | 7 | 1.0 | -0.020 (-0.160, +0.120) |
| claude-haiku-5-5|biomcp_vs_biomcp_go | 50 | 11 | 2 | 0.022461 | +0.180 (+0.060, +0.320) |
| claude-haiku-5-5|biomcp_vs_no_tools | 50 | 31 | 4 | 3e-06 | +0.540 (+0.360, +0.720) |

| template | claude-haiku-5-5|biomcp | claude-haiku-5-5|biomcp_go | claude-haiku-5-5|no_tools | claude-haiku-5-5|web_search |
|---|---|---|---|---|
| h_eligibility_check | 0.91 | 0.91 | 0.09 | 1.00 |
| h_late_generic_boxed | 0.92 | 0.75 | 0.42 | 0.64 |
| h_recruitment_footprint | 1.00 | 0.75 | 0.00 | 0.92 |
| h_source_conflict | 0.58 | 0.50 | 0.75 | 1.00 |
| h_untested_target_drugs | 0.78 | 0.21 | 0.22 | 0.49 |
