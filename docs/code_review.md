# Comprehensive Code Review

Reviewed: 2026-09-27
Scope: the complete current repository, including tracked code, the working-tree delta from `HEAD`, and relevant untracked source, tests, deployment files, and documentation. Generated dependencies, caches, and CrewAI sample output artifacts were not treated as application source.

## Executive summary

The repository has a promising evidence-oriented Deep Research implementation and several good safety practices: ticker validation in Deep Research, credential redaction in its exports, bounded FMP MCP calls, explicit user actions for the expensive research flow, adjusted Yahoo prices in the optimizer, and useful recovery tests.

The review nevertheless found two high-severity defects and several medium-severity reliability, correctness, and maintainability risks. The most urgent issue is that the portfolio constraint validator can return weights that still violate its advertised position and sector caps. The other high-severity issue is credential exposure: FMP keys are embedded in request URLs, while raw exception text is retained, logged, and displayed in multiple paths.

Finding count:

- High: 2
- Medium: 7
- Low: 1

## Remediation status

Implemented on 2026-09-27:

- Findings 1–10 have corresponding code, test, dependency, or documentation changes in the working tree.
- Portfolio allocation now uses cap-aware redistribution and residual cash; regression tests reproduce the original zero-weight failure case.
- Provider/model errors and structured logs use centralized credential redaction, and raw user prompts are no longer logged.
- Direct OpenAI clients share bounded timeout/retry defaults.
- Introduction TTM figures require consecutive, deduplicated quarterly periods with a consistent currency.
- Top Movers returns explicit partial coverage and provider warnings.
- FMP REST access used by current workspaces routes through a shared session/retry/error adapter.
- Development dependencies and deployment constraints are documented and wired into Docker.
- Duplicate active Equity Report function names were eliminated; legacy implementations are explicitly named instead of silently shadowing runtime functions.
- README, PLAN, and ignore rules now reflect the seven-workspace app and local artifact policy.
- Equity Report now offers an explicit, structured CrewAI best-buy debate that is bound to the saved scorecard fingerprint and rejects out-of-universe recommendations.
- Validation after remediation originally completed with 69 tests passing; subsequent feature verification is recorded in the implementation handoff.

## Findings

### 1. High — Constraint normalization can reintroduce cap violations

Affected code: `src/langgraphagenticai/portfolio_manager/constraint_validator.py:20`, `src/langgraphagenticai/portfolio_manager/constraint_validator.py:33`, `src/langgraphagenticai/portfolio_manager/constraint_validator.py:36`, `src/langgraphagenticai/portfolio_manager/constraint_validator.py:39`, `src/langgraphagenticai/portfolio_manager/constraint_validator.py:63`, `src/langgraphagenticai/portfolio_manager/constraint_validator.py:66`, and `src/langgraphagenticai/portfolio_manager/constraint_validator.py:109`.

When an overweight position is clipped and every underweight destination currently has zero weight, `room_total` is zero and redistribution stops. The function then normalizes the clipped vector back to the target sum, increasing the overweight position above the cap again. Sector caps have the same failure mode. The final normalization at lines 109–110 can compound the problem.

This was reproduced directly in the project virtual environment:

```text
_apply_position_caps([1.0, 0.0, 0.0], cap=0.4, target=1.0) -> [1.0, 0.0, 0.0]
_apply_sector_caps(sectors=[A, A, B], weights=[1.0, 0.0, 0.0], cap=0.5, target=1.0) -> [1.0, 0.0, 0.0]
```

The generated recommendation can therefore claim that validation was applied while still exceeding hard limits, directly affecting trade values and portfolio recommendations.

Smallest correction direction: replace proportional-only redistribution with a bounded allocation algorithm that includes zero-weight eligible positions, never normalize above remaining capacity, and return explicit residual cash when the constraints are infeasible. Add invariant tests asserting every position/sector is within tolerance and securities plus cash sum to 100%.

