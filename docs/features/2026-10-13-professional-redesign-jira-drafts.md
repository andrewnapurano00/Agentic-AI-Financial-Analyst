# Jira follow-up drafts — 2026-10-13 professional redesign

These are deferred enhancements from run `2026-10-13-professional-redesign-team`, baseline `be858cd6b8660c02de84bcb1a9561d73575d86ce`. P02 shared shell is local working-tree work; the page-body redesign and heatmap contracts remain open. No live financial/provider result is claimed.

## P03 / RDS-03

Project AAFA; type Task; priority Medium; labels `2026-10-13-professional-redesign-team`, `professional-redesign`, `rds-03`.

Summary: **RDS-03: Redesign Market Brief and Top Movers page bodies with content parity**

Description:

Run ID: 2026-10-13-professional-redesign-team. Proposal P03/RDS-03. Baseline be858cd6b8660c02de84bcb1a9561d73575d86ce; shared navy/gold shell P02 is implemented locally, while Market Brief and Top Movers page bodies remain in their prior composition. This is deferred presentation and preservation work, not a financial-data defect or a claim that the redesign is complete.

Problem and evidence: The approved market-brief concept places the existing main chart, deterministic observations and sector ETF evidence in a 50/25/25 analytical row, followed by candidate cards and macro/AI draft. The Top Movers contract places ranking and selected-company evidence side by side, then sector context and methodology. Current active renderers `src/langgraphagenticai/ui/introduction_tab.py` and `top_movers_tab.py` retain their earlier layouts. The reviewed 714-active-row inventory and `docs/redesign/discovery/preservation-map.csv` provide item-level preservation targets; `docs/redesign/references/market-brief.png` is illustrative composition only.

Data boundaries (D01/D03): Use existing normalized facts, dates, statuses and saved results. `providers/discovery.py` ranks a capped 500-stock legacy screener with batched price changes; its sector mean is a screened-stock aggregate, not ETF performance or a broad-market sector return. Do not invent screenshot values, sector heatmap data, completed-session volume ratios, or dated excess returns. AAFA-13 owns the benchmark comparison contract and AAFA-14 owns volume qualification. No paid model call on ordinary controls.

Proposed work: Adapt the active Introduction/Top Movers renderers and shared presentation components to the contract's MKT/MOV layouts. Preserve company snapshot, search, chart horizons and technical controls, source/as-of/basis/error states, refresh, selected ticker, keyboard row alternative, news, and editable Research handoffs. Keep page-body styles consistent with the P02 shell.

Acceptance criteria: (1) At 1440/1920/1024/390px, Market Brief presents existing chart/observations/sector evidence, candidates and macro/AI draft in the approved order; Top Movers presents period/sector/direction controls, ranking, selected-company evidence, sector summary and methodology without clipping or hidden controls. (2) Every active MKT/MOV preservation row has an exact destination and fixture-backed output/control check; detailed table columns, chart/technical settings, news, units/currency/period/source/retrieval and unavailable/partial/stale/mismatch states remain reachable. (3) Selection, filters, refresh and handoffs preserve ticker and saved work; Research opens an editable draft requiring explicit submit. (4) Exports and provider/calculation contracts remain unchanged; navigation, selection, formatting and downloads cause zero model calls. (5) Focused offline tests, shared-route full pytest as applicable, compile/import, fresh Streamlit health, keyboard walkthrough and same-viewport browser screenshots at all four widths pass; independently review preservation rows and record actual limits.

Suggested offline verification (not tests of this unbuilt follow-up): synthetic complete/empty/partial provider packets, missing versus zero changes, keyboard/table selection, source and date labels, chart controls, saved AI reuse and call counters. Live entitlement or market freshness is not established by offline fixtures. Duplicate review: AAFA-9 delivered earlier terminal headers; AAFA-13 and AAFA-14 track distinct benchmark and volume evidence contracts. No matching RDS-03 page-body task was found in targeted AAFA search, including closed issues.

## Remaining ranked proposals (draft only until separately searched)

2. **P04 / RDS-04/05 Research and Equity:** Exact payload below.
3. **P05 / RDS-06 Deep Research V1/V2:** Exact payload below.
4. **P06 / RDS-07 Screener/Portfolio:** Exact payload below.
5. **P08 / RDS-09 heatmap data contract:** Exact payload below.

## P04 / RDS-04/05 exact payload

Project AAFA; type Task; priority Medium; labels `2026-10-13-professional-redesign-team`, `professional-redesign`, `rds-04-05`.

Summary: **RDS-04/05: Redesign Research and Equity Report bodies with content parity**

Description:

