# Axiom Research — 10-Step Improvement Plan

## Product objective

Turn the existing collection of capable research tools into one cohesive investment-research workstation: live and transparent data, connected workflows, grounded AI conclusions, reliable portfolio analytics, and a fast interface that helps a user move from market discovery to a defensible decision.

## Audit summary

The application already has substantial depth: seven workspaces, multiple financial/news providers, LangGraph tools, sector-aware reports, a large portfolio-management subsystem, Deep Research with recovery/citations, exports, and 63 automated tests.

The most consequential gaps are architectural and product-level:

- FMP and price/news access are implemented in several separate modules with different caching and error behavior.
- Data source, period, currency, freshness, and partial-failure status are not consistently visible.
- Workspaces share some session data, but there is no canonical ticker/research context across the whole app.
- Deep Research is well tested; Introduction, Top Movers, Research routing, Equity Report, Screener, and Portfolio Lab have much less direct interaction coverage.
- Several critical modules are very large (`equity_report_tab.py` is about 4,900 lines; `decision_engine.py` about 1,700), increasing regression risk.
- AI cost accounting, evidence reuse, and stage-specific model routing are incomplete.
- The README reflects an earlier five-tab structure and does not fully describe the current Axiom workspace.

The steps below are ordered by user impact and dependency, not implementation novelty.

## Implementation status — 2026-09-27 hardening pass

The repository-wide code review initiated the following completed foundations:

- Shared FMP HTTP transport with bounded retries/timeouts and credential-safe provider errors.
- Centralized secret redaction for logs, UI errors, and structured values.
- Bounded direct OpenAI clients with a common timeout/retry policy.
- Cap-safe portfolio allocation with residual cash instead of post-cap renormalization.
- Period-validated quarterly TTM construction for the Introduction snapshot.
- Explicit partial-coverage reporting for Top Movers.
- Reconciled package metadata, deployment constraints, and developer test dependencies.
- Removal of duplicate active Equity Report function names and updated seven-workspace documentation.
- Equity Report now has an opt-in, structured CrewAI best-buy debate over the saved scorecard, with specialist dissent, risk controls, input fingerprinting, and no automatic provider recollection.
- A separate Deep Research V2 pilot now implements the cost-optimization roadmap with stage routing, compact contexts, deterministic validation, caching, cost ceilings, Groq/Ollama light stages, decision modes, and evaluation fixtures while preserving V1 behavior.

The broader typed provenance model, universal freshness components, and canonical cross-workspace `ResearchContext` remain roadmap work; this pass establishes the safety and provider boundaries they will use.

---

## 1. Create a canonical market-data and provenance layer

**Why first:** Trust and consistency depend on every page interpreting the same source data the same way.

**Deliverables**

- Introduce shared provider adapters for FMP, yfinance, Marketaux, and Serper.
- Define typed records for security identity, quote, price history, statement value, news item, and provider error.
- Include provider, retrieved-at time, source as-of date, currency/unit, fiscal period, and freshness status in each record.
- Add one retry/timeout/rate-limit policy and one normalized error taxonomy.
- Consolidate duplicate FMP request logic currently spread across company snapshot, Top Movers, Equity Report, Screener, Deep Research, and portfolio modules.
- Define source precedence and explicitly label fallbacks rather than silently mixing providers.

**Acceptance criteria**

- The same ticker quote requested by two workspaces resolves through the same adapter and metadata model.
- Provider failures produce a typed partial-data result rather than an empty table or swallowed exception.
- Contract tests cover success, timeout, rate limit, malformed payload, empty result, and stale result.
- No API key appears in logs, errors, cache diagnostics, or exports.

**Impact:** Very high | **Effort:** High

---

## 2. Add universal freshness, source, and data-quality UX

**Why:** Users cannot judge live financial output without knowing its date, basis, and coverage.

**Deliverables**

- Build shared source badges, as-of labels, freshness indicators, warning panels, and coverage summaries.
- Show quote time, statement period, currency, news publication time, and retrieval time in the relevant card/table.
- Add clear states for live, delayed, cached, stale, fallback, partial, and unavailable data.
- Add a Data Quality drawer showing provider errors and missing fields without overwhelming the executive view.
- Replace misleading generic “SYSTEM READY” states with capability-aware status.

**Acceptance criteria**

- Introduction, Top Movers, Equity Report, Screener, Portfolio Lab, and Deep Research all display source and as-of metadata.
- Stale data has a visible non-color-only warning.
- Partial data remains usable and names the missing provider/category.
- A user can distinguish provider facts, calculated fields, and AI interpretation at a glance.

**Impact:** Very high | **Effort:** Medium

---

## 3. Build a shared company context and connected research journey

