# Axiom Research - Living Status and Improvement Plan

**Last audited:** 2026-10-01. **Repository baseline:** `ff1709e` (2026-09-27), plus the current uncommitted market-workspace fixes, project skills, and documentation updates. This describes the local working tree, not a deployed release.

## Purpose and how to read this file

Build one trustworthy research workstation: transparent data, connected workflows, grounded conclusions, reliable portfolio analytics, and predictable cost. [AGENTS.md](AGENTS.md) defines engineering requirements; this file records what exists, how it works, what was verified, and what remains.

- **Implemented:** the named capability exists in code; verification scope is recorded separately.
- **Partial:** useful foundations exist, but the roadmap acceptance criteria are unmet.
- **Pilot:** isolated experimental capability; production promotion requires additional evaluation.
- **Planned:** proposed work without evidence of completion.
- **Verified:** a specific dated check passed. It never means all behavior in that area is covered.

Use stable roadmap IDs R01-R10 and delivery/verification IDs below when adding work. Keep historical entries and append evidence; update the current matrices when behavior changes.

## Current application status

There are **eight navigation entries: seven main workspaces and one V2 pilot**. Session-backed results and several handoffs exist; a universal typed research context does not.

| Workspace | Current capability and implementation approach | Verification and remaining limits |
| --- | --- | --- |
| Introduction | Live overview and company snapshot, news, explicit AI summary. Market charts use a shared history adapter and actual Streamlit range controls with Altair hover/zoom. FMP commodity/crypto aliases are mapped; missing quotes fall back to labelled Yahoo daily closes. Company range changes reuse saved analysis. | Eight market tests include three Streamlit interactions across Introduction/Top Movers. Prior desktop/mobile browser checks passed. Universal currency/freshness contracts remain incomplete; company closing-price charts are not total-return series. |
| Top Movers | Five-trading-day rankings, direction/sector filters, breadth, Serper news, and company handoff. Normalized symbol joins and a bounded quote batch enrich displayed global leaders/laggards. Missing/nonpositive average volume remains unavailable; partial failures preserve valid rows. | Synthetic enrichment/coverage tests and filter interaction coverage. Sector-filtered rows outside the enriched global set may still lack fields. Full cross-workspace handoff is not automatically covered. |
| Research | LangGraph finance chat with FMP/Marketaux tools, thread checkpoints, structured table handling, response formatting, and sanitized event logs. | Cleaner/configuration tests cover helpers; complete tool-routing/chat interaction coverage remains missing. Changing model/use case currently resets the chat thread without the intended visible new-thread UX. |
| Equity Report | Sector-aware financial/technical scoring, peers, rankings, optional saved narrative, PDF/Excel/CSV exports, and explicit CrewAI debate over a saved scorecard with fingerprinting and structured output. Duplicate active helper definitions were removed. | Three committee tests cover bounded packets/schema/universe validation. Full report scoring/UI/export coverage is incomplete. The UI module remains approximately 5,707 lines. |
| Stock Screener | FMP universe filters, paginated results, optional metric enrichment, shared transport, and partial-result metadata. | A hardening contract covers pagination failure metadata. Full filtering/enrichment/UI tests remain missing; module-global key and cache behavior need review for session isolation. |
| Portfolio Lab | Historical Yahoo adjusted-price optimizer plus hybrid AI manager, constraints, evidence, recommendations, rebalance/monitoring, and reports. Allocation caps preserve residual cash rather than renormalizing above caps. | Constraint/parser regressions are covered. Broad optimizer math, risk assumptions, trade reconciliation, full UI, and Excel/PDF artifact coverage remain incomplete. |
| Deep Research (V1) | Evidence collection, bounded investigation tools, planning, streaming draft, review/patching, saved checkpoints, retry/resume, follow-ups, comparison output, PDF/JSON/CSV downloads, and optional committee. Saved app context is allowlisted. | Strongest coverage: 32 core, 14 recovery, and 9 UI tests. Citation existence/recovery tests do not prove every factual claim. Real-provider/model quality and full committee costs are not certified by offline tests. |
| Deep Research V2 | Isolated cost pilot: Economy/Balanced/Maximum Quality, stage routing, compact prompts/output caps, mechanical checks, optional review, saved-session reuse/force refresh, evidence-only/later synthesis, Groq/Ollama light stages, quick/full decisions, diagnostics and budget guard. V1 remains separate. | Five helper/fixture tests. No complete V2 Streamlit/evaluation benchmark or measured savings. Cached request/config reuse is not universal evidence-content/freshness validation; unknown-price models weaken dollar-budget enforcement. |

