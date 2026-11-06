| model | condition | n | accuracy (95% CI) | mean score | abstain | invalid IDs | ungrounded IDs | ECE | API-equiv $/q (not billed) | median s | tool calls |
|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-haiku-5-5 | biomcp | 50 | 0.960 (0.865–0.989) | 0.947 | 0.000 | 0.0 | 0.0 | 0.1328 | 0.0026 | 9.73 | 3.98 |
| claude-haiku-5-5 | no_tools | 50 | 0.260 (0.159–0.396) | 0.253 | 0.480 | None | None | 0.1255 | 0.0042 | 5.87 | 0.0 |
| claude-haiku-5-5 | web_search | 50 | 0.780 (0.648–0.873) | 0.763 | 0.040 | 0.0 | None | 0.1302 | 0.0194 | 20.03 | 3.94 |

| comparison | n | biomcp-only correct | other-only correct | McNemar p | Δacc (95% CI) |
|---|---|---|---|---|---|
| claude-haiku-5-5|biomcp_vs_no_tools | 50 | 36 | 1 | 0.0 | +0.700 (+0.560, +0.820) |
| claude-haiku-5-5|biomcp_vs_web_search | 50 | 11 | 2 | 0.022461 | +0.180 (+0.060, +0.300) |

| template | claude-haiku-5-5|biomcp | claude-haiku-5-5|no_tools | claude-haiku-5-5|web_search |
|---|---|---|---|
| h_eligibility_check | 0.91 | 0.09 | 1.00 |
| h_late_generic_boxed | 0.92 | 0.42 | 0.64 |
| h_recruitment_footprint | 1.00 | 0.00 | 0.92 |
| h_source_conflict | 1.00 | 0.50 | 0.58 |
| h_untested_target_drugs | 0.78 | 0.22 | 0.49 |
