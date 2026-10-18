# Axiom Research — Professional Investment Workspace Redesign

## Recommendation
Keep Axiom Research and its dark financial workstation identity. Evolve it into an institutional interface: dark navy, restrained gold accents, clear report typography, consistent table formatting, and a stable navigation shell. Retain the dense Bloomberg-inspired market layouts requested earlier. Use more breathing room for investment narratives than for market tables.

This is a design proposal based on static inspection of the uploaded finance_app_for_codex (3).zip. The live app was not run and financial calculations were not validated. The three accompanying generated images are illustrative visual concepts, not implemented screens or verified market data. No application files were modified.

## What the source review found

- Eight routed workspaces: Introduction (displayed as Market Brief), Top Movers, Research, Equity Report, Stock Screener, Portfolio Lab, Deep Research, and Deep Research V2.
- Research includes Chat and Guided research; Portfolio Lab includes Optimizer and AI Portfolio Manager. These distinctions need to remain visible.
- Shared shell styles already exist in ui/app_shell.py, but opening_presentation.py adds page-specific overrides. Heading sizes, page structure and content density consequently vary.
- Introduction and Top Movers return early in main.py, before the shared command bar, market strip and page header used by other workspaces. A consistent shell requires unifying presentation without changing the routing behavior.
- Workspace renderers add their own headings beneath the shared page heading. Several pages therefore risk redundant titles and explanatory text competing with the actual content.
- Global sidebar configuration is combined with workspace-specific controls. Portfolio Manager adds another sidebar header and its own benchmark/risk/position controls. Separate global settings from local task configuration.
- Equity Report is a substantial module (5,711 lines) with several presentation generations and helper layers. Trace the active renderer and its helper calls before redesigning; a text search across all headings alone does not establish current displayed content.
- The source has saved-run history, evidence dates, partial results, retries, audit tables, explicit AI actions and exports. These are product features to preserve, not visual clutter to delete.
- No dedicated Sector Heatmap renderer appears among the supplied UI modules or the eight routed pages. The earlier heatmap specification should be treated as a proposed component/workspace addition, not a feature already implemented in this ZIP.

## Visual system

| Element | Proposed treatment |
| --- | --- |
| Canvas | Deep navy #0B1220 |
| Main panels | Slate #121D2B; alternate #172334 |
| Borders | Cool gray #283649, thin and quiet |
| Primary text | Soft white #E6EBF2 |
| Secondary text | Steel #9AA9BC |
| Selected control | Restrained gold #C8AA73 |
| Positive / negative | Emerald #37B68C / muted red #E2747E, always with signed values |
| Type | Inter or system sans; tabular numbers in data; avoid condensed type for long reports |
| Sizes | Body 14–16px, table 12–14px, heading 22–26px, evidence 11–12px |
| Rhythm | 8px spacing scale; 16–20px panel padding; 12–16px gaps; 4–6px corners |
| Charts | Clear axes, subtle grid, limited consistent series colors, source/as-of footer |
| Primary buttons | One visually dominant action per task region; secondary actions quiet |

Keep market data dense but readable. Avoid using the same narrow monospace typography for financial narratives. Reserve red and green for directional changes and state; use gold for navigation and selection. The prior screenshot's red selected border may remain in the heatmap variant if desired, but it should be a conscious component rule rather than a second accidental theme.

## Shared shell

Left navigation remains stable, approximately 210–230px wide. Group existing routes under Discover (Market Brief, Top Movers, Stock Screener), Analyze (Research, Equity Report, Deep Research, Deep Research V2), and Allocate (Portfolio Lab), while preserving their underlying route identities. Groups improve scanning; they do not merge or remove routes.

Use one compact top context bar for workspace, selected securities, search/handoff, and evidence state. Market index strips belong on market pages; do not label placeholder index values as live data. Put global model, use case, API key inputs, provider readiness and debug controls in a clearly named settings disclosure. Keep local analysis controls in the page's configuration region.

Every page follows the same order: title/context → local configuration → summary → primary analysis → supporting content → evidence/audit/export. Successful saved results should remain prominent when configuration is reopened.

## Page-by-page content preservation map