### 2. High — Provider and model exceptions can expose API keys and sensitive request data

Affected code: `src/langgraphagenticai/tools/fmp_mcp_client.py:42`, `src/langgraphagenticai/tools/fmp_mcp_client.py:51`, `src/langgraphagenticai/tools/fmp_mcp_client.py:192`, `src/langgraphagenticai/ui/company_snapshot.py:32`, `src/langgraphagenticai/ui/company_snapshot.py:112`, `src/langgraphagenticai/ui/top_movers_tab.py:72`, `src/langgraphagenticai/ui/introduction_tab.py:216`, `src/langgraphagenticai/main.py:415`, `src/langgraphagenticai/main.py:450`, and `src/langgraphagenticai/utils/logging_utils.py:84`.

FMP credentials are placed in URL query strings. HTTP and transport exceptions commonly include the prepared URL; those exception strings are copied into result envelopes, session-visible errors, AI-facing context, and logs without a common sanitizer. Model errors are also rendered verbatim. In addition, `main.py:429-435` logs the first 500 characters of every user prompt, which can capture account data, portfolio details, or credentials pasted by mistake.

A failed provider call can therefore disclose a paid API key to the browser, application logs, debug output, or a later model prompt. This conflicts with the repository requirement that keys, prompts, logs, and downloads not leak secrets.

Smallest correction direction: introduce one redaction/sanitization utility at the provider boundary; strip query secrets and known credential patterns before storing, logging, rendering, or sending errors to a model. Log stable error codes and provider metadata instead of raw exceptions, and make prompt-content logging opt-in with redaction.

### 3. Medium — Most OpenAI calls have no explicit timeout or bounded retry policy

Affected examples: `src/langgraphagenticai/ui/equity_report_tab.py:5508`, `src/langgraphagenticai/ui/equity_report_tab.py:5550`, `src/langgraphagenticai/portfolio_manager/llm_allocator.py:16`, `src/langgraphagenticai/portfolio_manager/llm_allocator.py:36`, `src/langgraphagenticai/portfolio_manager/agentic_committee.py:194`, `src/langgraphagenticai/portfolio_manager/agentic_committee.py:195`, `src/langgraphagenticai/portfolio_manager/portfolio_reporting.py:368`, and `src/langgraphagenticai/ui/ai_portfolio_manager_tab.py:357`.

The centralized LangChain wrapper has a timeout, and Deep Research implements bounded stages, but the direct OpenAI clients used by Equity Report and Portfolio Lab do not. A stalled connection can hold a Streamlit run indefinitely, provide no recovery boundary, and create ambiguous retry/cost behavior. Several call sites also expose the raw failure string afterward.

Smallest correction direction: centralize direct model construction with explicit connect/read/overall timeouts, bounded safe retries, consistent sanitized failures, and usage/cost capture. Add timeout and fallback contract tests for each AI workflow.

### 4. Medium — Company “TTM” metrics can combine incompatible or duplicated periods

Affected code: `src/langgraphagenticai/ui/company_snapshot.py:118`, `src/langgraphagenticai/ui/company_snapshot.py:128`, `src/langgraphagenticai/ui/company_snapshot.py:134`, and `src/langgraphagenticai/ui/company_snapshot.py:150`.

The Introduction company snapshot labels revenue, free cash flow, and margins as TTM by summing the first four provider rows. It does not sort, deduplicate, verify consecutive quarters, verify period type, check currency, or detect gaps. If FMP returns annual rows, duplicate amended filings, an incomplete latest quarter, or a different ordering, the displayed TTM figures and growth rates are wrong while still presented as authoritative.

Smallest correction direction: normalize and validate period/currency metadata, sort by reporting date, deduplicate fiscal periods, require four consecutive quarters, and otherwise label the basis as incomplete or unavailable. Reuse the stricter period-aware domain logic already present in Deep Research instead of rebuilding it in the UI module.