Entry points: [app.py](app.py), [main.py](src/langgraphagenticai/main.py), [sidebar routing](src/langgraphagenticai/ui/streamlitui/loadui.py). Shared design: [app_shell.py](src/langgraphagenticai/ui/app_shell.py).

**Current configuration limit:** the main OpenAI-key gate exempts Introduction and Top Movers only. Other workspaces, including deterministic Screener/optimizer paths, can still be blocked without that key. Capability-specific gates are remaining work.

## Delivered foundations and how they were built

| Foundation | Current implementation | Boundaries still outstanding |
| --- | --- | --- |
| Provider reliability | Shared FMP REST sessions, safe-GET retries, bounded timeouts and sanitized provider exceptions under `providers/`. FMP MCP has its own bounded transport and investigation budget. | This is shared transport, not one canonical adapter/schema for every financial/news source. |
| Credential handling | Recursive redaction and safe UI/provider errors in `utils/safety.py`; sanitized timing/request events avoid logging raw prompts. | Complete HTML, link, download, persistence and dependency audits are still required. |
| Financial correctness | Introduction TTM validates quarterly period/currency alignment; zero is preserved; portfolio caps retain cash; unavailable liquidity is not fabricated as zero. | Universal period/currency/return-basis validation and broad optimizer/scoring tests are incomplete. |
| Market controls/data | `providers/market_history.py` sorts/deduplicates/filter histories and falls back as a complete labelled series; Introduction uses real range controls; Top Movers tolerates enrichment failures. | Intro market 5D filtering is a calendar-day window, not a guaranteed five trading sessions. FMP daily closing-price and Yahoo adjusted-series bases must remain explicit. |
| Model-call safety | Bounded direct OpenAI clients. Introduction analysis, saved report/committee actions and Deep Research stages are explicitly initiated and results reused. | No app-wide rerun/navigation/download paid-call regression suite or uniform cost ceiling exists. |
| Deep Research recovery | Separate evidence/draft/review checkpoints, stage-specific failures, draft preservation, exact review patches and resume paths; model usage estimates when response usage is absent. | Mechanical citation checks are narrower than factual/semantic validation. |
| Deployment baseline | Python 3.11/3.12 support, developer requirements, dependency constraints, non-root Docker image and health endpoint configuration. | Constraints are not a full transitive lock. Dependency-set parity, clean constrained installs, Docker build/workflow CI and release operations remain unverified. |
| Contributor workflows | Ten repo-local skills with UI metadata, targeted references and [usage guide](docs/PROJECT_SKILLS.md), including a requested GitHub sync workflow. | These guide coding agents; they do not add app agents, Jira execution, runtime dependencies or automatic deployments. |

The standalone `crew_ai/stock_picker` example and experimental notebooks are separate from the eight main navigation entries.

## Delivery history

Append new rows; do not rewrite previous delivery claims into release certification.

