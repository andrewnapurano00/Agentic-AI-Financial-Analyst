# Axiom Research — Feature Development Team Implementation Roadmap

**Prepared:** 2026-10-22\
**Repository:** `Agentic-AI-Financial-Analyst/`\
**Audience:** Codex feature-development team, financial-data specialist, implementation engineer, independent verifier, and Jira writer\
**Document status:** Engineering implementation specification / proposed work, **not** authorization that implementation has occurred.

## 0. Primary development-team instruction (copy into Codex)

> **Use the repository's `.agents/skills/feature-development-team/SKILL.md` and `AGENTS.md` to evaluate and deliver the scoped Axiom Research roadmap below. Start in PLAN-ONLY mode. Inspect `PLAN.md`, existing implementation, tests and Git status; do not assume a feature is missing simply because this roadmap proposes it. Produce a dependency-aware implementation plan and Jira-ready work breakdown, with no code edits, live API/model calls, ticket creation, commits, pushes, or deployment until separately authorized. When I subsequently approve an individual work package for BUILD mode, perform the full specialist → planner → builder → independent verifier handoff and meet the acceptance criteria below. Preserve every currently reachable feature, existing saved reports and the dark professional terminal/Bloomberg-inspired design. Do not perform a wholesale redesign.**

### Important execution and authorization rules

1. **Plan-only is the default for this document.** Ten proposals are **not** approval to implement ten unrelated changes simultaneously. Implement only the work package the product owner explicitly authorizes in a subsequent request.
2. Do not create Jira issues unless separately requested. If Jira is authorized, follow the feature-development-team skill's deduplication, snapshot, durable attempt ledger, and **maximum five creation attempts per run**. Draft additional work locally instead of bypassing the cap.
3. Read `AGENTS.md`, `PLAN.md`, `.agents/skills/feature-development-team/SKILL.md`, `docs/DEPLOYMENT.md` and relevant existing `docs/features/` reports first. Treat dated implementation claims as historical until verified against the current tree.
4. Record Git status and scoped file hashes before any changes; do not overwrite unrelated edits. No staging/commit/push, external publishing, deployment, or paid live-provider/model calls without separate authorization.
5. Keep existing **nine primary workspaces** and the dark professional design. Do not restore removed tabs, resurrect legacy traders, rename routes casually, or move Robo Advisor away from prompt-led portfolio construction.
6. Preserve Deep Research **Standard V1** and **Low Cost V2** compatibility. A unified UX may wrap both engines, but do not merge/rewrite the engines until their outputs and recovery paths are covered by regression tests.
7. **Axiom is investment research software, not a licensed personalized investment adviser.** Describe model portfolios, research scenarios and risk preferences accurately; do not imply fiduciary advice, suitability certification, guaranteed outperformance, or autonomous execution.
8. All financial computations and constraint checks are deterministic. LLMs may explain, critique and request evidence, but must not silently invent values, change risk limits or overwrite verified financial facts.
9. Default automated verification uses offline fixtures; do not consume paid credits. Streamlit reruns, viewing/downloads and navigation must not launch LLM or provider calls unexpectedly.
10. For each approved slice, provide a feature report with baseline, exact changed paths, tests and outcomes, screenshots where available, unmet criteria, regression concerns, risks, and Jira drafts/outcomes as applicable.

## 1. Strategic outcomes and non-goals

**Goals:** More coherent user workflows; genuinely useful agent delegation; reproducible data quality; transparent evidence and risk; shared research with safe provenance; reliable hosted operation. Prioritize trust and correctness before autonomy and visual polish.

**Non-goals:** Rebuilding the UI; removing information or reports; replacing every existing agent framework; creating a brokerage or auto-trading product; promising investment outcomes; switching to a new data vendor as a shortcut; blanket migrations without compatibility tests.

### Definition of Done (applies to *each* approved package)

