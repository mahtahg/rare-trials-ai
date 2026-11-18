| model | condition | n | accuracy (95% CI) | mean score | abstain | invalid IDs | ungrounded IDs | ECE | API-equiv $/q (not billed) | median s | tool calls |
|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-haiku-5-5 | biomcp | 254 | 0.965 (0.934–0.981) | 0.961 | 0.079 | 0.0 | 0.0 | 0.0611 | 0.0012 | 6.25 | 1.7 |
| claude-haiku-5-5 | biomcp_go | 254 | 0.791 (0.737–0.837) | 0.785 | 0.138 | 0.0 | 0.0 | 0.0904 | 0.0025 | 10.1 | 4.49 |
| claude-haiku-5-5 | no_tools | 254 | 0.386 (0.328–0.447) | 0.373 | 0.500 | 0.3333 | None | 0.1599 | 0.0051 | 5.63 | 0.0 |
| claude-haiku-5-5 | web_search | 254 | 0.783 (0.729–0.830) | 0.774 | 0.221 | 0.0 | None | 0.1174 | 0.0110 | 16.58 | 3.37 |

| comparison | n | biomcp-only correct | other-only correct | McNemar p | Δacc (95% CI) |
|---|---|---|---|---|---|
| claude-haiku-5-5|biomcp_vs_web_search | 254 | 49 | 3 | 0.0 | +0.181 (+0.130, +0.232) |
| claude-haiku-5-5|biomcp_vs_biomcp_go | 254 | 46 | 2 | 0.0 | +0.173 (+0.126, +0.221) |
| claude-haiku-5-5|biomcp_vs_no_tools | 254 | 148 | 1 | 0.0 | +0.579 (+0.516, +0.638) |

| template | claude-haiku-5-5|biomcp | claude-haiku-5-5|biomcp_go | claude-haiku-5-5|no_tools | claude-haiku-5-5|web_search |
|---|---|---|---|---|
| disease_late_stage_drugs | 0.99 | 0.38 | 0.35 | 0.16 |
| disease_rarity | 0.75 | 0.25 | 0.45 | 0.50 |
| disease_top_targets | 0.98 | 0.87 | 0.06 | 0.02 |
| drug_first_approval | 1.00 | 0.85 | 0.80 | 1.00 |
| drug_generic_us | 0.90 | 1.00 | 0.85 | 0.95 |
| drug_targets | 1.00 | 0.94 | 0.92 | 0.93 |
| multihop_generic_late_stage | 0.99 | 0.51 | 0.37 | 0.46 |
| not_found | 1.00 | 1.00 | 0.95 | 1.00 |
| trial_count | 0.90 | 0.80 | 0.00 | 0.95 |
| trial_enrollment | 1.00 | 0.97 | 0.05 | 1.00 |
| trial_has_sap | 1.00 | 0.55 | 0.00 | 1.00 |
| trial_n_sites | 1.00 | 1.00 | 0.05 | 1.00 |
| trial_why_stopped | 1.00 | 1.00 | 0.00 | 1.00 |