| ID / date | Delivery and approach | Evidence / status |
| --- | --- | --- |
| D-20260927-01 | Hardening and research features: shared transports/redaction, allocation and TTM fixes, partial coverage, bounded model calls, V1 recovery, and optional Equity Report debate. | Commit `ac3e349`; historical [code review](docs/code_review.md). Corresponding fixes exist; broader roadmap acceptance remains open. |
| D-20260927-02 | Separate V2 cost pilot with compact stage packets/routing, validators, reuse, optional decisions and evaluation fixtures. | Commit `7c73deb`; [V2 implementation](src/langgraphagenticai/deep_research/v2.py). Pilot, not proven savings or default promotion. |
| D-20260927-03 | README refreshed for the then-current app and pilot. | Commit `ff1709e`; superseded test inventory is corrected in this audit. |
| D-20261001-01 | Repaired Introduction historical controls and missing commodity/crypto quotes; hardened Top Movers enrichment and missing liquidity; saved summaries survive chart reruns without automatic AI calls. | Current working tree: `market_history.py`, `introduction_tab.py`, `market_overview_data.py`, `top_movers_data.py`, `top_movers_tab.py`, shared shell CSS and `tests/test_market_tabs.py`. V-20261001-01/02 below. |
| D-20261001-02 | Added nine focused coding skills, invocation guide, metadata and provider/financial/portfolio/export/release references. | Current working tree: `.agents/skills/`, `docs/PROJECT_SKILLS.md`, README. Skill manifests, links, YAML and referenced repository paths validated during that task. |
| D-20261001-03 | Rebuilt current-state documentation with workspace matrix, dated test inventory, delivery ledger and maintainable roadmap; separated requirements from implementation. | Documentation-only audit. Fresh offline suite and compile/import checks: V-20261001-02. No deployment or new app feature in this entry. |
| D-20261002-01 | Added `axiom-github-sync`: verifies repository/branch, change scope and applicable checks, then commits/pushes when requested; preserves unrelated work and disallows force-push. Collection now has ten skills. | Skill/docs-only change. Manifest/UI YAML, references and diff checks validated; app tests and live publication not repeated. October 1 work was pushed in commit `930d332`; this skill is a subsequent local change. |

## Verification ledger

### V-20261001-02 - Fresh documentation audit

- Full offline pytest: **85 passed, 128 warnings, 116.66 seconds**, across ten modules. Provider/model boundaries in these tests use synthetic/mocked inputs; no paid workflow was requested.
- Environment: Python **3.12.7**, pytest **7.4.4**, Streamlit **1.64.0**, existing local Anaconda interpreter. The declared dev requirement is pytest >=8,<10; deployment constraints pin Streamlit 1.61.1. This run verifies the current environment, not a clean constrained installation.
- `python -m compileall -q app.py src` passed. `import app; import langgraphagenticai.main` passed. Import emitted caching and LangGraph deprecation warnings; import success is not full app startup.
- Pytest warnings: 127 Altair/jsonschema deprecation warnings plus one imported-plugin assertion-rewrite warning from the inventory wrapper. No test failures.
- No new startup/health, browser interaction, live-provider/model, Docker build, dependency upgrade or paid evaluation was performed for this documentation-only audit.
- Documentation checks passed: local links and referenced paths, UTF-8/encoding, code-fence balance and `git diff --check`. Hash comparison confirmed all 136 existing source, test and skill files were unchanged by this audit.

Reproduce in the project's installed environment from the repository root:

```powershell
$env:PYTHONPATH = (Resolve-Path "src").Path
python -m pytest -q
python -m compileall -q app.py src
python -c "import app; import langgraphagenticai.main"
```

The audit used a pytest collection plugin to count module inventory; a normal pytest invocation need not reproduce its extra plugin warning. Do not hard-code this developer's interpreter path into shared scripts.

### V-20261001-01 - Earlier market-repair verification

The earlier repair task ran the suite (**85 passed, 127 warnings**), compile/import checks, and Streamlit startup/health on port 8507. Browser checks exercised Introduction 1D/1M/1Y charts, restored commodity/crypto quote cards, Top Movers Leaders/Laggards, desktop and 390px mobile layouts. These were live-provider smoke checks with AI actions left unclicked, not an offline certification. Browser console showed chart-library warnings; no JavaScript errors were observed.

This is prior task evidence retained for traceability, not newly repeated by the documentation audit. It does not certify every workspace or currency/coverage combination.

### Test inventory at V-20261001-02