Run ID: 2026-10-13-professional-redesign-team. Proposal P04/RDS-04 and RDS-05. Baseline be858cd6b8660c02de84bcb1a9561d73575d86ce. The local P02 navy/gold shell is complete; Research Chat/Guided and Equity Report retain their earlier page-body organization. This is deferred presentation and preservation work, not a claim of missing workflow features.

Problem and evidence: The approved contract calls for Chat to show saved conversation, editable draft and explicit submit with evidence nearby; Guided to show Configure → Prepare → Run → saved facts/risks/evidence; Equity Report to lead with company/peer context, summary and decision material while retaining every active report tab, scorecard, table and export. The active paths are `src/langgraphagenticai/main.py` Research routing, `ui/guided_research_tab.py` and `ui/equity_report_tab.py`. The 714-active-row discovery inventory and preservation map identify source items. The three reference images are illustrative; no screenshot-only controls or metrics are authorized.

Data boundaries D01/D02: Reuse existing normalized/saved facts and source/period/currency/retrieval metadata. Company terminal annual, TTM and forward bases stay distinct; missing and zero stay distinct. No provider route, metric formula, score, recommendation, peer comparison basis, model prompt or call trigger changes.

Proposed work: Adapt Research Chat/Guided and the active Equity Report presentation functions to shared P02 components and the RES/EQ composition contracts. Preserve typed ticker navigation metadata, saved conversations/results, model/use-case configuration mismatch and explicit New thread, Guided spend/price acknowledgement and separate Prepare/Run controls, and all Equity tabs, committee evidence, audits and downloads.

Acceptance criteria: (1) Chat and Guided remain visibly selectable; saved chat, editable handoff draft, citations, New thread/mismatch notice, Guided plan/result/usage/evidence/gaps and JSON download remain reachable with unchanged state identity. Ordinary reruns and downloads make zero model calls; explicit submit/Prepare/Run prerequisites and bounded behavior remain. (2) Equity Report retains active Thesis, Performance, Financials/Valuation, Sources/Audit and Exports content, full narratives and tables, factor/rating/return/scoring details, peer framework, coverage warnings, committee actions and PDF/Excel/CSV outputs with unchanged schema/content. (3) Complete, empty, partial, stale, provider failure, saved mismatch and missing-key states place limitations near affected outputs; provider facts, calculations, AI text and user assumptions remain distinguishable. (4) Every active RES/EQ preservation row gains an exact destination and fixture-backed output/control check; browser comparison at 1440/1920/1024/390px shows no clipping or hidden controls, with keyboard/focus checks. (5) Focused offline state/export/call-parity tests, full suite if shared routing changes, compile/import, fresh Streamlit health and independent row review pass and record actual limits.

Suggested future offline verification (not tests of unbuilt layouts): synthetic saved chat/thread and mismatch, Guided partial tool results and usage, Equity populated/partial peers and exports, missing versus zero financial values, ticker remounts and model-call counters. Live provider/model correctness remains unverified. Duplicate review across AAFA including closed: AAFA-9 delivered shared headers/evidence presentation, AAFA-10 Guided workflow logic and AAFA-11 saved brief logic; no existing issue covers the page-body layout and full parity outcome.

## P05 / RDS-06 exact payload

Project AAFA; type Task; priority Medium; labels `2026-10-13-professional-redesign-team`, `professional-redesign`, `rds-06`.

Summary: **RDS-06: Redesign Deep Research V1/V2 saved-report bodies with content parity**

Description:

Run ID: 2026-10-13-professional-redesign-team. Proposal P05/RDS-06. Baseline be858cd6b8660c02de84bcb1a9561d73575d86ce. The local P02 shared navy/gold shell is implemented; Deep Research V1/V2 saved-report bodies and investment brief/scenario layout have not been adapted to the approved report composition. This is deferred presentation and preservation work, not a defect claim about existing recovery or financial calculations.

Problem and evidence: The approved deep-research image and implementation contract call for a readable saved thesis pane, report status/history, compact configuration and adjacent evidence with all existing tabs and exports still reachable. Current active renderers are `src/langgraphagenticai/ui/deep_research_tab.py`, `deep_research_v2_tab.py` and `investment_brief.py`. Gate 1 traced the active paths in `docs/redesign/discovery/current-content-inventory.csv` and `preservation-map.csv`. Fixture-backed actual-main baseline screenshots show V1/V2 saved and V2 partial states; screenshot values and coverage badges are illustrative and do not authorize new facts or actions.