- Named user journey works on intended existing route with no regressions to other workspaces.
- New functions have unit and integration tests for success, missing/null/zero, partial, stale, invalid, timeout and failure conditions where relevant.
- Facts carry ticker/security ID, source/route, fiscal or quote date, retrieval time, currency/unit, period basis, adjustment methodology if known, and availability/verification state; **unknown remains unknown**.
- Outputs distinguish provider observations, deterministic calculations, analyst/AI inference and user-defined assumptions.
- No implicit paid model calls on Streamlit rerun, filter changes, export, navigation, or displaying saved data.
- Existing V1/V2 research, saved results and file exports remain accessible. Old session-state values handled without crash.
- Bounded calls, retry/cost limits, timeouts, idempotence where applicable, stable run identifiers and actionable error messages.
- Offline tests and relevant `python -m compileall`/imports pass; shared routing changes require full guarded `pytest`; Streamlit UI changes require a health/smoke check and browser walkthrough when available.
- README/`PLAN.md` and the scoped feature-team report updated for meaningful changes; unverified live behavior called out explicitly.

---

## 2. Work packages — prioritized backlog

### AX-01 — Guided Robo Advisor experience
**Priority:** P0 UX | **Effort:** Medium | **Depends on:** AX-05 for enforceable risk claims

**User problem:** Prompt-led portfolio building still exposes advanced portfolio-engineering jargon and too many configuration decisions; users may misread descriptive risk labels as enforced limits.

**Inspect first:**
- `src/langgraphagenticai/ui/robo_advisor_tab.py`
- `src/langgraphagenticai/ui/portfolio_architect_tab.py`
- `src/langgraphagenticai/portfolio_architect/{mandate,workflow,optimizer,construction,risk}.py`
- Current tests for portfolio-architect UI, mandate parsing, optimizer and cached reruns.

**Engineering instructions:**
1. Trace the actual Robo Advisor route and inventory existing inputs, results, saved-state keys and downloads. The Robo Advisor currently delegates to Portfolio Architect; reuse this engine rather than building a duplicate.
2. Introduce **three progressive stages** within the existing page: (1) plain-English investment objective, (2) editable mandate preview, (3) portfolio review. Keep prompt-led construction directly accessible on entry; no mandatory long onboarding wizard.
3. Extract proposed horizon, investable amount, investment style and preferences only when supported by the current parser; show unparsed/ambiguous fields as **Needs confirmation** instead of silently inferring.
4. Put detailed covariance budgets, sector limits, eligible instruments and sizing methods under **Advanced settings**. Preserve all existing configurable parameters and defaults for existing sessions.
5. On the review view, present holdings, weights, portfolio roles, dominant exposures, key reasons **for/against** each holding, missing data, risk limitations, and downloadable existing outputs. Make visible which fields were user-specified versus inferred.
6. Never label a portfolio Conservative/Moderate/Aggressive as a numerically enforced risk mandate until AX-05 implements corresponding guardrails. Until then describe the risk setting as indicative.
7. Add a deterministic audit summary of applied caps/constraints, infeasibility and fallback behavior. Preserve the original underlying optimizer and session safety.

**Acceptance criteria:**
- A simple natural-language prompt can produce a clear confirmed mandate and portfolio review without navigating advanced settings.
- Advanced users can still reach and edit all supported controls; existing exports and calculations remain available.
- Edited input invalidates only dependent portfolio results, not unrelated research or navigation state.
- No provider/model rerun occurs when only toggling display sections, navigating or downloading.
- Unsupported or conflicting risk preferences trigger an explicit clarification/limitation, never a false suitability claim.

**Tests:** UI flow and rerun tests; mandate inference/override tests; infeasible cap scenario; empty prompt; provider failure; existing portfolio regression suite.

### AX-02 — Unified Deep Research UX (retain V1 and V2 engines)
**Priority:** P0 UX | **Effort:** Medium–high | **Depends on:** AX-06 for verification display

**User problem:** User-facing Standard vs Low Cost engines and provider/model controls emphasize implementation details over research outcomes.

**Inspect first:**
- `ui/deep_research_workspace.py`, `ui/deep_research_tab.py`, `ui/deep_research_v2_tab.py`
- `deep_research/{manager,v2_workflow,delivery,presentation,report_basis}.py`
- Saved report/session/export/committee tests and V1/V2 failure recovery cases.

