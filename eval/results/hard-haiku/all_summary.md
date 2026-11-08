| model | condition | n | accuracy (95% CI) | mean score | abstain | invalid IDs | ungrounded IDs | ECE | API-equiv $/q (not billed) | median s | tool calls |
|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-haiku-5-5 | biomcp | 60 | 0.800 (0.682–0.882) | 0.794 | 0.000 | 0.0 | 0.0 | 0.0857 | 0.0032 | 10.81 | 6.3 |
| claude-haiku-5-5 | biomcp_go | 60 | 0.633 (0.507–0.744) | 0.661 | 0.017 | 0.0 | 0.0 | 0.1037 | 0.0109 | 22.18 | 12.33 |
| claude-haiku-5-5 | no_tools | 60 | 0.283 (0.185–0.408) | 0.278 | 0.500 | None | None | 0.137 | 0.0080 | 6.15 | 0.0 |
| claude-haiku-5-5 | web_search | 60 | 0.783 (0.664–0.869) | 0.782 | 0.083 | 0.0 | None | 0.1748 | 0.0199 | 23.33 | 4.17 |

| comparison | n | biomcp-only correct | other-only correct | McNemar p | Δacc (95% CI) |
|---|---|---|---|---|---|
| claude-haiku-5-5|biomcp_vs_no_tools | 60 | 35 | 4 | 0.0 | +0.517 (+0.367, +0.667) |
| claude-haiku-5-5|biomcp_vs_web_search | 60 | 8 | 7 | 1.0 | +0.017 (-0.100, +0.150) |
| claude-haiku-5-5|biomcp_vs_biomcp_go | 60 | 13 | 3 | 0.021271 | +0.167 (+0.050, +0.283) |

| template | claude-haiku-5-5|biomcp | claude-haiku-5-5|biomcp_go | claude-haiku-5-5|no_tools | claude-haiku-5-5|web_search |
|---|---|---|---|---|
| h_eligibility_check | 0.92 | 0.92 | 0.17 | 1.00 |
| h_late_generic_boxed | 0.92 | 0.75 | 0.42 | 0.64 |
| h_recruitment_footprint | 1.00 | 0.75 | 0.00 | 0.92 |
| h_source_conflict | 0.58 | 0.50 | 0.75 | 1.00 |
| h_untested_target_drugs | 0.55 | 0.39 | 0.06 | 0.35 |