**Why:** The highest-value workflow crosses pages: discover a mover, inspect it, research it, compare it, and decide whether it fits a portfolio.

**Deliverables**

- Define a typed `ResearchContext` containing active ticker(s), comparison set, originating page, intended action, evidence IDs, and as-of metadata.
- Replace ad hoc session keys with explicit navigation helpers.
- Add consistent actions: Open Snapshot, Ask Research, Build Equity Report, Start Deep Research, Compare, Add to Portfolio Lab, and Return to Results.
- Preserve completed results and filters across page navigation.
- Add recent securities and pinned comparison sets using session persistence first, with an optional durable store later.

**Acceptance criteria**

- A Top Movers ticker can open Research with a formatted, prefilled question and then move into Deep Research without re-entering the ticker.
- Returning to Top Movers preserves direction, sector, and selected symbol.
- No navigation action silently clears completed chat or research.
- Cross-page routing has automated Streamlit interaction tests.

**Impact:** Very high | **Effort:** Medium

---

## 4. Make AI research evidence-first and deterministically validated

**Why:** Attractive prose is not enough; investment research must be traceable and internally consistent.

**Deliverables**

- Use structured schemas for research summaries, company briefs, comparison tables, recommendations, risks, catalysts, and invalidation signals.
- Attach evidence/source identifiers to material claims and display clickable source blocks.
- Add deterministic validators for figures, currencies, dates, ticker coverage, citation existence, recommendation enums, scenario arithmetic, and period alignment.
- Flag unsupported claims, contradictions, missing evidence, and stale inputs before rendering a confident conclusion.
- Reuse the improved formatted research renderer across Research, Introduction AI summary, Equity Report narrative, and committee outputs.

**Acceptance criteria**

- Every material numerical claim in a structured research brief maps to evidence or is labeled as an estimate/inference.
- Unknown citations and mismatched periods fail validation visibly.
- AI output cannot overwrite provider facts or deterministic portfolio calculations.
- A saved evidence packet can reproduce or audit the displayed conclusion.

**Impact:** Very high | **Effort:** High

---

## 5. Refactor the largest modules into stable domain components

**Why:** Large mixed-responsibility files slow improvement and make regressions more likely.

**Deliverables**

- Split `equity_report_tab.py` into provider/service, normalization, scoring, narrative, export, and UI sections.
- Split portfolio `decision_engine.py` into policy, signal calculation, constraints, decision synthesis, and validation.
- Reduce direct network access from UI files.
- Consolidate duplicate formatters, safe-number handling, ticker parsing, HTTP helpers, and report components.
- Add stable interfaces before changing behavior.

**Acceptance criteria**

- No primary Streamlit page contains provider-specific HTTP logic.
- New domain modules have focused tests and clear public interfaces.
- Existing report outputs pass characterization/snapshot tests before and after extraction.
- Large-file line counts and duplicated request/formatting code are materially reduced.

**Impact:** High | **Effort:** High

---

## 6. Expand automated coverage to every user-critical workflow

**Why:** Current tests strongly protect Deep Research but leave other major pages exposed.

**Deliverables**

- Add unit tests for Introduction, company snapshot, Top Movers ranking, Screener filters, Equity Report scoring, optimizer math, and portfolio constraints.
- Add provider contract fixtures with synthetic/recorded sanitized payloads.
- Add Streamlit tests for every navigation page, form submission, empty state, partial state, and cross-page handoff.
- Add a mocked end-to-end path: discover → snapshot → research → deep research → portfolio.
- Add CI for lint/format, type checks, tests, import smoke test, and Docker health check.

**Acceptance criteria**

- Every workspace has at least one successful interaction test and one failure/empty-state test.
- Tests perform no paid model or data-provider calls.
- Core financial calculations have boundary tests for zero, missing, negative, currency mismatch, and short history.
- CI blocks regressions in routing, provider contracts, exports, and portfolio weight constraints.

**Impact:** High | **Effort:** Medium-high

---

## 7. Improve performance, caching, and AI cost controls

**Why:** A research workstation must remain fast and predictable as data and agent depth grow.

**Deliverables**

- Establish latency and call-count baselines for each workspace.
- Apply data-specific cache policies and cache evidence separately from generated narratives.
- Add request batching, capped concurrency, and provider-level rate-limit handling.
- Implement Deep Research modes: Economy, Balanced, and Maximum Quality with stage-specific models and token budgets.
- Include CrewAI calls in cost telemetry; add pre-run cost estimates and configurable spending limits.
- Ensure reruns, downloads, tab changes, and formatting never repeat paid work.

**Acceptance criteria**