**Engineering instructions:**
1. Retain current engines and evidence/report data models while designing a shared research front-end with **Quick Brief**, **Deep Dive**, and **Investment Committee** intent presets. This is a UX wrapper, not permission to rewrite V1 or promote V2 from pilot without evidence.
2. Document an explicit routing table: preset → supported engine/stages/models/evidence requirements/cost caps. If capability is unavailable, show a supported alternative; never quietly downgrade quality.
3. Hide raw provider/model names and budgets under Advanced settings; preserve existing expert controls and explicit provider availability, pricing uncertainty and bounded-call semantics.
4. Use a common top-level result structure: conclusion, key evidence, valuation implications, competing perspectives, material risks, research gaps, and source/freshness information. All original long-form reports and evidence packets remain accessible unchanged.
5. Show research stage and run status without exposing speculative 'agent thought' internals. Include resumable failed/partial states, preserved saved results and user-invoked continuation.
6. Maintain original committee and PDF semantics: optional committee action and its saved result belong in a regenerated download, without re-fetching data.
7. Define an adapter-based migration strategy and rollback flag; ship behind a feature flag first if shared result schemas are not yet equivalent.

**Acceptance criteria:**
- A user chooses research depth without needing to know V1/V2 terminology; advanced controls remain available.
- V1 and V2 evidence/results persist and their respective source lineage is visible.
- Existing research/follow-ups, investment briefs, committee results and exports do not disappear.
- Display-only reruns, saving and exporting never recollect data or consume AI credits.

**Tests:** Both engines under each supported preset; legacy saved sessions; partial evidence; model timeout; committee add-on; export after committee; rapid Streamlit reruns.

### AX-03 — Genuine specialized agent orchestration
**Priority:** P1 | **Effort:** High | **Depends on:** AX-04, AX-06

**User problem:** Multiple specialized agent labels do not automatically ensure independent work, evidence exchange or adversarial review.

**Inspect first:** `portfolio_manager/agents/`, `portfolio_architect/committee.py`, `deep_research/crew_committee.py`, `graph/graph_builder.py` (where applicable), existing workflow state and cost guards.

**Engineering instructions:**
1. Inventory existing agents and identify which independently call tools, which only contribute sections of one model prompt, and which have deterministic domain checks. Do not claim existing components are independent when they are not.
2. Create typed **Task**, **EvidenceRef**, **AgentResult**, **ReviewFinding** and **FinalDecision** contracts. Specify input eligibility, evidence IDs, as-of/currency/period, tool allowlists, budgets and timeouts.
3. Establish a lead orchestration flow: scope question → deterministic evidence gathering → parallel/sequential *bounded* specialist analyses as useful → verification → synthesis → optional adversarial committee.
4. Implement a conditional **research gap** route (only for specific missing evidence); no unrestricted agent loops. Require strict per-run recursion, tool, duration and token budgets.
5. Require the valuation/risk specialist to flag unsupported extrapolations or numerical inconsistencies; do not let AI output mutate the underlying numerical portfolio constraints.
6. Surface a compact public agent work summary (finished/partial/failed; evidence counts and named disagreements) and full source audit metadata without showing private reasoning traces.
7. Roll out on one bounded company-research workflow first; compare quality, latency and cost versus the current approach before expanding.

**Acceptance criteria:** Clear traceable delegation, distinct specialist evidence and independent checks; model/provider failures yield a partial labeled result, not fabricated consensus; no new implicit spending; all tool calls bounded.

**Tests:** Synthetic conflicting valuation, missing source, agent timeout, retry ceiling, malicious retrieved-text injection, stale evidence, deterministic committee reconciliation.

### AX-04 — Centralized financial metric contracts and data validation
**Priority:** P0 correctness | **Effort:** High | **Prerequisite for:** AX-03, AX-05, AX-06, AX-07

**Inspect first:** `providers/`, `deep_research/{quarterly_ttm,research_metrics}.py`, `valuation/{metrics,framework,model}.py`, `portfolio_manager/fmp_fundamentals.py`, `docs/OPENING_METRIC_DICTIONARY.md`, `fmp_data_reference/` where available.

