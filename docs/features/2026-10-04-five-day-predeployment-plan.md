# Axiom: five improvements in five days

Planning date: 2026-10-04. Reviewed baseline: `77f7275070790cda4ec18754f3dfa01258ef3e9c` on `main`.

This is an executable backlog for the feature development team. It recommends five small, connected deliveries before a deployment decision. It does not claim that implementation, Jira tickets, or deployment have occurred. Each day is an estimated 6-8 hours of focused engineering plus review; provider access, dependency failures, and deployment credentials can extend that estimate. Keep the minimum scope below and defer stretch work.

## Recommended order

| Day / ID | Improvement | User outcome | Roadmap alignment |
| --- | --- | --- | --- |
| 1 / P01 | Connected company context and workspace-specific readiness | Select a company once, move between workspaces, retain work, and use non-AI features without an OpenAI key. | R03; reliability |
| 2 / P02 | Consistent terminal UI with clear evidence and status | A cleaner executive view makes facts, freshness, missing data, and actions easy to scan. | Shared presentation; provenance |
| 3 / P03 | A bounded research copilot with a visible plan | An agent selects useful research steps, shows progress, and returns an evidence-linked answer within explicit limits. | Grounding; cost and recovery |
| 4 / P04 | An auditable investment brief and scenario explorer | Users can see what drives a thesis and test bull/base/bear assumptions against saved financial evidence. | Financial correctness; decision usefulness |
| 5 / P05 | Automated release checks and a deployment rehearsal | Changes are repeatably tested, the production image starts correctly, and the chosen deployment has a rollback path. | Release readiness; verification |

The roadmap references are directional: update the exact applicable R01-R10 subitems in PLAN.md during implementation. Completing this backlog does not complete all ten roadmap milestones.

## What the structural review found

The review covered the application entry points, all eight navigation workspaces, shared UI, providers, financial calculations, chat graph/tools, Deep Research orchestration, portfolio agents, exports, tests, dependency manifests, and Docker configuration. Findings below come from source inspection and the existing delivery record, not a new live-provider audit or a fresh visual browser review.

| Boundary | Current implementation | Opportunity informing this backlog |
| --- | --- | --- |
| Routing / sidebar | `app.py`, `main.py`, `ui/streamlitui/loadui.py` orchestrate the workspaces. | `main.py` blocks pages other than Introduction/Top Movers on global runtime errors, including missing OpenAI configuration. Model/use-case changes reset chat state before page routing. |
| Introduction | Company snapshot, news, explicit AI summary, multi-horizon charts and configurable indicators. | Connect the selected company to downstream workspaces and apply trustworthy shared status components. The newly delivered chart work should be preserved. |
| Top Movers | Five-trading-day ranking, sector breadth, Serper news, quote enrichment, company handoff. | The current handoff primarily targets Introduction; a shared intent-based route would connect discovery to research. |
| Research | `graph/graph_builder.py` loops between a tool-enabled chatbot and ToolNode with MemorySaver. `tools/finance_tool_registry.py` exposes many finance tools. | Add a visible plan and application-level execution limits. Existing graph termination/default recursion protections are not a user-visible tool or spend budget. Some tools can themselves call models. |
| Equity Report | Sector-aware scorecards, peer analysis, technicals, optional committee, PDF/Excel/CSV exports. | Reuse the sector definitions and evidence presentation. Avoid expanding the already large page module or rewriting its scorecard in five days. |
| Stock Screener | FMP universe filtering and metric enrichment in a page-oriented implementation. | Allow deterministic use without an LLM key and add company handoffs; a complete provider/domain extraction is outside this sprint. |
| Portfolio Lab | Historical optimizer plus hybrid specialist-agent manager, debate, constraints, rebalance and reporting modules. | Preserve existing analysis and weighting logic. Improve readiness and navigation instead of adding another committee. |
| Deep Research | Planning, evidence gathering, generation, review/recovery, citations and optional committee. | Surface its audited inputs in a concise investment brief; do not replace its orchestration. |
| Deep Research V2 | Separate stage-routed pilot, compact contexts, validation, saved-result timestamps, explicit quick/full decisions. | Let its own provider preflight govern alternate model routes; retain the V1/V2 boundary and honest validation limits. |
| Financial / provider layer | Shared FMP transport; focused quarterly, sector, research-metric and historical-price modules. Adapters are not universally normalized. | New analysis must consume audited contracts and refuse incompatible periods/currencies rather than silently filling gaps. |
| Shared UI | `ui/app_shell.py` supplies terminal styling, responsive rules, cards and status. | The page header always renders SYSTEM READY; terminal AS OF uses the UI clock. Configuration, successful retrieval, evidence age and page-render time need distinct labels. Static inspection suggests uneven hierarchy across pages; browser checks must establish actual visual defects. |
| Verification / packaging | Offline test inventory, Python 3.11/3.12 support, Docker health check and non-root runtime. | No `.github` workflow was present. `requirements.txt` and `pyproject.toml` differ in dependency coverage. Docker excludes tests, so runtime-image verification needs a separate harness or verification stage. |

