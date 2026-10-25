# AGENTS.md — Axiom Research Engineering Requirements

## Purpose

This file defines how coding agents and contributors must work on Axiom Research. The product is a Streamlit financial-research application that combines live market data, company research, screening, portfolio analytics, LangGraph chat, Deep Research, and optional multi-agent investment decisions.

The goal is not to add the most features. The goal is to make the existing capabilities trustworthy, connected, fast, explainable, and useful for real investment research.

## Implementation orientation (updated 2026-10-18)

These engineering requirements are the target standard, not a claim that every requirement is already implemented. [PLAN.md](PLAN.md) is the dated source of truth for implementation status, delivery history, verification evidence, and remaining work. Do not infer completion from a module name or a passing test count.

The sidebar exposes nine research workspaces plus the Data Validation utility: Market Brief (internal Introduction identity), Top Movers, Stock Screener, Research, Equity Report, AI Valuation, Deep Research, Portfolio Lab and AI Robo Advisor. Deep Research contains **Standard format** and experimental **Low cost format**; V2 is not a separate current sidebar destination. Data Validation adds an explicit, read-only provider endpoint checker; it does not transfer raw responses into financial workspaces or invoke models. The application entry points are `app.py`, `src/langgraphagenticai/main.py`, and `src/langgraphagenticai/ui/streamlitui/loadui.py`.

Module paths abbreviated below are relative to `src/langgraphagenticai/`; repository-level release/test paths are explicit.

| Area | Implementation boundary |
| --- | --- |
| Shared presentation | `ui/app_shell.py`, `ui/workspace_presentation.py` and `ui/workspace_handoff.py`; shared terminal headers/evidence states and bounded navigation adapters, while page modules orchestrate controls |
| Provider transport | `src/langgraphagenticai/providers/`; shared FMP REST transport, bounded OpenAI clients and symbol-aware Introduction history exist, but adapters and metadata are not uniform across every provider |
| Financial/domain logic | Company snapshots, Equity Report scoring, `portfolio_manager/`, audited research calculations in `deep_research/{quarterly_ttm,research_metrics}.py`, and configurable chart calculations in `technical_analysis/`; preserve each metric basis |
| AI Valuation | `valuation/{framework,model,projection,book_value,ai,metrics,citations}.py` separates conditional sector routing, dated annual/consensus anchors, deterministic pricing and explicit structured AI; `providers/{valuation,company_evidence}.py` supplies bounded source-aware collection/reuse |
| Market ribbon/dashboard | `providers/market_strip.py` and `ui/market_strip.py` populate the shared five-index shell ribbon independently of the explicit-refresh Market Brief dashboard and constituent ticker |
| Research | LangGraph chat remains session-backed; `research/{guided_workflow,guided_schemas}.py`, `providers/guided_research.py` and `ui/guided_research_tab.py` implement the opt-in bounded one-company Guided plan/run workflow |
| Saved investment brief | `analysis/{investment_brief,scenarios}.py` and `ui/investment_brief.py`; shared V1/V2 saved narrative excerpts, audited earnings-multiple sensitivities and bounded provenance exports |
| Company navigation | `state/research_context.py` supplies metadata-only typed identity/intent; `ui/workspace_handoff.py` applies supported session handoffs without transferring financial packets |
| Deep Research | `src/langgraphagenticai/deep_research/`; V1/V2 orchestration stays separate while fresh financial collection, sector applicability, audit contracts and bounded model packets are shared |
| Verification/release | `tests/conftest.py` guards offline collection/tests; `.github/workflows/offline-release.yml`, `Dockerfile.verify` and `scripts/release_inventory.py` define release gates/artifacts. Consult PLAN and `docs/DEPLOYMENT.md` for executed checks and unverified gates |
| Contributor skills | `.agents/skills/`; [project skill guide](docs/PROJECT_SKILLS.md) describes all thirteen skills and invocation, including GitHub commit/push |

P01 delivers a bounded typed, metadata-only `ResearchContext` for supported company handoffs; saved page results remain session-backed. Universal financial provenance, complete Portfolio/Compare handoff adoption and universal freshness UI remain roadmap work. The bounded credential/ticker/session-scoped raw FMP reuse bridge from new Equity Report runs to AI Valuation is explicitly supported; it preserves original retrieval times and annual/quarterly/TTM/forecast meanings. It is separate from metadata-only navigation and does not validate legacy scorecards as financial inputs. Navigation metadata is not financial evidence, and unverified financial-packet bridges remain disabled. V2 is a pilot; its helpers and fixtures do not establish end-to-end financial accuracy or measured cost savings.

