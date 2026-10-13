# Agentic AI Financial Analyst: connected Market Brief and Top Movers

Planning date: 2026-10-11 (America/New_York).

Current local delivery record (2026-10-12): [opening UI team report](2026-10-11-opening-ui-team.md). The original proposed workstreams below are retained as the planning baseline; the team report records implemented scope, actual checks, unresolved requirements and confirmed Jira outcomes. Reference images are saved at [Market Brief](assets/2026-10-11-opening-ui/market-brief-reference.png) and [Top Movers](assets/2026-10-11-opening-ui/top-movers-reference.png).

This is an executable feature backlog and multi-agent implementation brief. It does not claim that code changes, Jira tickets, commits, or deployment have occurred. The approved generated Market Brief and Top Movers images are visual references only; all depicted prices, headlines, dates, and source attributions are illustrative.

## Objective

Deliver two professional, attractive, interactive opening pages that connect market context to company discovery and evidence-backed research:

**Market Brief → sector or company discovery → Top Movers → company evidence → Research.**

Retain Streamlit, existing provider clients, company snapshots, historical charts, and working research handoffs. Make important findings digestible before exposing technical detail.

## Jira tracking shell

Suggested epic: **Connected market discovery experience**.

The IDs below are planning IDs, not Jira issue keys. Record actual issue keys after checking for existing tickets. Use one implementation story per workstream with subtasks when useful. Keep workstream ownership explicit and link dependencies in Jira.

| Planning ID | Story | User outcome | Owner | Depends on | Jira key | Status |
| --- | --- | --- | --- | --- | --- | --- |
| MB00 | Repository review and implementation contracts | Existing capabilities are preserved and the team shares one implementation target. | Lead / integrator | — | TBD | Proposed |
| MB01 | Shared research design system | Both pages feel consistent, readable, and professional. | UI components agent | MB00 | TBD | Proposed |
| MB02 | Movers data and evidence contracts | Rankings and comparisons are accurate, scoped, and recoverable. | Data agent | MB00 | TBD | Proposed |
| MB03 | Market Brief redesign | Users understand what matters and where to research next. | Market Brief agent | MB01; MB02 contract | TBD | Proposed |
| MB04 | Interactive Top Movers | Selecting a company connects performance, context, and evidence. | Top Movers agent | MB01; MB02 | TBD | Proposed |
| MB05 | Connected state and research handoffs | Filters and discovery reasons survive cross-page navigation. | Navigation agent | MB00; MB02 contract | TBD | Proposed |
| MB06 | Integration and visual verification | The complete discovery journey works and matches the concepts. | Integrator / QA agent | MB03; MB04; MB05 | TBD | Proposed |

MB01, MB02, and MB05 can proceed in parallel after MB00 publishes interfaces. Page agents may build against agreed synthetic fixtures while data integration proceeds. Assign a single owner for shared files; avoid concurrent edits to the app shell, routing, or state definitions.

## Reviewed starting point

The three supplied files were inspected. The full repository, shared CSS, and rendered application have not been reviewed for this plan. Resolve exact paths and current behavior during MB00; do not assume the attached copies are the repository's latest versions.

| File | Existing capability | Redesign opportunity |
| --- | --- | --- |
| introduction_tab.py | Market overview, sector display, company snapshot, technical charts, AI summary, research routing | Remove repeated information, create briefing hierarchy, connect sector selection to discovery |
| top_movers_tab.py | Weekly rankings, sector filter, breadth, news, company handoff | Selectable table and synchronized company evidence panel |
| top_movers_data.py | Screened universe, performance batches, limited quote enrichment, sector aggregation, news | Independent caching, aligned comparisons, selected-company enrichment, honest coverage |

Observed issues to resolve:

- Market Pulse / AI Insights selection currently does not alter dashboard rendering.
- Introduction sparklines use preset positive/negative shapes rather than historical prices.
- Movers news remains tied to the initial leaders and laggards after sector filtering.
- “News driving the movers” overstates causality.
- A cache TTL does not establish automatic refresh; current refresh wording is misleading.
- The screener request caps the starting universe at 500 stocks.
- Sector averages represent screened stocks, not sector ETF returns.
- Saved company interpretation keys do not identify the evidence snapshot.

## MB00: repository review and contracts

**Outcome:** A runnable implementation shell with clear responsibilities and preserved functionality.

**Minimum implementation:**