Key source anchors: `src/langgraphagenticai/main.py`, `utils/app_health.py` within that package, `ui/app_shell.py`, `deep_research/context.py`, `deep_research/research_metrics.py`, `deep_research/model_packets.py`, `portfolio_manager/agent_runner.py`, `portfolio_manager/schemas.py`, `Dockerfile`, `pyproject.toml`, `requirements.txt`, and `tests/`.

### Preserve the latest deliveries

- Both Deep Research modules already have sector-aware audited metrics, rolling four-quarter income/cash-flow calculations and independently latest balance-sheet snapshots. Preserve fiscal continuity, average-balance return calculations, actual source records, units, currencies and legacy-session notices.
- Serper news integration and coverage reporting already exist in both research modules. Requested lookback is not proof of each article's age.
- V2 generation time and result age already exist and remain separate from evidence dates.
- Introduction already supports 1D, 5D, 1M, 3M, 1Y, 3Y, 5Y and 10Y, configurable indicators and explicit technical-agent analysis. Preserve warmup, source/timezone labeling, single-provider series and rerun reuse.
- Optional equity and portfolio committees already exist. More agent names are not the missing capability.

PLAN.md records 322 passing offline tests for the latest delivery. That is historical evidence, not a fresh run for this planning document, and does not establish complete workspace, export or live-data coverage.

## Day 1 - P01: connected context and honest readiness

**Outcome:** Discover AAPL in Introduction or Top Movers, open its report or research without retyping, and return without losing saved work.

**Minimum implementation:**

1. Add a small typed navigation context: normalized symbols, destination, intent, originating workspace, and optional saved-evidence references with source/as-of metadata. Keep credentials and raw financial payloads out of it.
2. Centralize handoff helpers and add adapters for existing session keys. Implement Introduction/Top Movers -> Research, Equity Report and both Deep Research modules; Screener -> Introduction. Research navigation must prefill a request, not submit a paid action automatically.
3. Replace the global OpenAI gate with workspace/action-specific capability checks. Screener and optimizer should remain available without an LLM key. V2 should use its existing stage-specific provider preflight. Missing keys disable the relevant action and explain the dependency.
4. Scope chat configuration handling to Research. Explain a required reset visibly and provide an explicit New thread action; do not silently clear saved chat when configuring another workspace.

**Likely files:** `main.py`, `ui/streamlitui/loadui.py`, `utils/app_health.py`, selected page adapters; proposed focused `state/research_context.py` and `ui/workspace_handoff.py`.

**Acceptance / offline verification:**

- Invalid symbols are rejected before any provider call; valid symbols are uppercased.
- AppTest exercises the handoff journey and return navigation with synthetic providers; saved reports and chat remain available.
- Missing OpenAI configuration does not block the Screener/optimizer, and V2 alternate-provider readiness is covered without real model calls.
- Handoff, navigation and ordinary reruns make zero model calls; a call counter proves this.
- Two independent sessions do not share context or chat history.
- The financial packet bridges disabled by the recent audit remain disabled. Navigation metadata is not authorization to reuse unaudited scorecard values.

**Cut line:** Do not migrate all saved-session formats or implement a universal financial provenance model in one day. Deliver one context contract and bounded adapters.

## Day 2 - P02: a cleaner, consistent terminal interface

**Outcome:** Users immediately understand the selected company, the important findings, data quality, and the next action.

**Minimum implementation:**

