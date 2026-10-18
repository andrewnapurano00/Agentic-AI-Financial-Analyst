# Axiom Research — Engineering Implementation Contract
Version: 1.0
Status: Ready for requirements discovery; implementation starts only after Gate 1 passes.
Objective: Reproduce the approved institutional visual direction while retaining every existing content item, control, export, state behavior and explicit AI action.

## 1. Authority and scope

This contract is the source of truth for engineering scope and behavior. Reference images define composition and visual character, not financial facts, calculations, supported features or backend behavior.

Order of precedence:
1. User instructions and applicable repository instructions.
2. This implementation contract and the verified content-preservation inventory.
3. Axiom_Research_Professional_Redesign.md for page coverage and design rationale.
4. Approved mockups for visual layout.
5. Existing behavior where this contract does not explicitly change it.

Retain Streamlit and the Axiom Research name. This project redesigns presentation and information organization. It does not migrate to React, rewrite agents, change providers, modify financial formulas, adjust investment scoring or introduce trade execution.

The previous Bloomberg_Style_Introduction_Top_Movers_Engineering_Prompt.md contains additional requested company metrics, earnings/peer panels and sector heatmap specifications. Track those as a separate feature workstream. Existing functions can be restyled immediately after Gate 1; missing capabilities require their own verified data contracts. The professional navy/gold theme in this contract supersedes the earlier red-accent theme for shared UI. Heatmap gains/losses remain green/red; selected tile outline is gold.

## 2. Reference package to place in the repository

Create this structure, adapting existing docs conventions without creating competing specifications:

```text
docs/redesign/
  implementation-contract.md
  professional-redesign.md
  references/
    market-brief.png
    deep-research.png
    portfolio-lab.png
  discovery/
    requirements-understanding.md
    current-content-inventory.csv
    preservation-map.csv
    behavior-contracts.md
    design-decisions.md
  qa/
    acceptance-matrix.csv
    visual-comparison.md
    screenshots/
```

Reference image correspondence:
- market-brief.png = approved Market Brief concept (original exec-6a69070f-093d-42ed-82f7-1ff532a22390.png).
- deep-research.png = approved Deep Research concept (original exec-f21d5ee4-c8a5-40a1-9b97-e057236af8bf.png).
- portfolio-lab.png = approved Portfolio Lab concept (original exec-1d97d2d8-e4d7-42ed-998e-a86b8f4fd66f.png).

These names describe copies placed in the engineering repository; the original image downloads must be supplied. Do not infer image contents from filenames alone.

Image corrections required in code:
- Do not implement mockup Live data, Evidence up to date, Source coverage percentages or research assertions unless actual evidence supports them.
- Do not add the mockup Global Equities selector, user profile, portfolio preset service, new saved-history service or new risk score just to match a picture.
- Do not treat mockup ticker prices, counts, dates, weights, return percentages, comparison ratios or market narratives as data.
- The mockup's index/sector rows must use canonical mappings. SPY is a benchmark ETF, not a sector.
- Use existing run-state semantics. A designed Review complete badge is not authorization to mark an incomplete report complete.
- Keep the three branding treatments consistent in implementation: use one Axiom Research wordmark, icon set, spacing system and navigation pattern.

## 3. Gate 0 — read-only discovery

Before editing application code, every agent reads:
- applicable AGENTS.md and relevant repository skill instructions;
- this contract, the redesign plan and all three actual images;
- main.py routing, ui/streamlitui/loadui.py, ui/app_shell.py and ui/opening_presentation.py;
- its assigned active renderer and the helpers, state modules and provider interfaces that renderer calls;
- relevant existing tests.

The uploaded ZIP was reviewed statically; runtime appearance and calculations were not validated. Establish a reproducible baseline locally. Run in a safe development environment using configured secrets without printing them. If provider access is unavailable, use clearly identified test fixtures for UI verification and document unavailable live checks. Keep fixtures isolated from production behavior.

Discovery deliverables:
1. Trace the route → renderer → relevant helpers → state/provider interfaces for every assigned page.
2. Capture current desktop screens, including result tabs and important failure/partial states.
3. Inventory displayed content and controls from active render paths. Scanning headings alone is insufficient.
4. Document dependencies and any unclear or unavailable functionality.
5. Record baseline checks and any pre-existing failures.

Do not edit app source, CSS or provider logic during discovery. Documentation, inventories and baseline captures are allowed.

