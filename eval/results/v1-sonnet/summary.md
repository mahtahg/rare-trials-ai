| model | condition | n | accuracy (95% CI) | mean score | abstain | invalid IDs | ungrounded IDs | ECE | API-equiv $/q (not billed) | median s | tool calls |
|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-sonnet-5-5 | biomcp | 254 | 0.992 (0.972–0.998) | 0.991 | 0.079 | 0.0 | 0.0 | 0.0465 | 0.0159 | 8.14 | 1.34 |
| claude-sonnet-5-5 | biomcp_go | 254 | 0.874 (0.828–0.909) | 0.853 | 0.079 | 0.0 | 0.0 | 0.0924 | 0.0207 | 7.23 | 2.33 |
| claude-sonnet-5-5 | no_tools | 254 | 0.469 (0.408–0.530) | 0.461 | 0.343 | 0.0 | None | 0.1422 | 0.0125 | 5.74 | 0.0 |
| claude-sonnet-5-5 | web_search | 254 | 0.819 (0.767–0.861) | 0.816 | 0.102 | 0.0 | None | 0.0861 | 0.0101 | 8.71 | 1.15 |

| comparison | n | biomcp-only correct | other-only correct | McNemar p | Δacc (95% CI) |
|---|---|---|---|---|---|
| claude-sonnet-5-5|biomcp_vs_no_tools | 254 | 134 | 1 | 0.0 | +0.524 (+0.461, +0.587) |
| claude-sonnet-5-5|biomcp_vs_biomcp_go | 254 | 31 | 1 | 0.0 | +0.118 (+0.079, +0.161) |
| claude-sonnet-5-5|biomcp_vs_web_search | 254 | 45 | 1 | 0.0 | +0.173 (+0.126, +0.224) |

| template | claude-sonnet-5-5|biomcp | claude-sonnet-5-5|biomcp_go | claude-sonnet-5-5|no_tools | claude-sonnet-5-5|web_search |
|---|---|---|---|---|
| disease_late_stage_drugs | 0.99 | 0.61 | 0.47 | 0.48 |
| disease_rarity | 1.00 | 0.50 | 0.50 | 0.50 |
| disease_top_targets | 1.00 | 0.87 | 0.26 | 0.19 |
| drug_first_approval | 1.00 | 0.80 | 0.90 | 1.00 |
| drug_generic_us | 0.90 | 0.90 | 0.85 | 0.90 |
| drug_targets | 1.00 | 0.94 | 0.95 | 0.98 |
| multihop_generic_late_stage | 0.99 | 0.60 | 0.47 | 0.52 |
| not_found | 1.00 | 1.00 | 1.00 | 1.00 |
| trial_count | 1.00 | 0.95 | 0.25 | 0.95 |
| trial_enrollment | 1.00 | 1.00 | 0.00 | 1.00 |
| trial_has_sap | 1.00 | 0.85 | 0.35 | 1.00 |
| trial_n_sites | 1.00 | 1.00 | 0.00 | 1.00 |
| trial_why_stopped | 1.00 | 1.00 | 0.00 | 1.00 |