1. Extend the existing `app_shell.py` design system with a compact company header, executive-summary cards, an evidence/status row and a reusable progress panel. Retain the terminal palette and typography.
2. Use shared honest status labels across all workspace headers: Configured, Retrieval successful, Partial, Missing or Stale only when supported by actual metadata. Replace unconditional SYSTEM READY and distinguish Page rendered at from provider/evidence As of.
3. Apply the complete executive layout to Introduction, Research and Deep Research V2: selected company, at most three summary cards, primary action, concise findings, then detail expanders. Give V1 the shared evidence/status row. Keep existing report and portfolio tables intact.
4. Standardize empty/error/retry states, readable metric formatting and descriptive source links. Do not hide incomplete inputs behind a reassuring summary.

**Likely files:** `ui/app_shell.py`, Introduction/Research rendering helpers, both Deep Research tab renderers and `deep_research/presentation.py`; extract shared components rather than enlarging page modules.

**Acceptance / offline verification:**

- Browser screenshots at 1440x900, 1280x800 and 390x844 establish readable primary actions and intentional table scrolling.
- No clipped headers, overlapping controls or inaccessible expander content in the changed views.
- Loading, empty, partial, stale and failure fixtures show explicit text, not color alone.
- Evidence dates remain accurate when reopening a saved result; the UI clock never makes old evidence appear newly retrieved.
- Keyboard focus and source links are usable; provider-controlled HTML remains escaped.
- Navigation, chart settings and expanders trigger zero paid calls.

**Cut line:** Polish the three specified primary views and shared headers. Defer a full redesign of every table, animation, custom frontend framework and decorative market widgets.

## Day 3 - P03: visible, bounded agentic research

**Outcome:** Ask a focused company question, inspect the proposed research plan, run it explicitly, and see an answer linked to the collected evidence.

**Minimum implementation:**

1. Add an opt-in Guided research mode alongside existing chat. A structured planner chooses up to three approved read-only tools for one company and states what each step will establish.
2. Show the plan and limits before Run plan. Execute through a focused LangGraph workflow with a bounded executor, deterministic evidence checks and structured synthesis. Capture completed steps and partial failures.
3. Start with a narrow allowlist of existing quote/profile, financial snapshot and news tools that have inspectable output contracts. Exclude tools that call additional LLMs unless those calls are accounted for in the same budget.
4. Display step status, sanitized evidence references, missing inputs and usage. Return useful partial output on failure. Provide an explicit link into existing Deep Research for questions outside this slice; do not launch that paid workflow automatically.
5. Save the plan/result under an input fingerprint. Reopening, rerunning Streamlit or downloading reuses the result. Changed ticker, model or evidence marks it mismatched until a new explicit run.

**Proposed initial limits:** At most two model calls total (planner and synthesis), three tool dispatches, 12 graph steps, bounded serialized evidence, and an estimated spend ceiling shown before execution. Reserve cost using input/output token limits and configured pricing before each call; unknown pricing must not imply a guaranteed dollar cap. These are engineering targets, not measured current performance. Reject any oversized planner output or unapproved tool before dispatch.

**Likely files:** `graph/graph_builder.py`, focused new guided-research state/nodes under `graph/` or `research/`, `tools/finance_tool_registry.py`, Research rendering and existing bounded model-client helpers.

**Acceptance / offline verification:**

- Synthetic planner cannot invoke an unknown tool, mutate state outside its contract or exceed the tool/model/step budget.
- A failing news tool preserves successful quote/financial evidence and produces a partial-data answer.
- Repeated reruns after Run plan make no new provider/model calls; a new explicit run is separately counted.
- Material structured facts cite existing evidence IDs. Invalid references and incompatible periods are rejected or clearly withheld.
- Two sessions and two tickers do not reuse each other's results.
- Debug/progress output contains no secrets, raw credentials or private prompts.

**Cut line:** One company, three approved tools, two model calls. Defer autonomous web browsing, long-running jobs, durable cross-restart checkpoints and additional committees. Session-backed approval is sufficient for this slice; do not claim it survives server restart.