| Existing workspace | Proposed layout | Content and controls that remain available |
| --- | --- | --- |
| Market Brief | Index strip; main chart; observations and sector panel; candidate cards; AI draft input | Search, company snapshot, all range/technical controls, market observations, sector ETF evidence, research candidates, macro context, refresh, source errors, saved interpretation and explicit regeneration |
| Company snapshot within Introduction | Full-width quote header; chart left; metrics right; supporting panels below | Existing quote/profile/fundamentals/performance, financial basis, currencies, news, technical analysis, interpretation and workspace handoffs. Earnings/peers/new metric panels from the earlier prompt remain proposed additions until mapped to providers |
| Top Movers | Filter toolbar; compact summary; ranked table left; selected company right; sector context below | Leaders/Laggards, sector, period, refresh, usable counts, advancing share, median, finite-return rankings, keyboard selection, selected quote/history/news, snapshot/research handoffs and methodology |
| Research — Chat | Context toolbar; wide conversation pane; compact submission composer; evidence access | Use cases/model, new thread, configuration mismatch warning, drafted requests, explicit submit, prior conversation, tables/takeaways, individual-answer citations and optional debug trace |
| Research — Guided | Configure → Prepare plan → Run plan → Saved result sections | Single-company question, spend ceiling, user pricing, unknown-cost acknowledgement, planning/execution usage, proposed steps, mismatch warnings, structured facts, risks, missing inputs, evidence details, JSON download and Deep Research handoff |
| Equity Report | Company/peer context; retained report tabs; summary and committee panel; tables in categorized sections | Thesis, Performance, Financials/Valuation, Sources/Audit, Exports; decision summary, AI evidence note, CrewAI debate, recommendation snapshot, peer framework, returns, Profile/Ratings/Factor Grades/Momentum/Total Return/Valuation/Growth/Profitability/Balance Sheet, takeaways, coverage audit, raw scorecard and existing downloads |
| Stock Screener | Compact query configuration; grouped filter disclosures; result table and export toolbar | Country/exchange/sector/industry, all server ranges, wide-open defaults, pagination/limits, enrichment limits, display limits, RSI period, post-screen ratios/technical filters, missing-value setting, saved output, CSV and company handoff |
| Portfolio Lab — Optimizer | Local setup; backtest summary; efficient frontier and risk table; allocation panels | Portfolio/ticker inputs, regimes, equal-weight/custom test portfolios, price data, efficient frontier, risk/return table, crisis fingerprint roles, portfolio weights and existing backtest controls/results |
| Portfolio Lab — AI Portfolio Manager | Analysis mode and configuration disclosure; summary; retained result tabs | Uploaded holdings, manual tickers, screening mode/candidates, optional watchlist, benchmark/history/risk profile, weight/sector/cash/min-trade limits, explicit hybrid committee run, recommendations, rebalance trades, debate, evidence scores, exposure, monitoring, diagnostics, AI chat and current holdings |
| Deep Research | Saved-run toolbar; brief status strip; readable thesis pane; optional evidence rail | New research configuration, horizon/depth/statement period/news window, history, gaps, review/finalize/retry, thesis, comparison, CrewAI decision, sources, research notebook/follow-ups, investment brief/scenarios and existing exports |
| Deep Research V2 | Same research shell, with clearly distinct V2 runtime/cost controls | Pilot configuration/limitations, provider choices, cost mode, depth/horizon/statement period, reuse policy, history, recovery/finalization, decision stage/retry, Report/Decision/Comparison/Sources/Performance/Investment brief & scenarios |
| Investment brief & scenarios in both research versions | Narrative topics; scenario input/result grid; sensitivity chart; provenance disclosure | Saved excerpts and evidence gaps, company selector, audited TTM and dated cap inputs, eligibility/freshness limitations, editable Bear/Base/Bull earnings and P/E assumptions, value calculations, sensitivity plot, provenance JSON, CSV/JSON downloads |
| Sector Heatmap — proposed | Full-width sector mosaic; industries lower left; Day/Week/YTD lower right | Follow the earlier screenshot specification, including 11-sector coverage, declared market-cap universe, return basis, real selection events and ticker handoffs. Keep existing sector bars and screened sector context reachable |

## Three visual concepts

1. **Market workstation:** restrained institutional version of the market overview, with consistent navigation, chart and sector density. The optional Sector Heatmap tab is labeled as proposed.
2. **Investment research:** a more readable thesis layout with preserved research tabs, run history, evidence gaps, and explicit committee actions. This visual pattern also fits Equity Report and V2.
3. **Portfolio operations:** clear distinction between current holdings and proposed target weights, with recommendation tables, exposure and committee rationale. Optimizer remains a separate visible tab.

Concept images show representative first-screen content, not every field at once. The preservation map specifies where full content remains reachable. Any illustrative extra card, derived statistic or action in an image requires an existing field/function or a separately defined addition; images do not authorize inventing data or functionality.

## Rules for preserving content

- Before implementation, inventory the active render paths, all widget keys, dynamic tables, exports, warnings and state transitions. Reconcile this map against that inventory.
- Maintain a checklist recording original component, original module/function, proposed destination, preserved action/state key and verification result. No feature disappears merely because it does not fit in a concept image.
- Detailed formulas, sources and diagnostic data may move into clearly labeled tabs/expanders. Missing evidence, run failures, stale/mismatched results and material eligibility restrictions remain visible at the point of use.
- Keep provider facts, calculated values, AI interpretation and user assumptions distinguishable. Cosmetic redesign must not change financial formulas, universes, units or default risk limits.
- Preserve explicit paid-model submission, saved results, caching, retry semantics, keyboard alternatives and selected ticker context.
- Never use display-only HTML buttons where a real callback is required. Custom styling must preserve accessible names/focus and native Streamlit functionality.

## Engineering approach

Begin with app_shell.py and a common design-token layer. Consolidate opening_presentation.py overrides into reusable page/panel/chart patterns. Adapt each active renderer incrementally rather than replacing entire modules. Preserve state identities and public interfaces.

Implement Market Brief/Top Movers first, then report/research layouts, then Screener/Portfolio Lab. The earlier three-workspace prompt remains the detailed specification for company metrics, earnings/peers and the proposed heatmap; this proposal extends visual consistency across the rest of the app.

Check desktop at 1440 and 1920px, intermediate at 1024px, and narrow layouts at 390px. Tables may scroll inside panels; controls and narrative text should not clip. Validate empty/configuration-missing, loading, saved-success, partial-data, mismatch and failure states. Confirm navigation does not trigger new model calls and that exports still contain the original content.

## Definition of success

The application feels like one investment research product, with a consistent shell and predictable page structure. Market analysis remains compact; investment narratives become easier to read; forms stop dominating saved results. Every existing content item and action has a recorded destination and passes a functional check. New heatmap or screenshot-only metric capabilities are identified as additions, not falsely presented as existing functions.