## Current active workflow and repository map (2026-10-24)

- Navigation retains nine research workspaces plus **Data Validation**, in its own **Validate** ribbon after Discover, Analyze and Allocate. Data Validation has 115 allowlisted probes, report/metric-family filters, thirty source-backed usage mappings and a source-definition index. This metadata is not universal runtime/per-cell lineage or an accuracy certificate; only explicit Fetch calls providers.
- **AI Robo Advisor:** active Build/retry uses metrics-led sector/mandate selection and local sizing with optional **explanation-only AI**. AI must cover the exact fixed holdings and cannot change order, holdings, conviction budgets or weights. Preserve canonical Equity Report applicability/priorities, the narrower provider-TTM/separate annual-growth basis, ETF fund-role framework, hard caps/cash and historical-risk gates. Legacy domain selection mode remains for retained consumers; earlier saved results are labeled and never silently regenerated. Reader projections live in `portfolio_architect/executive.py` and `ui/advisor_executive.py`. Stage checkpoints/retry recover within a surviving session; a full session/server restart can still lose work.
- **Equity Report:** structured committee tickers are bound to the saved universe with normalization and strict post-validation. Executive PDF uses portrait Deep Research-style typography, full saved summary/note and matching committee narrative; no compact metrics appendix. `analysis/equity_report_pdf.py` owns PDF rendering. Downloads make no provider/model calls.
- **Saved executive memos:** `analysis/memo_pdf.py` supplies a session-owned pure deferred download callback. PDF layout occurs on explicit download, not report navigation; size checks still run before offering the download. Preserve frozen saved content, per-payload reuse and later-decision invalidation; callbacks must not call Streamlit, providers or models.
- **Market Brief:** fuller 5D/calendar 1M/3M macro/sector and synthesized news summaries use dated saved evidence; provider news collection is broader and deduplicated. These reports are interpretation, not certified forecasts.
- **Portfolio Lab:** Optimizer remains default; Manager settings/run controls belong inside **AI Portfolio Manager**, not the global sidebar. Existing bundles, exports and paid-action gates remain.
- Runtime entry points remain `app.py`, `src/langgraphagenticai/main.py` and `ui/streamlitui/loadui.py`; `portfolio_architect_app.py` is a supported focused launcher. Runtime source is `src/`; `tests/` and FMP samples are verification dependencies. Do not delete apparently unused engines, fixtures or historical design/QA records without checking consumers.
- [Repository layout](docs/REPOSITORY_LAYOUT.md) identifies active runtime, tests, references, roadmap/history and local-only artifacts. The experimental notebook lives under `docs/references/`; the historical cost plan lives under `docs/roadmap/`. Root `mcp_prompts.txt` and the FMP workbook remain retained reference inputs; reference scripts still resolve the root workbook. Private course material remains ignored and must never be force-added.

The latest dated verification and source-publication outcome belong in PLAN's current-status and final repository-sync entries. Clean offline tests are separate from the failed dependency audit and unverified hosted/clean-install/container gates; do not convert source synchronization into a deployment or production-readiness claim.

## User-improvement implementation cycle (2026-10-22)

