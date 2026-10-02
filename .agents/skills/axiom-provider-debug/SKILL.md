---
name: axiom-provider-debug
description: "Diagnose missing, stale, or inconsistent FMP, Yahoo, Marketaux, and Serper data in Axiom and repair provider contracts."
---

# Axiom Provider Debugging

Trace a visible data defect back to the provider contract, preserving successful records.

## Repository entry points

Paths below are relative to the repository root; find that root from Git and read its AGENTS.md.

- Shared FMP transport: `src/langgraphagenticai/providers/fmp_http.py`.
- Introduction: `ui/market_overview_data.py`, `ui/company_snapshot.py`; history adapter: `providers/market_history.py`.
- Movers and screener: `ui/top_movers_data.py`, `portfolio_manager/fmp_screener.py`.
- News: `tools/serper_tools.py`, `tools/news_pipeline_tools.py`, `tools/news_chat_tools.py`.
- Deep Research evidence: `deep_research/data.py`.
- Abbreviated module paths above are under `src/langgraphagenticai/`.

## Diagnose and repair

1. Pin down the ticker, workspace, field, expected period, and actual state. Distinguish a missing provider row from a missing field, formatting failure, entitlement error, stale cache, or dropped merge.
2. Follow the value from response to normalized record to table/card. Inspect actual field names, numeric types, ticker aliases, join keys, and pandas MultiIndex orientation. Use synthetic responses first; never print credentials or complete request URLs containing keys.
3. Validate symbols before requests. Keep provider-specific aliases at the adapter boundary: FMP commodity/crypto names differ from Yahoo futures/crypto names. Do not substitute a different instrument just to fill a card.
4. Reuse the shared FMP HTTP transport. Keep new retrieval code in a provider/service module. Make malformed rows fail independently when other records remain usable.
5. Make fallback provenance explicit, including observation time and price basis. A fallback history is a separate complete series, not a splice into FMP history. Do not turn missing change or volume into a flat return or zero liquidity.
6. Preserve valid results through a partial failure. Include useful missing-field/coverage warnings and explicit refresh recovery. Match cache TTL to the data type; never persist keys.

Read [contract-cases.md](references/contract-cases.md) when adding adapter or normalization tests. Existing examples are `tests/test_market_tabs.py`, `tests/test_hardening.py`, and `tests/test_deep_research.py`.

For provider endpoint changes, verify current primary provider documentation. Live checks are optional and explicit; contract tests must stay offline.

## Handoff

State the root cause, affected tickers/fields, what still lacks coverage, and the focused tests. If a UI changed, follow the repository's health/browser requirements. A successful fallback does not prove that FMP coverage is restored.
