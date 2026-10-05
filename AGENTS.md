# AGENTS.md — Axiom Research Engineering Requirements

## Purpose

This file defines how coding agents and contributors must work on Axiom Research. The product is a Streamlit financial-research application that combines live market data, company research, screening, portfolio analytics, LangGraph chat, Deep Research, and optional multi-agent investment decisions.

The goal is not to add the most features. The goal is to make the existing capabilities trustworthy, connected, fast, explainable, and useful for real investment research.

## Implementation orientation (updated 2026-10-01)

These engineering requirements are the target standard, not a claim that every requirement is already implemented. [PLAN.md](PLAN.md) is the dated source of truth for implementation status, delivery history, verification evidence, and remaining work. Do not infer completion from a module name or a passing test count.

The sidebar currently exposes seven main workspaces plus the isolated **Deep Research V2 cost pilot**. The application entry points are `app.py`, `src/langgraphagenticai/main.py`, and `src/langgraphagenticai/ui/streamlitui/loadui.py`.

| Area | Implementation boundary |
| --- | --- |
| Shared presentation | `src/langgraphagenticai/ui/app_shell.py`; page modules orchestrate Streamlit controls |
| Provider transport | `src/langgraphagenticai/providers/`; shared FMP REST transport and bounded OpenAI clients exist, but adapters and metadata are not yet uniform across every provider |
| Financial/domain logic | Company snapshot calculations, Equity Report scoring, and `src/langgraphagenticai/portfolio_manager/`; use focused domain modules for new calculations |
| Research chat | LangGraph graph, nodes, and tools; thread state is session-backed |
| Deep Research | `src/langgraphagenticai/deep_research/`; V1 orchestration/recovery and isolated V2 routing/validation |
| Verification | `tests/`; consult the dated inventory in PLAN rather than assuming full workspace or export coverage |
| Contributor skills | `.agents/skills/`; [project skill guide](docs/PROJECT_SKILLS.md) describes all thirteen skills and invocation, including GitHub commit/push |

Existing ticker handoffs and saved page results use session-state conventions. A canonical typed `ResearchContext`, universal provenance records, and universal freshness UI remain roadmap work. V2 is a pilot; its helpers and fixtures do not establish end-to-end financial accuracy or measured cost savings.

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

- **Introduction:** live market overview, company search, price/fundamental snapshot, news, and AI summary.
- **Top Movers:** five-trading-day leaders and laggards, sector breadth, Serper news, and company handoff.
- **Research:** LangGraph finance chat with FMP and Marketaux tools, structured tables, and formatted analyst output.
- **Equity Report:** sector-aware company/peer analysis, scoring, charts, recommendations, and PDF/Excel/CSV exports.
- **Stock Screener:** FMP universe filtering and metric enrichment.
- **Portfolio Lab:** historical optimizer plus hybrid AI portfolio manager, constraints, evidence, and reporting.
- **Deep Research:** evidence collection, planning, report generation, review/recovery, citations, downloads, and optional CrewAI committee.
- **Deep Research V2:** separate cost pilot with stage-specific routing, compact contexts, mechanical validation, saved-session reuse, and optional quick/full decisions. Preserve V1 behavior when changing the pilot.

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