**Engineering instructions:**
1. Inventory the *currently used* financial metrics by screen and map formula, ticker/security ID, endpoint and response field, fiscal period, TTM/annual/quarterly type, as-of availability, source/retrieval date, currency, scaling and missing/zero semantics.
2. Build a typed **MetricObservation** and **MetricDefinition** interface (or adapt existing contracts instead of introducing duplicative types); add lightweight adapters around **one high-value metric family first**.
3. Normalize quote currency vs reporting currency; fiscal quarter vs calendar date; annual vs TTM; split-adjusted/unadjusted price; end-of-period vs filing availability. Never silently mix incompatible bases.
4. Validation: arithmetic reconciliations within documented tolerances, four consecutive fiscal-quarter TTM eligibility, corporate-event handling where evidenced, duplicate/late/revised filings, finite values, reasonable units, explicit unsupported-sector applicability.
5. Distinguish **missing**, **valid zero**, **stale**, **derived**, **inconsistent** and **unverifiable**. Fail closed on core price-target prerequisites while allowing other independently valid sections to display.
6. Create a consumer-independent service/registry so the same fact appears consistently in research, valuation, portfolio and exports, without global cache contamination.
7. Compare outputs to known saved FMP reference samples and synthetic edge cases; do not treat sample schemas as proof of universal endpoint entitlement.

**Acceptance criteria:** Matching metric identity/period/source produces the same interpretation across consuming workspaces; invalid TTM windows cannot be represented as audited; missing values never become zero; user sees stale/partial/unverified status.

**Tests:** Sector-specific samples including financials/REITs; fiscal 53-week/irregular periods; revised filings; zero vs null; currencies; mismatched dates; absent quote; negative earnings and denominator edge cases.

### AX-05 — Enforceable portfolio risk and transparent suitability limitations
**Priority:** P0 correctness | **Effort:** High | **Depends on:** AX-04

**Inspect first:** `portfolio_architect/{optimizer,risk,construction,workflow,mandate_fit}.py`, `portfolio_manager/{rebalance_engine,portfolio_actions}.py`, current benchmark/position-cap tests.

**Engineering instructions:**
1. Inventory currently **enforced** limits separately from descriptive portfolio statistics and AI explanations. Publish a machine-readable risk-policy summary.
2. Add optional configurable risk guardrails (e.g., ex-ante volatility constraint, concentration and sector exposure, benchmark-relative risk where evidence is available); never claim historical estimates can guarantee future outcomes.
3. Build scenario stress views with explicit shocks and assumptions; keep forecast metrics clearly labeled as model estimates, not observed values.
4. Introduce ETF holdings look-through **only with eligible dated constituent data**. When unavailable, label hidden exposure/overlap unknown rather than fabricating complete diversification.
5. Add benchmark-relative weights, effective exposure/overlap warnings and estimated transaction costs/turnover when underlying price and holdings information supports them.
6. Make infeasible mandates actionable: explain violated constraints and present user-approved relaxation options, never silently violate caps.
7. Create a separate risk explanation panel for every portfolio and label as **educational/model portfolio analysis**, not personalized advice.

**Acceptance criteria:** Every displayed 'enforced' constraint is tested against optimizer output; lack of ETF look-through is disclosed; high-concentration portfolios are flagged; missing exposures do not become reassuring zeros; allocations sum within established tolerance.

**Tests:** Infeasible optimization, correlated assets, sparse history, ETF overlap, stress sign and units, cash/weights, missing benchmark, extreme constraints.

### AX-06 — Independent verification of research claims
**Priority:** P0 trust | **Effort:** Medium–high | **Depends on:** AX-04

**Inspect first:** `deep_research/{manager,report_basis,research_metrics,v2_workflow}.py`, citations/audit contracts, saved investment briefs and source displays.

**Engineering instructions:**
1. Extract material numeric claims into a structured record containing claim type, ticker, cited evidence ID(s), metric definition, figure, period, unit and source references.
2. Verify cited amounts and independently recompute arithmetic/period comparisons using deterministic functions. Do not use an LLM 'fact-check' alone as proof.
3. Tag statements separately as **verified numerical fact**, **derived calculation**, **assumption/opinion**, **contradicted** or **unverifiable**. Add severity and informative remediation hints.
4. Validate citation ID existence, source identity, retrieval/date basis and source applicability; a valid citation URL is not sufficient evidence that the quoted number is correct.
5. Show evidence coverage and unresolved contradictions on the executive summary. Avoid one opaque confidence score: use distinct indicators for coverage, freshness, reconciliation and interpretive uncertainty.
6. Preserve original research text, citations and diagnostics for audit; prevent unsupported price-target language from being promoted into verified conclusions.