### 5. Medium — Top Movers silently treats partial quote-change coverage as a complete universe

Affected code: `src/langgraphagenticai/ui/top_movers_data.py:42`, `src/langgraphagenticai/ui/top_movers_data.py:50`, `src/langgraphagenticai/ui/top_movers_data.py:58`, and `src/langgraphagenticai/ui/top_movers_data.py:86`.

The universe is split into concurrent chunks. Any failed chunk is discarded with `except Exception: continue`, and the page proceeds as long as one chunk returned data. The resulting rankings, breadth, sector averages, and `universe_size` then describe only the surviving subset, with no partial-data warning or list of missing symbols/chunks.

Smallest correction direction: record chunk-level structured failures, compute and display coverage counts, mark rankings partial, and preserve successful records. Retry only safe transient failures within a shared provider client.

### 6. Medium — Provider behavior is fragmented across UI and domain modules

Affected examples: `src/langgraphagenticai/ui/equity_report_tab.py:22`, `src/langgraphagenticai/ui/company_snapshot.py:32`, `src/langgraphagenticai/ui/market_overview_data.py:74`, `src/langgraphagenticai/ui/top_movers_data.py:21`, `src/langgraphagenticai/portfolio_manager/research_snapshot.py:15`, and `src/langgraphagenticai/portfolio_manager/fmp_fundamentals.py:29`.

There are multiple independent FMP HTTP clients plus the MCP wrapper. They use different timeouts, cache TTLs, error shapes, validation rules, retries, and symbol handling. Provider access is also implemented directly in Streamlit-facing modules. A provider response can consequently mean different things across Introduction, Top Movers, Equity Report, Deep Research, and Portfolio Lab, and fixes such as secret redaction must be repeated everywhere.

Smallest correction direction: extract one FMP adapter/service with a shared session, normalized records/errors, bounded retry policy, freshness metadata, symbol validation, and endpoint-specific TTLs. Keep pages focused on controls and rendering.

### 7. Medium — Core financial and routing surfaces have almost no regression coverage

Affected area: `tests/` compared with `src/langgraphagenticai/portfolio_manager/`, `src/langgraphagenticai/ui/equity_report_tab.py`, `src/langgraphagenticai/ui/portfolio_optimizer_tab.py`, `src/langgraphagenticai/ui/stock_screener_tab.py`, and the new Introduction/Top Movers routes in `src/langgraphagenticai/main.py:334`.

The current tests concentrate heavily on Deep Research and small formatting/health helpers. There are no dedicated tests for the constraint validator, optimizer math, portfolio rebalance invariants, FMP REST adapters, Equity Report exports, screener behavior, Introduction, Top Movers partial failures, or workspace handoffs. The cap violation in finding 1 is an example of a critical financial invariant that currently has no test.

Smallest correction direction: add unit tests for all allocation and period-basis invariants, synthetic contract tests for every provider adapter, Streamlit interaction tests for each workspace/handoff, and export tests for PDF/Excel/CSV/JSON. Keep all provider/model calls mocked.

### 8. Medium — Dependency resolution is not reproducible

Affected code: `requirements.txt:1`, `requirements.txt:8`, `pyproject.toml:5`, and `Dockerfile:21`.

Most top-level dependencies are unconstrained, while `crewai` alone is exactly pinned. The package metadata declares no runtime dependencies, so `pip install .` produces an unusable installation; Docker instead resolves the latest transitive versions on every rebuild. This is especially risky for fast-moving OpenAI, LangChain, LangGraph, Streamlit, FastMCP, pandas, and yfinance APIs.

Smallest correction direction: define runtime dependencies in `pyproject.toml`, maintain a reviewed lock/constraints file for deployment, and use one installation path in local development, CI, and Docker. Add an import/startup smoke test against the locked environment.

### 9. Medium — Equity Report contains multiple shadowed implementations