| Module | Collected | Actual protection |
| --- | ---: | --- |
| `test_app_health.py` | 2 | Configuration validation only; despite the filename, no startup or HTTP health check |
| `test_deep_research.py` | 32 | Evidence/provider envelopes, financial periods/trends, tool bounds, orchestration, citation failures and PDF/JSON helpers |
| `test_deep_research_recovery.py` | 14 | Checkpoints, retries, draft preservation, stream/output failures, review patching and bounded prompts |
| `test_deep_research_ui.py` | 9 | Mocked V1 Streamlit interactions, saved runs, follow-ups and recovery |
| `test_deep_research_v2.py` | 5 | Routing/limits, mechanical validators, cache-key inputs, committee packet/estimated usage and fixture presence |
| `test_equity_committee.py` | 3 | Bounded packet, structured decision consistency and selected-universe guard |
| `test_formatters.py` | 3 | Numeric formatting and rectangular tables |
| `test_hardening.py` | 6 | Allocation caps, redaction, TTM alignment, parsers, mover partial batches and Screener metadata |
| `test_market_tabs.py` | 8 | History/fallback/alias/enrichment contracts and three Streamlit control/state tests |
| `test_response_cleaner.py` | 3 | Research headings/bullets formatting |
| **Total** | **85** | **Twelve Streamlit interaction cases are concentrated in V1 Deep Research and market controls** |

Counts describe collected cases, not a code-coverage percentage.

| Coverage target | Current evidence | Remaining acceptance gap |
| --- | --- | --- |
| Financial/domain unit tests | Several important regressions protected | Broad scoring, return/risk math, currency, short history and trade reconciliation |
| Provider contracts | Synthetic FMP/MCP/Serper/Yahoo boundaries in selected tests | Uniform timeout/rate-limit/malformed/stale/empty cases across all adapters, including Marketaux |
| Streamlit workflows | V1 Deep Research and market controls | Research, Equity Report, Screener, Portfolio Lab, V2, and complete cross-page path |
| Agent/AI validation | Recovery, citation existence, structured decisions and helper routing | End-to-end tool choice, numerical grounding, model quality, adversarial cases and paid-call invariants |
| Exports | Deep Research PDF/JSON and formatting helpers | All-workspace PDF/Excel/CSV/JSON artifacts, credential/URL checks and data consistency |
| Integration/deployment | Fresh compile/import; earlier local health/browser smoke | Automated startup/health plus mocked full workflow, clean install and Docker/CI |
| Evaluation/observability | Five V2 scenario fixtures; local events and stage diagnostics | Executed scored benchmark, real per-agent usage, application-wide traces and quality thresholds |

## Configured limits versus measured outcomes

These are current settings, not measured performance promises.

| Scope | Current settings / mechanism | Limitation |
| --- | --- | --- |
| Market cache | Overview/history 300s; Top Movers and company snapshot 900s; company summary 1,800s | No universal freshness-state or narrative evidence fingerprint |
| Other data caches | Screener universe uses 3,600s; Screener enrichment 1,800s; optimizer price downloads 900s | TTLs alone do not establish correct cross-session/provider/credential cache identity |
| V1 model stages | Plan 1,200 output tokens / 75s; draft 4,500 standard or 6,000 extended / 150s; review 3,000 / 120s; follow-up 2,200 / 90s | Specific stage policies differ from other direct/graph clients |
| V2 output/context | Economy draft 1,800 standard / 3,000 extended; other modes 2,200 / 3,500. Draft context 22,000 / 34,000 characters; compact review/follow-up packets | Mechanical validation is not numerical claim verification |
| V2 routing | Economy defaults to nano light stages and mini drafting; Balanced uses optional review; Maximum Quality uses larger drafting/lead model. Groq/Ollama are opt-in light-stage routes | Alternate-provider operational quality is not established by helper tests |
| Budget/usage | V2 default UI budget $0.35; stage estimates and session diagnostics; CrewAI aggregate usage split is explicitly estimated | Unknown model prices can evade dollar checks; no proven complete per-agent cost attribution |
| Saved results | V1/V2 histories isolated; V1 retains five runs, V2 eight; explicit refresh/later-synthesis controls | Session reuse is not durable persistence or a universal freshness-aware cache |