**Acceptance criteria:** Synthetic wrong-period revenue claim fails; correct arithmetic passes; absent citation remains unverified; subjective views are never marked numeric-verified; saved reports are not overwritten by remediation.

**Tests:** Off-by-1000 scaling, period mismatch, evidence ID spoofing, 0 vs missing, currency mismatch, stale price, false multiple arithmetic, untrusted retrieved source instructions.

### AX-07 — Verified shared research memory and cross-workspace handoffs
**Priority:** P1 | **Effort:** Medium–high | **Depends on:** AX-04, AX-06

**Inspect first:** `state/research_context.py`, `ui/workspace_handoff.py`, `portfolio_manager/research_snapshot.py`, `deep_research/context.py`, current saved research/session behavior.

**Engineering instructions:**
1. Preserve existing metadata-only ticker/intent navigation. Do not broaden it into financial data reuse by default.
2. Design a separate **VerifiedResearchSnapshot** contract: versioned run ID, user/session scope, normalized security ID, typed financial observations/evidence, timestamps, source/entitlement and purpose, validation results and fingerprint.
3. Allow a recipient workflow to import data **only when** necessary metric basis/currency/time/freshness checks pass. Otherwise transfer the ticker only and explain why the financial packet is not reusable.
4. Add visible, explicit **Use saved verified research** actions for qualified transfers; never silently substitute saved data for current market facts.
5. Ensure no cross-user/session leakage, credential-scope confusion, model-context contamination, or unintended new requests on navigation.
6. Pilot on one high-value handoff (e.g., saved company research → valuation) and extend to advisor only after lineage and stale-state tests pass.

**Acceptance criteria:** Same verified data can be reused without refetch under stated conditions; incompatible packets are rejected while ticker navigation still works; stale inputs generate warnings or force explicit refresh; sessions are isolated.

**Tests:** Cross-ticker, cross-user, cached credentials changed, stale filing, mismatched fiscal basis, legacy saved snapshot, missing metadata, revalidation after refresh.

### AX-08 — Event-driven monitoring and advisory-only rebalancing
**Priority:** P2 | **Effort:** High | **Depends on:** AX-04, AX-05, AX-07, AX-10

**Inspect first:** `portfolio_manager/{rebalance_engine,portfolio_actions}.py`, `paper_trading/`, advisor portfolio saves and existing alert/scheduler architecture.

**Engineering instructions:**
1. Implement **opt-in** monitoring for specifically saved model portfolios/theses, never for arbitrary unsaved browsing.
2. Store immutable snapshots of holdings, constraints, benchmark, sources, investment thesis and evidence freshness. Define monitored events (earnings, material estimate revision, concentration drift) only where sources and entitlements permit.
3. Build idempotent detection/reassessment jobs; avoid duplicate alerts, repeated paid agent runs, and schedules tied to an unreliable browser session.
4. Show **what changed**, old/new evidence, potential impact and *proposed* action with assumptions, confidence/verification and transaction-cost caveats.
5. Require explicit user approval before changing a simulated portfolio, and never submit live broker orders.
6. Use durable storage, retry queues, bounded spending and disable controls; keep monitoring off until production authentication and job isolation exist.

**Acceptance criteria:** One event creates one traceable advisory recommendation; stale/failed data produces no invented signal; disabling monitoring stops subsequent analysis; no brokerage execution; restart/retry does not duplicate changes.

**Tests:** Duplicate event IDs, delayed reporting, job restart, model timeout, partial financial refresh, approval/rejection, expired credential, user isolation.

### AX-09 — Unified investment memo and decision-focused reporting
**Priority:** P1 UX | **Effort:** Medium | **Depends on:** AX-02, AX-06

**Inspect first:** `deep_research/{delivery,presentation,committee_export}.py`, `portfolio_architect/export.py`, `analysis/investment_brief.py`, PDF and source-appendix regression tests.