- Read the [User Improvement Roadmap](docs/roadmap/user-improvements.md) for AX-01 through AX-10 specifications and acceptance criteria, and [PLAN's execution queue](PLAN.md#user-improvement-execution-queue-2026-10-22) for current scope, dependencies, R01 through R10 mapping and verification. AX IDs are local packages, not Jira keys or completion claims.
- Roadmap organization authorizes documentation preparation; implement the individual package/slice requested by the user. Reusable prompts in the specification do not activate themselves. Apply explicit ongoing session authorization without asking for redundant approval.
- Start each selected slice by checking current source/tests, Git status, saved-state contracts, provider/model call boundaries and dated evidence. Reuse existing financial audits, advisor construction and navigation contracts rather than duplicating them. Record the baseline and scoped plan before implementation.
- AX-01 presentation work may precede AX-05, but descriptive risk preferences must not become enforced-risk claims. AX-02 retains separate V1/V2 engines and pilot status; verification displays depend on AX-06. AX-04 begins with one metric family. AX-08 remains disabled until its data/risk/reuse and durable authenticated-job prerequisites are verified. Apply AX-10 security requirements throughout.
- Preserve all nine research workspaces and Data Validation, saved results, exports, advanced controls and explicit paid-action boundaries. Keep a changed input draft distinguishable from the last saved/generated result; avoid destructive resets and blanket engine migrations.
- Update the affected R entries and append dated delivery/verification evidence in PLAN for each meaningful slice. Keep detailed specifications in `docs/roadmap/`, completed feature reports in `docs/features/`, and user workflow changes in README. Use the feature-development-team skill when invoked; this section alone does not request sub-agents, ticket creation, publication or deployment.

## Current AX delivery boundaries and remaining work (2026-10-24)

The package sequence has local deliveries, not blanket roadmap completion. Before proposing or implementing follow-ups, read [PLAN's remaining-work queue](PLAN.md#remaining-implementation-and-verification-2026-10-24) and the [roadmap's detailed register](docs/roadmap/user-improvements.md#remaining-work-register-2026-10-24). PLAN owns dated status/evidence; the roadmap owns the detailed follow-up checklist and acceptance criteria. Keep this section as engineering guardrails rather than a competing completion ledger.

- AX-01 guided UX, AX-02 unified research controls and AX-09 shared executive memos are implemented locally. AX-01 parser expansion is an optional follow-up; manual amount/horizon confirmation is supported. Do not rebuild these surfaces or merge V1/V2 engines because broader financial/release criteria remain open.
- AX-03 is a bounded saved-evidence specialist pilot: fresh-evidence gap collection, measured evaluation and broader integration remain open. AX-04 contracts cover total-company net income, not every metric. Extend a named metric family/consumer with its own source/basis/currency/period tests before extending AX-06 claim coverage or AX-07 reuse.
- AX-05 supplies deterministic allocation checks, an optional historical-volatility gate and stress assumptions. ETF look-through/overlap, benchmark-relative/account-aware costs and broader Portfolio Lab policy adoption remain open. Descriptive preferences are not enforced future-loss promises.
- AX-06 checks selected explicit numerical claims; broader prose/table/formula/sector coverage and forward-target prerequisites remain open. AX-07 reuses qualified saved research only for session/credential-bound valuation earnings sensitivities; advisor/general authenticated durable reuse remains open. Do not promote a passed arithmetic/citation check into universal AI or source-truth verification.
- AX-08 provides disabled saved-model plans and an offline event/advisory ledger, not an active monitoring service. Do not enable schedules, earnings/estimate refresh, alerts, reassessment or advisory integration until data/risk/reuse, authenticated workers and entitlement gates are verified. Never add broker execution under this roadmap.
- AX-10 is not merely deployment. Local telemetry/FMP limits/session isolation and an encrypted checkpoint service exist. Real sign-in, authorized app-level durable save/resume, jobs, distributed budgets, complete model-stage telemetry and managed secret/key lifecycle remain open. A server-issued service test grant is not hosted authentication; no app currently creates or resumes these checkpoints automatically. Keep hosted/unknown runtime modes blocked and monitoring disabled until the relevant integration is verified.
- The 2026-10-24 installed-project audit reports 122 advisories across 19 packages and is a failed gate; see [sanitized findings](docs/roadmap/dependency-audit-2026-10-24.json). Triage/resolve compatible dependencies and repeat tests/audit; do not silence findings, assume exploitability, or remove retained functionality to claim readiness. `pip check` and passing offline tests are different checks from vulnerability auditing.
- Separate missing implementation from unexecuted checks: clean Python 3.11/3.12 installs, actual Docker/non-root/resource startup, remote CI, native PDF disk-save, authenticated concurrent users, protected live smoke and hosted backup/rollback still need evidence. Local graph isolation, service backup tests and the browser-served PDF check do not establish those broader gates. Use [release gate declarations](docs/roadmap/production-gates.json) and [runbook](docs/DEPLOYMENT.md); declarations cannot activate hosted mode.
- Latest recorded full offline inventory is **1413 passed in 700.87s** (V-20261024-REPOSITORY-SYNC), including current workflow/export/validation changes and deferred memo navigation repair. Cite its date/scope; do not imply a fresh run or complete acceptance from this number. This remaining-work documentation does not authorize additional code, team delegation, paid calls, external writes, source publication or deployment; apply actual subsequent user authorization.

## Product principles

AI Robo Advisor opens directly to portfolio construction (user-directed correction, 2026-10-20). Agent traders and synthetic-demo controls are removed from its active route and focused launcher; retained simulation engines/fixtures are legacy. Preserve cutoff, next-session execution, checkpoint/idempotence and bias-disclosure contracts when maintaining those engines. Current advisor research screens S&P 500 members plus curated ETFs using the Equity Report sector registry and shared Market Brief provider; it does not certify future outperformance or full audited Equity Report parity.

Every change must improve at least one of these outcomes without materially degrading the others:

1. **Trust:** Users can see where a fact came from, when it was retrieved, and whether it is stale or incomplete.
2. **Decision usefulness:** Screens lead to a clear next question, comparison, risk, or action—not just more data.
3. **Consistency:** The same ticker, metric, period, and source mean the same thing across every workspace.
4. **Speed:** Initial pages remain responsive, provider calls are bounded, and paid model calls never happen because of an ordinary Streamlit rerun.
5. **Resilience:** One provider or model failure must not erase valid results from other sources.
6. **Auditability:** AI conclusions remain distinguishable from provider facts and deterministic calculations.
7. **Safety:** The app is research software, not personalized financial advice. Credentials, prompts, logs, downloads, and session state must not leak secrets.

## Current product surfaces

Changes must account for the complete application, not only the active page:

- **Market Brief (Introduction identity):** explicit-refresh dashboard, macro/sector ETF heatmap and metrics, constituent ticker, news and separate market/news AI briefings, dashboard follow-ups, daily ticker/index/ETF chart and technical indicators/AI. Active daily-chart ranges are 1M/3M/1Y/3Y/5Y/10Y. Legacy snapshot helpers and shared eight-horizon history support do not prove that every old screen remains reachable; document active routing.
- **Top Movers:** explicit-refresh capped-screen leaders/laggards over 1D/5D/1M/ytd, Top50/filtered Top10%, sector concentration/participation, selected company quote/history/news, explicit news AI, analyst consensus/targets, social activity and supported company handoffs. Screen breadth is not whole-market breadth.
- **Research:** LangGraph finance chat with FMP and Marketaux tools, editable explicit-submit drafts and preserved threads; opt-in Guided research prepares a one-company plan and runs allowlisted evidence tools with exact cited-field validation, partial-result recovery and saved session reuse.
- **Equity Report:** sector-aware company/peer analysis, scoring, charts, recommendations, and PDF/Excel/CSV exports.
- **AI Valuation:** one explicit Generate creates three conditional AI growth/multiple cases; prices are calculated locally. All sectors and unknown classifications have an earnings framework where usable positive annual inputs exist, with financial P/B preference and earnings fallback, explicit proxy/specialist limitations, saved-case reuse, local edits and horizon recalculation.
- **Stock Screener:** FMP universe filtering, metric enrichment, optional post-filters, CSV and company chart handoff.
- **Portfolio Lab:** Optimizer is the default tab; AI Portfolio Manager remains the second tab. Portfolio Ideas was removed from active routing on2026-10-19 at the user's request; its source/tests are retained as legacy, with no entry-point reload hook. Prompt-led portfolio construction lives on **AI Robo Advisor**; manual/replay trader workflows are retained legacy source, with separate session state and explicit provider/model actions. `Live_Agent_Traders/` is ignored local course/reference material, not an application dependency.
- **Deep Research Standard format:** one-shot evidence collection/planning/report generation, shared quarterly financial audit and sector comparisons, news, recovery, separate evidence/notebook views, question-aware executive sections, clean reader prose, optional committee, saved follow-ups, PDF/memo/evidence/comparison downloads and saved brief/sensitivities. A saved committee decision belongs in the PDF.
- **Deep Research Low cost format (V2):** separate cost pilot with the shared financial audit, stage-specific routing, bounded sector-aware contexts, mechanical validation, saved generation time/age, session reuse, shared saved investment brief/earnings-multiple scenarios and optional quick/full decisions. Keep workflow-specific V1 behavior separate when modifying the pilot.

## Delivered foundations through 2026-10-10

These are scoped deliveries, not completion of the broad R01-R10 roadmap. Preserve their contracts when extending the product; consult PLAN verification records and feature-team reports for exact evidence.

- **AAFA-6, both research versions:** fresh income/cash-flow TTM uses four validated consecutive fiscal quarters; balance facts use independently latest quarterly snapshots. ROE/ROA use matched beginning/end balances, annual CAGR and forward annual estimates remain separate, and unavailable specialist metrics stay missing. `quarterly_data.py`, `research_metrics.py` and `research_workflow.py` share collection/calculation; `sector.py` supplies Equity Report's canonical applicability. Comparisons, PDFs and model contexts respect per-company sectors. Metric audits retain units, currency, dates, formulas and actual source inputs; never replace missing debt/cash with zero or substitute provider TTM/annual facts silently.
- **Research evidence and saved results:** standardized standalone-quarter assumptions and unknown price/currency meanings must remain disclosed. Serper retrieval time is separate from publication time and requested lookback. Legacy saved financial values remain readable without silent recalculation or provider/model calls; old-evidence recovery requires explicit acknowledgement. V2 generation timestamps describe saved-result operations, not evidence freshness. Unverified cross-workspace financial packets remain disabled. `model_packets.py` bounds complete serialized contexts while retaining substantive sector-projected evidence and explicit omissions.
- **AAFA-7, Introduction charts:** `providers/symbol_history.py` shares market/company retrieval; `market_history.py` remains a compatibility wrapper. Both charts offer 1D/5D/1M/3M/1Y/3Y/5Y/10Y. Short ranges select one/five observed trading dates; long ranges use daily bars. Fallback replaces a whole series, with no provider stitching. Report actual coverage, source, adjustment basis, timezone, currency/units, as-of and retrieval time; unknown FMP adjustment/timezone and complete-session coverage are not inferred. Future aware timestamps are rejected against the UTC instant; unknown-zone naive records use the documented UTC calendar-date policy, with same-day timing unverifiable.
- **Technical analysis:** `technical_analysis/{indicators,evidence,agent}.py` separates local SMA/EMA/Wilder RSI/MACD/Bollinger arithmetic, evidence fingerprints and bounded structured AI. `ui/technical_chart.py` renders adjustable bar windows, warmup, separate oscillator panels and period-aware provider wall-clock axes with original timestamp tooltips. Window units are observed bars, not calendar days. Technical AI requires an explicit action and validates identity/evidence references; ordinary controls reuse data and do not call models. Preserve prior results with mismatch/failure notices and disable analysis for invalid settings. Schema/citation checks do not certify every numerical claim in model prose.

- **P01 / AAFA-8, connected company context:** normalized metadata-only handoffs connect Introduction/Top Movers to Research, Equity Report and both Deep Research versions, and Screener to Introduction. Incoming Research requests are editable drafts requiring explicit submit. Configuration/navigation preserve chat and saved results; changed chat settings require a visible New thread action. Deterministic workspaces are not globally blocked by missing OpenAI; individual AI actions enforce dependencies. Portfolio/Compare handoffs remain open.
- **P02 / AAFA-9, terminal presentation:** shared executive cards, workspace headers and evidence-status rows distinguish source/retrieval dates, partial evidence and unavailable metadata. Configuration readiness and page-render time do not establish evidence freshness; remaining pages still need universal data-quality adoption.
- **P03 / AAFA-10, Guided research:** explicit Prepare/Run actions allow at most two model attempts and three tool dispatches, with no model retries and bounded packets. Quote/profile has independent requests; shared safe FMP retries can add HTTP attempts. Annual FY evidence stays distinct from audited TTM; zero remains valid and failed news retains successful facts. Exact field/currency/date/basis citations are validated, while AI prose semantics remain unverified. Unknown-price acknowledgement cannot guarantee a dollar ceiling. Reruns/downloads reuse session results without additional calls.
- **P04 / AAFA-11, saved brief/scenarios:** V1/V2 share immutable saved narrative excerpts and deterministic Bull/Base/Bear total equity sensitivities. Eligibility requires resolvable audited four-quarter earnings, dated cap, explicit compatible quote currency, sector applicability and supported freshness; legacy/inferred-currency/unsupported cases stay readable with unavailable scenarios. Defaults are user assumptions, not forecasts. Preserve safe bounded JSON/CSV provenance and original reports without recollection or model calls.
- **P05 / AAFA-12, local release automation:** Python3.11/3.12 CI definitions use constrained installs, pip check, guarded offline tests, compile/import and safe version/JUnit artifacts. Direct manifests agree, newspaper4k is the sole newspaper namespace owner, and NumPy constraints respect Python versions. Runtime copies app.py/src only; a separate derived image adds verification tests/samples. Keep TLS verification enabled and optional public CA bundles in BuildKit secrets. Local source is finished; AAFA-12 remains In Progress for unverified release gates.

## Current delivered boundaries (2026-10-18)

- **Executive research delivery:** production Standard/Low cost workflows use a single-pass report path without mandatory interpretive review/rewrite or user approval. Optional committees remain explicit decisions. Preserve full retained reports and evidence on failure/recovery; never silently replace a substantial saved draft with a generic overview. Keep supporting references/audits accessible outside reader-facing prose, and do not present missing evidence as verified recommendations.
- **Executive exports:** question-aware sections and safe presentation cleanup apply to reader reports; saved committee/quick decisions are included in the research PDF when available. Export/download must not recollect evidence or call models. A committee added later requires a new PDF download.
- **Conditional valuation:** use the disclosed sector framework, source IDs, formula and exact dated projection anchor. REIT/Materials/unknown sectors can use provisional P/E; financials prefer usable common-book P/B and independently fall back to earnings when book evidence fails. Missing reported diluted EPS can use a labeled same-FY net-income/diluted-share proxy; never replace explicit zero/negative/invalid EPS with a positive proxy or mix proxy/reported-EPS growth histories. Consensus EPS is context only for that proxy. Do not fabricate FFO/AFFO, normalized mid-cycle earnings, regulatory capital, peer medians or NAV. The saved brief's audited-TTM total-equity sensitivities have a separate stricter contract and are not future per-share AI Valuation targets.
- **Market ribbon:** existing ribbon routes share five-minute credential-scoped actual-index quotes; at most a primary index batch and one legacy fallback, plus shared bounded transport retries. Preserve original timestamps and visibly mark retained/stale/undated quotes. Percentage-point aliases and explicit previous-close arithmetic preserve zero/missing distinctions. All five indices remain visible on mobile. This small quote refresh is independent of paid AI and the explicit-refresh full Market Brief dashboard.
- **Repository boundaries:** current app source is under `src/` with `app.py`; obsolete AI_Valuation_Tab/partial_redesign uploads and unused crew_ai tutorial were archived outside the Git tree. The active CrewAI committee remains in the app. Preserve canonical docs/redesign specifications/images/QA records, contract fixtures and user outputs; do not reintroduce obsolete shells as active code.

Historical2026-10-18 full offline inventory (current inventory is in PLAN.md): **974 tests passed in337.71s**, installed project Python3.12.0 / pytest9.1.1 / Streamlit1.61.1 (V-20261018-IDEAS-SCREEN-FIRST-FINAL). Includes14 new local-screen/reuse/optional-AI cases beyond960; focused67, final compilation/imports, app health and guarded incomplete-response browser recovery passed with scopes in PLAN. Valid optional refinement is unit-tested, not live-model certified. Earlier real-provider12/12 collection and historical browser checks retain their dates. Working tree only; no publication/deployment or broad financial-correctness guarantee follows.


**Open release gates:** local Docker builds failed during intercepted PyPI transport (initial certificate trust, then `InvalidChunkLength`); no runtime image was produced. Clean Python3.11/3.12 installs, runtime non-root startup/health, derived-image workflow and remote GitHub CI are unverified. Hosting target, protected preview/access, hosted smoke and rollback rehearsal remain pending. No live entitlement/financial freshness/model-quality guarantee, clean-install certification or deployment follows from offline checks. Current source publication does not establish a hosted release; future commit/push and deployment require explicit authorization. Consult current Git history for revisions after the dated publication above. See [deployment runbook](docs/DEPLOYMENT.md) and the current PLAN verification entry.

## Architecture requirements

### 1. Separate presentation, domain logic, and providers

- Streamlit files should orchestrate controls and rendering; they should not become new data clients.
- New provider access belongs under a shared provider/service layer, not inside a page module.
- Deterministic financial calculations belong in domain modules with unit tests.
- AI prompts and model routing must remain separate from data retrieval and display formatting.
- Do not add more functionality to oversized modules when a focused extraction is possible. In particular, avoid expanding `equity_report_tab.py`, `decision_engine.py`, and `data_sources.py` without first identifying an appropriate module boundary.

### 2. Use one canonical security and metric model

- Normalize symbols to uppercase and validate them before network calls.
- Every market or financial value should support: value, unit/currency, period or as-of date, provider, retrieval time, and status.
- Do not compare TTM, annual, quarterly, forward, and point-in-time values without labeling the basis.
- Keep price return distinct from total return.
- Preserve zero separately from missing data.
- Cross-page handoffs should use a typed shared context rather than unrelated session-state keys.

### 3. Centralize provider behavior

- Reuse one FMP client with a shared HTTP session, bounded timeouts, retry policy, response validation, and normalized error types.
- Treat yfinance as a fallback or specifically labeled source; never silently mix it with FMP in the same series.
- News records from Serper and Marketaux must be normalized into one schema and deduplicated by canonical URL/title/time.
- Cache TTL must match the data type: quotes/intraday, news, profiles, statements, and historical series must not share an arbitrary TTL.
- Never cache an API key in persisted output or include it in cache diagnostics.
- Partial provider failures must return structured warnings and preserve successful records.

### 4. AI output must be grounded and structured

- AI summaries must receive dated evidence, not unlabeled raw blobs.
- Material factual claims should link to evidence IDs or source records when the workflow supports citations.
- Recommendations must disclose the evidence date, missing inputs, uncertainty, key risks, and thesis invalidation conditions.
- Use Pydantic or equivalent schemas for structured model outputs; do not depend on fragile prose parsing for critical decisions.
- Validate figures, tickers, recommendation enums, weights, and citations deterministically before display.
- The UI must label provider facts, calculated metrics, and AI interpretation distinctly.
- Model calls require explicit user action. Streamlit reruns, downloads, tab changes, or formatting changes must not trigger a paid call.

### 5. Keep workflows connected

- A selected company should be reusable across Introduction, Top Movers, Research, Equity Report, Deep Research, and Portfolio Lab.
- Page-to-page actions must carry the ticker and an explicit intent, such as `analyze`, `compare`, `deep_research`, or `add_to_portfolio`.
- Preserve completed work when users navigate between pages.
- Avoid hidden resets. If a model/use-case change resets chat context, explain it or provide a visible new-thread action.

## User-experience requirements

- Follow the existing Axiom terminal design system in `ui/app_shell.py`.
- Reuse shared cards, typography, spacing, status, empty-state, and source components instead of adding isolated page CSS.
- Every data-heavy view needs loading, empty, partial-data, stale-data, provider-error, and recovery states.
- Show an **as-of time** and provider near the data it qualifies—not only in the footer.
- Use concise executive summaries first; place raw data and diagnostics behind tabs or expanders.
- Tables must remain scannable at common laptop widths and usable on narrow screens.
- Color cannot be the only indicator of gains, losses, risk, or status.
- All external links must be safe, descriptive, and open without exposing credentials.
- Research output should use consistent headings, bullets, tables, citations, and source blocks.

## Financial correctness requirements

- Use adjusted prices when calculating comparable historical returns unless the UI explicitly states otherwise.
- Validate portfolio weights sum to 100% within tolerance after constraints.
- Report the risk-free-rate assumption, benchmark, sampling window, and annualization convention for portfolio metrics.
- Avoid forward-looking statements presented as facts.
- Surface currency mismatches before aggregating or comparing values.
- Do not infer growth from mismatched fiscal periods.
- Make survivorship bias, missing history, stale quotes, and provider coverage limitations visible.
- Every recommendation or score must be reproducible from saved inputs or explicitly marked as model-derived.

## Reliability, security, and privacy requirements

- API keys may come from environment variables, Streamlit secrets, or password inputs. Never render, log, export, or commit them.
- Sanitize provider/model errors before showing them to users.
- Apply timeouts to every network and model call; retries must be bounded and limited to safe transient failures.
- Do not use broad `except Exception` without either logging context or returning a structured failure state.
- Downloads and saved research must be checked for embedded credentials and unsafe URLs.
- External HTML rendered with `unsafe_allow_html=True` must escape provider-controlled values.
- Keep `.env` ignored and maintain `.env.example` with key names only.

## Performance and cost requirements

- Set measurable budgets for initial render time, provider calls, model calls, prompt size, output size, and estimated cost.
- Batch provider requests where supported and cap concurrency.
- Cache evidence separately from AI narratives so users can regenerate presentation without recollecting data.
- Expose cache/freshness status and allow an explicit force-refresh.
- Track model usage by stage, including Deep Research and CrewAI.
- Provide an economical default path; expensive multi-agent or extended workflows remain opt-in.

## Testing requirements

Every behavioral change must add or update tests at the lowest useful level.

Required coverage targets (current coverage is recorded in PLAN.md; these are not claims of completed coverage):

- Unit tests for calculations, normalization, formatting, validation, and routing.
- Contract tests with recorded/synthetic responses for FMP, Marketaux, Serper, and yfinance adapters.
- Streamlit interaction tests for each primary workspace and cross-page handoff.
- Agent tests for tool selection, structured output, citation validation, recovery, and cost limits.
- Integration smoke test for app import, startup, health endpoint, and one representative workflow.
- Export tests for PDF, Excel, CSV, and JSON outputs.

Tests must not consume paid API credits. Live-provider smoke checks should be explicit, optional, and clearly marked.

## Required verification before handoff

For code changes, agents must:

1. Inspect the working tree and preserve unrelated user changes.
2. Run focused tests for the modified area.
3. Run the full test suite when shared infrastructure or routing changes.
4. Compile/import affected Python modules.
5. Start Streamlit and verify `/_stcore/health` for app-level changes.
6. Exercise the changed interaction in a browser when browser tooling is available.
7. Report what was tested, what was not tested, and any remaining risk.

## Documentation requirements

- Keep `README.md` as a nontechnical executive how-to: numbered steps using active UI labels, examples, interpretation, exports and recovery for every reachable workspace. Update it when navigation, access requirements or workflows change. Do not add architecture, build history, test inventories, code implementation details or release-engineering instructions to the user guide. Keep contributor instructions here and engineering evidence in PLAN/docs.
- Update `PLAN.md` when a milestone is completed, materially rescoped, or reordered.
- Keep `DEEP_RESEARCH.md` focused on that subsystem; avoid duplicating global architecture guidance.
- Record architectural decisions that affect multiple workspaces in a short ADR or clearly labeled design note.
- Use UTF-8 and remove mojibake from user-visible strings and documentation.

## Maintaining the living status record

For each meaningful delivery, update PLAN.md in the same change:

1. Update the affected workspace and roadmap entry using stable IDs R01-R10. Mark only delivered subitems complete; retain unmet acceptance criteria.
2. Append a delivery entry with date, user outcome, implementation approach, source/test paths, commit or working-tree status, and remaining work.
3. Record verification separately: command, interpreter/dependency versions, result, test scope, mocks versus live services, and checks not performed. Never present earlier browser evidence as a newly run check.
4. Keep test totals and verification scope in PLAN's dated inventory. Keep README focused on product use rather than engineering verification totals. A passing suite does not establish coverage of untested workflows.
5. Retain historical review and optimization notes as dated records; link the current status instead of treating old proposals or unchecked lists as implementation truth.
6. Do not mark a roadmap milestone complete until its acceptance criteria and the definition of done below are satisfied.

Use the project's installed Python 3.11/3.12 environment. For this src-layout repository, the core offline commands from the repository root are:

```powershell
$env:PYTHONPATH = (Resolve-Path "src").Path
python -m pytest -q
python -m compileall -q app.py src
python -c "import app; import langgraphagenticai.main"
```

Use pytest for the full inventory; unittest discovery alone misses pytest-style tests. Startup, health, browser interactions, exports, and clean-install checks require their own evidence. Follow [the release-check commands](.agents/skills/axiom-release-check/references/verification-commands.md) for the scope of the change. Documentation-only edits need document/diff validation; do not imply that they required or received a new deployment.

## Definition of done

A feature is done only when:

- It has a clear user outcome and acceptance criteria.
- Live, stale, missing, partial, and failed data states are handled.
- Source, timestamp, units, currency, and period are visible where relevant.
- AI claims are grounded and validation failures are disclosed.
- Cross-page behavior and session state are intentional.
- Tests pass and no paid calls occur during tests.
- Relevant documentation is updated.
- No credentials, unrelated changes, temporary files, or debug artifacts are introduced.

## Priority order

Unless the user explicitly overrides it, work in this order:

1. Correctness, security, and data provenance.
2. Reliability and recovery.
3. Cross-workspace product cohesion.
4. Test coverage and observability.
5. Performance and cost.
6. Visual polish.
7. New providers or net-new feature breadth.

See `PLAN.md` for the current 10-step improvement roadmap.
