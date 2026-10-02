---
name: axiom-export-safety
description: "Build or repair Axiom PDF, Excel, CSV, and JSON exports with consistent financial content, safe links, and credential filtering."
---

# Axiom Safe Exports

Export the saved research result faithfully, with safe text, links, metadata, and spreadsheet cells.

Read the repository AGENTS.md. Download/format actions should reuse saved results and should not recollect data or invoke models.

## Existing boundaries

Under `src/langgraphagenticai/`:

- Deep Research: `deep_research/presentation.py`, `deep_research/models.py`, and the two `ui/deep_research*_tab.py` modules.
- Portfolio exports: `portfolio_manager/portfolio_reporting.py`.
- Equity exports: locate active builders/callers in `ui/equity_report_tab.py` before extracting a focused export module.
- Credential-safe helpers: `utils/safety.py`; evidence serialization: json_safe/dumps in `deep_research/models.py`.

Existing export tests are embedded in `tests/test_deep_research.py` and `tests/test_deep_research_v2.py`; inspect the actual cases before assuming a format is covered.

## Preserve financial content

Define the saved input packet and expected tables/sections once. Carry source, observation date, fiscal basis, units/currency, uncertainty, unresolved review status, and missing-data notes into the export.

Keep numeric spreadsheet cells numeric, with formatting applied separately. Preserve zero versus blank. Do not relabel an adjusted-price return or a model estimate when changing output formats.

Validate the exported artifact rather than merely checking for nonempty bytes:
- PDF: text/section presence, special-character escaping, page overflow, source appendix, safe hyperlinks.
- Excel: sheet names, stored values, number formats, formulas, and expected blank cells.
- CSV: headers, field ordering, encoding, quoting, and textual formula injection.
- JSON: parseability, finite numbers, schema/metadata, and absence of credentials/binary session artifacts.

## Apply format-specific safety

Read [export-cases.md](references/export-cases.md) for adversarial fixtures.

Credential filtering must cover nested records, model/provider errors, and URL query parameters. Existing safe_url permits HTTP(S) and rejects user-info links, but its query handling does not by itself remove every credential; inspect and sanitize the actual exported destination.

Escape provider text for the target renderer. ReportLab paragraph markup and HTML need their own escaping; sanitizing a URL is not HTML escaping.

For CSV/Excel text, prevent user/provider strings beginning with formula-trigger characters from being executed as spreadsheet formulas. Preserve legitimate numeric negative values as numbers. Reuse or configure the existing writer rather than converting all cells to text.

Keep generated fixtures/artifacts in a temporary directory. Do not export the full Streamlit session, raw prompts, API keys, or sensitive holdings beyond the requested report.

## Handoff

State which formats were tested, which artifact contents were inspected, and which safety cases remain uncovered. For changed download controls, verify that a rerun/download makes zero new model calls.