**Engineering instructions:**
1. Create a **shared presentation schema**, not a shared data computation engine: executive thesis; evidence highlights; valuation implications; upside/downside drivers; key risks; evidence quality; assumptions and complete references.
2. Keep complete retained original reports, appendices, source packets, detailed tables, committee decisions and existing file formats; provide a simplified executive first-page/first-screen view.
3. Make portfolio memos include positions, roles, weights, concentration/exposure, quantified risks where eligible, assumptions and limitations.
4. Cite source ID and as-of date near key figures; ensure printer/PDF fonts render without missing glyphs or overlapping text.
5. Regenerate exports **from saved verified state only**; no hidden live calls, no sample numbers and no unverifiable target claims.

**Acceptance criteria:** Executive first page fits and is clear; full legacy depth remains accessible; screen and export agree on values/periods; source appendix and committee are retained; exports are deterministic for unchanged saved inputs.

**Tests:** Long titles, missing sections, special characters, zero/negative metrics, repeated exports, PDF extraction/visual checks, committee appended after initial report.

### AX-10 — Production security, resilience and observability
**Priority:** P0 release gate | **Effort:** High | **Depends on:** Deployment target/hosting decisions

**Inspect first:** `docs/DEPLOYMENT.md`, `.github/workflows/offline-release.yml`, `Dockerfile`, `Dockerfile.verify`, `utils/app_health.py`, provider/model wrappers, env/secrets handling and `PLAN.md`.

**Engineering instructions:**
1. Do not mark release-ready based only on historical local pytest passes. Explicitly inventory **unverified** Docker build, Python 3.11/3.12 clean installs, non-root runtime, CI, hosted smoke/preview and rollback gates.
2. Establish hosted authentication and per-user isolation for portfolio holdings, saved reports, caches, exports, data retrieval and agent run IDs, appropriate to deployment target.
3. Keep API/model credentials server-side with least privilege and managed secret rotation. Never log keys, private prompts/holdings or raw sensitive packets by default.
4. Add central structured run/event logging: request/run ID, page, bounded tool calls, source IDs, latency, error category, cost estimates versus actual billable telemetry if available, verification status and safe redacted trace metadata.
5. Implement rate limits, quotas, timeout/retry policies, circuit breakers and provider degradation without masking stale/unavailable data.
6. Implement persistence/checkpointing for hosted long-running research outside volatile Streamlit session state, with authorization checks on resume and export.
7. Add security and release checks: dependency audit, prompt/tool injection boundaries, unsafe path/export handling, TLS verification, non-root container, resource limits, concurrency, warm/cold startup, backup/restore and tested rollback.
8. Conduct a **protected**, separately authorized live-provider smoke test only after offline gates pass; report timestamp, supported endpoints and gaps without making universal entitlement claims.

**Acceptance criteria:** No session/data leakage in concurrent-user tests; app survives provider outages with labeled retained/partial states; restart/resume behavior documented; reproducible clean build and health check; rollback demonstrated; remaining release gates explicitly tracked.

**Tests:** Concurrent sessions; auth escalation; cache key collision; provider 429/5xx; runaway agent loop; server restart mid-report; invalid secret; log redaction; hostile filename; gated deployment smoke.

---

## 3. Dependencies, delivery waves and scope controls

| Wave | Packages | Goal | Gate before next wave |
|---|---|---|---|
| A — guided UX | AX-01, AX-02 (design and bounded frontend slice) | Reduce confusion without replacing engines | Baseline UI and V1/V2/portfolio behavior preserved; no hidden model calls |
| B — financial trust | AX-04, AX-06, AX-05 | Make data, claims and risk assertions reproducible | Financial basis, validation and constraint tests pass |
| C — connected intelligence | AX-03, AX-07 | Evidence-aware multi-agent handoffs and validated context reuse | Bounded cost, independent verification and cross-session isolation |
| D — executive outputs | AX-09 | Usable investment decisions and exports | Saved result parity and PDF/report regression checks |
| E — production readiness | AX-10, then AX-08 | Secure hosting and opt-in monitoring | Security/concurrency, hosted/rollback gates and durable jobs |