Cold/warm render latency, call-count budgets per workspace, and achieved savings have **not** been benchmarked here. Static model pricing tables need maintenance; do not treat estimates as current provider bills.

## Ten-step roadmap

All ten broad milestones remain **partial**. Individual delivered foundations below do not satisfy every acceptance criterion. Preserve the numbered dependency order; tests accompany each behavioral change rather than waiting for R06.

| ID | Milestone | Current status | Next acceptance focus |
| --- | --- | --- | --- |
| R01 | Canonical market data and provenance | Partial | Typed shared records/adapters and provider contract matrix |
| R02 | Universal freshness/source/data-quality UX | Partial | Consistent states and currency/period/source visibility across pages |
| R03 | Shared company context and connected journey | Partial | Typed intent handoffs and preserved cross-page state |
| R04 | Evidence-first validated AI research | Partial | Numerical/period/currency grounding beyond citation existence |
| R05 | Stable domain modules | Partial | Characterized extraction of large mixed-responsibility modules |
| R06 | User-critical automated workflow coverage | Partial | Remaining workspace interactions, cross-page path and CI |
| R07 | Performance/cache/AI economics | Partial; V2 pilot | Measured latency/call counts and complete enforceable cost accounting |
| R08 | Portfolio decision and monitoring workflow | Partial | Unified holdings/constraints, assumptions and trade reconciliation |
| R09 | Observability, evaluations and feedback | Partial | Executed versioned evaluation and end-to-end sanitized traces |
| R10 | Documentation/deployment readiness | Partial | Clean installs, dependency parity, Docker CI and release runbook |

### R01 - Canonical data and provenance

**Impact: very high. Effort: high.** Shared FMP transport and labelled history fallbacks are implemented. REST, MCP, news and portfolio adapters still have different contracts.

- [x] Bounded shared REST transport, safe errors and selected partial-result metadata.
- [ ] Typed security, quote, history, financial value, news and provider-error records with provider, retrieved time, source as-of, unit/currency, period and status.
- [ ] Consolidate duplicate retrieval/normalization; define source precedence and uniform safe retry/rate-limit behavior.
- [ ] Normalize/deduplicate Marketaux and Serper news under one contract.

**Acceptance:** two workspaces resolve the same quote through the same adapter/metadata model; failures preserve typed partial results; contracts cover success/timeout/rate limit/malformed/empty/stale; secrets are absent from logs/errors/diagnostics/exports.

### R02 - Universal data-quality UX

**Impact: very high. Effort: medium.** Source/date notes and partial warnings exist in market and research paths; shared shell styling exists.

- [x] Market quote/fallback source notes, unavailable liquidity and partial coverage.
- [ ] Shared badges, freshness indicators, coverage summaries and data-quality drawer.
- [ ] Relevant quote/statement/news dates, currency, period and retrieval time on every data-heavy page.
- [ ] Capability-aware readiness, including deterministic workspaces without an unnecessary model-key gate.

**Acceptance:** every major workspace distinguishes live/delayed/cached/stale/fallback/partial/unavailable using text as well as color; successful partial data survives; provider facts, calculations and AI interpretation are visibly different.

### R03 - Connected company context

**Impact: very high. Effort: medium.** Existing navigation keys, selected-company handoffs, saved filters/results and Deep Research context collection provide foundations.

- [x] Selected ticker handoffs and allowlisted saved context in some paths.
- [ ] Typed `ResearchContext`: tickers, comparison set, origin, intent, evidence IDs and dates; shared navigation helpers replace unrelated keys.
- [ ] Consistent Snapshot/Research/Report/Deep Research/Compare/Portfolio actions and return-to-results.
- [ ] Recent securities/pinned comparisons, preserved state and visible chat reset/new-thread behavior.

**Acceptance:** mover -> prefilled Research -> Deep Research without re-entry; returning preserves filters; no silent loss of completed work; full path covered by mocked interactions.

### R04 - Grounded and validated conclusions

