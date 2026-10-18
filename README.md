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

The app contains eight connected workspaces; Deep Research offers two formats:

| Workspace | Primary use | AI calls |
|---|---|---|
| Market Brief | Combined macro/sector heatmap, multi-horizon returns, daily technicals, configurable ticker chart and Serper/Marketaux news | Explicit dashboard summary, follow-up chat and technical interpretation |
| Top Movers | Period-aware leaders/laggards, charts, analyst targets, ticker news and research drafts | Explicit ticker-news AI summary |
| Research | LangGraph finance chat with FMP and Marketaux tools | Explicit chat action |
| Equity Report | Sector-aware company comparison, scoring, charts, exports, and best-buy debate | Optional recommendation and CrewAI debate |
| AI Valuation | One-action Bear/Base/Bull AI price targets, signed upside/downside, company metrics and sensitivity charts | Explicit Generate AI Valuation |
| Stock Screener | FMP universe filtering and metric enrichment | None |
| Portfolio Lab | Historical optimizer plus hybrid AI portfolio manager | Optional portfolio committee |
| Deep Research | Standard and Low cost formats with separate saved histories, recovery, citations and optional committee | Explicit research/committee actions |

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

### 1. Market Brief (Introduction compatibility identity)

Market Brief is the combined market overview. Its eleven-sector ETF heatmap appears on the main page: tile color and the large signed number use the **1-day** price change, while a second number shows the **5-trading-day** return. Tiles remain equal-sized; market-cap placeholders, the separate heatmap selector, duplicate Explore sectors chart, company-analysis controls and research candidates are removed from this workspace.

**Macro context & sector ETFs** includes all eleven sector ETFs plus the S&P 500, Nasdaq, Dow, Russell 2000, VIX, US 10Y yield index, gold, oil, Bitcoin, dollar index, TLT and IWM. The table shows level, 1/5/30/60-trading-observation and YTD changes, Wilder RSI (14), and signed percentage distances from 7/14/21/50/200-day simple moving averages. Positive/negative values use green/red and explicit signs. Source/as-of columns are hidden in this table; exact inputs/dates remain in Calculation inputs & data diagnostics, with stale/missing warnings retained. Levels have instrument-specific units: a yield-index percentage move is not a basis-point yield change.

FMP `/api/v3/historical-price-full/{symbol}` supplies explicit `adjClose` baselines. Returns are `(latest dated FMP quote price / prior adjusted-close baseline - 1) * 100`; dated historical `close` is used when a usable quote is absent/older. Windows count observed trading dates, excluding the price date; YTD uses the last prior-year observation. Day/week baselines retain 4/10 calendar-day gap guards; 30/60 windows permit at most 55/100 calendar days. YTD requires a baseline within seven days of year end. Missing adjusted inputs remain unavailable, with no substitute provider. RSI uses the uninterrupted valid adjusted-close tail; SMA distance is `(latest price / historical adjusted-close SMA - 1) * 100`. Quotes are not appended as extra daily indicator bars. Actual quote and indicator dates may differ. Quote-to-daily-date policy is UTC for Bitcoin and New York for the other dashboard instruments; this is an explicit calculation policy, not independently verified exchange-session metadata. These are defined adjusted-baseline price comparisons, not independently certified total returns.

