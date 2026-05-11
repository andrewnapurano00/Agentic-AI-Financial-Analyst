# Agentic AI Financial Analyst

A Streamlit-based financial research and portfolio analysis application powered by LangGraph, OpenAI, Financial Modeling Prep data, Marketaux news, yfinance price data, and a hybrid multi-agent portfolio committee workflow.

The app is designed to help users research public companies, compare peer groups, screen stocks, analyze portfolio risk/return, and generate agentic portfolio recommendations using a combination of deterministic evidence-building and AI decision-making.

> **Disclaimer:** This application is for research, education, and portfolio analytics support only. It does not provide personalized financial advice, investment recommendations, or guarantees of future returns. Always validate outputs with your own analysis before making investment decisions.

---

## Table of Contents

- [Core Features](#core-features)
- [Application Pages](#application-pages)
  - [1. Agent Chat](#1-agent-chat)
  - [2. Equity Research Report](#2-equity-research-report)
  - [3. Portfolio Optimizer & Backtests](#3-portfolio-optimizer--backtests)
  - [4. Stock Screener](#4-stock-screener)
  - [5. Agentic AI Portfolio Manager](#5-agentic-ai-portfolio-manager)
- [Architecture Overview](#architecture-overview)
- [Data Sources](#data-sources)
- [Installation](#installation)
- [Environment Variables](#environment-variables)
- [Running the App](#running-the-app)
- [How to Use the App](#how-to-use-the-app)
- [Example Agent Chat Prompts](#example-agent-chat-prompts)
- [Project Structure](#project-structure)
- [Downloadable Outputs](#downloadable-outputs)
- [Troubleshooting](#troubleshooting)
- [Future Enhancements](#future-enhancements)

---

## Core Features

This project combines several finance analytics workflows into one application:

- **Agentic finance chat** using LangGraph and OpenAI.
- **FMP-backed financial tools** for company profiles, quotes, statements, ratios, valuation, analyst estimates, ratings, calendars, ESG data, and research bundles.
- **Marketaux-powered news tools** for enhanced company news retrieval and news Q&A when a Marketaux API key is available.
- **CFA-style equity research reports** with sector-aware scoring, factor grades, valuation analysis, growth analysis, profitability analysis, leverage review, technical signals, price return charts, and downloadable PDF/Excel reports.
- **Offline-first portfolio optimizer** using yfinance price history, efficient frontier simulation, Sharpe ratio analysis, drawdown metrics, beta, volatility, and crisis-period diagnostics.
- **Rule-based stock screener** using Financial Modeling Prep with server-side filters and optional post-screen metric enrichment.
- **Hybrid agentic portfolio manager** where deterministic calculations build evidence, an AI committee makes final portfolio decisions and target weights, and a constraint validator fixes position/sector limits and math consistency.

---

## Application Pages

The Streamlit app is organized into five primary tabs.

---

## 1. Agent Chat

The **Agent Chat** page is the natural-language interface for company analysis, comparisons, valuation questions, news review, earnings transcript review, and tool-driven financial research.

### What it does

The chat agent uses a LangGraph workflow with OpenAI and a centralized finance tool registry. Depending on the prompt, the agent can call tools for:

- Company profile and overview data.
- Current quote and market data.
- Historical price performance.
- Financial statements.
- Financial ratios and key metrics.
- Analyst estimates.
- Analyst ratings and stock grades.
- Price target consensus.
- DCF and levered DCF valuation data.
- Earnings calendar and dividend history.
- Earnings transcript discovery and transcript retrieval.
- Sector, industry, peer, and directory/reference data.
- ESG data where available.
- Marketaux news summaries and news Q&A when configured.

### Use case selector

The sidebar includes a **Select Use Case** dropdown. The selected use case adjusts the system prompt and response style:

- **Basic Finance Chat**: general finance questions and flexible company research.
- **Single Company Analysis**: compact full-company analysis across business, financials, price action, catalysts, and risks.
- **Compare Companies**: balanced multi-company comparison across fundamentals, valuation, growth, news, and risk.
- **News and Earnings Review**: emphasizes catalysts, guidance tone, earnings transcript takeaways, and recent news.
- **Full Company Research Report**: produces a structured research-style answer with business overview, financial highlights, news/catalysts, risks, and bottom line.

### Table behavior

If the user asks for a table, comparison table, ranking, matrix, or scorecard, the chat workflow attempts to return structured JSON that the app converts into a clean Streamlit dataframe. This helps avoid messy markdown tables and inconsistent formatting.

### Debug mode

The sidebar includes **Show debug trace**. When enabled, the app displays the graph message path and tool outputs in an expandable trace. This is useful for diagnosing which tools were called and what data was returned.

---

## 2. Equity Research Report

The **Equity Research Report** page builds a story-first, sector-aware equity comparison report for one or more tickers.

### What it does

This tab pulls company fundamentals, market data, technicals, historical valuation averages, price history, analyst-related fields, and sector-aware scoring inputs. It converts the raw data into a research-ready report with both tables and narrative summaries.

### Main inputs

- **Tickers**: comma-separated ticker list such as `AAPL, MSFT, NVDA, GOOGL`.
- **Use OpenAI final recommendation**: optionally adds an OpenAI-generated recommendation note.
- **Auto-detect sector framework**: attempts to infer the appropriate sector framework from company profile data.
- **Manual sector / peer framework**: used when auto-detection is off or when the ticker list spans multiple sectors.
- **Price history from / to**: controls the price history window used for return charts and technical analysis.

### Report sections

The page is split into several sub-tabs:

#### Research Story

Includes:

- Executive summary.
- OpenAI final recommendation, if enabled.
- Recommendation snapshot.
- Selected sector/peer framework.

#### Price Return Chart

Allows the user to select a return period and compare ticker price performance. The app displays both a return table and a line chart.

Supported return periods include common windows such as short-term, year-to-date, 1-year, multi-year, and maximum available history depending on data availability.

#### Metric Sections

Displays simplified research sections such as:

- Profile.
- Ratings.
- Factor grades.
- Momentum.
- Total return.
- Valuation.
- Growth.
- Profitability.
- Balance sheet / leverage.

For important sections, the app also adds research takeaways explaining the drivers behind the metrics.

#### Audit / Raw Data

Includes:

- Sector metric coverage audit.
- Raw combined scorecard.

This page helps users validate where the report had strong data coverage versus where fields were unavailable.

#### Downloads

Provides downloadable outputs:

- PDF equity research report.
- Excel research pack.
- Display CSV.
- Raw CSV.
- Ranking CSV.

---

## 3. Portfolio Optimizer & Backtests

The **Portfolio Optimizer & Backtests** page is an offline-first portfolio analytics tool that uses historical price data to evaluate risk, return, drawdowns, efficient frontier behavior, and crisis-period roles.

### What it does

This page uses yfinance price data to calculate portfolio analytics without requiring the LLM. It is designed for quantitative portfolio review and historical risk/return testing.

### Main inputs

- **Ticker list**: defaults to a diversified example list such as `VTI, VTV, MGK, JPM, MSFT, CVX, LMT`.
- **Date range**: controls the historical testing window.
- **Risk-free rate**: used in Sharpe ratio calculations.
- **Regime / testing mode**: allows the user to evaluate full-period or crisis-specific behavior.
- **Test portfolio**: choose no test portfolio, equal-weight portfolio, or custom weights.
- **Custom weights**: accepts values such as `20%, 20%, 15%, 15%, 10%, 10%, 10%` or decimal equivalents.

### Output sections

#### 1. Price Data

Confirms whether historical prices were fetched successfully.

#### 2. Efficient Frontier

Simulates portfolios and visualizes risk/return tradeoffs. The optimizer identifies key portfolios such as maximum Sharpe and minimum volatility.

#### 3. Risk / Return Table

Shows asset-level metrics such as:

- Annualized return.
- Annualized volatility.
- Sharpe ratio.
- Max drawdown.
- Beta.
- Downside volatility.

#### 4. Crisis Fingerprint Roles

Evaluates how assets behaved during major market stress periods such as:

- Global Financial Crisis.
- 2011 downgrade / eurozone stress.
- 2015-2016 China/oil selloff.
- COVID-19 crash.
- 2022 rates/inflation drawdown.

This helps classify assets by their defensive or cyclical behavior during historical stress windows.

#### 5. Key Portfolio Weights

Displays the weights for selected optimized portfolios and/or user-specified test portfolios.

---

## 4. Stock Screener

The **Stock Screener** page is a rule-based Financial Modeling Prep screener with optional metric enrichment. This page does not use the LLM.

### What it does

The screener first applies broad FMP server-side filters, then optionally enriches the resulting companies with additional metrics and technical indicators.

### Server-side filters

Users can filter by:

- Country.
- Exchange.
- Sector.
- Industry text search.
- Market cap range.
- Price range.
- Volume range.
- Beta range.
- Dividend range.
- API page size.
- Maximum pages to request.

### Enrichment controls

Users can choose:

- Maximum tickers to enrich with metrics.
- Final number of companies to display.
- RSI period.

### Optional post-screen metric filters

The app can apply filters after enrichment for metrics such as:

- P/E.
- Price to sales.
- Price to book.
- Debt to equity.
- Current ratio.
- RSI.
- ROE.
- ROA.
- ROIC.
- Operating margin.
- Net margin.
- Dividend yield.
- Distance from 52-week high.
- Percent above 50-day moving average.
- Percent above 200-day moving average.

### Final output

The final screener output is sorted by market cap and includes enriched company, valuation, profitability, leverage, dividend, and technical fields where available.

---

## 5. Agentic AI Portfolio Manager

The **Agentic AI Portfolio Manager** page is the app’s hybrid multi-agent recommendation engine for portfolio decisions and rebalancing.

### What it does

This page implements a hybrid workflow:

1. **Deterministic evidence builder** gathers portfolio holdings, current values, sector exposure, technical/momentum data, valuation and fundamental evidence, and risk signals.
2. **AI committee** reviews the evidence and makes final buy/hold/sell/trim/add decisions and target weights.
3. **Constraint validator** checks the AI target weights and adjusts only when needed to satisfy rules such as maximum position weight, maximum sector weight, target cash buffer, and total weight summing.
4. **Rebalance engine** converts target weights into actionable trade values and share changes.

The news overlay is intentionally disabled in this tab to reduce token usage and keep the portfolio workflow focused on technicals, momentum, fundamentals, valuation, portfolio fit, and concentration rules.

### Portfolio input options

Users can enter portfolio holdings in three ways:

- Use the example portfolio.
- Type holdings directly in the app.
- Upload a CSV or XLSX file.

The expected holdings format is:

```csv
ticker,shares
AAPL,25
MSFT,18
NVDA,12
JPM,14
XOM,16
```

The app also provides a downloadable holdings template.

### Sidebar controls

The Portfolio Manager sidebar includes:

- **Benchmark**: default is `SPY`.
- **Price history window**: `1y`, `2y`, or `5y`.
- **Risk profile**: Conservative, Balanced, or Aggressive.
- **Maximum position weight**: caps single-name concentration.
- **Maximum sector weight**: caps sector concentration.
- **Target cash buffer**: optional cash allocation.
- **Ignore trades smaller than**: suppresses small rebalance noise.

### Output tabs

After clicking **Run hybrid AI committee**, the page produces several sub-tabs:

#### Recommendations

Shows the compact recommendation grid with:

- Ticker.
- Company name.
- Sector.
- Asset type.
- Final action.
- Committee conviction.
- Current weight.
- Target weight.
- Weight change.
- Trade value.
- Share change.
- Constraint flags.

Below the grid, the page shows ticker-by-ticker committee decision summaries so the user can clearly see the rationale, risks, monitoring triggers, target weights, and trade values without cluttering the main table.

#### Rebalance Plan

Shows detailed trade instructions including:

- Final action.
- Rebalance action.
- Trade direction.
- Current and target values.
- Current and target shares.
- Share change.
- Last price.
- Trade priority.
- Rebalance reason.

#### Agent Debate

Shows the internal committee views used to support the final recommendation. This is useful for understanding how different agents evaluated the portfolio.

#### Evidence Scores

Displays the evidence table used by the AI committee, including the deterministic signals and scoring inputs.

#### Sector Exposure

Shows current and target sector allocation so the user can evaluate whether the portfolio remains diversified after rebalancing.

#### Monitoring

Lists follow-up risks, watch items, and triggers that should be monitored after the recommendation.

#### Diagnostics

Displays run diagnostics and raw AI committee results. This is useful for debugging model output, fallback behavior, target weight validation, and data availability.

#### AI Chat

Lets the user ask a focused follow-up question about the latest portfolio run. This chat uses compact context from the generated recommendations and does not pull news articles.

Example questions:

```text
Why did the committee recommend these target weights?
```

```text
Which holdings contributed most to portfolio concentration risk?
```

```text
What are the highest-priority trades and why?
```

---

## Architecture Overview

The app is built around a `src/` Python package layout.

At a high level:

- `app.py` loads environment variables, adds `src/` to the Python path, and starts the Streamlit app.
- `main.py` initializes Streamlit session state, loads sidebar configuration, builds the LangGraph finance agent, validates API keys, and renders the five main tabs.
- `LLMS/openaillm.py` creates the OpenAI model client.
- `graph/graph_builder.py` builds the LangGraph tool-calling workflow.
- `nodes/chatbot_with_Tool_node.py` contains the chatbot/tool node logic.
- `prompts/system_prompts.py` defines use-case-specific system prompts.
- `tools/finance_tool_registry.py` registers the available finance tools.
- `tools/` contains MCP-backed FMP tools and Marketaux news tools.
- `ui/` contains the Streamlit tab renderers.
- `portfolio_manager/` contains the agentic committee, evidence builder, hybrid workflow, constraint validator, and rebalance logic.
- `utils/` contains formatting, response cleaning, health checks, and logging utilities.

---

## Data Sources

The app uses multiple data sources depending on the page:

### Financial Modeling Prep

Used for:

- Company profiles.
- Quotes.
- Statements.
- Ratios.
- Key metrics.
- Analyst estimates.
- Analyst ratings.
- Price targets.
- DCF and levered DCF.
- Earnings calendars.
- Dividend data.
- Earnings transcripts.
- Company screener.
- Sector/industry/reference data.
- ESG data where available.

### OpenAI

Used for:

- Agent Chat reasoning.
- Tool-driven finance responses.
- Equity report recommendation notes.
- Agentic portfolio committee decisions.
- Portfolio Manager follow-up chat.

### Marketaux

Optional. Used for:

- Recent company news retrieval.
- News summaries.
- News question answering.

Marketaux is intentionally disabled in the AI Portfolio Manager tab to reduce token usage.

### yfinance

Used for:

- Portfolio Optimizer price history.
- Historical risk/return calculations.
- Efficient frontier simulation.

---

## Installation

### 1. Clone the repository

```bash
git clone <your-repository-url>
cd <your-repository-folder>
```

### 2. Create a virtual environment

Using `venv`:

```bash
python -m venv venv
```

Activate it on Windows:

```bash
venv\Scripts\activate
```

Activate it on macOS/Linux:

```bash
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Environment Variables

The app can read API keys from sidebar inputs, Streamlit secrets, or a `.env` file.

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your_openai_api_key_here
FMP_API_KEY=your_fmp_api_key_here
MARKETAUX_API_KEY=your_marketaux_api_key_here
```

`MARKETAUX_API_KEY` is optional, but required for enhanced news workflows.

For Streamlit Cloud or another hosted deployment, use `.streamlit/secrets.toml`:

```toml
OPENAI_API_KEY = "your_openai_api_key_here"
FMP_API_KEY = "your_fmp_api_key_here"
MARKETAUX_API_KEY = "your_marketaux_api_key_here"
```

The repository includes `.streamlit/secrets.toml.example` as a template.

---

## Running the App

Run the Streamlit app from the project root:

```bash
streamlit run app.py
```

Then open the local Streamlit URL shown in the terminal.

---

## How to Use the App

### Step 1: Start the app

Run:

```bash
streamlit run app.py
```

### Step 2: Configure the sidebar

In the sidebar:

1. Select the OpenAI model.
2. Select the Agent Chat use case.
3. Enter API keys if they are not already loaded from `.env` or Streamlit secrets.
4. Optionally enable debug mode.

The sidebar displays whether OpenAI, FMP, and Marketaux keys were detected.

### Step 3: Choose a page

Use the top tabs:

- **Agent Chat** for natural-language research.
- **Equity Comparison Report** for sector-aware multi-ticker research reports.
- **Portfolio Optimizer** for historical risk/return and efficient frontier analytics.
- **Stock Screener** for rule-based company discovery.
- **AI Portfolio Manager** for hybrid agentic portfolio recommendations and rebalancing.

### Step 4: Download outputs

Several pages include downloadable outputs such as CSV, Excel, PDF, and holdings/recommendation templates.

---

## Example Agent Chat Prompts

Use these prompts in the **Agent Chat** tab to test core functionality.

### Single-company analysis

```text
Analyze AAPL across business overview, financials, valuation, technicals, catalysts, and risks.
```

```text
Give me a full investment analysis of MSFT using fundamentals, analyst expectations, valuation, DCF, ratings, technicals, and risks.
```

```text
Build a buy/hold/sell view for GOOGL using company profile, quote, valuation, analyst estimates, ratings, recent price performance, and risks.
```

### Company comparison

```text
Compare AAPL and MSFT across analyst estimates, valuation, ratings, DCF, price target upside, and 5-year price return. Return a table and a short conclusion.
```

```text
Compare AAPL, MSFT, and NVDA across fundamentals, analyst expectations, DCF valuation, price target upside, ratings, and technical momentum.
```

```text
Rank AAPL, MSFT, NVDA, GOOGL, and AMZN from best to worst using fundamentals, analyst estimates, valuation, price target upside, ratings, DCF, and technical momentum.
```

### Analyst estimates and ratings

```text
What are analyst estimates for AAPL for the next two fiscal years? Include revenue, EPS, and growth expectations.
```

```text
Which has the better analyst setup right now: AAPL, MSFT, or GOOGL? Compare estimates, ratings, and price target upside.
```

```text
For AMZN, summarize analyst expectations, price target upside, and the current ratings snapshot.
```

### Valuation and DCF

```text
Run a valuation analysis for NVDA using DCF, levered DCF, trading multiples, and analyst price targets.
```

```text
Is META undervalued or overvalued based on DCF, analyst targets, and current valuation multiples?
```

```text
Give me a valuation summary for JPM including DCF, market cap, analyst targets, and key financial ratios.
```

### News and earnings

```text
Summarize recent news and transcript takeaways for NVDA.
```

```text
What were the key themes from MSFT's latest earnings call?
```

```text
Find available earnings transcript periods for AAPL.
```

```text
Summarize AAPL Q2 2025 earnings transcript with management tone, guidance, risks, and analyst Q&A takeaways.
```

### Calendar and dividends

```text
When does AAPL report earnings, and what does its recent earnings calendar history look like?
```

```text
Does MSFT pay dividends? Summarize its dividend history and recent dividend trend.
```

```text
Compare the dividend profiles of JPM, BAC, and WFC.
```

### Technical analysis

```text
Give me a technical indicator summary for NVDA using RSI, moving averages, trend strength, and recent price momentum.
```

```text
Which looks technically stronger right now: AAPL, MSFT, or NVDA?
```

```text
Compare the 5-year price return for AAPL, MSFT, NVDA, and GOOGL.
```

### Portfolio watchlist

```text
Create a portfolio watchlist table for AAPL, MSFT, NVDA, AMZN, and META with current price, market cap, revenue growth, margins, analyst upside, DCF upside, ratings, and technical signal.
```

---

## Project Structure

```text
.
├── app.py
├── requirements.txt
├── pyproject.toml
├── README.md
├── data/
│   └── sample_holdings.csv
├── .streamlit/
│   ├── config.toml
│   └── secrets.toml.example
├── src/
│   └── langgraphagenticai/
│       ├── main.py
│       ├── LLMS/
│       │   └── openaillm.py
│       ├── graph/
│       │   └── graph_builder.py
│       ├── nodes/
│       │   └── chatbot_with_Tool_node.py
│       ├── prompts/
│       │   └── system_prompts.py
│       ├── state/
│       │   └── state.py
│       ├── tools/
│       │   ├── finance_tool_registry.py
│       │   ├── fmp_mcp_client.py
│       │   ├── company_overview_tools.py
│       │   ├── financial_statement_tools.py
│       │   ├── price_data_tools.py
│       │   ├── earnings_transcript_tools.py
│       │   ├── analyst_tools.py
│       │   ├── valuation_tools.py
│       │   ├── calendar_tools.py
│       │   ├── directory_tools.py
│       │   ├── esg_tools.py
│       │   ├── research_bundle_tools.py
│       │   ├── news_pipeline_tools.py
│       │   └── news_chat_tools.py
│       ├── ui/
│       │   ├── equity_report_tab.py
│       │   ├── portfolio_optimizer_tab.py
│       │   ├── stock_screener_tab.py
│       │   ├── ai_portfolio_manager_tab.py
│       │   ├── streamlitui/
│       │   │   └── loadui.py
│       │   └── components/
│       │       ├── pm_cards.py
│       │       ├── pm_charts.py
│       │       ├── pm_explainability.py
│       │       ├── pm_filters.py
│       │       └── pm_tables.py
│       ├── portfolio_manager/
│       │   ├── hybrid_workflow.py
│       │   ├── agentic_committee.py
│       │   ├── evidence_builder.py
│       │   ├── constraint_validator.py
│       │   ├── rebalance_engine.py
│       │   ├── decision_engine.py
│       │   ├── data_sources.py
│       │   ├── analytics.py
│       │   ├── research_snapshot.py
│       │   ├── portfolio_reporting.py
│       │   ├── scoring.py
│       │   ├── schemas.py
│       │   └── agents/
│       │       ├── fundamental_agent.py
│       │       ├── valuation_agent.py
│       │       ├── technical_agent.py
│       │       ├── risk_agent.py
│       │       ├── portfolio_fit_agent.py
│       │       ├── lead_pm_agent.py
│       │       └── debate_orchestrator.py
│       └── utils/
│           ├── app_health.py
│           ├── formatters.py
│           ├── logging_utils.py
│           └── response_cleaner.py
└── tests/
    ├── test_app_health.py
    ├── test_formatters.py
    └── test_response_cleaner.py
```

---

## Downloadable Outputs

The app can generate several downloadable files:

### Equity Research Report

- PDF report.
- Excel research pack.
- Display CSV.
- Raw CSV.
- Ranking CSV.

### AI Portfolio Manager

- Holdings template CSV.
- Recommendation table CSV.
- Rebalance table CSV.

### Stock Screener

- Final screener table can be exported from Streamlit's dataframe interface or extended with a download button if desired.

---

## Troubleshooting

### `ModuleNotFoundError: No module named 'langgraphagenticai'`

Run the app from the project root:

```bash
streamlit run app.py
```

`app.py` adds `src/` to the Python path before importing the package.

### API key is not detected

Check one of the following:

1. The key is entered in the Streamlit sidebar.
2. The key exists in `.env` in the project root.
3. The key exists in `.streamlit/secrets.toml` for Streamlit deployment.

Expected `.env` format:

```env
OPENAI_API_KEY=your_key
FMP_API_KEY=your_key
MARKETAUX_API_KEY=your_key
```

### Agent Chat returns missing or `N/A` values

Possible reasons:

- The data provider did not return the requested field.
- The selected endpoint does not support that ticker.
- The API key does not have access to the requested data.
- The prompt asked for a metric that is not available in the current tool registry.

Enable **Show debug trace** in the sidebar to inspect which tools were called and what they returned.

### Earnings transcript prompt asks for clarification

The chat agent is intentionally instructed not to guess transcript periods. If you ask for a transcript without quarter and year, it may ask for clarification unless you explicitly say “latest” or “most recent.”

Good examples:

```text
Summarize AAPL Q2 2025 earnings transcript.
```

```text
Summarize the latest MSFT earnings transcript.
```

### Portfolio Manager target weights were adjusted

The AI committee proposes actions and target weights, but the constraint validator may adjust them to satisfy:

- Maximum position weight.
- Maximum sector weight.
- Cash buffer.
- Total target weight sum.
- Minimum trade threshold.

Adjusted names and target-weight validation details appear in the Portfolio Manager diagnostics.

### yfinance price data fails

The Portfolio Optimizer depends on yfinance. If price data fails:

- Confirm the tickers are valid.
- Try fewer tickers.
- Try a shorter date range.
- Re-run after a short delay if Yahoo data is temporarily unavailable.

---

## Future Enhancements

Potential future improvements:

- Add persistent portfolio storage.
- Add broker-ready trade export format.
- Add portfolio scenario analysis with macro regimes.
- Add richer sector-specific metrics for banks, REITs, insurers, and energy companies.
- Add a dedicated news/catalyst overlay back into Portfolio Manager as an optional toggle.
- Add benchmark-relative attribution.
- Add tax-aware rebalancing.
- Add model evaluation logs for committee decisions.
- Add Streamlit authentication for deployed use.

---

## Summary

Agentic AI Financial Analyst is a multi-page financial research and portfolio analysis app that combines deterministic financial analytics with LLM-powered reasoning. It supports natural-language research, structured equity reports, portfolio optimization, stock screening, and hybrid agentic portfolio recommendations.

The app is best used as a research assistant and portfolio decision-support tool: it helps gather evidence, compare companies, explain tradeoffs, and generate structured outputs that can be reviewed, exported, and improved over time.