Data boundaries D01/D02: Reuse saved financial audit and normalized dated evidence without recollection, recalculation or silent annual/quarterly/TTM/forward substitution. Separate evidence freshness from V2 generation age, news retrieval from publication/lookback, provider facts from calculations, AI narrative from user scenario assumptions. No changes to provider routes, metric arithmetic, model routing, CrewAI decisions or export schemas.

Proposed work: Adapt active V1/V2 and shared brief/scenario renderers to the DR composition while preserving version-specific configuration, history, report/decision/review/retry semantics, provenance, comparison, notebook/follow-ups, eligibility warnings and downloads. Keep V1 and V2 behavior distinct.

Acceptance criteria: (1) V1 retains its saved-run toolbar, status/evidence gaps, thesis, comparison, committee, sources, notebook/follow-ups, scenarios, retry/finalize and original exports. V2 retains pilot provider/cost controls, generation-time versus evidence-time labels, separate decision/recovery states, Report/Decision/Comparison/Sources/Performance/Brief tabs and exports. (2) Saved results remain prominent when configuration reopens; complete, partial, stale, missing-key, failed and ticker/configuration-mismatch states keep valid saved work and place limitations near affected output. (3) Every active DR/brief preservation row has a precise destination and fixture-backed content/control/export check; original narratives, source IDs, metric units/bases/currencies/dates, assumptions and export payloads remain equivalent. (4) Ordinary navigation, tab/disclosure/scenario controls and downloads make zero provider/model calls; explicit run/retry/decision prerequisites and bounds remain unchanged. (5) Browser compare at 1440/1920/1024/390px, keyboard/focus checks, focused offline state/export/call-parity tests, full suite if shared routing changes, compile/import, fresh Streamlit health and independent row review pass with limits recorded.

Suggested future offline verification (not tests of this unbuilt follow-up): synthetic V1/V2 complete, partial, failed and saved-mismatch packets; old-evidence acknowledgement; scenario eligible/ineligible inputs; export payload equality and zero call counters. No live financial freshness or model-quality claim. Duplicate review including closed: AAFA-2 completed V2 recovery, AAFA-5 generation age, AAFA-6 financial audit, AAFA-9 shared evidence headers, and AAFA-11 brief/scenario logic. This ticket owns only the remaining page-body composition and preservation verification.

## P06 / RDS-07 exact payload

Project AAFA; type Task; priority Medium; labels `2026-10-13-professional-redesign-team`, `professional-redesign`, `rds-07`.

Summary: **RDS-07: Redesign Stock Screener and Portfolio Lab bodies with content parity**

Description:

Run ID: 2026-10-13-professional-redesign-team. Proposal P06/RDS-07. Baseline be858cd6b8660c02de84bcb1a9561d73575d86ce. The local P02 shared navy/gold shell is implemented; Stock Screener, Portfolio Optimizer and AI Portfolio Manager bodies retain their previous arrangement. This ticket tracks remaining presentation and preservation work, not new screening or portfolio algorithms.

Problem and evidence: The approved contract calls for compact Screener query controls, grouped filters, results and export toolbar; Portfolio Lab keeps Optimizer and AI Portfolio Manager clearly distinct and presents holdings versus proposed target weights, recommendations, rebalance and exposure with readable evidence. Active renderers are `src/langgraphagenticai/ui/stock_screener_tab.py`, `portfolio_optimizer_tab.py` and `ai_portfolio_manager_tab.py`. Gate 1's `current-content-inventory.csv` and `preservation-map.csv` identify active controls, outputs and conditional branches. The portfolio reference image includes illustrative presets, universes and numbers; these are not supported additions.

Data boundary D01: Reuse existing saved provider/calculated/model-derived results and metadata. Preserve optimizer arithmetic, allocation caps, residual cash, benchmarks, risk assumptions and existing missing/zero/currency behavior. No provider, formula, scoring, model or export schema change is authorized by the image.

Proposed work: Adapt Screener and both Portfolio Lab modes to the P02 shared visual components and SCR/PM composition contracts, keeping their native widgets and session-state identities. Move details only after exact preservation mapping and fixture proof.