Affected code: `src/langgraphagenticai/ui/equity_report_tab.py:3632`, `src/langgraphagenticai/ui/equity_report_tab.py:3698`, `src/langgraphagenticai/ui/equity_report_tab.py:4066`, `src/langgraphagenticai/ui/equity_report_tab.py:4759`, `src/langgraphagenticai/ui/equity_report_tab.py:4938`, `src/langgraphagenticai/ui/equity_report_tab.py:5432`, `src/langgraphagenticai/ui/equity_report_tab.py:5504`, and `src/langgraphagenticai/ui/equity_report_tab.py:5562`.

The module defines `render_equity_report_tab` twice, `summarize_scorecard_with_gpt` three times, and several report/PDF helpers more than once. Python silently binds only the last definition. Earlier code remains importable only during module execution and is otherwise dead, so a maintainer can fix or test the wrong implementation without changing runtime behavior. At more than 5,500 lines, the module also mixes provider calls, financial calculations, prompts, rendering, and export generation.

Smallest correction direction: remove shadowed implementations after behavior-parity tests, then split providers, calculations/scoring, prompts, presentation, and exports into focused modules.

### 10. Low — Repository documentation and artifacts do not match the current product

Affected code: `README.md:47`, `README.md:437`, and untracked `debug_codex.txt`.

The README still describes five tabs and older navigation while the application now exposes seven workspaces, including Introduction, Top Movers, and Deep Research. `debug_codex.txt` is an untracked machine-specific troubleshooting transcript containing absolute local paths and process-kill commands; it is not ignored and can be committed accidentally.

Smallest correction direction: update README navigation, provider/key, workflow, and test instructions; remove or ignore local troubleshooting artifacts; keep Deep Research-specific detail in `DEEP_RESEARCH.md`.

## Verification performed

- Inspected `git status --short`, staged/unstaged diffs, and relevant untracked files.
- Enumerated all repository source, test, deployment, and documentation files.
- Ran `python -m compileall -q app.py src crew_ai/stock_picker/src`: passed.
- Ran `git diff --check`: passed; only line-ending conversion warnings were emitted by Git elsewhere.
- Scanned for hard-coded secret-like values: no committed live API key was identified; `.env` and `.streamlit/secrets.toml` are ignored.
- Used AST inspection to identify duplicate top-level definitions; duplicates were confined to `equity_report_tab.py`.
- Reproduced the position-cap and sector-cap failures shown in finding 1 with the adjacent project virtual environment.
- Attempted `python -m pytest -q` in both available Python environments: pytest is not installed, so the intended full suite could not run.
- Ran `unittest` discovery in the adjacent project virtual environment: 56 tests were discovered; 54 passed, one module import failed because `src` was not on `PYTHONPATH`, and one Streamlit `AppTest` timed out after 20 seconds. Re-running with `PYTHONPATH` showed the health file contains pytest-style functions, so `unittest` discovers zero tests there.

## Verification gaps and residual risk

- The full pytest suite was not run because pytest is absent from both available environments and is not declared in project dependencies.
- No paid or live provider/model calls were made.
- Streamlit was not started for this read-only review, and browser interaction coverage was not available.
- PDF generation received indirect coverage through the passing Deep Research unit tests, but Equity Report PDF/Excel/CSV exports were not exercised.
- The breadth of untested financial code means additional defects may remain in the large Equity Report and Portfolio Manager modules even after the listed findings are addressed.

## Recommended remediation order

1. Fix and invariant-test allocation caps and residual cash.
2. Centralize error redaction and stop logging raw prompts/errors.
3. Add timeouts and bounded retry/usage handling to every direct model call.
4. Correct period-aware TTM construction and partial-data signaling.
5. Consolidate provider clients and add synthetic contract tests.
6. Lock dependencies and make CI run the complete offline test matrix.
7. Remove shadowed Equity Report code and update documentation/artifact hygiene.
