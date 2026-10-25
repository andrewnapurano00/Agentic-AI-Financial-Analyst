# AX-04 - Earnings metric contracts pilot

Date: 2026-10-23. Status: earnings-family slice implemented locally; offline, health and guarded browser verification passed. Working tree only.

## Baseline and plan

Preserve the existing AX-01/02/03 and roadmap working changes. HEAD e94c677. Baseline SHA256: research_metrics9338A4E5A0DD56DFA831C82D705962195BC6763A5F5FA954D70D6ED4F58A4192; specialist_workflow7D41593357F8711F1B19DE229503AD6E7D16D6F21F4D3B375A66533577EF0226; shared overview3ACD247460F1A5047E645223EAEBC15F698EA2812A6AA93F679A09BE6DEB5438. No staging, Jira, delegated team, publication, deployment or paid/live-provider calls.

Selected family: total-company net income, quarterly/annual/audited four-quarter TTM; not EPS, FFO/AFFO, normalized cyclical earnings or forecasts. Plan: consumer-independent typed MetricDefinition/MetricObservation/source records, immutable registry, raw statement adapter reusing existing window/duration audits, read-only saved-contract reconciliation and explicit status/origin/zero semantics. Consumers: Deep Research earnings quality view, AX-03 net-income eligibility, saved earnings sensitivity eligibility/provenance exports. Original saved rows and reports are never recalculated in place. Existing sector/quote scenario prerequisites remain stricter and separate.

## Source evidence and inventory

D01: FMP-061 stable income-statement, period=quarter limit8 and annual limit5; symbol parameter. coverage_matrix.csv records AAPL/JPM/PLD annual/quarter success and exact sample paths under samples/FMP-061/20261003T044241108241Z. Observed netIncome is integer monetary data; the dictionary definition is inferred, not a certified common-share/adjusted-earnings definition. Preserve reportedCurrency, symbol, date, fiscalYear, period, filingDate and acceptedDate. Raw reported amounts are not rescaled. Samples establish dated observed schema/coverage, not future entitlement.

D02: Deep Research quarterly_data collects raw income_quarterly/income_annual and derives income_ttm with source_records. research_metrics stores Net income (TTM) and latest-period values with source inputs/basis/formula. Both versions share this domain boundary. Saved scenarios require positive audited TTM company earnings, compatible dated cap/currency and sector applicability; they are not AI Valuation per-share targets. AX-03 currently checks metric metadata locally; its net-income consumer will delegate to the common service.

D03: Market Brief/company terminal uses provider TTM/quarterly margin contexts; Equity Report sector scores and Portfolio Manager still have distinct provider earnings/ratios. AI Valuation uses dated annual diluted EPS or a labeled same-FY income/share proxy; consensus is context. Those bases are inventoried but not migrated in this slice. No new cross-workspace financial packets, global caches or provider calls.

Acceptance: missing remains missing, zero/loss remain observations; four consecutive same-currency quarters required; duplicate conflicts/revisions fail closed; identical duplicates deduplicate; annual/quarterly/TTM meanings distinct; fiscal and retrieval/filing availability dates separate; stale/unverifiable/inconsistent flags visible; no saved-number replacement. One family delivery does not complete universal AX-04 or unlock AX-05/06/07 without their own scope.


## Current-use family inventory

| Surface | Existing earnings meaning and boundary | Adoption in this slice |
| --- | --- | --- |
| Market Brief / Top Movers selected company | company_terminal uses same-window quarterly netIncome/revenue for TTM net margin; separate provider ratios may be undated | Inventory only; no relabeling of its provider metrics |
| Research Guided | guided_research annual FY income-statement netIncome, source/date/currency explicit; chat tools remain independently routed | Inventory only; annual does not become TTM |
| Equity Report | Sector-specific scoring, provider ratios and reported statement context; applicability remains canonical sector registry | Inventory only; no score/calculation migration |
| Stock Screener | FMP screening/enrichment; no new direct company-earnings observation adapter | Existing universe/filters unchanged |
| AI Valuation | Dated annual diluted EPS or explicitly labeled same-FY net-income/diluted-share proxy; consensus/context separate | No TTM-to-per-share input bridge |
| Deep Research Standard / Low cost | netIncome from raw stable income-statement quarter/annual records; income_ttm is four validated quarters; source IDs retained | Shared quality view, specialist net-income eligibility and saved sensitivity/export adapters |
| Portfolio Lab | Portfolio Manager fmp_fundamentals keeps its existing rolling TTM, margins and earnings-growth features | Inventory only; not certified by this delivery |
| AI Robo Advisor | Existing sector screen/research facts and structured conviction packet | Original provider/score/optimizer contracts preserved |

Every adapter in this slice consumes netIncome only. It does not substitute bottomLineNetIncome, common-share earnings, EPS, adjusted earnings, FFO/AFFO or forecasts. FMP reference samples show netIncome integers in reported currency units; semantic/scaling uncertainty remains disclosed. Future family adoption requires its own endpoint/period/unit inventory and tests.

## Design note: additive immutable observations

analysis/metric_contracts.py defines frozen MetricDefinition, MetricInput and MetricObservation plus a read-only registry. Basis is part of metric identity: net_income.quarterly, net_income.annual and net_income.ttm. A versioned observation export contains formula, original route/source IDs, fiscal identities, reporting currency, optional CIK, filing/acceptance and retrieval dates. Freshness evaluation is separate from stable fact identity; no global cache or credentials are introduced.