- Warm cached pages make no unnecessary provider requests.
- Standard Deep Research uses no more than three model calls unless recovery is needed.
- Displayed run cost includes every model stage and clearly labels estimates.
- Typical cached navigation feels immediate; provider/model latency is visible when it is not.

**Impact:** High | **Effort:** Medium-high

---

## 8. Upgrade portfolio analytics into a decision-and-monitoring workflow

**Why:** The portfolio subsystem is technically rich but can deliver more user value by connecting recommendations to holdings, constraints, and change over time.

**Deliverables**

- Add portfolio import with canonical validation for tickers, quantities, cost basis, account type, and cash.
- Unify optimizer output and AI manager recommendations around the same holdings and constraint model.
- Show current versus target weights, required trades, turnover, taxes/slippage assumptions, concentration, factor/sector exposure, and risk contribution.
- Add scenario/stress testing and benchmark attribution with explicit methodology.
- Save decision snapshots so users can compare recommendation changes as evidence updates.

**Acceptance criteria**

- Proposed trades reconcile to target weights and available capital within tolerance.
- Constraint corrections are explained and deterministic.
- Metrics display benchmark, window, frequency, risk-free rate, and price/return basis.
- Users can trace each proposed trade to evidence, a constraint, or a portfolio objective.

**Impact:** High | **Effort:** High

---

## 9. Add observability, evaluation, and user feedback loops

**Why:** Reliability and AI quality cannot improve if failures, latency, and answer quality are invisible.

**Deliverables**

- Add structured request IDs spanning UI action, provider calls, graph/tool calls, model stages, and exports.
- Record sanitized latency, cache hits, error categories, token usage, and estimated cost.
- Create an evaluation set covering large cap, sparse coverage, same-sector comparison, cross-sector comparison, missing data, and adverse news.
- Score factual accuracy, numerical consistency, citation correctness, risk coverage, readability, latency, and cost.
- Add lightweight answer feedback and issue capture without collecting credentials or sensitive portfolio details by default.

**Acceptance criteria**

- A failed user action can be traced across providers and model stages without exposing secrets.
- Release comparisons use a fixed, versioned evaluation set.
- Model/provider changes cannot become defaults until they meet defined accuracy and latency thresholds.
- Users receive actionable recovery messages rather than raw exceptions.

**Impact:** Medium-high | **Effort:** Medium

---

## 10. Finish product hardening, documentation, and deployment readiness

**Why:** The current product has outgrown parts of its setup and documentation.

**Deliverables**

- Rewrite the README around the current seven-workspace Axiom experience and connected workflows.
- Reconcile `requirements.txt` and `pyproject.toml`; adopt repeatable dependency locking and documented supported Python versions.
- Add configuration profiles for local, test, and production environments.
- Add security checks for dependencies, secrets, unsafe HTML, URLs, exports, and container configuration.
- Add accessibility/responsive review, onboarding, sample workflows, provider capability matrix, and troubleshooting.
- Define release versioning, migration notes, backup/export expectations, and operational runbook.

**Acceptance criteria**

- A clean environment can install, configure, test, and start the app using documented commands.
- Docker health and one mocked workflow pass in CI.
- Documentation matches the current navigation, keys, providers, limits, and data freshness behavior.
- No known mojibake, committed secret, temporary debug file, or undocumented paid action remains.

**Impact:** Medium-high | **Effort:** Medium

---

## Recommended delivery sequence

Use the numbered order. Steps 1–4 establish the product contract; Step 5 makes it safer to extend; Step 6 protects the refactor; Steps 7–9 improve economics and operating quality; Step 10 makes the result maintainable and deployable.

For delivery, group work into four milestones:

- **Milestone A — Trusted data:** Steps 1–2
- **Milestone B — Connected, grounded research:** Steps 3–4
- **Milestone C — Maintainable and tested platform:** Steps 5–7
- **Milestone D — Portfolio product and production readiness:** Steps 8–10

## Success measures

Track these across the roadmap:

- Percentage of visible financial metrics with provider, as-of date, period, and unit/currency.
- Provider error rate and partial-result recovery rate.
- Median cold and warm render time per workspace.
- Cross-page workflow completion rate.
- Citation and numerical validation pass rate.
- Model calls, tokens, and cost per completed research task.
- Automated workflow coverage by workspace.
- Portfolio recommendation reconciliation/constraint pass rate.
- User-rated usefulness and trust in research output.

## Explicit non-goals until Steps 1–6 are complete

- Adding more loosely integrated data providers.
- Adding autonomous trading or brokerage execution.
- Expanding agent count as a proxy for research quality.
- Persisting sensitive user portfolios without an authentication, privacy, and storage design.
- Shipping mobile-native applications before the responsive web workflow is reliable.