1. Read applicable AGENTS.md and inspect routing, app_shell, styles, provider clients, market/history charts, company_snapshot, ResearchContext, and workspace_handoff.
2. Locate current equivalents of the supplied files and identify public callers.
3. Publish shared component interfaces, discovery-state contract, data contract, and a file ownership map.
4. Create focused modules using repository conventions. Suggested responsibilities: shared research UI, Market Brief renderer, movers renderer, movers evidence layer, discovery state/handoffs.
5. Establish runnable page shells and deterministic development fixtures. Fixture values must stay isolated from production rendering and be visibly identified in development previews.

**Acceptance / verification:**

- [ ] Current entry points and preserved features are documented.
- [ ] Shared interfaces and dependency ordering are agreed before parallel edits.
- [ ] Only one agent owns each shared file at a time.
- [ ] Baseline checks and actual repository revision are recorded.

**Cut line:** No framework migration or general rewrite of the application.

## MB01: shared research design system

**Outcome:** Calm, consistent visual hierarchy matching the approved concepts.

**Minimum implementation:**

1. Use navy navigation, warm off-white canvas, white cards, subtle borders, navy text, teal actions, and restrained performance colors.
2. Build reusable headers, metric cards, briefing cards, company identity, evidence rows, filters, and empty/loading/partial/error states.
3. Standardize compact currency and percentage formatting, sentence-case headings, spacing, timestamps, and readable typography.
4. Scope styles to the changed views; preserve unrelated workspaces. Prefer native Streamlit controls and avoid brittle generated-DOM selectors.

**Acceptance / verification:**

- [ ] Both pages use the same components and spacing conventions.
- [ ] State is expressed in text as well as color.
- [ ] Controls are functional and keyboard accessible.
- [ ] No decorative HTML button masquerades as an interactive control.
- [ ] Existing unrelated page styling remains usable.

**Cut line:** Defer animations, decorative widgets, and a complete application-wide restyle.

## MB02: movers data and evidence

**Outcome:** Trustworthy rankings with on-demand company evidence.

**Minimum implementation:**

1. Separate cached universe/performance loading from benchmark context and selected-company quote/history/news enrichment.
2. Keep the ranked table usable while company evidence loads or fails. Bound requests and reuse existing FMP transport and news clients.
3. Define explicit units and supported periods. Align benchmark/sector comparisons by dates and return methodology; display excess returns in percentage points.
4. Return requested/usable counts, coverage, screening rules, quote/performance timestamps, providers, missing datasets, and warnings.
5. Represent related news with safe links, actual publication metadata when supplied, and retrieval timestamps. Retrieval date is not publication date.
6. Bind interpretations to ticker, period, model, and evidence snapshot. Regenerate only on explicit request.

**Shared contract shell:**

| Area | Required contract information |
| --- | --- |
| Universe | Screening rules, request limit, requested count, usable count, coverage percentage |
| Performance | Available periods, explicit units, observation dates, price/return basis |
| Comparison | Benchmark identifier, aligned return dates, sector method, compatibility status |
| Volume | Current versus completed session, average-volume basis, measurement time |
| Evidence | Company identity, history, news, source links, quote dates, retrieval dates |
| Interpretation | Evidence fingerprint, ticker, period, model, generation time |
| Recovery | Partial status, missing datasets, sanitized warnings, retry scope |

**Acceptance / verification:**

- [ ] Ranking and comparison fixtures independently verify calculations and units.
- [ ] Unsupported periods and incompatible comparisons are withheld explicitly.
- [ ] Universe scope and partial coverage are visible.
- [ ] Real historical observations replace preset sparklines.
- [ ] Screened-sector averages and sector ETF returns have distinct labels.
- [ ] Intraday volume is not presented as completed-session relative volume.
- [ ] Selected-company news failure preserves rankings and price evidence.
- [ ] Ordinary filters and chart controls make zero model calls.
- [ ] Provider/model credentials never enter payloads, logs, or exports.

**Cut line:** Use available providers; defer new paid services and universal market coverage.

## MB03: Market Brief redesign

**Outcome:** Users quickly answer “What is happening? What matters? Where should I look next?”

**Minimum implementation:**

1. Display Market Brief in navigation while preserving render_introduction_tab or safely migrating its callers.
2. Header: title, subtitle, market-session status, evidence time, Refresh, and company/question search.
3. Compact snapshot: S&P 500, Nasdaq, VIX, leading sector, and breadth only for a defined supported universe.
4. “The market in 30 seconds”: three concise observations with supporting evidence/actions. Label deterministic interpretation accurately; do not imply model generation.
5. Benchmark chart with supported timeframe controls alongside ranked sector bars.
6. Sector selection routes to filtered Top Movers. Up to three documented research candidates link to company detail or Research.
7. Consolidate cross-asset data into expandable Macro context. Remove duplicate panels and implement or remove the ineffective view toggle.
8. Preserve company snapshots, configurable historical technical charts, explicit AI analysis, and existing company handoffs.

