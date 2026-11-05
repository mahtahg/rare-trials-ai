| model | condition | n | accuracy (95% CI) | mean score | abstain | invalid IDs | ungrounded IDs | ECE | API-equiv $/q (not billed) | median s | tool calls |
|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-sonnet-5-5 | biomcp | 60 | 0.900 (0.798–0.953) | 0.906 | 0.000 | 0.0 | 0.0 | 0.0927 | 0.0400 | 12.42 | 3.98 |
| claude-sonnet-5-5 | no_tools | 60 | 0.367 (0.256–0.493) | 0.323 | 0.367 | 0.0 | None | 0.1242 | 0.0080 | 7.53 | 0.0 |
| claude-sonnet-5-5 | web_search | 60 | 0.733 (0.610–0.829) | 0.704 | 0.000 | 0.0 | None | 0.1263 | 0.0116 | 10.29 | 0.73 |

| comparison | n | biomcp-only correct | other-only correct | McNemar p | Δacc (95% CI) |
|---|---|---|---|---|---|
| claude-sonnet-5-5|biomcp_vs_no_tools | 60 | 35 | 3 | 0.0 | +0.533 (+0.367, +0.683) |
| claude-sonnet-5-5|biomcp_vs_web_search | 60 | 12 | 2 | 0.012939 | +0.167 (+0.050, +0.283) |

| template | claude-sonnet-5-5|biomcp | claude-sonnet-5-5|no_tools | claude-sonnet-5-5|web_search |
|---|---|---|---|
| h_eligibility_check | 1.00 | 0.08 | 1.00 |
| h_late_generic_boxed | 0.92 | 0.31 | 0.39 |
| h_recruitment_footprint | 1.00 | 0.08 | 1.00 |
| h_source_conflict | 1.00 | 0.58 | 0.58 |
| h_untested_target_drugs | 0.62 | 0.56 | 0.55 |
