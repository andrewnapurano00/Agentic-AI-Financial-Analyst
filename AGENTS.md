# AGENTS.md — Axiom Research Engineering Requirements

## Purpose

This file defines how coding agents and contributors must work on Axiom Research. The product is a Streamlit financial-research application that combines live market data, company research, screening, portfolio analytics, LangGraph chat, Deep Research, and optional multi-agent investment decisions.

The goal is not to add the most features. The goal is to make the existing capabilities trustworthy, connected, fast, explainable, and useful for real investment research.

## Implementation orientation (updated 2026-10-10)

These engineering requirements are the target standard, not a claim that every requirement is already implemented. [PLAN.md](PLAN.md) is the dated source of truth for implementation status, delivery history, verification evidence, and remaining work. Do not infer completion from a module name or a passing test count.

The sidebar currently exposes seven main workspaces plus the isolated **Deep Research V2 cost pilot**. The application entry points are `app.py`, `src/langgraphagenticai/main.py`, and `src/langgraphagenticai/ui/streamlitui/loadui.py`.

Module paths abbreviated below are relative to `src/langgraphagenticai/`; repository-level release/test paths are explicit.

| Area | Implementation boundary |
| --- | --- |
| Shared presentation | `ui/app_shell.py`, `ui/workspace_presentation.py` and `ui/workspace_handoff.py`; shared terminal headers/evidence states and bounded navigation adapters, while page modules orchestrate controls |
| Provider transport | `src/langgraphagenticai/providers/`; shared FMP REST transport, bounded OpenAI clients and symbol-aware Introduction history exist, but adapters and metadata are not uniform across every provider |
| Financial/domain logic | Company snapshots, Equity Report scoring, `portfolio_manager/`, audited research calculations in `deep_research/{quarterly_ttm,research_metrics}.py`, and configurable chart calculations in `technical_analysis/`; preserve each metric basis |
| Research | LangGraph chat remains session-backed; `research/{guided_workflow,guided_schemas}.py`, `providers/guided_research.py` and `ui/guided_research_tab.py` implement the opt-in bounded one-company Guided plan/run workflow |
| Saved investment brief | `analysis/{investment_brief,scenarios}.py` and `ui/investment_brief.py`; shared V1/V2 saved narrative excerpts, audited earnings-multiple sensitivities and bounded provenance exports |
| Company navigation | `state/research_context.py` supplies metadata-only typed identity/intent; `ui/workspace_handoff.py` applies supported session handoffs without transferring financial packets |
| Deep Research | `src/langgraphagenticai/deep_research/`; V1/V2 orchestration stays separate while fresh financial collection, sector applicability, audit contracts and bounded model packets are shared |
| Verification/release | `tests/conftest.py` guards offline collection/tests; `.github/workflows/offline-release.yml`, `Dockerfile.verify` and `scripts/release_inventory.py` define release gates/artifacts. Consult PLAN and `docs/DEPLOYMENT.md` for executed checks and unverified gates |
| Contributor skills | `.agents/skills/`; [project skill guide](docs/PROJECT_SKILLS.md) describes all thirteen skills and invocation, including GitHub commit/push |

P01 delivers a bounded typed, metadata-only `ResearchContext` for supported company handoffs; saved page results remain session-backed. Universal financial provenance, complete Portfolio/Compare handoff adoption and universal freshness UI remain roadmap work. Navigation metadata is not financial evidence, and unverified financial-packet bridges remain disabled. V2 is a pilot; its helpers and fixtures do not establish end-to-end financial accuracy or measured cost savings.

## Product principles

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

- **Introduction:** live market overview, company snapshot/news, eight price-chart horizons, configurable technical indicators, calculated technical summary, and explicit company/technical AI analysis.
- **Top Movers:** five-trading-day leaders and laggards, sector breadth, Serper news, and company handoff.
- **Research:** LangGraph finance chat with FMP and Marketaux tools, editable explicit-submit drafts and preserved threads; opt-in Guided research prepares a one-company plan and runs allowlisted evidence tools with exact cited-field validation, partial-result recovery and saved session reuse.
- **Equity Report:** sector-aware company/peer analysis, scoring, charts, recommendations, and PDF/Excel/CSV exports.
- **Stock Screener:** FMP universe filtering and metric enrichment.
- **Portfolio Lab:** historical optimizer plus hybrid AI portfolio manager, constraints, evidence, and reporting.
- **Deep Research:** evidence collection, shared quarterly financial audit and sector-aware comparisons, Serper news coverage, planning, reports, recovery, citations, downloads, saved investment brief/earnings-multiple scenarios and optional CrewAI committee.
- **Deep Research V2:** separate cost pilot with the shared financial audit, stage-specific routing, bounded sector-aware contexts, mechanical validation, saved generation time/age, session reuse, shared saved investment brief/earnings-multiple scenarios and optional quick/full decisions. Keep workflow-specific V1 behavior separate when modifying the pilot.

## Latest delivered boundaries (2026-10-10)

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

Latest measured offline inventory: **430 passing tests in597.19s**, independently run in the installed project Python3.12.0 environment (V-20261010-P05; pytest9.1.1 / Streamlit1.61.1). The P05 run also passed focused checks, compile/import, installed pip check, fresh app/harness health and a synthetic actual-main browser journey with two isolated sessions and zero external calls. Eight-route cases establish readiness/rendering, not exhaustive behavior. Earlier P01-P04 browser/export evidence retains its original dates. No new checks follow from documentation updates.

**Open release gates:** local Docker builds failed during intercepted PyPI transport (initial certificate trust, then `InvalidChunkLength`); no runtime image was produced. Clean Python3.11/3.12 installs, runtime non-root startup/health, derived-image workflow and remote GitHub CI are unverified. Hosting target, protected preview/access, hosted smoke and rollback rehearsal remain pending. No live entitlement/financial freshness/model-quality guarantee, clean-install certification or deployment follows from offline checks. P01-P05 are local working-tree implementations, not a hosted release; commit/push and deployment require explicit authorization. See [deployment runbook](docs/DEPLOYMENT.md) and the current PLAN verification entry.

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

- Update `README.md` whenever navigation, setup, providers, required keys, or workflows change.
- Update `PLAN.md` when a milestone is completed, materially rescoped, or reordered.
- Keep `DEEP_RESEARCH.md` focused on that subsystem; avoid duplicating global architecture guidance.
- Record architectural decisions that affect multiple workspaces in a short ADR or clearly labeled design note.
- Use UTF-8 and remove mojibake from user-visible strings and documentation.

## Maintaining the living status record

For each meaningful delivery, update PLAN.md in the same change:

1. Update the affected workspace and roadmap entry using stable IDs R01-R10. Mark only delivered subitems complete; retain unmet acceptance criteria.
2. Append a delivery entry with date, user outcome, implementation approach, source/test paths, commit or working-tree status, and remaining work.
3. Record verification separately: command, interpreter/dependency versions, result, test scope, mocks versus live services, and checks not performed. Never present earlier browser evidence as a newly run check.
4. Keep test totals in PLAN's dated inventory; update README's verification summary when that inventory changes. A passing suite does not establish coverage of untested workflows.
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