**Impact: very high. Effort: high.** V1 evidence/review recovery, period-aware helpers and committee schemas exist. V2 adds mechanical report checks.

- [x] Evidence identifiers, unknown-citation failure handling, saved packets and structured committee outputs.
- [ ] Structured briefs/recommendations/risks/catalysts/invalidation across all AI surfaces.
- [ ] Deterministic numerical/date/currency/period/scenario checks against evidence; surface unsupported or contradictory claims.
- [ ] Shared grounded renderer and clickable source blocks across chat, snapshots, reports and committees.

**Acceptance:** material numerical claims map to evidence or labelled estimates; invalid periods/citations fail visibly; AI cannot overwrite facts/calculations; saved inputs audit the conclusion.

### R05 - Domain extraction

**Impact: high. Effort: high.** Focused transports/history/validators exist; duplicate active Equity Report names were removed. Major modules remain large: Equity Report ~5,707 lines, portfolio decision engine ~1,893, portfolio data sources ~1,140 at this audit.

- [x] New history adapter and focused safety/constraint boundaries.
- [ ] Characterization tests before extracting Equity Report retrieval, normalization, scoring, narrative, exports and rendering.
- [ ] Extract portfolio policy/signals/constraints/synthesis/validation with stable interfaces.
- [ ] Remove provider HTTP from primary pages; consolidate formatting, parsing and report components.

**Acceptance:** materially smaller mixed modules, stable tested public interfaces, and equivalent report outputs before/after extraction.

### R06 - Workflow protection

**Impact: high. Effort: medium-high.** Current inventory is 85 cases; V1 recovery and market controls have direct interaction protection.

- [x] Offline core/recovery/UI cases and market repair contracts.
- [ ] Unit/contract boundary coverage for scoring, filters, optimizer math, periods/currencies and missing/negative/short histories.
- [ ] Success and empty/failure interactions for every workspace and navigation action.
- [ ] Mocked discover -> snapshot -> research -> deep research -> portfolio workflow.
- [ ] CI lint/format/type/tests/import/startup/Docker gates; no `.github` workflow currently exists.

**Acceptance:** each workspace has successful and failed/empty interactions, no paid tests, and CI blocks routing/provider/export/weight regressions.

### R07 - Performance and cost

**Impact: high. Effort: medium-high.** Cached evidence, bounded requests, saved analyses and V2 stage profiles exist.

- [x] Isolated Economy/Balanced/Maximum Quality pilot, compact packets and labelled usage estimates.
- [ ] Cold/warm latency, provider/model call counts, prompt/output size baselines and measurable budgets by workspace.
- [ ] Evidence-content/freshness-aware reuse, bounded batching/concurrency and explicit refresh.
- [ ] Complete CrewAI/model cost attribution, unknown-price handling and enforceable pre-run/run ceilings.
- [ ] Rerun/navigation/download paid-call regression checks and a scored V1/V2 comparison.

**Acceptance:** no unnecessary warm-cache calls; standard research <=3 model calls unless recovery; all-stage cost is included or clearly unknown; latency is visible and the economical route meets quality criteria. Claimed savings require measurements.

### R08 - Portfolio decisions and monitoring

**Impact: high. Effort: high.** Optimizer, AI manager, risk/regime analyses, constraints and monitoring exist; cap arithmetic has targeted protection.

- [x] Cap-safe constrained allocations with residual cash.
- [ ] Canonical imported tickers/quantities/cost basis/account/cash and unified optimizer/manager holdings model.
- [ ] Current/target weights, reconciled trades/capital, turnover, tax/slippage assumptions, exposures and risk contributions.
- [ ] Explicit benchmark/window/frequency/risk-free/return basis; scenario/stress and attribution methodology.
- [ ] Saved decision snapshots and evidence/constraint explanations for recommendation changes.

**Acceptance:** trades reconcile within tolerance, corrections are deterministic/explained, assumptions are visible and every proposed trade traces to evidence/constraint/objective.

### R09 - Operating evidence and evaluations

