# RareMCP 0.1.1 (Drugs@FDA fix) versus comparators, gold v1.1

Server condition = 0.1.0 answers, with the 58 Drugs@FDA-dependent questions replaced by 0.1.1 re-runs.

## base tier

| model | condition | n | accuracy (95% CI) |
|---|---|---|---|
| sonnet | no_tools | 254 | 0.469 (0.408–0.530) |
| sonnet | web_search | 254 | 0.819 (0.767–0.861) |
| sonnet | biomcp_go | 254 | 0.878 (0.832–0.913) |
| sonnet | biomcp | 254 | 0.992 (0.972–0.998) |
| sonnet | biomcp_v011 | 254 | 1.000 (0.985–1.000) |
| sonnet | (0.1.1 re-run answers substituted: 58) | | |
| haiku | no_tools | 254 | 0.386 (0.328–0.447) |
| haiku | web_search | 254 | 0.783 (0.729–0.830) |
| haiku | biomcp_go | 254 | 0.795 (0.741–0.840) |
| haiku | biomcp | 254 | 0.965 (0.934–0.981) |
| haiku | biomcp_v011 | 254 | 0.972 (0.944–0.987) |
| haiku | (0.1.1 re-run answers substituted: 58) | | |

| model | comparison | n | 0.1.1 only | other only | McNemar p | Δacc (95% CI) |
|---|---|---|---|---|---|---|
| sonnet | 0.1.1 vs web_search | 254 | 46 | 0 | 2.84e-14 | +0.181 (+0.134, +0.228) |
| sonnet | 0.1.1 vs biomcp_go | 254 | 31 | 0 | 9.31e-10 | +0.122 (+0.083, +0.165) |
| sonnet | 0.1.1 vs no_tools | 254 | 135 | 0 | 4.59e-41 | +0.531 (+0.469, +0.595) |
| sonnet | 0.1.1 vs biomcp | 254 | 2 | 0 | 0.5 | +0.008 (+0.000, +0.020) |
| haiku | 0.1.1 vs web_search | 254 | 50 | 2 | 6.12e-13 | +0.189 (+0.142, +0.240) |
| haiku | 0.1.1 vs biomcp_go | 254 | 46 | 1 | 6.82e-13 | +0.177 (+0.130, +0.224) |
| haiku | 0.1.1 vs no_tools | 254 | 149 | 0 | 2.8e-45 | +0.587 (+0.524, +0.646) |
| haiku | 0.1.1 vs biomcp | 254 | 2 | 0 | 0.5 | +0.008 (+0.000, +0.020) |

## hard tier

| model | condition | n | accuracy (95% CI) |
|---|---|---|---|
| sonnet | no_tools | 60 | 0.417 (0.301–0.543) |
| sonnet | web_search | 60 | 0.817 (0.701–0.894) |
| sonnet | biomcp_go | 60 | 0.733 (0.610–0.829) |
| sonnet | biomcp | 60 | 0.817 (0.701–0.894) |
| sonnet | biomcp_v011 | 60 | 0.900 (0.798–0.953) |
| sonnet | (0.1.1 re-run answers substituted: 58) | | |
| haiku | no_tools | 60 | 0.283 (0.185–0.408) |
| haiku | web_search | 60 | 0.783 (0.664–0.869) |
| haiku | biomcp_go | 60 | 0.633 (0.507–0.744) |
| haiku | biomcp | 60 | 0.800 (0.682–0.882) |
| haiku | biomcp_v011 | 60 | 0.900 (0.798–0.953) |
| haiku | (0.1.1 re-run answers substituted: 58) | | |

| model | comparison | n | 0.1.1 only | other only | McNemar p | Δacc (95% CI) |
|---|---|---|---|---|---|---|
| sonnet | 0.1.1 vs web_search | 60 | 7 | 2 | 0.18 | +0.083 (-0.017, +0.183) |
| sonnet | 0.1.1 vs biomcp_go | 60 | 12 | 2 | 0.0129 | +0.167 (+0.050, +0.283) |
| sonnet | 0.1.1 vs no_tools | 60 | 32 | 3 | 4.18e-07 | +0.483 (+0.333, +0.633) |
| sonnet | 0.1.1 vs biomcp | 60 | 5 | 0 | 0.0625 | +0.083 (+0.017, +0.167) |
| haiku | 0.1.1 vs web_search | 60 | 8 | 1 | 0.0391 | +0.117 (+0.033, +0.217) |
| haiku | 0.1.1 vs biomcp_go | 60 | 17 | 1 | 0.000145 | +0.267 (+0.150, +0.383) |
| haiku | 0.1.1 vs no_tools | 60 | 37 | 0 | 1.46e-11 | +0.617 (+0.500, +0.733) |
| haiku | 0.1.1 vs biomcp | 60 | 6 | 0 | 0.0312 | +0.100 (+0.033, +0.183) |

