# Changelog

## 0.1.1 (2026-11-06)
- Renamed `biomcp-rare` to **RareMCP** (`raremcp`, `raremcp-*` entry points). Unrelated to GenomOncology's BioMCP.
- Drugs@FDA look-ups (`fda_generic_availability`) now take the union of `openfda.generic_name` and
  `products.active_ingredients.name` searches. The 0.1.0 generic-name-only search missed older applications
  without an openFDA block (found by the eval's gold audit; see `eval/review/fda_search_check.md`).
- Eval gold v1.1 (`eval/gold_corrections_v1_1.json`) applies the same fix to the four Drugs@FDA-dependent templates.

## 0.1.0 (2026-11-03)
- First release: 6 servers, 17 tools, provenance envelope, cassettes. Used for eval runs v1-* and hard-*.