**Impact: medium-high. Effort: medium.** Sanitized events/request IDs, Deep Research stage diagnostics and five V2 scenario fixtures exist.

- [x] Local event safety/timing and versioned large-cap/sparse/same-sector/cross-sector/missing-data fixtures.
- [ ] Request IDs spanning UI/providers/tools/models/exports; cache/error/token/cost telemetry across the app.
- [ ] Execute evaluation for factual/numerical/citation/risk/readability/latency/cost criteria, including adverse news.
- [ ] Quality thresholds before provider/model default changes and privacy-conscious feedback/issue capture.

**Acceptance:** failed actions are traceable without secrets; releases compare fixed scored fixtures; defaults meet accuracy/latency thresholds; errors offer actionable recovery.

### R10 - Deployment and documentation

**Impact: medium-high. Effort: medium.** Current README, subsystem guide, requirements/constraints, non-root Docker setup and project skills are present. This audit repairs documentation organization and stale test claims.

- [x] Eight-entry workspace documentation, living status ledger and contributor skills.
- [ ] Clean supported-Python installs; reconcile package/requirements extras and reproducible transitive dependencies.
- [ ] Local/test/production profiles and operational key/capability/freshness matrix.
- [ ] Dependency/secrets/HTML/URL/export/container checks; accessibility/responsive/onboarding/troubleshooting.
- [ ] Docker health plus mocked workflow in CI; release versioning/migration/backup/operations runbook.

**Acceptance:** documented clean setup/test/start works; Docker CI passes; docs match runtime limits/paid actions; no known secret/debug artifact/mojibake remains. Local imports and a healthy earlier server alone do not satisfy this.

## Delivery sequence and success measures

- **Milestone A - Trusted data:** R01-R02.
- **Milestone B - Connected, grounded research:** R03-R04.
- **Milestone C - Maintainable and tested platform:** R05-R07.
- **Milestone D - Portfolio product and production readiness:** R08-R10.

Begin with canonical provider records/contracts, then consistent data-quality display and intent-bearing context. Add tests with each slice. V2 quality/cost experiments stay isolated while these foundations mature.

Track metric provenance coverage; provider failure/partial recovery rate; cold/warm render latency; cross-page completion; citation/numerical validation; calls/tokens/cost per task; workspace interaction coverage; portfolio reconciliation; user usefulness/trust. Targets and measured baselines must be dated, not invented.

**Non-goals until R01-R06 are complete:** more loosely integrated providers, autonomous brokerage execution, more agents as a quality proxy, sensitive durable portfolio storage without privacy/authentication design, or mobile-native expansion before responsive workflows are reliable.

## Documentation boundaries and design notes

- AGENTS: durable engineering rules and maintenance procedure. PLAN: current implementation and dated proof. README: user setup/workflows. [DEEP_RESEARCH.md](DEEP_RESEARCH.md): subsystem behavior.
- [Cost optimization TODO](TODO_DEEP_RESEARCH_COST_OPTIMIZATION.md) is the original design checklist, not a completion ledger; V2 status and unmet acceptance are recorded here.
- [Historical code review](docs/code_review.md) retains the September findings and remediation history; its old environment/test counts are not current verification.
- Shared transport is a foundation for canonical adapters, not a substitute for them. Existing session handoffs are a foundation for typed context, not that model itself.
- V2 is an isolated experimental boundary. Promote defaults only after executed quality/cost evaluation; keep V1 recovery behavior protected.

## Template for continuing updates

For each meaningful change, update the relevant matrix and Rxx checkboxes, then append:

```text
Delivery ID / date:
Related roadmap IDs and workspaces:
User outcome and acceptance criteria:
Implementation approach / architectural decision:
Source paths and test paths:
Commit or working-tree status:
Verification ID, commands, environment, results:
Mocks/live services and checks not performed:
Remaining risks, follow-up IDs and next acceptance step:
```

A verification entry should retain the exact date/result and scope even after test counts grow. A delivered subitem can be checked while its parent milestone remains partial. Do not erase unverified work by describing a whole feature as done.