**Acceptance / verification:**

- [ ] Findings and next actions are visible before long technical detail.
- [ ] Search, sector selection, chart controls, and candidate actions work.
- [ ] Market/session wording reflects evidence timing, including closed markets.
- [ ] Missing observations are withheld rather than inferred from defaults.
- [ ] Company snapshots and technical analysis remain accessible.

**Cut line:** Research opportunities are discovery candidates, not investment recommendations.

## MB04: interactive Top Movers

**Outcome:** Select a mover and immediately understand performance and available evidence.

**Minimum implementation:**

1. Implement approximately 65% table / 35% company panel on desktop; stack on narrower screens.
2. Controls: Leaders/Laggards, sector, supported timeframe, benchmark.
3. Summaries: usable universe, advancing percentage, median period return. Explicitly label filtered versus full-universe scope.
4. Table: company/ticker, period return, benchmark excess return, qualified volume ratio, and supported related event. Keep secondary metrics in optional details.
5. Use native selectable rows when supported by installed Streamlit; otherwise a functional selection alternative.
6. Selection synchronizes identity, actual price history, comparison, dated related news, optional interpretation, and research/peer actions.
7. Preserve valid selection after filtering; otherwise select the first usable result deterministically. Handle no results cleanly.
8. Add watchlist controls only if an existing supported watchlist workflow is present.

**Acceptance / verification:**

- [ ] Selecting a row updates that company's chart and evidence.
- [ ] Changing period updates rankings, summaries, labels, and comparisons together.
- [ ] Sector filtering does not leave unrelated headlines visible.
- [ ] News says “Related news & potential catalysts” and does not assert unsupported causes.
- [ ] Empty, partial, and missing enrichment states remain usable.
- [ ] Refresh/cache wording matches actual behavior.

**Cut line:** No unsupported buttons, trade execution, or automatic AI generation on selection.

## MB05: connected state and research handoffs

**Outcome:** Users carry their discovery context into research and return without losing filters.

**Minimum implementation:**

1. Extend existing handoff/state patterns through bounded compatible adapters.
2. Preserve sector, timeframe, benchmark, direction, ticker, and originating workspace.
3. Support Market Brief → sector movers; candidate → company/Research; mover → Research; company → existing peer comparison; return → restored selection.
4. Include discovery reason, period performance, compatible comparisons, evidence times, and bounded source references in research context.
5. Prefill the research request; do not automatically submit a paid analysis through navigation. Use a distinct explicit action to run research.

**Acceptance / verification:**

- [ ] End-to-end navigation preserves filters and selection.
- [ ] Invalid tickers fail before provider dispatch.
- [ ] Existing handoffs remain compatible.
- [ ] Independent sessions do not share state or results.
- [ ] Navigation and reruns make zero model calls.
- [ ] No credentials or oversized raw financial payloads enter handoffs.

**Cut line:** Defer universal session migration and durable cross-restart navigation recovery.

## MB06: integration and visual verification

**Outcome:** A verified local implementation with clear release status.

**Minimum implementation:**

1. Integrate incrementally with one shared-file owner and preserve unrelated changes.
2. Run focused tests for calculations, selection transitions, evidence fingerprints, and handoffs. Run the full offline suite when shared routing/state changes.
3. Verify actual browser journeys and layout at 1440×900, 1280×800, and 390×844. Tables may scroll intentionally; controls and evidence must remain readable.
4. Verify missing keys, partial providers, empty sectors, unavailable comparisons, and saved interpretation mismatch states.
5. Capture review screenshots and compare with both approved concepts. Live provider verification is separate from synthetic UI checks.
6. Update PLAN.md and README as appropriate with actual commands, results, limitations, and mocked versus live scope.

**Acceptance / verification:**

- [ ] Both pages load and resemble the approved hierarchy.
- [ ] Market Brief → filtered movers → selected evidence → Research → return works.
- [ ] No clipped primary controls or inaccessible detail panels.
- [ ] Source links, keyboard focus, labels, and formatting are usable.
- [ ] Quotes, retrieval times, and AI generation times remain distinct.
- [ ] No fictional concept data appears in production.
- [ ] Existing company charts and unrelated workspaces pass regression checks.
- [ ] Remaining dependencies and checks not performed are recorded honestly.

**Cut line:** Local implementation and verification are the delivery target. Do not claim deployment or create a hosted release from this document alone.

## Team invocation prompt