Acceptance criteria: (1) Screener retains country/exchange/sector/industry filters, all server ranges, wide-open defaults, page/limit and enrichment/display limits, RSI and post-screen filters, missing-value option, saved result, CSV and company handoff; changing layout does not rerun expensive evidence or clear saved output. (2) Optimizer retains portfolio/ticker inputs, regimes, equal/custom tests, historical period/benchmark assumptions, efficient frontier, risk/return/crisis metrics and allocations. (3) Manager retains uploaded/manual/screened holdings modes, watchlist, benchmark/history/risk/position/sector/cash/min-trade limits, explicit hybrid run, recommendations/rebalance/debate/evidence/exposure/monitoring/diagnostics/AI chat/current holdings and existing downloads. Current versus proposed values remain clearly labeled. (4) Complete, empty, partial, stale, missing-key and failed states preserve usable saved work and show source/date/unit/basis/limitations near affected outputs. Every active SCR/PM preservation row has a precise destination and fixture-backed control/output/export check. (5) At 1440/1920/1024/390px, no controls or results clip; keyboard/focus and local table scrolling work. Focused offline state, arithmetic regression, export and provider/model call-parity tests, compile/import, fresh Streamlit health, browser walkthrough and independent review pass; run full pytest if shared routing changes.

Suggested future offline verification (not tests of unbuilt layouts): synthetic zero/missing/partial screening data; saved pagination/handoff; optimizer constraint and residual cash fixtures; Manager hold-versus-target/rebalance fixtures, errors and zero model calls on ordinary controls/downloads. Live market freshness and model-quality are outside this ticket. Duplicate review of the complete AAFA project including closed issues: AAFA-8 delivered Screener saved-result and handoff behavior; AAFA-9 delivered shared terminal presentation. Neither delivers these page-body layouts and full parity.

## P08 / RDS-09 exact payload

Project AAFA; type Task; priority Medium; labels `2026-10-13-professional-redesign-team`, `professional-redesign`, `rds-09`, `data-contract`.

Summary: **RDS-09: Verify sector heatmap return and constituent data contracts before implementation**

Description:

Run ID: 2026-10-13-professional-redesign-team. Proposal P08/RDS-09; data requirements D04/D05. Baseline be858cd6b8660c02de84bcb1a9561d73575d86ce. The professional redesign's heatmap is an illustrative proposed addition, not an existing working tab. Implement it only after its financial data contract is independently evidenced.

Problem and evidence: The requested sector mosaic requires eleven sector ETF Day/Week/YTD returns, declared market-cap sizing, industry grouping, selection events and ticker handoffs. Current `src/langgraphagenticai/providers/discovery.py` produces a capped 500-liquid-US-stock screen and screened-stock five-day sector means; it cannot establish broad sector returns, complete constituents, industry weights or sector capitalization. Saved `fmp_data_reference/collection_report.md` and `endpoint_inventory.csv` show FMP-148 ETF holdings mixed restricted/success and FMP-238 batch quote mixed restricted/success; restricted bulk routes and sample-specific coverage do not prove an efficient entitled complete universe. FMP-136 dated history samples do not by themselves verify all eleven ETF periods or adjustment/currency/session compatibility. The approved reference image has illustrative numbers only.

Proposed work: First establish exact provider routes/variants, parameters, entitlement and bounded request costs for the eleven ETF histories and a defensible constituent universe/industry taxonomy. Specify security identity, start/end trading observations, adjustment basis, currency, price versus total return, retrieval time, missing/future/partial rules, duplicate and cross-listing policy, market-cap date and aggregation semantics. Keep ETF performance distinct from screened-stock sector means and from company/benchmark comparisons in AAFA-13. If an input is unsupported, scope the UI to what can be truthfully labeled instead of fabricating a comprehensive heatmap.

Acceptance criteria: (1) A reviewed D04 contract supplies per-ETF Day/Week/YTD observed endpoints, consistent return arithmetic/basis and source/date/currency/coverage for all eleven sectors, with synthetic tests for mismatched dates, missing bars, split/adjustment uncertainty, zero and nonfinite values. (2) A reviewed D05 contract defines an entitled, bounded constituent universe, sector/industry taxonomy, duplicate policy, dated compatible market caps, weighting/aggregation and partial-coverage disclosure; prove representative sample coverage without treating historical success as future entitlement. (3) The implementation plan sets provider-call/cache/latency limits and failure recovery. Any eventual tile/industry/period selector uses actual events, keyboard alternatives, a gold selection outline, signed green/red values plus text, safe ticker handoffs and no model call on ordinary controls. (4) Unsupported or incomplete size/industry/return claims remain unavailable with explicit reasons; existing sector bars and Screener context remain reachable. (5) Only after evidence passes, implement behind focused offline provider/domain/UI tests, full checks for shared routing, compile/import, fresh health, four-width browser review and independent financial/preservation review. Record any live entitlement check separately; no paid/live call is part of offline verification.

Suggested future verification is proposed, not completed. Duplicate review across AAFA including closed: AAFA-13 is a company/benchmark comparison contract, AAFA-15 excludes new heatmap data from the Market/Movers layout slice. No existing issue owns this eleven-sector ETF and constituent contract.