## 4. Gate 1 — demonstrate requirements understanding before coding

Each implementation agent submits a written requirements readback containing:
- the user's intended result in its own words;
- the exact approved image and regions it owns;
- existing content it will preserve and each proposed destination;
- active renderer/functions and state keys it must protect;
- which visual-only elements will be omitted because there is no supporting functionality;
- explicit non-goals;
- failure, partial-data and mismatch states it must render;
- acceptance IDs and how it will verify them;
- dependencies on the shared shell/component owner.

The integration owner reviews the readback against actual code. Gate 1 passes only when:
- every inventoried existing item has a proposed destination;
- no uncontrolled feature additions or invented data remain;
- all route/state/paid-call contracts are understood;
- shared component interfaces and edit ownership are recorded;
- unresolved questions have either an evidence-backed decision or are isolated from dependent work.

Record reviewer name/agent, date, reviewed artifact versions and PASS/FAIL. Agents must not self-certify their own readback. The integration owner can request corrections without asking the user to approve routine implementation choices. Escalate only genuine product ambiguity that cannot be resolved from the references and current behavior.

A vague statement such as “I will make it look like the screenshot” does not pass.

### Required preservation inventory schema

One row per existing content group AND each independently meaningful interactive control/export:

| Column | Required meaning |
| --- | --- |
| item_id | Stable ID, e.g. PM-LIMIT-MAX-POSITION |
| route / subview | Existing workspace and tab/mode |
| source | Canonical module and active function |
| content_or_action | Exact content/control/export |
| data_basis | Existing field/provider/formula or static text |
| state_contract | Widget/session key and persistence behavior |
| current_location | Current visible region |
| proposed_location | Exact redesigned tab/panel/disclosure |
| visibility_rule | Always, conditional, or labeled disclosure |
| regression_check | Interaction/output that proves preservation |
| owner / status | Agent and discovery/implemented/verified |

“No content removed” means every baseline item remains reachable with equivalent information and behavior. Retaining unused helper code does not establish preservation. Removing duplicate decorative headings is permitted; removing facts, disclosures or actions is not.

## 5. Fixed design specification

| Token | Required starting value |
| --- | --- |
| Background | #0B1220 |
| Panel / alternate panel | #121D2B / #172334 |
| Border | #283649, 1px |
| Primary / secondary text | #E6EBF2 / #9AA9BC |
| Selected/primary accent | #C8AA73 |
| Positive / negative | #37B68C / #E2747E |
| Corner radius | 6px panels; 4px controls |
| Font | Inter if bundled/available, otherwise system sans-serif |
| Numeric text | Tabular numerals; monospace where appropriate |
| Page title | 24px; one per workspace |
| Section title / body | 16px / 14px; report prose 16px |
| Table text / evidence | 13px / 12px |
| Spacing scale | 4, 8, 12, 16, 24, 32px |

Maintain readable contrast and keyboard focus; adjust a token if accessibility requires it, recording the reason. Do not fetch fonts at runtime solely for cosmetics. Use neutral backgrounds, no decorative gradients, neon glows or excessive shadows.

At 1440px:
- expanded sidebar: 220px;
- main page padding: 20px;
- context bar: approximately 48px;
- index strip when relevant: approximately 64px;
- panel gap: 16px;
- first screen prioritizes analysis rather than a large introduction;
- controls approximately 36–40px high; preserve comfortable keyboard/pointer use.

At 1920px, keep main content up to approximately 1680px wide and increase usable chart/table width, not type sizes. At 1024px collapse secondary rails below main content where necessary. At 390px collapse sidebar, stack panels, allow local horizontal table scrolling and wrap controls. Never force the full desktop layout onto a phone.

Use one visual system in app_shell and shared components. Remove redundant page-specific style overrides after proving their replacement covers the existing elements. Avoid generated Streamlit class selectors; favor documented theme options, semantic/test attributes and scoped component classes. Centralize unavoidable version-sensitive selectors and test them.

## 6. Shared shell and component contracts

Preserve all eight route identities:
Introduction, Top Movers, Research, Equity Report, Stock Screener, Portfolio Lab, Deep Research, Deep Research V2.
Display Introduction as Market Brief.

Sidebar groups:
- Discover: Market Brief, Top Movers, Stock Screener.
- Analyze: Research, Equity Report, Deep Research, Deep Research V2.
- Allocate: Portfolio Lab.

