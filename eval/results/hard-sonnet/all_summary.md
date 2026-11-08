| model | condition | n | accuracy (95% CI) | mean score | abstain | invalid IDs | ungrounded IDs | ECE | API-equiv $/q (not billed) | median s | tool calls |
|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-sonnet-5-5 | biomcp | 60 | 0.817 (0.701–0.894) | 0.823 | 0.000 | 0.0 | 0.0 | 0.0497 | 0.0400 | 12.42 | 3.98 |
| claude-sonnet-5-5 | biomcp_go | 60 | 0.733 (0.610–0.829) | 0.738 | 0.000 | 0.0 | 0.0 | 0.0908 | 0.0449 | 22.24 | 7.42 |
| claude-sonnet-5-5 | no_tools | 60 | 0.417 (0.301–0.543) | 0.373 | 0.367 | 0.0 | None | 0.0925 | 0.0080 | 7.53 | 0.0 |
| claude-sonnet-5-5 | web_search | 60 | 0.817 (0.701–0.894) | 0.788 | 0.000 | 0.0 | None | 0.1897 | 0.0116 | 10.29 | 0.73 |

| comparison | n | biomcp-only correct | other-only correct | McNemar p | Δacc (95% CI) |
|---|---|---|---|---|---|
| claude-sonnet-5-5|biomcp_vs_no_tools | 60 | 31 | 7 | 0.000116 | +0.400 (+0.217, +0.567) |
| claude-sonnet-5-5|biomcp_vs_biomcp_go | 60 | 10 | 5 | 0.301758 | +0.083 (-0.050, +0.217) |
| claude-sonnet-5-5|biomcp_vs_web_search | 60 | 7 | 7 | 1.0 | +0.000 (-0.117, +0.117) |

| template | claude-sonnet-5-5|biomcp | claude-sonnet-5-5|biomcp_go | claude-sonnet-5-5|no_tools | claude-sonnet-5-5|web_search |
|---|---|---|---|---|
| h_eligibility_check | 1.00 | 1.00 | 0.08 | 1.00 |
| h_late_generic_boxed | 0.92 | 0.42 | 0.31 | 0.39 |
| h_recruitment_footprint | 1.00 | 1.00 | 0.08 | 1.00 |
| h_source_conflict | 0.58 | 0.75 | 0.83 | 1.00 |
| h_untested_target_drugs | 0.62 | 0.52 | 0.56 | 0.55 |
