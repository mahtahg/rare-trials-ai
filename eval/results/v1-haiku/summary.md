| model | condition | n | accuracy (95% CI) | mean score | abstain | invalid IDs | ungrounded IDs | ECE | API-equiv $/q (not billed) | median s | tool calls |
|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-haiku-5-5 | biomcp | 201 | 0.990 (0.965–0.997) | 0.987 | 0.000 | 0.0857 | 0.0 | 0.0708 | 0.0011 | 6.03 | 1.35 |
| claude-haiku-5-5 | no_tools | 198 | 0.313 (0.253–0.381) | 0.307 | 0.515 | 0.0 | None | 0.0865 | 0.0063 | 5.63 | 0.0 |
| claude-haiku-5-5 | web_search | 201 | 0.796 (0.735–0.846) | 0.796 | 0.164 | 0.0701 | None | 0.1257 | 0.0076 | 15.24 | 2.93 |

| comparison | n | biomcp-only correct | other-only correct | McNemar p | Δacc (95% CI) |
|---|---|---|---|---|---|
| claude-haiku-5-5|biomcp_vs_web_search | 201 | 41 | 2 | 0.0 | +0.194 (+0.134, +0.254) |
| claude-haiku-5-5|biomcp_vs_no_tools | 198 | 134 | 0 | 0.0 | +0.677 (+0.611, +0.742) |

| template | claude-haiku-5-5|biomcp | claude-haiku-5-5|no_tools | claude-haiku-5-5|web_search |
|---|---|---|---|
| disease_late_stage_drugs | 0.99 | 0.35 | 0.16 |
| disease_top_targets | 0.98 | 0.06 | 0.02 |
| drug_first_approval | 1.00 | 0.80 | 1.00 |
| drug_generic_us | 1.00 | 0.85 | 0.95 |
| drug_targets | 1.00 | 0.93 | 0.93 |
| multihop_generic_late_stage | 1.00 | 0.00 | 0.00 |
| trial_count | 0.90 | 0.00 | 0.95 |
| trial_enrollment | 1.00 | 0.05 | 1.00 |
| trial_has_sap | 1.00 | 0.00 | 1.00 |
| trial_n_sites | 1.00 | 0.05 | 1.00 |
| trial_why_stopped | 1.00 | 0.00 | 1.00 |