Use one selected-state accent and one Axiom Research wordmark. Global model/use-case configuration, key inputs, readiness and debug remain accessible in Settings. Local task configuration stays within its workspace. Never replace editable settings with decorative readiness labels.

Shared presentation interfaces should cover:
- page/context header;
- dated evidence/status strip;
- summary row;
- panel with title, optional caption/action and content slot;
- action toolbar;
- styled selectable table retaining native events;
- chart framing/theme and evidence footer;
- state banner: empty/loading/partial/error/saved/mismatch;
- labeled supporting disclosure and exports.

Agree exact interfaces before page work. Components accept existing normalized data; they do not fetch providers, mutate financial values or run models. Clearly distinguish provider fact, calculation, AI interpretation and user assumption.

Consolidate Introduction/Top Movers early-return presentation with the shared shell carefully. Keep one working command/search flow and prevent duplicate page headers. Routing remains owned by the integration agent.

## 7. Page composition contracts

### MKT — Market Brief and company view
- Context bar → index strip → Market Brief title/refresh → primary analytical row.
- Primary row desktop: chart 50%, deterministic observations 25%, sector ETF panel 25%, matching the approved image's three-panel composition.
- Next row: three existing research candidate cards; retain snapshot/research actions.
- Next row: macro context and existing AI draft input.
- Keep every chart range/technical control, provider/as-of/date basis, source errors and existing coverage disclosures.
- Company search opens the existing snapshot; arrange quote/chart/metrics using the previous company screenshot specification. Retain current fundamentals, performance, technical analysis, news and saved interpretation.
- Sector Heatmap is a separately scoped proposed addition. Do not add a tab that looks functional until its real feature is implemented.

### MOV — Top Movers
- Title/refresh/evidence → direction/sector/period toolbar → existing summary statistics.
- Ranked table 65%, selected-company panel 35%, sector aggregates and methodology below.
- Preserve selected-period ranking, row selection and keyboard alternative, empty-sector handling, saved ticker identity, dated quote/history/news and all handoffs.
- Keep chart/ranking date and basis distinctions. Do not fabricate volume ratios or excess returns.
- Use Market Brief's panel/table styles rather than inventing another theme.

### RES — Research
- Keep Chat and Guided research visibly selectable.
- Chat: security/context header → saved conversation → draft composer and explicit submit; supporting evidence/debug access nearby.
- Guided: compact configuration → Prepare plan → readable plan → Run plan → facts/interpretation/risks/missing inputs/evidence.
- Retain pricing/spend controls, acknowledgements, usage counts, New thread and configuration-mismatch behavior. UI relocation must not reset the thread or spend settings.

### EQ — Equity Report
- Use the active render_equity_report_tab path, not legacy presentation assumptions.
- Retain Thesis, Performance, Financials/Valuation, Sources/Audit, Exports.
- Thesis: executive summary and recommendation snapshot, AI note and explicit committee action.
- Performance: period control, return table/chart.
- Financials: all existing section tables and takeaways.
- Audit: coverage and raw combined scorecard.
- Exports: all existing formats and content; changing PDF appearance is a separate task.
- Preserve peer framework, grading/scoring labels, committee fingerprint mismatch handling and existing inputs.

### DR — Deep Research and V2
- Saved security/run header → local configuration disclosure and history → visible run state/gaps → existing tabs.
- For Deep Research, keep Investment thesis, Company comparison, CrewAI decision, Sources & evidence, Research notebook, Investment brief & scenarios.
- Thesis pane 75%, compact evidence rail 25%. The rail displays existing validated fields/counts, not a synthetic trust score. It may become a disclosure on narrow screens.
- Preserve new-run settings, saved history, all retries/finalization, follow-ups, sources and exports.
- V2 retains its own Report, Decision, Comparison, Sources, Performance, Investment brief & scenarios and distinct cost/runtime controls. Do not merge V1/V2 backend semantics.
- Scenario controls keep original eligibility/freshness rules and editable assumptions; narrative or images cannot override them.

### SCR — Stock Screener
- Compact base filters → clearly labeled server ranges/enrichment/post-screen disclosures → explicit Run Screener.
- Saved result table remains usable when configuration is reopened.
- Preserve every ratio/technical filter, missing-data setting, pagination/API limit, enrichment/display cap and RSI period.
- Preserve CSV and selected-company handoff. No implicit screener requests on filter changes.