**Important:** AX-10 security principles apply throughout, not just in wave E. AX-08 must not be switched on in a hosted environment before the relevant persistence/security foundations are verified. Waves are delivery groupings, **not** instructions to ship a whole wave in one change.

## 4. Required deliverables per approved feature

For each `AX-XX`, the feature development team must return:

1. **Baseline evidence:** existing UI behavior, exact source paths, current tests, saved-state and provider contracts, relevant `PLAN.md` entries, and precise gap being addressed.
2. **Financial-data handoff (D IDs):** route/field evidence, currencies/units, timestamps, coverage and assumptions; 'not applicable' is acceptable for a purely visual change.
3. **Implementation plan (P IDs):** minimal change boundaries, user journey, state/caching strategy, migration and rollback, dependencies, effort estimates and explicit non-goals.
4. **Code delta (build mode only):** exact paths, diff summary and reasons; no changes to unrelated features.
5. **Verifier report (F IDs):** independently evaluated findings, focused/full offline test commands and actual pass/fail counts, UI test evidence, missing live checks, and high-risk edge cases.
6. **Jira-ready draft:** title, problem, existing behavior, expected behavior, impacted files, dependencies, detailed acceptance criteria, test plan, rollback and explicitly labeled risks. Publish only when authorized under skill limits.
7. **User-facing summary:** what a real user will notice, what did not change, remaining limitations, and whether it is suitable for protected preview or public release.

### Suggested Jira breakdown (draft IDs — NOT existing Jira keys)

- `AX-01` Guided Robo Advisor and mandate explanation
- `AX-02` Unified Deep Research presets and compatibility
- `AX-03` Evidence-aware multi-agent research orchestration
- `AX-04` Canonical metric definition/validation service
- `AX-05` Enforceable portfolio risk and ETF overlap disclosures
- `AX-06` Structured claim verification and audit status
- `AX-07` Verified research snapshot and workspace reuse
- `AX-08` Opt-in thesis monitoring and advisory rebalancing
- `AX-09` Consistent executive report / portfolio memo
- `AX-10` Hosting hardening, observability and release gates

## 5. Suggested first build request (after plan-only review)

> **Invoke `feature-development-team` in BUILD mode for AX-01 only.** Preserve the current Robo Advisor route, engine, optimizer, dark design, full advanced settings, saved portfolio handling and downloads. Implement a progressive plain-language prompt → editable mandate → portfolio review layout with bounded session-state changes and no automatic paid calls. Read `AGENTS.md` and `PLAN.md` first; validate current files/tests rather than assuming this spec is fully current. Do not modify Deep Research, release infrastructure, or underlying financial formulas except for a specifically demonstrated in-scope bug. Run focused offline tests and relevant Streamlit interaction checks; independently verify and create the standard feature-team report. Do not create Jira tickets, commit, push or deploy.

**Next likely builds:** AX-02 UX wrapper (separate slice), AX-04 metric-contract pilot, then AX-06 claim checks and AX-05 risk guardrails. AX-03 and AX-08 should follow verified underlying data/risk controls, not precede them.

---

## 6. Quality bar and final sign-off checklist

- [ ] Existing nine workspaces, content and styling preserved.
- [ ] All existing options remain accessible or have explicit tested compatibility redirects.
- [ ] Robo Advisor retains prompt-led entry; no unearned suitability/risk guarantee.
- [ ] Standard Deep Research and Low Cost pilot outputs remain usable; reports/evidence recover on failure.
- [ ] All financial facts have explicit source, date, unit and period basis; unsupported claims are labeled.
- [ ] Agent workflows have bounded tools, token/cost limits, permission boundaries and deterministic checks.
- [ ] No silent provider/model calls on display reruns, saved results or exports.
- [ ] No cross-session leakage; secrets excluded from exports and logs.
- [ ] Tests record actual evidence rather than inheriting historic pass counts.
- [ ] Release status accurately names unverified hosted, CI, Docker and rollback steps.
- [ ] No Jira writes, commits, pushes, deployment or paid live calls without separate authorization.

**Bottom line:** Simplify the user's journey first, then strengthen verified financial evidence and risk guardrails, then expand agent autonomy. Retain the investment-grade depth beneath a clearer surface.
