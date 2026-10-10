---
title: Agentic AI Financial Analyst V2
emoji: 📊
colorFrom: purple
colorTo: green
sdk: docker
app_port: 7860
pinned: false
short_description: Evidence-grounded financial research and portfolio analytics
---

# Axiom Research — Agentic AI Financial Analyst

Axiom Research is a Streamlit financial-research application that combines live market data, deterministic financial analytics, LangGraph research chat, exportable equity reports, portfolio tools, recoverable Deep Research, and optional multi-agent investment debates.

[Open the hosted application](https://huggingface.co/spaces/andrewnap211/Agentic-AI-Financial-Analyst-v2)

> **Research software, not financial advice.** Outputs may be incomplete, stale, model-generated, or incorrect. Validate material facts and assumptions against original sources before making investment decisions.

## Current application

The app contains eight connected workspaces:

| Workspace | Primary use | AI calls |
|---|---|---|
| Introduction | Market overview, company snapshot, extended price charts, configurable indicators and technical summary | Explicit company/technical analysis |
| Top Movers | Five-trading-day leaders and laggards, breadth, sectors, and related news | None by default |
| Research | LangGraph finance chat with FMP and Marketaux tools | Explicit chat action |
| Equity Report | Sector-aware company comparison, scoring, charts, exports, and best-buy debate | Optional recommendation and CrewAI debate |
| Stock Screener | FMP universe filtering and metric enrichment | None |
| Portfolio Lab | Historical optimizer plus hybrid AI portfolio manager | Optional portfolio committee |
| Deep Research | Stable evidence-to-report workflow with recovery, citations, and optional committee | Explicit research/committee actions |
| Deep Research V2 | Isolated cost and performance pilot for lighter models | Explicit pilot actions |

Selected tickers and completed work can be reused across several workspaces through shared session context. Ordinary Streamlit reruns, tab changes, and downloads do not intentionally trigger paid model calls.

## Highlights

- Shared FMP transport with bounded retries, timeouts, response validation, and credential-safe errors.
- Explicit provider, retrieval-time, statement-period, currency, and coverage metadata where supported.
- Adjusted-price historical analytics and clear separation between price return and provider fundamentals.
- Sector-aware equity frameworks that avoid applying one generic metric set to every industry.
- Structured AI decisions with deterministic ticker, recommendation, weight, and citation validation.
- Recoverable Deep Research runs that preserve evidence and partial drafts when a model stage fails.
- CrewAI debates for Deep Research and Equity Report, both disabled until explicitly requested.
- Cap-safe portfolio allocation with residual cash instead of post-cap renormalization.
- Credential redaction across provider errors, logs, exports, and structured values.
- PDF, Excel, CSV, Markdown, and JSON exports depending on the workspace.

## Workspace guide

### 1. Introduction

Market and company price charts support **1D, 5D, 1M, 3M, 1Y, 3Y, 5Y and 10Y**. Intraday ranges use the latest one/five observed trading dates; longer ranges use daily bars. Company chart history is independent of the snapshot's shorter performance series. Coverage depends on the provider: partial/stale history is disclosed, and no bars are filled or stitched across sources. FMP close adjustment and naive timestamp timezones remain unverified; whole-series Yahoo fallback is explicitly auto-adjusted. Axes preserve provider wall-clock fields, with original timestamps in tooltips. Future aware timestamps are excluded by exact UTC instant; timezone-unknown naive timestamps are excluded only when their calendar date exceeds the current UTC date. Same-day intraday timing cannot be verified for naive timestamps, and no source timezone is invented.

Expand **Technical indicators & settings** to configure SMA, EMA, Wilder RSI, MACD and Bollinger windows (observed bars, up to 500) and the Bollinger deviation multiplier. Calculations use warmup before display trimming; RSI and MACD have separate panels. **Analyze technical evidence with AI** makes one explicit structured OpenAI request using the selected model and saved compact evidence. Settings/range changes make no model calls; previous interpretation remains visible with an input-mismatch notice, and failures preserve it. Identity and evidence references are validated, but model-written numerical claims are not individually certified. No new API key is required beyond optional `OPENAI_API_KEY` and the existing market data configuration. Intraday history caches for five minutes and daily history for one hour; the chart Retry controls refresh history.

The landing workspace provides an executive market view and an FMP-backed company snapshot.

- Market pulse and index context.
- Company lookup and canonical ticker handling.
- Quote, company profile, period-validated fundamentals, valuation, and price performance.
- Interactive S&P 500 charts with 1D, 5D, 1M, 3M, and 1Y controls, plus company closing-price charts with 1M, 3M, and 1Y controls.
- FMP commodity/crypto symbol translation and explicitly labelled Yahoo daily-close fallback for missing quotes. Each chart uses one provider series.
- Normalized company news.
- Provider and as-of metadata with missing/partial-data states.
- Optional evidence-grounded OpenAI summary generated only by Analyze Company; range changes and navigation reuse the saved summary.

### 2. Top Movers

Top Movers ranks a liquid U.S. equity universe using five trading days of price performance.

- Leaders and laggards.
- Market breadth and sector leadership.
- Serper news context when configured.
- Explicit partial-provider coverage warnings. Displayed leaders/laggards receive one bounded batch of quote enrichment; unavailable average volume is shown as Unavailable rather than zero.
- Company handoff into downstream research workflows.

### 3. Research

Research is the interactive LangGraph finance-chat workspace.

- Single-company research and peer comparisons.
- Financial statements, ratios, valuation, DCF, analyst estimates, ratings, calendars, transcripts, ESG, technicals, and news tools.
- Structured tables and consistent analyst-oriented formatting.
- Use-case-specific system prompts.
- Optional debug trace for tool selection and returned data.

Example questions:

```text
Compare MSFT and ORCL on revenue growth, margins, free cash flow, valuation, and downside risk.

Summarize AAPL's latest earnings transcript and identify changes in guidance.

Build a valuation snapshot for NVDA using forward estimates, historical multiples, and DCF evidence.
```

### 4. Equity Report

Equity Report creates a story-first, multi-company research pack.

- Automatic or manual sector/peer framework selection.
- Fundamentals, valuation, growth, profitability, leverage, momentum, ratings, and factor grades.
- Coverage-aware deterministic scores and rankings.
- Price and relative-performance charts.
- Executive summary and optional OpenAI recommendation.
- Raw-scorecard and sector-coverage audit views.
- PDF, Excel, display CSV, raw CSV, and ranking CSV exports.

#### CrewAI best-buy debate

An optional committee uses the saved Equity Report scorecard without recollecting provider data:

1. Fundamental-quality analyst.
2. Valuation and expectations analyst.
3. Bear-case and risk officer.
4. Investment-committee chair.

The chair returns `BUY`, `WATCH`, or `NO_BUY`, confidence, specialist arguments, dissent, catalysts, risks, evidence limitations, and thesis-invalidation conditions. Decisions are fingerprinted to the exact scorecard and rejected if they name an out-of-universe ticker.

### 5. Stock Screener

The screener combines server-side FMP universe filters with optional enrichment.

- Exchange, country, sector, industry, market-cap, price, volume, beta, dividend, and ETF/fund controls.
- Optional post-screen valuation, growth, profitability, leverage, analyst, and technical filters.
- Bounded enrichment and explicit missing-provider results.
- Downloadable final CSV.

### 6. Portfolio Lab

Portfolio Lab contains two related tools.

#### Optimizer

- Historical adjusted-price analysis.
- Annualized return and volatility.
- Sharpe ratio with a disclosed risk-free-rate assumption.
- Correlation, beta, drawdown, and crisis-period behavior.
- Efficient-frontier simulation and portfolio-weight comparisons.
- Custom weights and date windows.

#### AI Portfolio Manager

- Manual holdings entry or CSV/XLSX upload.
- Deterministic evidence, research snapshots, factor scores, and portfolio constraints.
- Specialist-agent debate and lead portfolio-manager decision.
- Target weights, rebalance trades, sector exposure, monitoring, diagnostics, and follow-up chat.
- Position/sector-cap validation and residual-cash handling.
- Recommendation and rebalance CSV exports.

### 7. Deep Research

The stable Deep Research workflow investigates one to four companies.

1. Collects FMP fundamentals, valuation, estimates, targets, and adjusted-price technicals.
2. Adds Serper news/web discovery and optional saved app context.
3. Plans targeted transcript, peer, valuation, rating, calendar, dividend, or ESG follow-ups.
4. Generates a cited investment memo with dated evidence, scenarios, risks, and invalidation criteria.
5. Reviews the memo and applies only uniquely matched corrections.
6. Preserves evidence, drafts, warnings, and recovery checkpoints.

Completed research provides a thesis, normalized comparison, source register, data gaps, follow-up questions, diagnostics, and PDF/Markdown/JSON/CSV downloads. The optional CrewAI investment committee reuses saved evidence and does not refetch market data.

See [DEEP_RESEARCH.md](DEEP_RESEARCH.md) for the detailed workflow.

### 8. Deep Research V2 — cost pilot

V2 is intentionally separate from the stable workflow. It is designed to measure whether lighter models can lower cost and latency without weakening financial usefulness.

#### Cost modes

| Mode | Planning | Report | Review | Specialists | Committee lead |
|---|---|---|---|---|---|
| Economy | Light route | GPT-5 Mini | Deterministic; light review only when needed | Light route | GPT-5 Mini |
| Balanced | Light route | GPT-5 Mini | Light interpretive review | Light route | GPT-5 Mini |
| Maximum quality | GPT-5 Mini | GPT-5 | GPT-5 Mini | GPT-5 Mini | GPT-5 |

The light route can use OpenAI, Groq, or an Ollama OpenAI-compatible endpoint. Provider failures are shown and never silently switched to another model.

V2 currently includes:

- Stage-specific provider/model routing.
- Smaller deterministic evidence packets and output limits.
- Python validation before interpretive review.
- `None`, one-call **Quick decision**, or full CrewAI committee modes.
- Compact committee briefs rather than replaying the full report to every specialist.
- Maximum estimated model cost per run.
- Stop after evidence collection and generate the report later.
- Use-saved-result and force-fresh controls.
- Per-stage input, cached-input, output, reasoning-token, latency, and cost diagnostics when available.
- Prompt-size estimates and cumulative V2 session cost.
- A fixed five-case evaluation fixture covering large-cap, sparse-data, same-sector, cross-sector, and missing-data scenarios.

CrewAI may expose only aggregate usage; when that happens, specialist/lead attribution is clearly marked as estimated. Cheaper modes remain experimental until live evaluation meets the quality threshold in [TODO_DEEP_RESEARCH_COST_OPTIMIZATION.md](TODO_DEEP_RESEARCH_COST_OPTIMIZATION.md).

## Data and model providers

| Provider | Used for | Required? |
|---|---|---|
| Financial Modeling Prep | Profiles, quotes, statements, ratios, metrics, estimates, ratings, targets, transcripts, calendars, screener, ESG | Required for most live financial workflows |
| OpenAI | Research chat, report synthesis, structured decisions, committee leads | Required for AI workflows |
| Serper | Top Movers and Deep Research news/web discovery | Optional |
| Marketaux | Enhanced company-news tools and news Q&A | Optional |
| yfinance | Portfolio historical prices and optimizer analytics | No API key |
| Groq | Deep Research V2 light planning/review/specialists | Optional pilot provider |
| Ollama | Local Deep Research V2 light stages through an OpenAI-compatible endpoint | Optional pilot provider |
| OpenRouter | Included experimental model notebook | Optional; not part of the primary app workflow |

Provider availability, entitlements, coverage, and rate limits vary. The app preserves partial successes and surfaces missing records rather than silently treating missing data as zero.

## Installation

Python 3.11 or 3.12 is supported.

```bash
git clone https://github.com/andrewnapurano00/Agentic-AI-Financial-Analyst.git
cd Agentic-AI-Financial-Analyst

python -m venv venv
```

Activate the environment:

```powershell
# Windows PowerShell
.\venv\Scripts\Activate.ps1
```

```bash
# macOS or Linux
source venv/bin/activate
```

Install reproducible runtime dependencies:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt -c constraints.txt
```

For development and tests:

```bash
pip install -r requirements-dev.txt -c constraints.txt
```

## Configuration

Copy `.env.example` to `.env` and populate only the services you intend to use:

```dotenv
OPENAI_API_KEY=
FMP_API_KEY=
SERPER_API_KEY=
MARKETAUX_API_KEY=
GROQ_API_KEY=
OPENROUTER_API_KEY=
```

Keys can also be entered in the sidebar or supplied through Streamlit secrets. For hosted Streamlit deployments, copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and keep the real file out of version control.

The app never intentionally renders, logs, exports, or caches API keys. `.env` and `.streamlit/secrets.toml` are ignored by Git.

## Run locally

```bash
streamlit run app.py
```

Open the local address printed by Streamlit. The health endpoint is:

```text
/_stcore/health
```

## Docker

```bash
docker build -t axiom-research .
docker run --rm -p 7860:7860 --env-file .env axiom-research
```

Then open `http://localhost:7860`.

## Tests

Tests use synthetic or mocked provider/model responses and must not consume paid API credits.

```powershell
$env:PYTHONPATH = (Resolve-Path "src").Path
python -m pytest -q
```

The 2026-10-03 quarterly-TTM verification collected **170 cases**: all **166 application cases passed**, plus two passing and two failing standalone FMP-reference cases. The two existing reference failures concern certificate export after truststore SSL injection. Independent financial/UI/PDF checks passed; startup/health and an offline browser workflow also passed. See [PLAN.md](PLAN.md#v-20261003-01---quarterly-derived-v2-ttm) for exact commands, inventory and remaining limits. Covered areas include:

- Formatting and response cleanup.
- Secret redaction and provider hardening.
- Portfolio constraints and financial invariants.
- Deep Research planning, evidence, citations, recovery, UI behavior, and exports.
- Deep Research V2 helper routing, prompt limits, mechanical validation, cache keys, estimated committee accounting, and fixture presence. Quarterly TTM cases protect fiscal/currency/security alignment, missing inputs, ratios, no-TTM calls, and UI/PDF financial units.
- V2 saved-evidence/report-review recovery, failure statuses, provider preflight, budget blocks, optional decision isolation and mocked Streamlit interactions. See [recovery controls](DEEP_RESEARCH.md#recovery-and-generation-controls-aafa-2).
- Application configuration validation. Startup/HTTP health checks are separate smoke checks, not covered by `test_app_health.py`.

Live-provider smoke checks should remain explicit and separate from the offline suite.

## Project-specific coding skills

Thirteen repository skills live in `.agents/skills/` for provider debugging, financial correctness, Streamlit interactions, grounded research, portfolio validation, cost/performance, safe refactoring, exports, release checks, GitHub synchronization, independent review, a review team with Jira ticket creation, and a feature development team. Use `$axiom-github-sync` to request a checked commit and push to this project's repository.

In a Codex chat for this project, use a prompt such as `Use $axiom-provider-debug to fix missing ticker data on Top Movers.` See [the project skills guide](docs/PROJECT_SKILLS.md) for selection advice, examples for every skill, and discovery troubleshooting.

## Architecture

```text
app.py
└── src/langgraphagenticai/
    ├── main.py                    # Session initialization and workspace routing
    ├── graph/                     # LangGraph finance-chat graph
    ├── nodes/                     # Chat and tool-execution nodes
    ├── prompts/                   # Use-case system prompts
    ├── tools/                     # FMP, Marketaux, Serper, transcript, and research tools
    ├── providers/                 # Shared FMP/OpenAI transport and failure handling
    ├── ui/                        # Eight Streamlit workspaces and shared shell
    ├── deep_research/             # V1 workflow, V2 pilot, evidence, review, exports
    ├── portfolio_manager/         # Analytics, agents, constraints, rebalance, reporting
    └── utils/                     # Safety, formatting, logging, health checks
```

Design boundaries:

- Streamlit modules orchestrate controls and presentation.
- Provider behavior is centralized where practical.
- Deterministic financial calculations live outside AI prompts.
- Provider facts, calculated metrics, and model interpretations remain distinguishable.
- Model calls require explicit actions and have bounded timeouts/retries.
- Successful provider records survive partial failures elsewhere in a workflow.

See [PLAN.md](PLAN.md) for the engineering roadmap and [docs/code_review.md](docs/code_review.md) for the comprehensive repository review and remediation record.

## Outputs

| Workspace | Available downloads |
|---|---|
| Equity Report | PDF, Excel, display CSV, raw CSV, ranking CSV |
| Stock Screener | CSV |
| Portfolio Lab | Holdings template, recommendations CSV, rebalance CSV |
| Deep Research | Executive PDF, Markdown memo, evidence/report JSON, comparison CSV |
| Deep Research V2 | PDF, Markdown memo, audit JSON |

Downloads retain the evidence and warnings appropriate to their format. Raw audit exports may be more detailed than executive-facing reports but are still passed through credential-safety controls.

## Reliability and financial conventions

- Symbols are normalized and validated before supported network calls.
- Missing values remain distinct from zero.
- TTM, annual, quarterly, forward, and point-in-time values are labeled and should not be treated as interchangeable.
- Adjusted prices are used for comparable historical-return calculations where available.
- Price return is not presented as total return.
- Portfolio weights are validated to sum to 100% within tolerance after constraints.
- Currency mismatches, stale evidence, coverage gaps, and provider failures are surfaced.
- Recommendations disclose uncertainty, risks, missing inputs, evidence date, and invalidation conditions where the workflow supports them.

## Troubleshooting

### API key is not detected

- Confirm the variable name exactly matches `.env.example`.
- Place `.env` in the repository root.
- Restart Streamlit after changing environment variables.
- For hosted deployment, use the platform's secret manager rather than committing keys.

### A provider returns missing or partial data

Coverage differs by ticker, exchange, endpoint, and subscription tier. Review the provider warnings, source register, timestamps, and audit views. Missing values are intentionally not converted to zero.

### Deep Research stops during writing or review

Use the saved retry action. Evidence and completed drafts are retained, and recovery does not recollect provider data unless you start a fresh run.

### V2 Groq or Ollama stage fails

- Confirm `GROQ_API_KEY` and the selected Groq model name.
- For Ollama, confirm the model is installed and the OpenAI-compatible endpoint is reachable.
- V2 does not silently fall back to OpenAI; change the route explicitly and rerun.

### TLS certificate verification fails

Configure `SSL_CERT_FILE` and `REQUESTS_CA_BUNDLE` with your organization's trusted certificate bundle. Do not disable TLS verification.

### Portfolio weights differ from the model proposal

The deterministic validator may adjust target weights to enforce position caps, sector caps, cash buffers, and the 100% total-weight invariant. Review the Diagnostics and Rebalance views for the applied changes.

## Security and contribution notes

- Never commit `.env`, `.streamlit/secrets.toml`, API responses containing credentials, or generated research output.
- Keep paid provider and model calls out of automated tests.
- Preserve provider dates, units, currency, period, and provenance in new financial features.
- Add tests at the lowest useful layer for every behavioral change.
- Follow [AGENTS.md](AGENTS.md) and the Definition of Done in that document when contributing.

## License and status

This repository is an actively developed research application. Review the repository license, provider terms, model terms, and market-data redistribution restrictions before production or commercial use.

For an independent code review, invoke `Use $code-review-agent`. The project skill lives in `.agents/skills/code-review-agent/` and saves uniquely named task reports in `docs/reviews/`.

For a three-agent review and Jira triage, invoke `Use $code-review-team`. The reviewer passes findings to a summarizer, then a Jira writer creates up to six highest-priority nonduplicate issues in `AAFA` on `https://bigmeatpete717.atlassian.net`. Reports go to `docs/reviews/`; authenticated Jira access is required for publication. Add `dry run` to save drafts without Jira writes. See the [project skill guide](docs/PROJECT_SKILLS.md#review-team-and-jira) for scoped examples.

For scoped feature improvements, invoke `Use $feature-development-team` with a workspace and desired outcome. It coordinates a financial data specialist, planner, builder, and independent verifier/Jira writer, capped at five creation attempts. Financial data choices use task-relevant `fmp_data_reference` coverage, fields and saved samples; live collection requires separate explicit authorization. Use `plan-only` to propose improvements, `drafts only` to disable Jira writes, or `dry run` to disable code changes and Jira writes. Delivery reports go to `docs/features/`. See [feature team examples](docs/PROJECT_SKILLS.md#feature-development-team).

Jira team workflows use MCP first, checking tool availability, authentication and project permissions separately. If a child agent lacks tools, the coordinator may publish its verified drafts under the same ledger and duplicate checks. Browser login is an explicit fallback. Diagnose local configured servers with `codex mcp list`; configuration alone does not establish authenticated access.

When native Jira tools are missing, the feature development team can use the working local MCP stdio bridge without a separate browser login. Its [access reference](.agents/skills/feature-development-team/references/jira-mcp-access.md) documents the helper, Windows trust/HTTP/2 configuration, payload handling and result checks. This workstation-specific tooling keeps the existing publication budget and authorization boundaries.


### Deep Research V2 quarterly financial basis

V2 derives supported TTM flows, margins, valuation ratios and average-balance ROE/ROA from validated quarterly statements, with separate dated balance snapshots. It avoids TTM endpoints and TTM-backed investigation bundles. Select **Force fresh research** to obtain this basis; older saved evidence remains explicitly labeled. V1 retains its existing behavior.

Missing or incompatible inputs remain unavailable; unsupported provider formulas are not reconstructed. Saved cross-workspace packets are excluded in this mode, and the disabled control explains why. See [the quarterly financial methodology](DEEP_RESEARCH.md#v2-quarterly-derived-ttm-2026-10-03) for calculation conventions, currencies, period handling and limitations.

### Saved V2 result age

Saved V2 results display **Saved result generated**, a UTC timestamp and elapsed age. This records the return of an explicit research or saved-evidence recovery operation, including evidence-only or incomplete output; it does not certify report completeness or evidence freshness. Reopening history, ordinary reruns, cache reuse, decisions and finalization preserve that timestamp. Older results without a valid timezone-aware timestamp show unavailable without fetching data.

Verification for the isolated October 4 timestamp release: **108 offline tests passed**, including 23 timestamp cases; compile/import, local health and a mocked browser saved-result workflow passed. This excludes earlier uncommitted V2 changes. See [PLAN verification](PLAN.md#v-20261004-01---saved-v2-result-generation-age-isolated-release) for scope and deployment limits.

The timestamp change is also installed and browser-verified in the local working tree. Deployment for this run is local only; no Hugging Face publish was requested.

### Serper news in Deep Research (2026-10-04)

Both Deep Research workspaces use `SERPER_API_KEY` for per-company news and optional planner-requested web research. Enable the news control and choose the requested 7/30/90-day lookback. Saved results show Serper article counts, company coverage, and retrieval timestamps, with warnings for missing or partial coverage. Article publication dates are provider-supplied; requesting a lookback does not independently verify article freshness. Reopening saved results or generating a report from saved evidence does not refresh news. Start fresh research to collect newer evidence.

Fresh Serper verification (October 4): 23 focused tests passed independently. Full local inventory: **214 passed, 2 failed**; both failures are the existing FMP reference collector TLS certificate-export issue. Local app health and synthetic browser checks passed for both research pages. This is offline verification, not proof of live Serper access; see PLAN V-20261004-02.

Serper company-news searches use company name plus ticker, or ticker alone when the name is unavailable. Existing saved news remains unchanged; use **Force fresh research** in V2 or start a new V1 run to collect with the updated query. Empty results, missing response collections and discarded unsafe/unusable rows have distinct diagnostics. No live coverage guarantee is implied.

Updated empty-news correction verification (October 4, V-20261004-03): **224 offline tests passed** in the local app environment (Python 3.12.0 / Streamlit 1.61.1), including 31 Serper regressions. The earlier Anaconda-specific FMP certificate failures did not recur. Restart Streamlit and choose fresh research to apply the simpler company-news queries; existing saved results are retained. Live Serper success remains unverified.

### Audited sector-aware Deep Research financials (2026-10-04 candidate)

Fresh V1 and V2 research share validated quarterly TTM calculations and Equity Report's canonical sector registry. Income/cash-flow amounts use four consecutive fiscal quarters; balance facts use the latest valid quarterly snapshot. ROE/ROA require matched TTM-end and same-quarter prior-year balances. Annual history remains separate for exact three-fiscal-year CAGR, including when the selected reported-period view is quarterly. Forward amounts use the nearest future annual consensus; forward growth compares FY+2 with FY+1. Bank/REIT specialist metrics remain unavailable without validated inputs. Each comparison has a metric audit with units, formulas, source/retrieval dates, status and applicability, downloadable as CSV alongside saved JSON/PDF. Saved legacy comparisons remain labelled and preserved; start fresh research for the new methodology. Cross-workspace financial packets are disabled in both fresh workflows because their basis is unverified. Offline arithmetic does not validate AI-written numerical claims.

Independent-review corrections (isolated candidate, 2026-10-04): metric audit inputs now identify both actual annual CAGR endpoints, beginning/end ROE/ROA snapshots, both annual forward-growth observations and actual estimate/target aliases with their source IDs, dates, values and currencies. Explicit YTD/as-reported/unknown selected-period flows are excluded from comparable latest metrics and model evidence; trends require compatible standalone durations and plausible prior-year dates. Model contexts select balanced substantive company evidence within the serialized budget, retaining omitted sources in the saved audit rather than emitting empty excerpts. `model_packets.py` shares per-company sector projection and compact audited units across analysis, quick decisions and full committee packets, bounds the complete JSON packet, and distinguishes legacy assumptions. Four-company18k/22k evidence and three/four-company10k decision/committee cases are covered offline. Earlier verification remains historical; final correction checks are recorded separately.


Sector-aware research verification (October4, AAFA-6): **276 offline tests passed** in the local app environment (Python3.12.0 / Streamlit1.61.1 / pytest9.1.1). Independent financial review, compilation/imports, fresh startup health and recorded browser comparisons/legacy notices passed for both research pages. The served audit CSV was validated; automated browser file-save completion remains unverified. No live financial-provider/model quality or universal standalone-quarter guarantee is established. See [PLAN verification](PLAN.md#v-20261004-04---shared-sector-aware-research-financial-audit-aafa-6). Start fresh research to use audited metrics; saved older results retain their original methodology and numbers.


Introduction chart verification (October4, AAFA-7): **322 offline tests passed** in the project Python3.12 environment, including46 new chart/provider/indicator/agent cases. Independent review, compilation/imports, fresh app health and synthetic browser checks passed; all eight ranges were exercised on both market and company charts. Live provider entitlement, complete price coverage and model narrative accuracy remain unverified. See [PLAN verification](PLAN.md#v-20261004-05---introduction-technical-charts-aafa-7). Restart Streamlit to load the local changes; expand Technical indicators & settings and use the explicit AI action when wanted.


Company navigation (P01, October5, AAFA-8): select a company in Introduction or Top Movers and use **Open Research**, **Open Equity Report**, **Open Deep Research** or **Open Deep Research V2**. These actions prepare the destination; Research shows an editable draft and requires **Submit research request**. Saved Screener results remain visible when returning and offer **Open Introduction**. Metadata-only handoffs carry normalized symbols and intent, with no financial packet or automatic paid generation. Both audited Deep Research financial bridges remain disabled.

OpenAI configuration now gates the relevant action rather than every workspace. Screener needs FMP; Portfolio Optimizer and deterministic Equity Report remain accessible without OpenAI. Missing dependencies disable AI actions while saved results stay available. V2 keeps its stage-specific OpenAI/Groq/Ollama checks. Changing the Research model/use case preserves the conversation and asks for an explicit **New thread** before submitting under the new configuration; changes elsewhere do not reset chat. Local implementation/verification is recorded in [PLAN](PLAN.md#d-20261005-p01---connected-company-navigation-and-action-readiness-aafa-8); deployment remains pending.


P01 verification (October 5, AAFA-8): **348 guarded offline tests passed** on the final corrected source (75.21s), including 26 new navigation/readiness cases; compile/import and fresh local app health passed. Synthetic browser checks exercised company handoffs, saved Screener return, preserved chat, and missing-OpenAI action gates with zero model calls. See [dated verification](PLAN.md#v-20261005-p01---full-local-offline-verification). Live providers, model quality and hosted deployment were not verified.


P02 terminal presentation (October 6, AAFA-9): all eight workspace headers describe evidence status without claiming system readiness. Sidebar/footer key presence means **Configured**; **Page rendered at** is the interface clock, not an evidence date. Introduction places company identity, up to three executive cards and saved AI interpretation before chart/financial details, with unknown currency and missing price change explicit. Research keeps editable drafts and saved conversation details, labels saved answers as AI interpretation and leaves unavailable chat source/date metadata explicit. V2 puts saved company/evidence coverage before the collapsed new-research form and configuration details and moves model cost/cache diagnostics to Performance; V1 shares the saved evidence row. Successful nonempty records determine coverage, and original retrieval dates stay separate from saved generation time. Local implementation only; full verification and deployment status are recorded in PLAN.


P02 final local verification (October 6, AAFA-9): **367 guarded offline tests passed**, including 19 new presentation cases; compilation/imports, fresh local health and independent review passed. Synthetic browser checks at 1440x900, 1280x800 and 390x844 verified the primary layouts, saved dates, textual evidence states, focus and zero paid calls. See [dated verification](PLAN.md#v-20261006-p02---final-local-verification). Local implementation complete; deployment pending. Live providers/model quality and hosted release were not verified.


### Guided research (P03 local delivery)

Research now offers **Chat** and opt-in **Guided research**. Choose one ticker and a focused question, configure pricing or acknowledge unknown cost, then **Prepare new plan**. Preparation uses one explicit model attempt and no providers. Inspect up to three allowlisted steps before **Run plan**; execution collects independent quote/profile, latest annual income amounts and a single-page seven-day news snapshot, then makes at most one synthesis attempt. OpenAI is required for planning/synthesis; FMP and Marketaux failures preserve other evidence.

Limits are two total model attempts (no model retries), three logical tool dispatches, 12 graph steps, bounded serialized inputs/output, and pre-call estimated spend reservations using user-configured prices. Completion limits include reasoning. Unknown pricing cannot guarantee a dollar ceiling. Quote/profile has two HTTP requests; shared FMP transient retries can add HTTP attempts, and inactivity timeouts do not guarantee total elapsed time.

Provider evidence retains security, source route, retrieval/as-of dates, unit/currency, missing fields and annual versus point-in-time basis. Profile business facts are undated; quote currency is profile-reported and actual quote currency/adjustment meaning remains unverified. Quote timestamps use an explicitly inferred Unix-seconds interpretation. Annual monetary values preserve the provider scale without rescaling; exact scaling is not independently verified. Structured facts must exactly match cited fields and dates/bases; unsupported facts are withheld. AI interpretation is separately labelled and not semantically certified. News coverage is incomplete and filtered records are disclosed.

Saved plans, evidence and answers belong to the session. Reruns, reopening, downloads and repeated Run reuse saved results; **Prepare new plan** creates a separately counted new run. Input changes disclose mismatches. Returning from Chat restores Guided controls and preserves the conversation. **Open Deep Research** carries navigation metadata and requires its own explicit execution. Server restarts do not preserve Guided results. No hosted deployment or live financial/model-quality certification is established by this delivery.


P03 initial builder verification (October7, AAFA-10; before review corrections): **386 guarded offline tests passed**, including 19 new Guided cases; full compilation/import and diff checks passed. Exact saved FMP samples and synthetic provider/model stubs establish bounded plan/run, partial recovery, exact citation fields and session/rerun behavior without paid calls. Fresh local browser/health and independent review are separately recorded in [PLAN](PLAN.md#v-20261007-p03-builder---scoped-offline-verification) when completed. Deployment remains pending; no live entitlement, financial freshness or narrative-quality guarantee follows.


P03 review corrections: configured credentials are removed before provider truncation or generic redaction; unknown pricing exports `reserved_cost: null` with explicit pricing status. The OpenAI JSON-mode request explicitly requests JSON; Pydantic validates the returned schema locally, rather than relying on JSON mode to enforce it. Truncated/refused responses are rejected without retrying. Final corrected verification is recorded below after completion.


P03 corrected builder verification (same October7 AAFA-10 run; checks completed October8): **389 guarded offline tests passed**, including 22 Guided cases and actual SDK request-contract doubles; full compilation/import and diff checks passed. Credential-boundary, unknown-pricing and JSON-mode review fixes are included. See [corrected inventory](PLAN.md#final-corrected-p03-builder-verification); fresh browser/health and independent review remain separately recorded coordinator evidence. Deployment remains pending.


P03 final local verification (October 8, original AAFA-10 run): **389 guarded offline tests passed**, including22 Guided cases; separate independent focused verification passed22. Compilation/imports, fresh actual-app/harness health and independent source review passed. Final-source synthetic browser checks covered plan/run/partial recovery, rerun/download/navigation reuse, ticker/model mismatches, AAPL/MSFT session isolation and explicit Deep Research handoff at desktop/laptop/mobile widths. Actual JSON export response/content passed; native browser CLI file-save completion remains unconfirmed after cancellation reports. See [fresh verification](PLAN.md#v-20261008-p03---fresh-final-local-verification) and the [original team report](docs/features/2026-10-07-p03-guided-research-team.md). Independent final review approved local completion; [AAFA-10](https://bigmeatpete717.atlassian.net/browse/AAFA-10) is **Done** with dated verification evidence. Deployment remains pending; no live provider/model-quality certification.


P04 adds **Investment brief & scenarios** to saved Deep Research V1/V2 results: original evidence-referenced narrative excerpts, editable hypothetical total equity sensitivities and safe JSON/CSV provenance exports. Strict audited TTM/date/sector/currency gates keep legacy, stale and unsupported data unavailable; recorded FMP quote currency inference does not qualify. Controls and downloads reuse saved evidence without model/provider calls. See [workflow details](DEEP_RESEARCH.md#saved-investment-brief-and-scenarios-p04).

Latest P04 offline inventory (October8): **419 guarded tests passed**, with **58 focused/recovery cases**, compilation/imports and diff checks passed. This supersedes the earlier389 inventory for offline testing. Independent browser/health and final Jira acceptance are recorded in [PLAN](PLAN.md#v-20261008-p04---local-verification) and the [P04 report](docs/features/2026-10-08-p04-investment-brief-team.md). Deployment remains pending; no live provider or narrative-quality certification.


P04 final local acceptance: independent30-case verification/source/export review, fresh app health and corrected synthetic actual-main browser checks passed, including unavailable/partial states, zero service calls, preserved results, V1/V2 parity and desktop/laptop/mobile layouts. Native browser file saving remains unconfirmed after cancellation reports; exact HTTP200 JSON/CSV download contents passed. Final Jira outcome is recorded in the linked P04 report. No commit/push/deployment.


[AAFA-11](https://bigmeatpete717.atlassian.net/browse/AAFA-11) is verified **Done** after final independent acceptance; P04 minimum is complete locally. Deployment remains pending.

### P05 release automation (local preparation)

The [offline release workflow](.github/workflows/offline-release.yml) installs constrained dependencies on Python 3.11/3.12, checks dependency consistency, runs the guarded offline suite and compile/import checks, and retains safe version/test artifacts. The container job verifies non-root health and a separate derived image's synthetic workflow; runtime images omit tests. Requirements and package metadata now agree, with newspaper4k as the sole newspaper namespace owner and Python-specific NumPy constraints.

See the [deployment rehearsal runbook](docs/DEPLOYMENT.md) for protected preview, secret injection, bounded paid smoke checks, session isolation and rollback. The hosting target and hosted rehearsal remain pending. Adding CI does not mean it has run on GitHub; local evidence is recorded in PLAN.


Latest P05 local inventory (October10): **430 guarded offline tests passed**, independently run on Python3.12; focused11 release tests and2 final guard checks, compile/import, installed dependency check, fresh app health and a synthetic browser journey/two-session isolation also passed. See [PLAN evidence](PLAN.md#v-20261010-p05---final-local-verification-and-remaining-release-gates). CI3.11/3.12 is configured, not yet executed on GitHub. Local Docker builds failed during intercepted package-download transport; image startup/health/workflow and clean installs remain unverified. Local code is finished; P05 release acceptance remains open in [AAFA-12](https://bigmeatpete717.atlassian.net/browse/AAFA-12), with hosted target/rehearsal/rollback pending.