**Top market news** combines a two-day Serper news search, Marketaux US-market headlines, FMP general news and up to five FMP-authored article bodies from the [FMP Articles API](https://site.financialmodelingprep.com/developer/docs/stable/fmp-articles). Duplicate records retain source labels and richer body text. Provider HTML is converted to bounded plain text; scripts/styles are discarded. Publication and retrieval dates remain distinct. The lower-page lead-story/headline cards remain available. Optional `SERPER_API_KEY`, `MARKETAUX_API_KEY` and `FMP_API_KEY` enable their respective sources; a failed or missing source preserves the others. Provider entity sentiment scores are not aggregated into a market-wide measure.

**Market news & sentiment**, directly below the top executive market-data summary, has a **Generate / refresh news briefing** action. It summarizes the top stories relevant to the broader market, separates reported developments from conditional market implications and explains a cited **risk-on / risk-off / mixed / unclear** news tone. This is qualitative AI interpretation of the available coverage, not a measured investor-sentiment index or a price forecast. Provider article bodies are used where available, with explicit counts/basis labels for body-text and preview-only coverage. Completeness is unverified: the app does not infer full articles from snippets or fetch/bypass publisher paywalls. Only citation existence, evidence identity and output enums are mechanically checked; article accuracy and prose meaning remain unverified. Legacy saved headline summaries remain readable until explicit regeneration. Requests retain at most30 records, five body excerpts of6000 characters each,800-character previews and100000 total evidence characters; they allow6000 combined reasoning/output tokens,75seconds and zero retries. Refreshing evidence, changing filters and navigation do not generate summaries. Explicit follow-up chat also receives the bounded article-text evidence.

The **Executive market brief at the top** considers the complete loaded macro/sector table, technicals and warnings. It requests at most 160 words: one market-stance sentence, followed by What is working, What is not working and What to watch. All horizons/RSI/SMA distances inform plain-English takeaways; the brief avoids instrument inventories and uses at most four numerical references. News remains available to explicit follow-up chat, but does not drive this metrics-based executive summary. **Generate / refresh market summary** and **Ask market AI** are explicit paid actions; ordinary reruns/range/indicator controls make no model calls. Saved summaries/conversation survive reruns, with mismatch notices when evidence changes. Requests are bounded to 100,000 serialized evidence characters, six prior messages, 6,000 combined reasoning/visible-output tokens per request, a 75-second timeout and zero model retries. Narrative claims remain model interpretation, not independently validated causal explanations.

The full-width **Daily price chart** starts at `^GSPC` and accepts a validated company/index/ETF ticker. Ranges are 1M/3M/1Y/3Y/5Y/10Y; SMA, EMA, RSI, MACD and Bollinger settings count daily bars, with warmup before display trimming and separate oscillator panels. Indicators use individual checkboxes, avoiding the failing lazy Multiselect asset in this panel. If an older browser tab still shows an asset-fetch error, restart the app and hard-refresh the browser. Daily FMP charts use explicit adjusted close; no-key Yahoo whole-series fallback is labeled. Chart source/time/basis remain visible. Top Movers/Screener links select the chart ticker; **Refresh market evidence** is still required before the first collection. Company research remains in the dedicated research workspaces. Existing saved company results are not deleted.

**Refresh market evidence** is required to collect the dashboard, ribbon, daily chart and news. Initial entry makes no market collection calls, allowing users to choose another workspace first. Reruns and return navigation reuse the session snapshot even after provider cache expiry; saved evidence may be stale. The refresh action clears dashboard/history/news/ribbon/membership caches. Chart ticker/range changes and **Refresh chart history** independently request chart observations; indicator changes reuse the saved chart. Dashboard collection is bounded to one batch quote and at most 23 daily history requests, with three history workers and five-minute caches; shared FMP safe transient retries can add HTTP attempts. News caches for ten minutes: one Serper request (up to10 stories), one Marketaux request (up to3), and up to two FMP requests (10 general headlines and5 authored articles). FMP body failure preserves headline coverage. Serper uses a broad US stock-market query; Marketaux uses UTC publication timestamps without offset/microseconds for parameter compatibility. FMP supplies its latest general feed, whose article dates may differ from the other providers' requested lookback. Entitlement, live freshness and complete sessions remain provider-dependent; missing adjusted history stays missing.

### 2. Top Movers

Top Movers screens U.S. equities with provider-requested market cap above 2B, volume above 500K, active trading and no ETFs/funds, capped at 500 requested records. It is not whole-market coverage.

- **1D, 5D, 1M and ytd** rankings preserve zero and exclude missing/nonfinite returns. Sector and direction filters update ranked rows, usable counts, advancing percentage and median together.
- **Ranking size** defaults to **Top 50 stocks** (or all usable stocks if fewer). **Top 10%** rounds up after the selected-period and sector filters. The ranking size survives return navigation; no extra universe is collected when changing it.
- The sector heatmap shows the displayed ranking's concentration and mean selected-period returns. A 100% stacked bar below it shows, for each sector, stocks **In top movers** versus **Other usable stocks**. The denominator is that sector's unique screened stocks with finite returns for the selected period; missing observations are excluded. Hover for counts and percentages. This describes the capped available screen, not every stock in the sector.
- The ranked table includes rank, ticker/company, sector, last price,1D and selected-period changes, cap, volume and average volume;1D has one change column. Missing values stay unavailable and quote/cap currency is not guessed.
- Select a native table row or use the keyboard-accessible company selector to synchronize the selected quote, actual history and related news. Valid selection persists; unavailable selection falls back deterministically.
- **Social sentiment** appears below the selected mover's ranked table. Select a leader/laggard, then **Load / refresh [ticker] social history**. The Stocktwits/Twitter chart offers daily **Average** or **Median** for raw sentiment score, posts, comments, likes and impressions. Only snapshots with at least one post on that platform qualify by default; zero sentiment scores are hidden so zero-activity placeholders do not dilute the view. **Activity filters** lets users raise the post threshold or include zero scores. This is a display/calculation policy: original provider zeros remain saved, and zero likes/comments remain valid when posts qualify. Latest eligible scores show their date and sample count; daily details show excluded counts. Eligible snapshots have equal weight; activity values are per snapshot, not daily totals or post-weighted sentiment. Unknown score calibration is not converted into bullish/bearish thresholds or percentages.
- Social history loads only on its own action, with a selectable3/5/10-page budget (default5),5000-row cap and15-minute credential/symbol/page-scoped provider cache. Empty/repeated pages stop collection; failures retain successful pages. Page/record caps and incomplete coverage are disclosed. Metric/statistic/date-window controls and ticker/navigation changes reuse up to eight saved credential/ticker snapshots; a failed refresh preserves the earlier usable chart. **Refresh movers** does not silently recollect social data.
- The default social window is **Last 5 trading days**, using the local `exchange-calendars` XNYS/NYSE calendar and New York's current date. Weekends, exchange holidays and recorded exceptional closures are excluded; an early-close day remains a trading date. On Saturday October17,2026 the window is October12–16. **Latest 5 reported trading dates** supports explicitly historical inspection and also excludes closed dates. Aware timestamps group by New York date; naive timestamps retain unverified provider dates. After-hours snapshots on a trading date remain eligible; this filters session dates, not market hours. Current-day timing and complete-day coverage remain unverified. Missing eligible values stay unavailable, not zero. Old calendar-window preferences migrate locally without new API/model calls. The new calendar dependency is declared in both install manifests; install updated requirements before starting the app. The [historical social endpoint](https://site.financialmodelingprep.com/developer/docs/social-sentiment-api) remains legacy and plan-dependent.
- Ranking, selected quote, history and Serper news caches are separate. Only the selected company requests enrichment; failed news/quotes/history preserve the ranking and successful evidence. Quote cache is five minutes, ranking/news up to fifteen minutes, and history follows its existing interval-specific cache. **Refresh movers** clears these caches.
- Publication text and news retrieval time are distinct. Related coverage does not establish the cause of a move. Safe source links exclude credential-bearing URLs.
- Screened sector context is an equal-weight mean of usable stocks, distinct from Market Brief's sector ETF quote changes. Benchmark/sector excess returns and completed-session volume ratios remain unavailable because compatible dated bases are not established. No unsupported dollar currency, market-session or total-return claim is inferred.
- **Research this move** opens an editable metadata-only draft; explicit Research submission runs the model. Returning restores sector, period, direction, ranking size and company in the same session. **Open daily chart** selects the ticker in Market Brief; first collection requires **Refresh market evidence**. No model calls occur on selection, filters, refresh or navigation.

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

The saved THESIS tab places the complete executive summary beside a compact comparison context showing the selected peer framework and report generation time. At narrower widths the context stacks below the summary. The five original result tabs, all nine financial sections, committee action and source audit remain available; report generation time does not establish source freshness.

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

With a saved nonempty screen, the server-range and enrichment disclosures start collapsed so the saved table appears sooner; reopen them to adjust every original filter before an explicit **Run Screener**. A fresh screen keeps those disclosures open. The saved table, raw-results CSV and company handoff remain available on ordinary reruns, including when FMP configuration is missing. If a new run yields no companies at the universe, industry, enrichment or advanced-filter stage, the earlier saved result stays visible with its original generation time and a failed-attempt notice.

Screener universe and enrichment caches are scoped to the requesting FMP credential. Changing credentials starts a separate cached result, while an ordinary rerun with the same saved screen does not make a provider request. Provider error notices remove the active credential before display.

### 6. Portfolio Lab

Portfolio Lab contains two related tools.

#### Optimizer

- Historical adjusted-price analysis.
- Annualized return and volatility.
- Sharpe ratio with a disclosed risk-free-rate assumption.
- Correlation, beta, drawdown, and crisis-period behavior.
- Efficient-frontier simulation and portfolio-weight comparisons.
- Custom weights and date windows.

The optimizer's input form is grouped above its five analysis sections. Run Portfolio Analysis still starts the calculation; the full chart/result view is not saved across ordinary reruns, though the limited handoff payload remains available.

#### AI Portfolio Manager

- Manual holdings entry or CSV/XLSX upload.
- Deterministic evidence, research snapshots, factor scores, and portfolio constraints.
- Specialist-agent debate and lead portfolio-manager decision.
- Target weights, rebalance trades, sector exposure, monitoring, diagnostics, and follow-up chat.
- Position/sector-cap validation and residual-cash handling.
- Recommendation and rebalance CSV exports.

The saved Manager result keeps four summary metrics and eight tabs. Recommendations places the full grid and per-ticker reasoning beside a compact saved sector current/target preview and committee summary on desktop; the rail stacks beneath the grid at narrower widths. Sector Exposure retains the full table. Example, typed and uploaded holdings still share the holdings-template download, and the existing sidebar limits remain in place.

### 7. Deep Research

The stable Deep Research workflow investigates one to four companies.

1. Collects FMP fundamentals, valuation, estimates, targets, and adjusted-price technicals.
2. Adds Serper news/web discovery and optional saved app context.
3. Plans targeted transcript, peer, valuation, rating, calendar, dividend, or ESG follow-ups.
4. Generates a cited investment memo with dated evidence, scenarios, risks, and invalidation criteria.
5. Reviews the memo and applies only uniquely matched corrections.
6. Preserves evidence, drafts, warnings, and recovery checkpoints.

Completed research provides a thesis, normalized comparison, source register, data gaps, follow-up questions, diagnostics, and PDF/Markdown/JSON/CSV downloads. The optional CrewAI investment committee reuses saved evidence and does not refetch market data.

Saved runs appear above the new-research configuration. The Investment thesis places the full memo beside a compact saved-evidence rail; warnings, source gaps, all six result tabs, recovery actions and downloads remain available. The rail's run time is a saved operation time, not evidence freshness.

See [DEEP_RESEARCH.md](DEEP_RESEARCH.md) for the detailed workflow.

#### Low cost format (V2 engine)

Choose **Standard format** or **Low cost format** using the Research format radio inside **Deep Research**. One sidebar entry and company handoff serves both formats. Each format keeps its own saved history and explicit run/recovery controls; switching formats does not run research or refresh evidence. Legacy V2 requests open this workspace with Low cost format selected. The V2 engine remains an experimental cost pilot internally; lower cost or equivalent quality is not guaranteed.

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

The saved V2 Report presents the full memo beside its selected-run evidence and operation-time rail. The pilot's configuration, six result tabs, recovery/decision actions and report-gated downloads retain their separate V2 behavior.

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

Both report formats automatically attempt one bounded recovery using saved evidence. If synthesis/review still cannot finish, the app delivers a completed factual overview with no rating; unchecked AI conclusions stay in the audit. Readers do not retry or finalize reports. Existing unfinished saved runs receive this no-call final view when opened.

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


Company navigation (P01, October5, AAFA-8): select a company in Introduction or Top Movers and use **Open Research**, **Open Equity Report**, **Open Deep Research** and select **Low cost format** inside that workspace. These actions prepare the destination; Research shows an editable draft and requires **Submit research request**. Saved Screener results remain visible when returning and offer **Open Introduction**. Metadata-only handoffs carry normalized symbols and intent, with no financial packet or automatic paid generation. Both audited Deep Research financial bridges remain disabled.

OpenAI configuration now gates the relevant action rather than every workspace. Screener needs FMP; Portfolio Optimizer and deterministic Equity Report remain accessible without OpenAI. Missing dependencies disable AI actions while saved results stay available. V2 keeps its stage-specific OpenAI/Groq/Ollama checks. Changing the Research model/use case preserves the conversation and asks for an explicit **New thread** before submitting under the new configuration; changes elsewhere do not reset chat. Local implementation/verification is recorded in [PLAN](PLAN.md#d-20261005-p01---connected-company-navigation-and-action-readiness-aafa-8); deployment remains pending.


P01 verification (October 5, AAFA-8): **348 guarded offline tests passed** on the final corrected source (75.21s), including 26 new navigation/readiness cases; compile/import and fresh local app health passed. Synthetic browser checks exercised company handoffs, saved Screener return, preserved chat, and missing-OpenAI action gates with zero model calls. See [dated verification](PLAN.md#v-20261005-p01---full-local-offline-verification). Live providers, model quality and hosted deployment were not verified.


P02 terminal presentation (October 6, AAFA-9): all eight workspace headers describe evidence status without claiming system readiness. Sidebar/footer key presence means **Configured**; **Page rendered at** is the interface clock, not an evidence date. Introduction places company identity, up to three executive cards and saved AI interpretation before chart/financial details, with unknown currency and missing price change explicit. Research keeps editable drafts and saved conversation details, labels saved answers as AI interpretation and leaves unavailable chat source/date metadata explicit. V2 puts saved company/evidence coverage before the collapsed new-research form and configuration details and moves model cost/cache diagnostics to Performance; V1 shares the saved evidence row. Successful nonempty records determine coverage, and original retrieval dates stay separate from saved generation time. Local implementation only; full verification and deployment status are recorded in PLAN.


P02 final local verification (October 6, AAFA-9): **367 guarded offline tests passed**, including 19 new presentation cases; compilation/imports, fresh local health and independent review passed. Synthetic browser checks at 1440x900, 1280x800 and 390x844 verified the primary layouts, saved dates, textual evidence states, focus and zero paid calls. See [dated verification](PLAN.md#v-20261006-p02---final-local-verification). Local implementation complete; deployment pending. Live providers/model quality and hosted release were not verified.


### Guided research (P03 local delivery)

Research now offers **Chat** and opt-in **Guided research**. Choose one ticker and a focused question, configure pricing or acknowledge unknown cost, then **Prepare new plan**. Preparation uses one explicit model attempt and no providers. Inspect up to three allowlisted steps before **Run plan**; execution collects independent quote/profile, latest annual income amounts and a single-page seven-day news snapshot, then makes at most one synthesis attempt. OpenAI is required for planning/synthesis; FMP and Marketaux failures preserve other evidence.

Limits are two total model attempts (no model retries), three logical tool dispatches, 12 graph steps, bounded serialized inputs/output, and pre-call estimated spend reservations using user-configured prices. Completion limits include reasoning. Unknown pricing cannot guarantee a dollar ceiling. Quote/profile has two HTTP requests; shared FMP transient retries can add HTTP attempts, and inactivity timeouts do not guarantee total elapsed time.

Provider evidence retains security, source route, retrieval/as-of dates, unit/currency, missing fields and annual versus point-in-time basis. Profile business facts are undated; quote currency is profile-reported and actual quote currency/adjustment meaning remains unverified. Quote timestamps use an explicitly inferred Unix-seconds interpretation. Annual monetary values preserve the provider scale without rescaling; exact scaling is not independently verified. Structured facts must exactly match cited fields and dates/bases; unsupported facts are withheld. AI interpretation is separately labelled and not semantically certified. News coverage is incomplete and filtered records are disclosed.

Saved plans, evidence and answers belong to the session. Reruns, reopening, downloads and repeated Run reuse saved results; **Prepare new plan** creates a separately counted new run. Input changes disclose mismatches. Returning from Chat restores Guided controls and preserves the conversation. **Open Deep Research** carries navigation metadata and requires its own explicit execution. Server restarts do not preserve Guided results. No hosted deployment or live financial/model-quality certification is established by this delivery.

The Guided page shows a saved answer below its company header before the configuration disclosure. Configure guided research opens when no answer exists and keeps the original keyed ticker, question and spend controls reachable when a result is saved; Prepare and Run remain separate explicit actions below setup.


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


Latest opening-discovery inventory (October12): **452 guarded offline tests passed in226.66s** on installed Python3.12.0 / pytest9.1.1 / Streamlit1.61.1, plus focused97 market/discovery/handoff/technical cases and41 corrected hardening/release/routing cases. The final empty-view filter-persistence follow-up passed45 opening/handoff cases; compile/import and fresh actual-app/harness health passed. Synthetic desktop/mobile journeys and two-session isolation made zero external/model attempts. The final inventory includes keyboard/native snapshot-roundtrip and empty-recovery frontend-default regressions. A fresh synthetic browser confirmed Technology/1M/AMD survives empty evidence, Research navigation, recovery and Refresh with selector/panel identity aligned. See [PLAN opening evidence](PLAN.md#verification-v-20261012-opening-local-syntheticoffline) for scope, the initial fixture failures and separate health/browser checks. No live provider/model, clean-install or deployment certification is implied.

Latest P05 local inventory (October10): **430 guarded offline tests passed**, independently run on Python3.12; focused11 release tests and2 final guard checks, compile/import, installed dependency check, fresh app health and a synthetic browser journey/two-session isolation also passed. See [PLAN evidence](PLAN.md#v-20261010-p05---final-local-verification-and-remaining-release-gates). CI3.11/3.12 is configured, not yet executed on GitHub. Local Docker builds failed during intercepted package-download transport; image startup/health/workflow and clean installs remain unverified. Local code is finished; P05 release acceptance remains open in [AAFA-12](https://bigmeatpete717.atlassian.net/browse/AAFA-12), with hosted target/rehearsal/rollback pending.

Latest terminal styling inventory (October12): **453 guarded offline tests passed in224.35s** on Python3.12.0 / pytest9.1.1 / Streamlit1.61.1, superseding the452 inventory above. Dark opening charts/cards, technical overlays and desktop/mobile presentation were checked using synthetic actual-main fixtures with zero external/model attempts; fresh local health passed. See [PLAN](PLAN.md) and [feature-team review](docs/features/2026-10-11-opening-ui-team.md). This remains local working-tree work; live provider/model and hosted release gates remain open.


Latest Bloomberg-opening builder inventory (October12): **478 guarded offline tests passed in125.59s** on installed Python3.12.0 / pytest9.1.1 / Streamlit1.61.1, with85 focused domain/provider/market/discovery/handoff checks, compile/import and diff validation. This supersedes the453 offline inventory above. Final builder checks used saved reference samples/synthetic providers, with external/model transports blocked; fresh health/browser and independent review remain separately recorded in the [team run](docs/features/2026-10-12-bloomberg-opening-team.md) and [PLAN](PLAN.md#v-20261012-bloomberg--builder-offline-checks). Exact comparison to the absent request screenshots, live entitlement/freshness/model-quality checks and hosted release remain unverified; no commit, push or deployment is implied.


Post-review F01 inventory (October12): **479 guarded offline tests passed in 169.74s**, with 99 focused company/opening/market/presentation/handoff checks and compilation/import/diff validation. The explicit summary prompt now receives bounded dated financial/currency/basis/filing metadata and sanitized partial-source errors; ordinary controls and saved interpretations preserve zero automatic calls. This supersedes the 478 inventory above. Final active-control CSS/punctuation corrections followed that full run and receive separate focused/browser checks in the team report; no new live provider/model or deployment certification follows.


After the final opening active-radio CSS/punctuation corrections,51 guarded focused company/market/opening cases passed in29.99s; affected compilation/diff checks passed. The 479-case full inventory above predates those presentation-only corrections. Exact browser color/interaction confirmation is separate coordinator evidence.


Opening metric wiring (October13): company ROIC/ROE/ROA/dividend yield now display documented FMP fractional ratios; forward P/E, EPS contributor count, consensus rating/target and target upside use the existing Equity Report feed types. Peer P/E/ROIC remain visible as provider snapshots; margin TTM dates are shown per peer. Undated sources and EPS/target currency/adjustment assumptions are explicit, with incompatible/invalid inputs still unavailable. Selected extension is bounded to18 dispatches/four workers with six-hour caching; ordinary controls make no model calls. See the [metric dictionary](docs/OPENING_METRIC_DICTIONARY.md) and [wiring repair](docs/features/2026-10-13-opening-metric-wiring.md) for methods and verification.

Latest opening wiring inventory (October13): **486 guarded offline tests passed in330.70s**, superseding479; focused105 passed102.87s, final compile/import/diff and fresh local app/harness health passed. Seven new wiring cases exercise recorded existing feeds and invalid/date/currency/zero/alias/escaping behavior. See [repair evidence](docs/features/2026-10-13-opening-metric-wiring.md) for separate mocked browser checks. No live provider/model accuracy or deployment certification follows.

Shared redesign shell inventory (October13): **488 guarded offline tests passed in177.12s** on the installed Python3.12 environment. The P02 change covers navy/gold shared styling, single-radio grouped navigation and editable Settings; focused route/settings tests also passed after the final test assertion update. Compile/import and diff validation passed. Browser visual checks and fresh health are recorded separately in the [redesign comparison](docs/redesign/qa/visual-comparison.md) and [PLAN](PLAN.md); the full page-body redesign and heatmap remain open. No live provider/model or deployment certification follows.

Latest local redesign inventory (October16): **521 guarded offline tests passed in 155.51s** on the installed Python3.12.0 / pytest9.1.1 / Streamlit1.61.1 environment, including saved-result recovery, representative export artifacts and Screener credential isolation. Bounded page layouts for Market Brief/Movers, Research Chat/Guided, Equity, Deep Research V1/V2, Screener and Portfolio Lab received focused tests, independent review and synthetic browser checks. Compile/import/diff checks and fresh guarded app/harness health passed. See the [dated PLAN verification](PLAN.md#v-20261016-screener-credential-isolation-final) and [visual comparison](docs/redesign/qa/visual-comparison.md) for branch and viewport limits. This is local working-tree code; full preservation-row/export/live-service parity, the heatmap data contract, clean installs and hosted release remain open.

Portfolio Optimizer now keeps a bounded completed analysis in the browser session. Ordinary reruns and navigation restore its price excerpt, efficient frontier, risk table, crisis roles and weight tables without refetching prices or resimulating. A failed new Run shows the failure and the earlier analysis with its original generation time; the existing portfolio handoff packet remains unchanged. Stock Screener likewise retains its earlier saved table, CSV and company handoff after an empty universe, industry filter, enrichment or advanced-filter result. A warning labels the failed new attempt and the earlier saved time. These results remain session-only; use the explicit Run action to collect newer data. Verification and limits are recorded in PLAN's October 15 behavioral follow-up.

Saved export parity (October 15): Equity raw, display and ranking CSV retain their distinct content; the PDF and Excel pack retain the saved research identity and numeric cells. Screener and Portfolio Manager CSV downloads retain raw saved rows and columns, while text that could execute as a spreadsheet formula is exported as inert text. Known credential patterns in exported text are redacted. Guided Research JSON retains saved run/evidence IDs and finite values while filtering credentials, binary fields and nonfinite numbers. If its saved packet exceeds 500 KB, the result stays visible and the download shows a size warning instead of truncating data. These are offline artifact checks; live data and every conditional export remain unverified.

Latest heatmap inventory (October16): **537 guarded offline tests passed in203.96s** on installed Python3.12.0 / pytest9.1.1 / Streamlit1.61.1. This includes sixteen heatmap calculation/provider/interaction cases. Compile/import/diff checks, fresh app/fixture health and synthetic desktop/narrow browser interactions passed. See [V-20261016-HEATMAP](PLAN.md#v-20261016-heatmap--verification). The equal-area fallback and screened-industry membership are local working-tree code; full constituent capitalization, dated industry returns, live entitlement/freshness and hosted release remain open.


Latest price-correction inventory (October16): **552 guarded offline tests passed in272.55s** on installed Python3.12.0 / pytest9.1.1 / Streamlit1.61.1; final focused price/heatmap checks passed31 in25.76s. Daily charts now use explicit FMP `adjClose`; the heatmap and Market Brief sector bars share latest FMP price versus prior trading-day adjusted close. Compile/import/diff, fresh health and guarded desktop/narrow browser interactions passed. One live XLK history request could not be completed, so live source access remains unverified. See [V-20261016-FMP-ADJCLOSE](PLAN.md#v-20261016-fmp-adjclose--verification). Broader market-cap/industry and release gates remain open.

Latest Market Brief consolidation verification (October16, V-20261016-MARKET-DASHBOARD): **555 guarded offline tests passed in370.22s** on installed Python3.12.0 / Streamlit1.61.1 / pytest9.1.1. Final dashboard tests passed eight, with two final news robustness cases also passing; compile/import/diff, fresh actual-app and synthetic-harness health, desktop/narrow browser summary/chat/ticker/indicator checks passed. These checks used synthetic evidence and no paid provider/model calls; live entitlement, financial freshness and model-output quality remain unverified. See [PLAN](PLAN.md#v-20261016-market-dashboard--verification) for scope and retained release gates.

Market Brief recovery (October17): `truststore>=0.10,<0.11` is now an explicit dependency in both manifests so verified HTTPS honors OS trusted roots. Restart an already-running app after installing/updating dependencies, then **Refresh market evidence** to discard cached failures. Empty/truncated AI responses now report reasoning/output exhaustion distinctly, preserve saved text and never trigger automatic paid retries. The executive brief still requests <=160 words; the larger token allowance also covers invisible reasoning. See PLAN D-20261017-MARKET-RECOVERY for verification.

Market updates (October17): Market Brief includes a cycling S&P 500 constituent ribbon with price and signed one-day percentage change (green/red), pause on hover/focus and reduced-motion support. FMP quotes are cached up to five minutes and membership for one day; **Refresh market evidence** clears both. Coverage and retrieval metadata are displayed; this is not a streaming feed. Top Movers now includes a sector concentration heatmap that follows Performance period, Sector and Leaders/Laggards filters. Equal-size tiles show the count/share of the displayed ranking and its mean selected-period price change. Focused synthetic verification: 27 tests passed; health and desktop/mobile component browser checks passed. Live quote coverage remains unverified; full-suite inventory above is unchanged. See PLAN D-20261017-RIBBON-MOVERS.

Latest market workflow verification (October17, V-20261017-MARKET-UPDATES): **576 guarded offline tests passed in254.06s** on installed Python3.12.0 / Streamlit1.61.1 / pytest9.1.1; final market-update/ribbon checks passed15 in23.15s after the chart-label refinement. Compile/import/diff, actual-app and synthetic-harness health, and desktop/mobile browser checks passed. Market Brief now requires Refresh market evidence before collection and reuses session evidence on navigation/settings changes. Top Movers defaults to Top50 with a filtered Top10% option and stacked within-sector participation; Market headlines offers an explicit cited summary across saved Serper/Marketaux/FMP coverage. Technical indicators use checkboxes. These are local working-tree changes; live FMP news entitlement, real model quality and hosted release remain unverified. See [PLAN](PLAN.md#v-20261017-market-updates---verification).

Final refresh verification: explicit market refresh now clears symbol-history caches too. The final focused market-update/ribbon/dashboard run passed **28 tests in61.98s**; it follows the576-case full run and verifies the last cache-clear wiring change. Both temporary verification servers/browser sessions were closed.

News briefing update (October17, V-20261017-NEWS-BRIEFING): Market news & sentiment now sits beside the top executive area, with cited top stories, conditional broader-market implications and qualitative coverage tone. A separate bounded live FMP check returned3 provider article bodies; completeness and other publishers' full-text access remain unverified. Final focused tests passed **63 in56.59s** with synthetic services/models; compile/import/diff, fresh health and desktop/mobile synthetic browser checks passed. No real AI generation or new full-suite inventory is claimed. See PLAN for the live-versus-offline evidence distinction.

Selected-mover social verification (October17, V-20261017-SOCIAL-SENTIMENT): focused suites passed36 and71 tests; final social-only checks passed13. Compile/import/diff, fresh actual/harness health and desktop/mobile synthetic browser checks passed. Separate bounded configured-key live probes confirmed AAPL Stocktwits/Twitter fields and217 usable snapshots across three pages, including October13-17 observations. This verifies sampled access, not complete-day coverage, calibrated sentiment or ongoing entitlement. No model calls, new full-suite inventory or hosted deployment. See PLAN for the exact scopes.

Active/trading-day social verification (October17, V-20261017-SOCIAL-ACTIVITY): **602 guarded offline tests passed in242.19s**; final focused activity/social checks passed20 in9.52s, including an additional UI migration/filter case added after full-suite collection. The FICO sample's October16 averages now display0.5218 Stocktwits and0.5585 Twitter, with6eligible snapshots each; inactive placeholders no longer pull either median to zero. October17 is excluded and the window is October12–16. Dependency installation/pip check, compile/import/diff, fresh health and desktop/mobile attachment-backed browser checks passed. No new live-provider or paid-model call, clean-install certification or hosted deployment is claimed.


Deep Research update (October17,2026): both formats collect annual consensus from FMP's configured-key v3 `analyst-estimates/{symbol}` endpoint. Future fiscal dates are selected in ascending order; revenue/EPS/EBITDA/net-income field aliases preserve the original provider inputs. No trailing statements are substituted for forecasts. PDFs retain the memo, dated/currency-labelled financial tables, review status and concise coverage notes; exhaustive metric contracts remain in Sources & Evidence and audit JSON instead of pages of metadata/unsupported-field diagnostics. Unavailable applicable sector priorities and failed datasets remain disclosed. Existing saved runs are not automatically recollected; use an explicit new run for refreshed estimates. See PLAN entry D-20261017-UNIFIED-DR for verification and limits.


Latest Deep Research verification (October17, V-20261017-UNIFIED-DR): **606 guarded offline tests passed in362.11s**; final financial/export/unified checks passed56 in26.61s, and final format checks passed4 in10.93s. Compile/import/diff, fresh app health, desktop/mobile format/navigation browser checks and rendered three-company PDF inspection passed. A separate bounded live probe confirmed20 AAPL v3 annual estimate records (4future periods); the prior stable route returnedHTTP402 for the configured account. TLS verification stayed enabled using Windows trusted roots. No paid report generation, complete live financial coverage, quality/cost benchmark or hosted release is claimed.


Deep Research executive presentation (October17): CrewAI and Low cost quick decisions display one paragraph with three inline sections - Decision, Key drivers, Risks & watchpoints - capped at130 content words. The complete saved decision stays under Full decision & limitations. Primary comparison tabs are Fundamentals, Valuation and Momentum & technicals, selected from Equity Report's sector priorities with per-company sector masking and balanced cross-sector selection. Fiscal bases, currencies and existing calculations remain unchanged; full tables and metric audit are under Detailed metrics, dates & calculation audit. PDFs use these same metric groups so technicals are not lost to a long fundamental list. New memos request a single <=100-word executive thesis while retaining deeper dated news, sentiment, contrary developments and investor implications in the body. Source markers and links are omitted from the thesis presentation, with raw citations retained in saved audit evidence and news links retained in the body. No model/provider call is needed to redisplay saved decisions.


Latest executive Deep Research verification (October17, V-20261017-EXECUTIVE-DR): **612 guarded offline tests passed in374.96s**. Final UI/financial/export checks passed79 in65.47s, including a cross-sector priority case added after full-suite collection; final executive-only checks passed7 in4.87s after PDF spacing refinement. Compile/import/diff, actual/harness health, desktop/mobile saved-decision/metric browser checks and representative rendered PDF inspection passed. No paid model generation or live data retrieval was performed for this presentation change; prompt compliance and investment prose accuracy remain unverified.


Executive summary cleanup (2026-10-17): saved and new summaries omit statement names, statement-field references, source/filing attribution and methodology labels. Business figures, risks and meaningful fiscal dates remain; detailed report sections and original saved evidence are unchanged. The Low cost findings preview now uses only the executive thesis, instead of the first600 characters of the full report. This display cleanup makes no provider/model calls.


Top Movers analyst consensus (October17): below the existing social chart, select a ranked stock under **Consensus stock** and click **Load / refresh [ticker] analyst consensus**. The semicircular Consensus Rating gauge shows a red-to-green arc, a needle and overall category, total ratings, and Sell/Hold/Buy counts and percentages. The needle indicates the largest category; ties show Mixed. Buy includes Strong Buy; Sell includes Strong Sell. Percentages use the sum of all five provider counts, with counts and retrieval metadata available alongside the chart. FMP's legacy v4 `upgrades-downgrades-consensus` endpoint uses the existing configured FMP key, one cached request per loaded stock (one-hour TTL), and no AI. Saved results survive ordinary reruns; a failed refresh preserves the previous chart. The snapshot is independent of the movers' performance-period filter, and the endpoint does not provide a rating as-of date. See [FMP endpoint documentation](https://site.financialmodelingprep.com/developer/docs/upgrades-and-downgrades-consensus-api).


Analyst-consensus verification (V-20261017-MOVER-CONSENSUS):66focused offline tests passed, followed by17feature checks after chart sizing. App/harness health, imports/compile/diff, desktop/mobile Buy/Hold/Sell arrows and saved-stock reuse passed. One separate configured-key live AAPL probe returned the sample's112ratings; rating publication dates and complete analyst/ticker coverage remain unknown. No paid AI job or new full-suite/hosted-release claim.


Top Movers target comparison (October17): the consensus gauge now blends into the terminal background. Below it, **[ticker] - Analyst price targets** follows **Consensus stock** and has an explicit **Load / refresh [ticker] price targets** action. A horizontal comparison connects the latest quote (white circle/dashed reference) to last-month and last-quarter average analyst targets (diamonds); signed percentages and green/red colors distinguish upside/downside. Cards retain average prices and coverage counts. Percentages use `(average target / latest quote - 1) * 100`. These are windows of target publication, not one-month/quarter holding-period forecasts; windows can overlap. Known currency mismatches block comparisons, and missing target/quote currency or price-basis verification is disclosed as an indicative same-basis assumption. No missing quote/target becomes zero. Valid zero-coverage windows show unavailable, and failed partial refreshes retain saved components with original retrieval times. Targets cache one hour, existing FMP quotes five minutes; reruns do not collect targets or call AI. Existing FMP settings and the user-requested v4 price-target-summary endpoint are reused. [FMP target-summary documentation](https://site.financialmodelingprep.com/developer/docs/stable/price-target-summary).


Target-visual verification (V-20261017-TARGET-COMPARISON):67offline integration tests passed, followed by32final target/consensus checks. Compile/import/diff, actual/harness health and desktop/mobile signed target, dark-gauge and missing-window browser checks passed. Two bounded live FICO requests confirmed target-summary and latest quote fields; currency/adjustment compatibility and target publication dates remain unverified. No AI calls or new full-suite/hosted-release claim.


Top Movers company news & sentiment (October17): choose **Consensus stock**, then use **Load / refresh [ticker] news** in the new panel below the charts. It combines available FMP stock news (up to12), Serper company news (up to8) and Marketaux (up to3) for a requested7-day window, deduplicates safe links and keeps successful feeds when another fails. **Generate / refresh [ticker] AI news summary** makes one explicit request using the configured OpenAI model/key and saved news. It shows an executive paragraph, Positive/Negative/Mixed/Insufficient evidence coverage tone, key developments and conditional company implications. Sources and publication/provider information are under **News sources & coverage**, without citation markers in the summary. Tone is qualitative AI interpretation, separate from Stocktwits/Twitter and analyst ratings; it is not a return forecast or proof of why the stock moved. Current feeds are headline/snippet evidence; publisher full text and article completeness are not assumed. News caches10minutes and up to8ticker results/summaries are retained per session/credential scope. Stock/filter/model changes and ordinary reruns do not trigger AI; changed news/model settings show a saved-result notice and failure preserves prior output. The new panel follows the chart selector; existing right-column Serper links still follow the main selected-company control. [FMP stock-news documentation](https://site.financialmodelingprep.com/developer/docs/stable/stock-news).

Selected-company news verification (October17, V-20261017-MOVER-NEWS-AI): latest full offline inventory **663 passed in360.42s**, with24final ticker/market-news tests passing in24.74s (three added after full-suite collection). Compile/import/diff, fresh actual/harness health and synthetic desktop/mobile explicit-action/ticker-isolation/source checks passed. One bounded live FMP request returned matching AAPL news; other live feeds and real AI summary quality remain unverified. No paid model generation or hosted release.


### AI Valuation workspace - automatic price targets (October18)

Select a company and a3/4/5-year target horizon, then click **Generate AI Valuation**. The action loads company metrics when needed, asks AI to select a distinct Bear/Base/Bull annual-growth and exit-multiple case, and immediately displays all three price targets with signed **% upside/downside** and annualized price returns. No compatibility checkbox, separate Apply action or manual calculation is required. The AI also provides its investment opinion, short executive thesis, confidence, case rationales, catalysts and risks. **Adjust scenario assumptions** lets users edit all three cases and recalculate locally. Changing the horizon recalculates saved annual assumptions without an AI call.

The evidence now reuses the app's canonical company-metric and technical calculations: historical EPS/BVPS growth, revenue CAGR, annual margins/free-cash-flow margin, provider TTM valuation/profitability/leverage, annual consensus EPS/forward P-E, adjusted-price technicals and available analyst-target publication windows. Annual, TTM and forecast bases remain separately labeled. FMP legacy/stable forecast aliases (`epsAvg`, `estimatedEpsAvg`, `estimatedEps`; `numAnalystsEps` and legacy count spellings) are supported. Dated annual estimates with positive coverage must align with the issuer's fiscal calendar; explicit currency conflicts remain excluded. Missing direct estimate/quote currency may use the disclosed same-issuer/listing-currency scenario assumption when no known conflict exists. Missing peers/macro lower confidence rather than automatically preventing scenarios. No peer medians/news/macro facts are fabricated.

Ten bounded FMP datasets use the existing transport, three concurrent jobs and five-minute in-memory evidence cache: quote/profile, up to5annual income/balance/cash-flow records each, up to6annual forecasts, provider ratios/key metrics, analyst-target summary and up to400daily historical bars. Existing configured OpenAI/FMP settings are reused. Ordinary controls, navigation and downloads do not call models. Explicit Generate reuses current saved metrics; **Refresh company metrics** recollects them without AI. Earlier five-feed shell results upgrade on explicit Generate, not navigation. Successful partial feeds retain original source timestamps when another fails.

AI selects three separate sets of drivers, replacing the earlier fixed illustration bands. New target = dated earnings anchor * (1+assumed annual growth)^remaining growth years * exit multiple. The exit date is quote-relative; eligible near-term consensus EPS replaces the historical anchor, with three-analyst coverage and current forecast-retrieval checks. Legacy saved targets retain the former annual-EPS/exact-horizon arithmetic. Upside/downside = target/current saved quote - 1. The local engine calculates these figures and verifies Bear <= Base <= Bull; Bear need not be below today's price when evidence implies all cases have upside. These are conditional future nominal exit prices, not present fair value or guaranteed returns. Dividends, dilution, capital actions, FX and leverage changes remain excluded; no probability weights. Profitable operating companies use P-E, financials common BVPS/P-B. Missing specialist REIT/commodity-cycle inputs, unknown sectors, non-positive denominators, stale/future quote/retrieval evidence and known currency conflicts still block pricing. Original monetary/share scaling and corporate-action compatibility remain disclosed assumptions rather than falsely verified facts.

One explicit AI request:90-second timeout, zero retries,9000completion-token ceiling,36k-character evidence cap,500-word prompt target/600-word hard prose ceiling including three case rationales. Strict schemas, exact ticker/fingerprint/source references, driver bounds, Base consistency and ordered targets are checked. These checks do not certify investment prose or forecast accuracy. Sources/metrics remain in an expandable audit; executive source markers and empty citation punctuation are removed. Previous analyses and safe failure status persist per company/credential scope; success clears failure. Eight-entry bounded saved evidence/view/scenario/control stores remain. No financial packets are silently imported from saved Deep Research; **Continue in Deep Research** hands off company metadata only. See [valuation design](docs/AI_VALUATION.md) and PLAN for verification.

Earlier AI Valuation integration/recovery checks are dated in PLAN. The compatibility-review gate introduced during the earlier recovery fix is superseded by the disclosed-assumption scenario policy above. No real AI quality or live issuer-coverage guarantee follows from synthetic tests.

Verification (V-20261018-AI-PRICE-CASES):118focused offline valuation/company-metric/analyst-target/handoff tests passed in52.26s. Compile/import/diff, fresh actual/harness health and desktop/mobile one-action target/horizon/assumption browser checks passed using synthetic providers and the real structured-response parser/calculator. No paid model or live-provider request was run; real AI recommendation quality remains unverified. The prior699full-suite inventory is unchanged.

AI metric grounding correction (October18): source validation now recognizes supplied growth/profitability/valuation metrics and valid annual consensus rather than requiring raw income/quote ID prefixes. Derived metric provenance must resolve to supplied sources, without cycles or dangling IDs; unknown references and technical-only support for financial scenario drivers remain rejected. The per-request structured output schema restricts citation choices to actual eligible IDs and requires non-empty driver references/three cases when eligible. **What the AI is using** shows the actual request's Fundamentals, Valuation, Technicals and Analyst expectations with familiar metric labels, values, units and period/observation dates. It does not claim full Equity Report parity: peer-set comparison and the full quarterly analysis are not included. Failures retain a safe rejected-field/reason status instead of implying the company lacks data.

Metric-reference verification:109focused offline valuation/company-metric/handoff checks passed in52.38s, including the actual OpenAI SDK request serialization and response parsing with an in-memory response. Compile/import/diff, fresh actual/harness health and desktop/mobile one-action metric-backed case/coverage browser checks passed. No real AI generation, live financial accuracy or new full-suite inventory is claimed.


AI Valuation earnings bridge update (October18): new generations use a quote-relative exit date and, for P/E where supported, the nearest annual EPS consensus within550days with at least3analysts. Case growth applies only from that forecast date to the exit date; otherwise reported annual EPS/BVPS grows from its fiscal date. Cards show exit earnings ? multiple and the actual anchor/date/remaining years. All cases share the near-term consensus bridge, whose uncertainty is not separately modeled. Existing saved targets keep their original arithmetic until explicit regeneration. See [valuation methodology](docs/AI_VALUATION.md) and the dated PLAN verification; mechanical checks do not establish forecast accuracy.

Forecast anchor freshness: normalized estimates must have a non-future retrieval timestamp no older than24hours at evidence preparation. Older or undated retained estimates remain context but cannot anchor new targets.


AI Valuation growth-unit review (October18): the model schema explicitly defines numeric percentage units (20.0 means20%) and requires a matching decimal (0.20). Inconsistent units reject the new result rather than silently rescaling it. Growth and valuation drivers exposes historical/consensus growth, the price/anchor-earnings ratio and the AI's original growth/multiple rationales. Near-flat scenarios against a positive supported consensus path are flagged for review, not forced upward. A separate hypothetical2x reverse-target table shows the earnings and growth required at each exit multiple; this is not a forecast. Older saved results remain readable and require Generate to use the new response contract.


Deep Research report delivery (October18): statement/source attribution and workflow instructions are removed throughout the reader-facing memo and PDF, with original drafts, citations, financial contracts and diagnostics retained in Sources/JSON. The PDF replaces review-workflow metadata with report type and preserves actual fiscal dates, units, currencies and TTM/FY distinctions. New Standard/Low cost runs automatically recover writing/review once from saved evidence under existing model/cost limits. Persistent failure or unresolved claims produce an explicitly limited financial overview with no investment rating; failed drafts are not promoted to reviewed recommendations. Report retry/finalize controls and the UI stop-after-evidence option are removed. Opening unfinished old runs finalizes the view deterministically with no paid/provider call. Optional decisions remain separate and do not run on evidence-only final reports. The compact writer packet retains legacy/stable estimate values and explicitly includes canonical forward consensus, addressing the supplied report's contradictory unavailable-estimates paragraph. See PLAN and DEEP_RESEARCH.md for verification and limits.


Latest offline inventory (October18, V-20261018-DEEP-RESEARCH-FINAL-DELIVERY): **757 tests passed in251.11s**, using the installed project Python3.12 environment with guarded synthetic provider/model boundaries. Focused recovery/export checks, compile/import/diff, fresh app health, Standard-format automatic recovery/final-overview browser journeys and rendered PDF checks are recorded in PLAN. No live/paid research-quality or deployment certification is implied.

Deep Research draft recovery (October18): when report review or validation fails, both formats now display the retained full analysis as an expanded **Saved research draft — unverified**, with review details above the separate fallback financial overview. Earlier fallback records can recover drafts retained in their audit. Automatic rewrite attempts preserve their original drafts. Opening/rerunning these views makes no provider/model call. Drafts are not reviewed recommendations; executive PDF/memo downloads still contain the safe overview, while evidence JSON retains the original analysis. Missing drafts cannot be recreated from a financial overview alone.

Latest offline inventory (October18, draft-recovery repair): **759 tests passed in352.93s**, Python3.12.0 / pytest9.1.1 / Streamlit1.61.1, with external transport blocked. Final focused52 passed; compilation/imports, app/harness health and synthetic browser checks for both saved fallback formats passed. See PLAN's V-20261018-DRAFT-RECOVERY. No live research/model-quality guarantee, clean-install or deployment verification follows.

Deep Research one-shot executive report (October18, supersedes earlier review/fallback notes): Standard and every Low cost profile collect research and write the report once, with no model review, automatic rewrite or clarification retry. Full saved memos retained behind earlier fallback records are restored directly without new calls. The report, executive PDF and memo omit statement attribution and internal IDs; originals and diagnostics stay in Sources/evidence JSON. Failed generation remains incomplete. Rerun the existing app to load these changes without restarting its server; keep the current saved session. AI conclusions remain model-derived and are not certified by workflow completion.

Latest offline inventory (October18, single-pass executive report): **769 tests passed in259.98s**, Python3.12.0 / pytest9.1.1 / Streamlit1.61.1, with external transport blocked; final focused121 passed. App compilation/imports, fresh app/harness health and synthetic browser checks passed. One fresh run in each format recorded2collections/2plans/2report-writing calls/**0reviews** in total. See PLAN's V-20261018-SINGLE-PASS-EXECUTIVE. This supersedes759 tests; it does not certify live provider/model quality, clean installs or deployment.

Deep Research organization and PDF (October18): PDFs now include the saved CrewAI committee decision automatically, including company recommendations/confidence, rationale, risks, catalysts, invalidation, dissent and limitations. Saved quick decisions are labeled separately. Downloads reuse saved inputs and never run the committee. PDFs place the executive analysis and decision ahead of supporting metric tables, with clearer headings, paragraphs, research-question context and pagination. New one-pass reports use question-focused sections for valuation, earnings, news/catalysts, downside/risk, strategy or company comparisons; the writer can tailor middle-section titles to the specific question. Existing reports receive presentation cleanup without paid regeneration; their original narrative stays intact in the audit.

Latest offline inventory (October18, question-focused reports/committee PDF): **787 tests passed in342.70s**, Python3.12.0 / pytest9.1.1 / Streamlit1.61.1, external transport blocked. New18-case formatting/export regressions, app compile/import/health, no-call Standard/Low cost download payload checks and rendered synthetic PDFs passed. Native browser file-save completion was not confirmed. See PLAN's V-20261018-QUESTION-REPORT-PDF for the serial rerun, earlier concurrent failure, visual evidence and limitations. This supersedes769 tests and does not certify live report quality, clean installs or deployment.

AI Valuation / Equity Report reuse (October18): new Equity Report runs retain a bounded, dated raw FMP input snapshot for AI Valuation. Generate reuses compatible inputs and collects missing annual anchors; Refresh company metrics fetches fresh data without AI. Financial common-BVPS anchors can use matched as-reported year-end common shares (or issued minus explicit treasury shares), with fiscal/currency/source checks and original dates. Provider TTM BVPS remains distinct context. Older scorecards cannot supply raw retrieval provenance; run Equity Report once to populate reuse, or refresh AI Valuation directly. Saved analyses remain readable, and ordinary reruns do not call models/providers. See docs/AI_VALUATION.md for the bounded bridge, denominator rules and remaining specialist/peer limitations.

Latest offline inventory (October18, Equity Report/AI Valuation reuse): **809 tests passed in234.21s**, Python3.12.0 / pytest9.1.1 / Streamlit1.61.1; external transport blocked. Focused160 passed before the final fiscal-year guard; full809 includes all22 new raw-reuse/common-share regressions. Compilation/imports, app/harness health and synthetic MS browser generate/horizon/refresh counts passed. See PLAN V-20261018-VALUATION-EVIDENCE for the earlier concurrent chart timeout, recorded JPM arithmetic and limits. No live issuer/provider/model-quality or deployment guarantee follows.

AI Valuation Energy coverage (October18): Generate now supports conditional earnings/P/E cases with reported annual or eligible annual consensus EPS. The page discloses that these are not validated mid-cycle earnings; existing currency, freshness and earnings gates remain. See [valuation methodology](docs/AI_VALUATION.md).

Latest offline inventory (October18, conditional Energy valuation): **817 tests passed in305.96s**, installed Python3.12.0 / pytest9.1.1 / Streamlit1.61.1, external transport blocked. Focused110, app/harness health and synthetic Energy Generate/horizon browser interaction passed. See PLAN V-20261018-ENERGY for scope and limits; no live CVX or paid model quality guarantee.

AI Valuation now provides a conditional framework across all sectors and unknown classifications when usable positive annual earnings evidence exists. REITs/Materials use provisional earnings P/E; financials can fall back from unusable common-book evidence to earnings P/E. Missing diluted EPS can use a clearly labeled same-year net-income/diluted-share proxy. Sector limitations remain visible, with one explicit Generate action and saved-case reuse. See [methodology and limits](docs/AI_VALUATION.md).

Latest offline inventory (October18, all-sector conditional valuation): **855 tests passed in406.78s**, installed Python3.12.0 / pytest9.1.1 / Streamlit1.61.1; external test transport blocked. Focused180, compilation/imports, fresh actual-app/harness health and synthetic REIT/proxy Generate/Refresh/horizon browser checks passed. See PLAN V-20261018-VALUATION-FRAMEWORKS for scope and unverified live-provider/model-quality limits.

The shared market ribbon now displays the latest reported S&P500, Nasdaq, Dow, Russell2000 and VIX levels with signed daily changes on every workspace that already showed it. FMP quotes share a five-minute cache; quote dates, saved/stale states and unavailable values remain visible, with all five indices retained on mobile. Cache expiry can load quotes on page entry/rerun without invoking AI. See [ribbon behavior and provenance](docs/MARKET_RIBBON.md).

Latest offline inventory (October18, shared market ribbon): **870 tests passed in204.99s**, installed Python3.12.0 / pytest9.1.1 / Streamlit1.61.1, external test transport blocked. Compilation/imports, app/harness health, desktop/mobile browser checks and cache reuse passed. A separate bounded live FMP check returned all five indices with dated quotes. See PLAN V-20261018-MARKET-RIBBON for scope and limits; no deployment or paid model calls.

Repository layout cleanup (October18): active application code lives under `src/` with the entry point `app.py`. Superseded `AI_Valuation_Tab/` and duplicate `partial_redesign/` uploads, plus the unreferenced standalone `crew_ai/stock_picker` tutorial, were archived outside the repository. The app?s CrewAI investment committee remains under `src/langgraphagenticai/deep_research/`; canonical design references, QA records and financial contract fixtures are preserved.

Cleanup verification reused the unchanged app?s latest870-test full result;14 focused release/provider tests passed, full collection still finds870 tests, and fresh compilation/staged credential-artifact/diff checks passed. Obsolete uploads/tutorial remain recoverable in a local sibling archive and are excluded from the repository. See PLAN V-20261018-REPOSITORY-CLEANUP.