Status (available/missing/stale/inconsistent/unverifiable/unsupported), origin (provider/derived), verification and valid_zero are separate dimensions. Zero/loss are facts; positive-earnings/quote/sector gates for sensitivities remain separate. Derived is not a freshness or semantic guarantee. Raw values are not rescaled, explicit unsupported units/scaling fail closed, and mismatched CIKs/currencies or ambiguous revisions are rejected. Identical duplicates deduplicate through the existing audited window helper. Total earnings have no share-price adjustment; corporate-event comparability is not inferred.

analysis/earnings_metrics.py validates raw statements through the existing flow_duration/window helpers, preserving the standardized standalone-quarter assumption. TTM arithmetic uses rel_tol1e-12 / abs_tol1e-6 reported currency units for saved/raw reconciliation. No saved amount is replaced: inconsistent original values remain visible but ineligible. Legacy derived-only records stay readable/unverifiable if raw quarters are absent. Retrieval freshness is thirty days; quarterly/TTM fiscal age two hundred days, annual five hundred fifty days. Fiscal end, filing and acceptance remain distinct; naive filing timestamps do not establish intraday availability.

No changes to provider requests, financial collection, existing raw aggregation outputs, forecasts or valuation prices. Shared consumers are ui/earnings_quality.py through the saved overview; AX-03's Net income (TTM) eligibility; analysis/scenarios.py eligibility; and the credential-safe brief JSON/CSV observation appendix. Scenario prices still use original saved numbers and their existing stricter quote/currency/sector checks. Auditing raw quarters is independent validation, not silent report regeneration. Existing annual-EPS valuation, portfolio earnings, margin families and universal provenance remain future scope.

## Verification in progress

New earnings/brief checks60 passed in20.82s. Expanded earnings/brief/specialist/intent107 passed in33.01s. Final earnings/brief/specialist90 passed in30.94s. Tests include raw arithmetic, zero/loss/null/nonfinite, duplicate/revised/missing/irregular/53-week quarters, annual duration/revisions, CIK/currency/unit/scale conflicts, retrieval/fiscal/filing availability, safe metadata and query removal, legacy/unresolvable sources, identical identity across specialist/export consumers, tampered raw earnings blocking sensitivities, preserved original amounts and UI immutability. Dated AAPL/JPM/PLD annual/quarter samples are read from the FMP coverage index with independently summed expectations; no live calls.

An initial pre-fixture-clock run had six brief failures because synthetic collection timestamps were generated today while evaluation used2026-10-08. The eligible fixture now explicitly stamps raw/derived source metadata2026-10-07 before rebuilding contracts; the final runs above passed. This is a test-clock correction, not fabricated provider evidence. Current full-suite run reported an unrelated pre-existing Market Brief interaction failure; isolated rerun passed1 in22.24s. Full failure details and repeat-suite result are pending.


## Verification follow-up

Final earnings/brief checks after adding the shared freshness-policy disclosure:64 passed in61.28s while other verification was active. Initial full inventory:1211 passed/2 failed in781.84s. Both failures were AppTest's default three-second widget-run timeouts in unchanged Market Brief tests (`test_company_terminal.test_market_chart_preserves_legacy_company_result_without_rendering_analysis` and `test_market_tabs.test_market_range_interaction_does_not_call_ai`), not failed financial/call-count assertions. The former passed alone1 in22.24s. Both harness constructors now set default_timeout=30, matching the project's other interaction tests, without changing assertions or product code. Final serial `python -m pytest -q --tb=short --durations=5`: **1213 passed in483.54s**, including the two unchanged-assertion interaction cases. Original failures remain recorded. The final repeat covers all current source, disclosure and test changes.

Fresh app/src compileall and app/main/earnings imports passed in project Python3.12.0/pytest9.1.1/Streamlit1.61.1. Main Streamlit health8585 and guarded fixture health8584 returned ok. Agent-browser isolated session ax04-20261023 exercised actual earnings-quality rendering with external requests/httpx/model construction blocked. Valid case showed available TTM40; inconsistent case retained original99 and flagged inconsistency; stale retained40/stale; missing raw component retained original40/missing. Fiscal, retrieval, currency, origin and zero fields were visible. Case changes, disclosures and safe export preparation retained zero external/model calls. Desktop and390px screenshots outside Git were visually inspected; browser errors were empty. Temporary servers stopped. The initial browser-close command reported a daemon connection timeout after screenshots; a final named-session close succeeded, so the browser is also closed. Native download artifact inspection was not performed; JSON/CSV content/safety is covered offline.

No live provider/model quality/freshness/entitlement check, clean install, hosted release, source publication, Jira or deployment. Existing release gates remain open. The registry covers this earnings family only; annual EPS/proxy valuation, portfolio metric migration, other families and AX-05/06/07 acceptance remain separate work.


## Delivery outcome

One earnings family is implemented and verified with its named consumers. Example oracle: quarterly net income30 +20 +0 -10 gives TTM40. If a saved report instead says99, the observation retains99 and flags inconsistency; it does not repair the saved report silently. Missing raw components never become zero. Negative and zero earnings remain facts but cannot bypass the existing positive-earnings/quote/currency/sector gates for sensitivities. Original research, exports and other valid sections remain available.

Final test inventory1213 includes34 new earnings tests beyond the prior1179 baseline. Final focused90 passed in30.94s, and disclosure follow-up64 passed in61.28s; full result above supersedes interim counts. No paid/live calls, Jira creation attempts (zero), staging, publication or deployment. Other metric families and broader AX-04/workspace adoption remain roadmap work rather than implied completion.
