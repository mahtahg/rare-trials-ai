| model | condition | n | accuracy (95% CI) | mean score | abstain | invalid IDs | ungrounded IDs | ECE | API-equiv $/q (not billed) | median s | tool calls |
|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-haiku-5-5 | biomcp | 60 | 0.883 (0.778–0.942) | 0.877 | 0.000 | None | 0.0 | 0.1007 | 0.0032 | 10.81 | 6.3 |
| claude-haiku-5-5 | biomcp_go | 60 | 0.667 (0.541–0.773) | 0.694 | 0.017 | None | 0.0 | 0.0853 | 0.0109 | 22.18 | 12.33 |
| claude-haiku-5-5 | no_tools | 60 | 0.233 (0.144–0.354) | 0.228 | 0.500 | None | None | 0.1333 | 0.0080 | 6.15 | 0.0 |
| claude-haiku-5-5 | web_search | 60 | 0.700 (0.575–0.801) | 0.698 | 0.083 | None | None | 0.1118 | 0.0199 | 23.33 | 4.17 |

| comparison | n | biomcp-only correct | other-only correct | McNemar p | Δacc (95% CI) |
|---|---|---|---|---|---|
| claude-haiku-5-5|biomcp_vs_no_tools | 60 | 40 | 1 | 0.0 | +0.650 (+0.517, +0.767) |
| claude-haiku-5-5|biomcp_vs_biomcp_go | 60 | 15 | 2 | 0.00235 | +0.217 (+0.100, +0.333) |
| claude-haiku-5-5|biomcp_vs_web_search | 60 | 13 | 2 | 0.007385 | +0.183 (+0.067, +0.300) |

| template | claude-haiku-5-5|biomcp | claude-haiku-5-5|biomcp_go | claude-haiku-5-5|no_tools | claude-haiku-5-5|web_search |
|---|---|---|---|---|
| h_eligibility_check | 0.92 | 0.92 | 0.17 | 1.00 |
| h_late_generic_boxed | 0.92 | 0.75 | 0.42 | 0.64 |
| h_recruitment_footprint | 1.00 | 0.75 | 0.00 | 0.92 |
| h_source_conflict | 1.00 | 0.67 | 0.50 | 0.58 |
| h_untested_target_drugs | 0.55 | 0.39 | 0.06 | 0.35 |