### PORT — Portfolio Lab
- Keep Optimizer and AI Portfolio Manager top-level tabs.
- Manager: existing analysis mode → local configuration/inputs → explicit run → existing summary → result tabs.
- Retain Recommendations, Rebalance Trades, Agent Debate, Evidence Scores, Sector Exposure, Monitoring, Diagnostics, AI Chat.
- Recommendations desktop: table 70%, exposure/committee summary rail 30%. Existing selection/detail capabilities may be reused; do not invent row-driven data loading if none exists.
- Preserve uploaded holdings, manual tickers, screen mode, candidates/watchlist, benchmark/history/risk, position/sector/cash/min-trade controls.
- Distinguish current weights, proposed targets and calculated trades.
- Optimizer keeps all current configuration, price data, efficient frontier, risk/return, crisis roles, weights and test portfolio outputs.

## 8. Behavioral invariants

- Navigation, row selection, filters, chart controls, disclosures and ordinary reruns do not cause new paid model calls.
- Explicit run/generate/retry actions retain their current meanings and prerequisites.
- Preserve provider caching/freshness and saved-result fingerprints; do not imply a cache hit is live evidence.
- Preserve widget/session-state keys unless a reviewed migration protects the original values. Moving widgets across tabs/containers can change lifecycle behavior even with the same key; test remounts and navigation.
- Partial failures retain usable results and saved work; another ticker's data must never appear under a newly selected symbol.
- Zero remains zero; missing remains unavailable; NaN/infinity never becomes an invented value.
- Evidence gaps, mismatch and scenario ineligibility remain visible near the affected output.
- Preserve safe link behavior, escaped provider text and secret handling.
- Export schemas, calculations and contents remain unchanged in this presentation workstream.
- No app-wide backend cleanup, new investment recommendations, universe expansion or default threshold changes.

## 9. Ownership and Jira tickets

Assign agents by files, not just by visual regions.

| Ticket | Owner | Edit boundary | Depends on |
| --- | --- | --- | --- |
| RDS-01 Discovery and preservation baseline | Integration owner + read-only page agents | docs/redesign/discovery only | None |
| RDS-02 Theme, shell and component contracts | Shared UI owner | app_shell.py, opening_presentation.py, shared presentation components; coordinate loadui.py | Gate 1 |
| RDS-03 Market Brief / Top Movers | Market UI owner | introduction_tab.py, top_movers_tab.py | RDS-02 contracts |
| RDS-04 Chat / Guided research | Research UI owner | research UI portions in main.py by integration-owned patch; guided_research_tab.py | RDS-02 contracts |
| RDS-05 Equity Report | Report UI owner | active equity_report_tab.py presentation functions | RDS-02 contracts |
| RDS-06 Deep Research / V2 / Scenarios | Deep Research UI owner | deep_research_tab.py, deep_research_v2_tab.py, investment_brief.py presentation | RDS-02 contracts |
| RDS-07 Screener / Portfolio Lab | Allocation UI owner | stock_screener_tab.py, portfolio_optimizer_tab.py, ai_portfolio_manager_tab.py | RDS-02 contracts |
| RDS-08 Integration and acceptance | Integration + independent QA reviewer | main.py, loadui.py, QA/checks and reviewed integration fixes | RDS-03 through RDS-07 |
| RDS-09 Heatmap / missing company metrics | Separate feature owner | Verified provider/UI scope from earlier prompt | Separate data discovery |

One owner at a time edits main.py, loadui.py or shared styling. Page agents request a shared change rather than modifying those files independently. Use isolated branches/worktrees if available. Agent availability determines staffing; these are ownership roles, not a requirement to run eight agents at once.

Every Jira ticket includes: objective, input images/spec IDs, owned files, dependencies, preserved item IDs, behavioral invariants, acceptance IDs, required QA evidence and explicit exclusions.

## 10. Gate 2 — implementation review

Each agent supplies:
- requirement/readback PASS record;
- changed files and scope;
- completed preservation rows;
- screenshots at required widths;
- test results and any baseline failures;
- known deviations with reasons;
- evidence of explicit-action and state behavior preservation.

A reviewer rejects changes that merely resemble the image while dropping controls, inventing data, using dead buttons or altering financial logic.

## 11. Gate 3 — measurable acceptance

