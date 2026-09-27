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
| Introduction | Market overview, company search, snapshot, fundamentals, performance, and news | Optional summary |
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

The landing workspace provides an executive market view and an FMP-backed company snapshot.

- Market pulse and index context.
- Company lookup and canonical ticker handling.
- Quote, company profile, period-validated fundamentals, valuation, and price performance.
- Adjusted-price charts and normalized company news.
- Provider and as-of metadata with missing/partial-data states.
- Optional evidence-grounded OpenAI summary.

### 2. Top Movers

Top Movers ranks a liquid U.S. equity universe using five trading days of price performance.

- Leaders and laggards.
- Market breadth and sector leadership.
- Serper news context when configured.
- Explicit partial-provider coverage warnings.
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

The current verified suite contains **77 passing tests**, covering:

- Formatting and response cleanup.
- Secret redaction and provider hardening.
- Portfolio constraints and financial invariants.
- Deep Research planning, evidence, citations, recovery, UI behavior, and exports.
- Deep Research V2 routing, prompt budgets, deterministic validation, caching, committee accounting, and evaluation fixtures.
- Application import and health behavior.

Live-provider smoke checks should remain explicit and separate from the offline suite.

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
