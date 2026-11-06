| model | condition | n | accuracy (95% CI) | mean score | abstain | invalid IDs | ungrounded IDs | ECE | API-equiv $/q (not billed) | median s | tool calls |
|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-haiku-5-5 | biomcp | 254 | 0.972 (0.944–0.987) | 0.970 | 0.079 | 0.0 | 0.0 | 0.0689 | 0.0012 | 6.25 | 1.7 |
| claude-haiku-5-5 | no_tools | 254 | 0.386 (0.328–0.447) | 0.371 | 0.500 | 0.3333 | None | 0.1513 | 0.0051 | 5.63 | 0.0 |
| claude-haiku-5-5 | web_search | 254 | 0.783 (0.729–0.830) | 0.774 | 0.221 | 0.0 | None | 0.1174 | 0.0110 | 16.58 | 3.37 |

| comparison | n | biomcp-only correct | other-only correct | McNemar p | Δacc (95% CI) |
|---|---|---|---|---|---|
| claude-haiku-5-5|biomcp_vs_no_tools | 254 | 149 | 0 | 0.0 | +0.587 (+0.528, +0.650) |
| claude-haiku-5-5|biomcp_vs_web_search | 254 | 50 | 2 | 0.0 | +0.189 (+0.138, +0.240) |

| template | claude-haiku-5-5|biomcp | claude-haiku-5-5|no_tools | claude-haiku-5-5|web_search |
|---|---|---|---|
| disease_late_stage_drugs | 0.99 | 0.35 | 0.16 |
| disease_rarity | 0.75 | 0.45 | 0.50 |
| disease_top_targets | 0.98 | 0.06 | 0.02 |
| drug_first_approval | 1.00 | 0.80 | 1.00 |
| drug_generic_us | 1.00 | 0.85 | 0.95 |
| drug_targets | 1.00 | 0.92 | 0.93 |
| multihop_generic_late_stage | 1.00 | 0.35 | 0.47 |
| not_found | 1.00 | 0.95 | 1.00 |
| trial_count | 0.90 | 0.00 | 0.95 |
| trial_enrollment | 1.00 | 0.05 | 1.00 |
| trial_has_sap | 1.00 | 0.00 | 1.00 |
| trial_n_sites | 1.00 | 0.05 | 1.00 |
| trial_why_stopped | 1.00 | 0.00 | 1.00 |
