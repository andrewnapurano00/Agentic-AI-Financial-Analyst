---
name: axiom-financial-correctness
description: "Validate or repair Axiom company metrics, fiscal-period comparisons, valuation scores, and historical return calculations."
---

# Axiom Financial Correctness

Make a reported number reproducible from dated inputs and a stated methodology.

Read the repository AGENTS.md. This workflow concerns application calculations; it is not a request to recommend an investment.

## Find the calculation

Start with `src/langgraphagenticai/ui/company_snapshot.py` for TTM construction and performance; `ui/equity_report_tab.py` for sector metric registries and scorecards; `portfolio_manager/fmp_fundamentals.py` and `portfolio_manager/scoring.py` for portfolio research features. All abbreviated paths are under `src/langgraphagenticai/`.

The Equity Report contains mixed responsibilities. Find a focused domain boundary before adding calculation logic to it; preserve its sector-specific metric treatment.

## Build a numerical contract

For each changed metric, record numerator, denominator, units, currency, fiscal dates, frequency, source, rounding, and missing-data behavior. Identify whether it is provider-supplied or calculated. Check the displayed label against that contract.

Use [financial-cases.md](references/financial-cases.md) for the cases relevant to the calculation:

- TTM needs consecutive, unique fiscal quarters and consistent reported currency. Fiscal year is not necessarily calendar year.
- Growth needs comparable periods and an explicit denominator policy. A missing quarter cannot silently become zero revenue.
- Ratios stored as fractions and provider changes stored as percentage points need different formatting.
- Comparable returns use an explicitly chosen adjusted-price basis. Do not call an adjusted price return total return without verifying the adjustment and dividend methodology.
- Valuation and peer scoring must respect sector applicability, fiscal basis, and metric coverage. Sparse data is not evidence of a good or bad score.

Trace a defect through the deterministic function and its display/export consumers. Add a test using independently calculated expected values, then fix the smallest responsible layer. For review-only requests, report defects without editing.

## Verification and handoff

Relevant existing tests include `tests/test_hardening.py`, `tests/test_formatters.py`, and `tests/test_market_tabs.py`. Add focused cases where coverage is absent; do not claim that these files already cover every scorecard.

Show a small before/after numeric example, the methodology, and any remaining currency or period limitation. Update UI labels and exports together when the meaning changes.