Framework grounding: LangGraph supports typed state and explicit graph nodes/edges; its recursion limit is a step bound, so separate tool and spend counters are still needed. See the [official Graph API documentation](https://docs.langchain.com/oss/python/langgraph/graph-api). If interrupts are used, follow the [official interrupt/checkpointer requirements](https://docs.langchain.com/oss/python/langgraph/interrupts) and test replay without duplicated provider calls.

## Day 4 - P04: evidence-backed investment brief and scenarios

**Outcome:** Read a concise thesis, understand its risks and invalidation conditions, and explore how valuation assumptions change the conclusion.

**Minimum implementation:**

1. Build a shared saved-result investment brief for both Deep Research modules: business drivers, supporting evidence, contrary evidence, catalysts with dates, risks, missing inputs and thesis invalidation conditions. Reorganize existing saved narrative and audited data; opening the brief must not recollect evidence or generate another narrative.
2. Add a clearly separate deterministic scenario panel for eligible companies with positive audited TTM net income and compatible market capitalization. Use user-supplied earnings-change assumptions and P/E multiples:

   `hypothetical equity value = audited TTM net income * (1 + assumed earnings change) * assumed P/E`

   `difference versus current market cap = hypothetical equity value / dated market cap - 1`

3. Present bull/base/bear rows, sensitivity chart, formulas, assumptions, source periods, currencies and valuation-date limitations. These are hypothetical sensitivities, not forecasts, price targets or guaranteed returns. No per-share target unless a separately validated share-count/EPS contract is available.
4. Gate the earnings-multiple model using the existing sector applicability rules. Mark inapplicable sectors, losses, missing market cap, currency mismatch or legacy unaudited sessions unavailable. Do not substitute net income for FFO/AFFO or silently use stale/unknown quote dates.
5. Allow export of the brief/scenario inputs and outputs with provenance; reuse existing safe download machinery and credential filtering.

**Likely files:** `deep_research/research_metrics.py`, `sector.py`, `presentation.py`, both saved-result renderers; proposed focused `analysis/scenarios.py` and `analysis/investment_brief.py`. Consume audited saved inputs without changing their calculations.

**Acceptance / offline verification:**

- Independently calculated fixtures prove the scenario arithmetic, percent formatting and monotonic response to earnings/multiple changes.
- Tests cover zero/losses, missing values, nonfinite inputs, invalid assumption ranges, currency mismatch, inapplicable sectors and legacy results.
- The brief distinguishes saved AI interpretation, provider facts, calculated values and user assumptions.
- Source IDs and financial bases are retained in UI and exports; malformed links/embedded credentials are rejected.
- Controls and downloads generate zero model calls and preserve the underlying saved report.
- V1 and V2 display the same scenario result for identical audited inputs.

**Cut line:** Deliver one supported earnings-multiple sensitivity model. A bank-specific book-value/P/B model is stretch work only after the minimum passes; DCF, universal sector valuation and portfolio aggregation are deferred.

## Day 5 - P05: release automation and deployment rehearsal

**Outcome:** A repeatable release gate catches workflow regressions before the app is exposed to users.

**Minimum implementation:**

1. Add `.github/workflows/ci.yml` for the supported Python 3.11/3.12 environments: clean dependency install, full offline pytest inventory, compile/import checks and retained verification artifacts. Resolve manifest differences for the chosen runtime install path without an unrelated mass dependency upgrade.
2. Add a synthetic cross-workspace smoke covering discovery -> Research plan -> saved Deep Research brief, with call counters and partial-provider failures. Cover all eight workspace routes at the readiness/rendering level; do not describe this as exhaustive behavioral coverage.
3. Build the existing Docker runtime, verify its non-root startup and `/_stcore/health`, and exercise one representative workflow with a separate test harness/verification stage. Tests are excluded from the runtime image today; host pytest alone does not verify that image.
4. Prepare a deployment runbook: chosen target, secret injection, access controls, bounded paid actions, per-session isolation, smoke commands, commit/image identity and rollback. Use platform access controls for a private preview if full public-user safeguards are not ready.
5. Rehearse the release on the selected target only after its access and configuration are authorized. Verify health, changed interactions, evidence labels and usage controls; record the actual hosted URL and evidence. If no target is selected, finish local verification and ask the user which target to use.

**Likely files:** proposed `.github/workflows/ci.yml`, focused interaction tests/fixtures, dependency manifests as required, Docker verification harness, `docs/DEPLOYMENT.md`, README.md and PLAN.md.

**Acceptance / verification:**

- Fresh CI runs pass without live-provider keys or paid credits.
- Missing optional providers produce usable partial states, and secrets never appear in artifacts/logs.
- The built image starts with its documented runtime configuration and responds successfully to health checks.
- Browser evidence is newly captured for the changed journey; two sessions remain isolated.
- A known-good image/commit rollback is documented and rehearsed where the target permits it.
- A public launch is withheld if access/spend controls for server-side paid credentials are unresolved; a protected preview is the bounded alternative.

**Cut line:** One deployment target and one repeatable release workflow. Defer multi-cloud support, Kubernetes, bespoke authentication and a major packaging rewrite.

Official implementation references: [Streamlit AppTest](https://docs.streamlit.io/develop/api-reference/app-testing) supports simulated interaction tests; use browser checks separately for rendered layout. [GitHub's Python CI guide](https://docs.github.com/en/actions/tutorials/build-and-test-code/python?learn=continuous_integration) covers interpreter matrices and pytest automation. Verify compatibility with the project's installed versions rather than copying examples blindly.

## Instructions for the feature development team

Execute P01-P05 in order. Start each day with the current working tree and PLAN.md; confirm earlier dependencies are delivered. The paths above identify boundaries, and proposed new modules are suggestions rather than existing files.

For each implementation, use the project's feature-development-team skill with its planner, builder and independent verifier roles. Include the financial specialist for scenario eligibility/formulas and any change to audited metric contracts. Use the provider-debug, research-grounding, Streamlit-workflows, financial-correctness and release-check skills where applicable under that team's workflow.

When starting a day, use this invocation, replacing `<ID>` with P01, P02, P03, P04 or P05:

```text
Use $feature-development-team to implement <ID> from
docs/features/2026-10-04-five-day-predeployment-plan.md.
Keep the minimum scope and acceptance criteria; defer stretch work.
Explicitly create one AAFA implementation ticket before coding and update it
with progress, verification results and remaining limitations. Check duplicates
before creating follow-up tickets for substantive unresolved issues.
Preserve unrelated changes and the recent chart/research financial deliveries.
Add offline tests, verify changed interactions, and update README/PLAN as needed.
For P01-P04, deliver and verify the local implementation; record deployment as
pending rather than claiming a hosted release. For P05, use the authorized
deployment target or ask which target to use after local checks are complete.
Mark a deployment-required implementation ticket complete only after that
deployment is verified. Report the actual result rather than assuming success.
```

Any commit/push should follow an explicitly requested GitHub-sync invocation. This document alone does not start implementation, create tickets or authorize a hosted release.

### Verification required for each delivery

- Inspect changes and preserve unrelated work; focused offline tests use synthetic/recorded provider responses and model stubs.
- Shared routing, state or infrastructure changes require the full pytest suite. Compile/import affected modules using the installed Python 3.11/3.12 environment and `PYTHONPATH=src`.
- App-level changes require a fresh Streamlit health check and browser verification of the changed interaction. UI layout checks and live-provider checks are separate evidence.
- Update PLAN.md with commands, interpreter/dependency versions, result, mocked versus live scope and checks not performed. Update README's verification summary when the inventory changes.
- Preserve existing source/date/currency/fiscal labels and saved-session recovery. Never let an ordinary rerun, navigation, setting change or download trigger a paid model call.

## Friday deployment decision

Proceed to the chosen deployment only when P01-P05 minimum acceptance checks pass, the scoped changes are reviewed, credentials/access are configured safely, and rollback is concrete. Record unresolved gaps explicitly. The existing Docker configuration provides a starting point, but it does not select or verify the eventual hosting target.

If time runs short, cut stretch scope first. Retain connected context, honest UI status, bounded agent execution, audited scenario eligibility and release checks. Defer broader autonomous workflows and universal financial coverage to the existing roadmap rather than weakening these gates.


### October 8 P04 local delivery record

P04 minimum scope is implemented in the local working tree under [AAFA-11](https://bigmeatpete717.atlassian.net/browse/AAFA-11). Shared saved-result briefs, audited earnings-multiple sensitivities and safe provenance JSON/CSV are documented in the [P04 team report](2026-10-08-p04-investment-brief-team.md); actual dated acceptance and limits are in [PLAN](../../PLAN.md#v-20261008-p04---local-verification). Stretch valuation models and deployment remain outside this delivery. Historical proposed scope above is retained.