```text
Use $feature-development-team to implement <PLANNING_ID> from
docs/features/market-brief-top-movers-jira-plan.md.

Attach the approved Market Brief and Top Movers concept images.
Check the current repository, applicable AGENTS.md, and existing Jira issues.
Create or reuse one AAFA implementation ticket before coding; record its actual
key in the backlog. Follow minimum scope, dependencies, ownership, acceptance
criteria, and cut lines. Publish contracts before parallel implementation.

Preserve existing providers, company snapshots, technical charts, handoffs,
saved research, and unrelated work. Use genuine data or honest unavailable
states. Concept-image numbers and headlines must never become production data.

Implement and verify the authorized local changes. Update the ticket with
progress, changed files, verification evidence, and remaining limitations.
Check duplicates before creating follow-up tickets. Update PLAN/README as
needed. Record deployment as pending unless separately authorized and verified.
Follow existing project authorization rules for commit/push/deployment.
Report actual outcomes; do not stop at a plan or assume checks passed.
```

The named team skill is a user-environment convention from the supplied example. If it is unavailable, use the available team workflow and report that substitution. This planning file itself does not create Jira tickets or start implementation.

## Jira completion record template

Copy into each implementation ticket and maintain throughout delivery:

```markdown
### Scope
Planning ID:
Owner:
Dependencies / linked issues:
Repository revision:

### Implementation
Changed files:
Preserved behavior:
Scope deviations and rationale:

### Verification
Commands and results:
Browser journeys / viewports:
Evidence: mocked / recorded / live:
Model/provider call-count checks:
Screenshots:
Checks not performed:

### Delivery status
Local implementation: Pending / Implemented / Verified
Deployment: Not in scope / Pending / Verified
Remaining limitations and linked follow-ups:
```

## Release boundary

Mark stories complete only against their actual acceptance criteria. If deployment is explicitly included in a ticket, local verification alone is insufficient to close it. Keep unsupported capabilities and unresolved data gaps visible; cut stretch scope before weakening evidence quality or navigation correctness.

## Reviewed local delivery — 2026-10-12

The explicitly invoked feature-development-team completed the bounded P01-P06 slice described in [the team report](2026-10-11-opening-ui-team.md). The proposed parallel owner names above remain planning history; one builder owned production edits, with sequential financial specialist/planner/independent verifier handoffs.

| Planning ID | Current scoped outcome | Remaining acceptance |
| --- | --- | --- |
| MB00 | Repository/provider/reference review and implementation boundaries verified | Live entitlement/freshness not certified |
| MB01 | Shared opening-page light presentation, native controls and responsive cards delivered | Native grids retain global dark theme; no full-app redesign/pixel match |
| MB02 | Finite normalization, screened coverage and period-aware ranking, independent quote/history/news delivered | [AAFA-13 dated comparisons](https://bigmeatpete717.atlassian.net/browse/AAFA-13); [AAFA-14 qualified volume](https://bigmeatpete717.atlassian.net/browse/AAFA-14) |
| MB03 | Market Brief hierarchy, observations, eight-range chart, ETF sector exploration/candidates/macro context delivered | Universal market breadth and exchange-session status remain unavailable |
| MB04 | Selectable movers, evidence panel, related news/recovery and sector context delivered | Comparison/volume contracts above; unsupported events/Watchlist/Compare deferred |
| MB05 | Typed local discovery metadata, editable explicit Research drafts and same-session restoration delivered | No financial packets or durable restart migration |
| MB06 | 452 full offline tests; compile/import, fresh health, desktop/mobile synthetic browser and independent review passed | No live model/provider, hosted, clean-install or deployment verification |

Both Jira issues are substantive follow-ups, not completion tickets for delivered code. Creation and verified payloads are recorded in the team report; existing issues were not modified. The initial planning table is not a claim these broad workstreams are fully complete.

Saved implementation screenshots: [Market Brief](assets/2026-10-11-opening-ui/qa/market-brief-desktop.png), [Market Brief chart/candidates](assets/2026-10-11-opening-ui/qa/market-brief-detail.png), [Top Movers](assets/2026-10-11-opening-ui/qa/top-movers-desktop.png), [mobile selected evidence](assets/2026-10-11-opening-ui/qa/top-movers-mobile-detail.png). Screenshots use clearly labelled synthetic offline evidence, not current market data.

Primary UI sources remain `src/langgraphagenticai/ui/introduction_tab.py` and `src/langgraphagenticai/ui/top_movers_tab.py`; shared styling is `ui/opening_presentation.py`, with separate provider/domain/state modules listed in the report. No commit, push or deployment performed.
