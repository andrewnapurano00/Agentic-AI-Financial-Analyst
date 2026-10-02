# Provider contract cases

Choose the rows relevant to the adapter being changed. Build sanitized synthetic fixtures, not cached real account responses.

| Case | Expected behavior |
| --- | --- |
| Numeric zero, string "0", and missing/null field | Preserve legitimate zero; retain an explicit missing state for absent values. |
| Non-numeric text, NaN, infinity, malformed row | Reject the affected value/row without discarding unrelated valid records. |
| Empty list, error dictionary, unexpected object | Return a structured empty/failure state, not an apparently successful zero-valued quote. |
| Partial batch or one timed-out future | Preserve successful records and report requested versus usable coverage. |
| HTTP 401/403 or plan restriction | Surface a sanitized configuration/entitlement warning; do not retry as a transient error. |
| HTTP 429/5xx or timeout | Use bounded safe GET retries/timeouts; verify the actual attempt bound. |
| FMP commodity/crypto versus Yahoo symbol | Translate only at the provider boundary and retain the requested security identity. |
| Different share-class conventions | Confirm equivalence with provider documentation; never conflate exchange/currency listings. |
| Yahoo Close at either MultiIndex level | Normalize both field-first and ticker-first layouts, plus a single-ticker frame. |
| Missing percent change with valid prior close | Derive from compatible prices; disclose the calculation basis. With no prior close, preserve missingness. |
| Duplicate news URL/title/time | Deduplicate canonical records while retaining publication time and provider. |
| Stale quote with recent retrieval | Observation time controls market freshness; retrieval time alone does not make it live. |
| One bad provider among several successes | Preserve successes, explicitly label fallback source, and retain warnings. |

## Useful integration patterns

Patch the symbol in the module that actually consumes it; patching the defining module alone may not replace an already imported function.

Use a mocked requests/session response to test the HTTP transport, and a normalized fixture to test the UI/service consumer. A mocked _get test does not exercise transport retries.

Streamlit cached functions can retain results across tests. Clear the relevant cache before/after a caching test, or use __wrapped__ for a pure contract test as existing test_market_tabs cases do. Verify cached and uncached behavior separately when caching is the defect.

For missing average volume: retain price and 5D return, render liquidity as unavailable, and assert that no numeric zero or NaN text leaks into the table.

For a historical fallback: assert a single provider identity for all points, chronological order, the selected range, and preservation of valid quote cards if chart retrieval fails.