| ID | Pass condition | Evidence |
| --- | --- | --- |
| ACC-01 | All eight routes and nested modes remain accessible | Navigation walkthrough |
| ACC-02 | Every baseline inventory item has a verified destination | No unresolved preservation rows |
| ACC-03 | Three implemented reference pages follow approved composition and shared tokens | Same-viewport screenshots with side-by-side review |
| ACC-04 | All remaining pages use the same shell and component rules | Screens for each route |
| ACC-05 | No clipping/page-level horizontal overflow at 1440, 1920, 1024, 390px | Browser screenshots; local table scroll permitted |
| ACC-06 | Route/filter/chart/tab/select interactions produce zero new paid calls | Instrumented counters or mocked workflow assertions |
| ACC-07 | Explicit runs retain existing prerequisites/outputs | Targeted workflow tests |
| ACC-08 | Selected ticker/thread/run/input settings survive appropriate navigation/remounts | State tests and browser walkthrough |
| ACC-09 | Partial/missing/mismatch/failure states preserve saved work and visible limitations | Fixture-driven screenshots and tests |
| ACC-10 | Existing exports retain content/schema and produce valid files | Before/after representative payload checks |
| ACC-11 | Facts/formulas/units/scoring/thresholds/provider contracts unchanged | Diff review and relevant regression tests |
| ACC-12 | Keyboard selection, focus and readable signed states work | Keyboard walkthrough/contrast inspection |

Pixel identity to generated images is not required: generated text and unsupported details are intentionally corrected. Visual acceptance checks composition, hierarchy, spacing, typography, palette, table/chart clarity and full content coverage. Record every material deviation; do not declare parity based on a small thumbnail.

Use existing tests as applicable: workspace handoffs/presentation, market tabs/opening discovery, Introduction technical, Guided research, Equity committee, Deep Research UI/recovery/V2/timestamps and Investment brief. Run required repository checks. New tests should protect changed behavior, especially state/remounts and paid-call boundaries; avoid brittle tests of static CSS strings alone.

## 12. Required completion report

Return:
1. Which gates passed and who reviewed them.
2. Implemented pages and visual comparison screenshots.
3. Preservation totals: baseline items, verified items, outstanding items.
4. Validation results and unresolved limitations.
5. Separate list of unimplemented new features from the earlier screenshot prompt.
6. Concrete changed-file summary and rollback approach.

No “complete” claim while preservation rows are outstanding or required checks are unrun without explicit explanation.

## 13. Copy-paste lead-agent prompt

```text
You are the integration lead for the Axiom Research professional Streamlit redesign.

Read docs/redesign/implementation-contract.md, professional-redesign.md, all three reference images, and applicable repository instructions. This is a presentation redesign with complete existing-content preservation.

Start with Gate 0 read-only discovery. Inspect every routed workspace and nested mode, trace active renderers and state/provider interfaces, and inventory content, controls, exports and important error/mismatch states.

Coordinate page agents with clear file ownership. Require a written requirements readback from every implementation agent and review it against the code. Do not allow any application/CSS edits until Gate 1 passes for that agent and the shared component contracts are agreed.

Build the shared theme/shell first. Implement approved layouts incrementally, preserving existing financial logic, provider contracts, session behavior and explicit paid actions. The images contain illustrative data and unsupported decorative capabilities; use real existing functionality only. Keep heatmap and missing screenshot metrics in the separately scoped feature backlog.

Verify against ACC-01 through ACC-12. Require side-by-side screenshots at the specified widths, complete preservation rows, targeted tests and an independent review. Continue through integration and fixes until the authorized redesign is complete. Escalate only genuine unresolved product decisions; do not ask for routine implementation permission.

Your first deliverable is the requirements-understanding document, content inventory, preservation map, behavior contracts, ownership plan and Gate 1 review result—not a code patch.
```

## 14. Copy-paste page-agent task template

```text
Assigned ticket: {RDS-ID}
Owned files: {explicit canonical paths}
Reference regions: {image + panels}
Preservation IDs: {assigned inventory rows}
Acceptance IDs: {applicable ACC IDs}
Dependencies: {shared contracts / preceding tickets}

Read the full contract and inspect the active code. Submit the Gate 1 requirements readback before editing app code. Explain the layout, all retained controls/content, protected state keys, paid-call boundaries and unsupported mockup elements.

After the integration reviewer records PASS, implement within owned files using shared components. Do not modify another agent's files, providers, financial formulas or state identities without a reviewed contract change.

Deliver the preservation map updates, screenshots, test results, deviations and changed-file summary. Do not claim completion without meeting the assigned acceptance criteria.
```
