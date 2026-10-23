# Axiom Research

## A practical guide to researching markets, companies and portfolios

Axiom Research helps you move from a market question to a company shortlist, a comparative investment case, a valuation range and a portfolio discussion. This guide follows the screens you will use, explains what to click and gives examples you can adapt.

Start with a decision: **What deserves attention? Which company looks stronger? What would justify the current price? What should we change in the portfolio?** The examples below are demonstrations, not investment recommendations.

### Find your task

| Your question | Start here | What you will get |
| --- | --- | --- |
| What is happening in markets? | [Market Brief](#3-market-brief) | Market and sector context, headlines, charts and optional AI briefings |
| Which stocks are moving? | [Top Movers](#4-top-movers) | Leaders/laggards, company news, analyst views and social activity |
| Which companies meet my criteria? | [Stock Screener](#5-stock-screener) | A filtered company list to review and export |
| Can I ask a financial question? | [Research](#6-research) | A conversation or guided investigation of one company |
| How do these companies compare? | [Equity Report](#7-equity-report) | A comparative scorecard, financial analysis, charts and reports |
| What price could this company reach? | [AI Valuation](#8-ai-valuation) | Bear/Base/Bull targets, assumptions and sensitivity analysis |
| Can I prepare a fuller investment report? | [Deep Research](#9-deep-research) | An executive report, evidence, comparisons and optional committee |
| How should I evaluate my holdings? | [Portfolio Lab](#10-portfolio-lab) | Historical optimization and portfolio management |
| Can I build an evidence-backed research portfolio? | **AI Robo Advisor** | S&P 500 screening, ETFs, position research and saved session results |

## 1. Get ready

1. Open the application link provided by your team. For a local app, use the browser address supplied when it starts. Ask the app owner for access if you do not have a running application.
2. Open the sidebar. On a small screen, expand the navigation first.
3. Open **Settings** and check the available services. Your team may already have configured access; a blank password field does not necessarily mean a service is missing.
4. If needed, enter access keys supplied by your organization in the password fields. Do not paste them into research questions or uploaded files.
5. Keep your team's model selection initially. **Select OpenAI Model** controls the main AI experience. Low cost Deep Research has additional settings.
6. Choose a workspace. Several data views work without AI access; AI actions become available when their requirements are met.

### Which services do I need?

| Service in Settings | What it enables |
| --- | --- |
| **FMP API Key** | Most company financials, screening, quotes and research evidence; coverage depends on your subscription |
| **OpenAI API Key** | AI summaries, Research chat, AI Valuation, executive research and committee discussions |
| **Serper API Key** | Web/company news research, including the optional Deep Research investigation |
| **Marketaux API Key** | Additional financial news coverage and supported chat news requests |
| **Groq API Key (V2 pilot)** | An optional service for selected stages of Low cost Deep Research |

The Portfolio Lab **Optimizer** uses historical prices and does not require OpenAI. The Portfolio Manager currently does **not** use the Marketaux news overlay, even when that key is configured.

Open **AI Robo Advisor**, configure FMP in Settings, enter an objective, click **Interpret mandate**, review the controls and click **Build portfolio**. It screens current S&P 500 constituents using sector-relative quality, valuation, cash-flow and leverage metrics, then researches up to 30 stocks alongside curated ETFs. Read position evidence, dated news, annual revenue growth, market risks and conditional catalysts; download CSV/JSON/HTML or save a session snapshot. AI review is optional with OpenAI. Full screening may take several minutes when bulk access is unavailable. See the [Portfolio Architect guide](docs/portfolio_architect/USER_GUIDE.md) for controls and recovery.

AI analysis and committee actions can incur provider charges. Treat displayed costs as estimates, especially when pricing is unknown. More depth, more companies and committee decisions can increase usage.

## 2. Navigate and read results confidently

### Refresh data, then request interpretation

**Refresh** or **Load** retrieves information. **Generate**, **Analyze**, **Ask** or **Run** requests the associated analysis. Some actions combine collection and AI, such as **Generate AI Valuation**.

Changing tabs or reopening saved results generally reuses existing analysis. Sending another question, generating another interpretation or rerunning a committee is a new AI action. Changing a chart ticker or range can load price history without requesting AI.

### Read the market ribbons

On pages with the five-index ribbon, you will see S&P 500, Nasdaq, Dow, Russell 2000 and VIX levels with signed daily changes. The plus/minus sign gives direction alongside color. These are index levels, not dollar-denominated stock prices.

Quotes are cached for up to five minutes and can refresh when you open or rerun a page after that interval. This is not a continuously updating trading feed. Check the dates below the ribbon; hover over an index for details. **Saved**, **stale** and **undated** labels explain when extra attention is needed. Weekend quotes may correctly show the prior trading day.

Market Brief also has a scrolling S&P 500 constituent ribbon. Hover over or focus it to pause and inspect company quotes.

### Understand the information

| Label or term | How to use it |
| --- | --- |
| **As of / quote date** | When the observation applies; check before acting on a price |
| **Retrieved** | When the app obtained it; this may differ from the observation date |
| **Annual / FY** | A full fiscal year's reported results |
| **Quarterly / reported period** | A specific reported quarter |
| **TTM** | Trailing twelve months; check the ending period |
| **Forward / consensus** | An estimate of future results, not a reported fact |
| **Price return** | A price change over the stated window; do not assume dividends are included |
| **Unavailable / partial** | Missing or incomplete coverage, not zero |
| **AI interpretation** | A conclusion or assumption to assess against the evidence |

A newly generated report can contain older evidence. Check periods, currencies and quote dates before comparing values.

### Move a company to the next workspace

Use available handoff buttons such as **Research this move**, **Open daily chart**, **Open Market Brief chart** and **Continue in Deep Research**. Other workspace shortcuts appear where supported.

Check the destination ticker and settings before proceeding. A handoff can prepare a draft; it does not automatically submit AI research or transfer every figure from the previous page. The top command bar, where shown, can open a Research request: enter a ticker/question, click **RUN ANALYSIS**, then inspect and submit the draft.

### Keep work you will need later

Results are primarily retained in your current app session. Download important reports and tables before ending the session, restarting the app or switching devices. Returning to a page is not the same as refreshing its evidence.

## 3. Market Brief

**Use it for:** a morning market read, sector context, headlines and price-chart questions.

### Step 1: Load the market picture

1. Select **Market Brief** and click **Refresh market evidence**. The initial page can be empty until you do this.
2. Read the scrolling company ribbon, sector heatmap and **Macro context & sector ETFs** table.
3. Compare the daily move with longer windows, moving-average distances and RSI. A strong day can occur inside a weak longer trend.
4. Check stale-data and coverage notices. The sector tiles represent sector ETFs; their size does not represent market capitalization.

Returning here reuses the saved snapshot. Click **Refresh market evidence** for new dashboard and headline evidence.

### Step 2: Request the briefings

1. Click **Generate / refresh market summary** for an executive interpretation of the dashboard.
2. Click **Generate / refresh news briefing** for key headlines and news tone.
3. Open story/source disclosures to check the evidence behind a claim.
4. Use **Read full story** to visit the publisher. An app preview may not contain the complete article.

The data summary and news briefing answer different questions. Read both when price behavior and headlines appear to disagree.

### Step 3: Ask a market question

Open **Ask AI about this dashboard**, enter a **Market question**, then click **Ask market AI**.

> Which sectors show the largest divergence between today's move and their longer-term trend? Identify what I should investigate next.

> Does this dashboard suggest broad participation or concentrated leadership? Separate observations from interpretation.

> What are the three most important risks to this market picture? State which information is missing.

Follow-ups use available dashboard context; they do not themselves refresh the snapshot.

### Step 4: Examine a chart

1. Under **Daily price chart**, enter **Chart ticker**: for example `^GSPC`, `SPY` or `MSFT`.
2. Click **Update chart**.
3. Choose **1M**, **3M**, **1Y**, **3Y**, **5Y** or **10Y** in **Daily chart range**.
4. Use **Refresh chart history** to reload observations.
5. Open **Technical indicators & settings** and select **SMA**, **EMA**, **RSI**, **MACD** or **Bollinger**.
6. Adjust available windows. A window measured in bars counts observations, not calendar days.
7. Read the technical summary and indicator panels. With enough usable evidence, click **Analyze technical evidence with AI** for interpretation.

Try `MSFT` over **1Y** with SMA and RSI, then compare trend and momentum. Technical analysis complements business research; it does not establish valuation on its own.

## 4. Top Movers

**Use it for:** finding strength or weakness, then investigating a company.

### Step 1: Build the ranking

1. Select **Top Movers** and click **Refresh movers**.
2. Choose **Leaders** or **Laggards** under **Direction**.
3. Set **Sector** and **Performance period**: **1D**, **5D**, **1M** or **ytd**.
4. Choose **Top 50 stocks** or **Top 10%** in **Ranking size**.
5. Read the ranking, sector concentration tiles and participation chart together.

Top 10% uses the available filtered companies. The capped U.S. screen is not every listed stock; its sector participation is not whole-market breadth.

### Step 2: Investigate a company

1. Select a row or use **Selected company (keyboard alternative to table rows)**.
2. Review its quote, period change, chart and related news.
3. Click **Research this move** to prepare a Research draft, or **Open daily chart** to continue in Market Brief.
4. Inspect **More research workspaces** for other supported destinations.

Example request for the Research draft:

> Investigate MSFT's recent move. What do the available earnings, business developments and valuation indicate? Distinguish reported catalysts from possible explanations.

A related headline is a lead, not proof of causation. Rankings and separate charts may have different observation dates.

### Step 3: Interpret company news

1. Use **Load / refresh [ticker] news**.
2. Click **Generate / refresh [ticker] AI news summary** for the key stories and qualitative tone.
3. Open **News sources & coverage** and **Available company news** for dates and sources.

Selecting another company does not automatically commission its AI news summary.

### Step 4: Check analyst views

1. Select a **Consensus stock**.
2. Click **Load / refresh [ticker] analyst consensus**.
3. Read the rating gauge alongside counts and coverage.
4. Inspect the available analyst target comparison with the current quote.

?Last month? and ?last quarter? describe target publication windows, not one-month or three-month investment forecasts. These targets are separate from AI Valuation's three-to-five-year cases.

### Step 5: Explore social activity

1. Choose **Social history page limit**, then **Load / refresh [ticker] social history**.
2. Compare **Last 5 trading days** with **Latest 5 reported trading dates** in **Social date window**. The latter can show older dates when recent observations are missing.
3. Choose **Sentiment score**, **Posts**, **Comments**, **Likes** or **Impressions**.
4. Switch **Daily statistic** between **Average** and **Median**.
5. Under **Activity filters**, adjust **Minimum posts per platform snapshot** and **Hide zero sentiment scores**.
6. Open **Daily social statistics & coverage** for sample counts and gaps.

These controls compare available Stocktwits and Twitter snapshots. Treat low-activity spikes cautiously. Missing coverage is not neutral sentiment, and the score is not a probability that the stock will rise.

## 5. Stock Screener

**Use it for:** creating a research shortlist from explicit criteria.

### Step 1: Define the universe

1. Select **Stock Screener**.
2. Choose **Country**, **Exchange**, **Sector** and, optionally, **Industry contains**.
3. Open **Server-side range filters**. Keep **Wide open server-side defaults** for a broad starting list, or clear it to narrow the initial screen.
4. Set market-cap, price, volume, beta and dividend ranges. Market capitalization uses billions where the label says **$B**.
5. Adjust **Page size / API limit** and **Max pages to request** for broader coverage. More pages take longer and still do not guarantee a complete universe.

### Step 2: Choose result depth

1. Open **Enrichment + final output controls**.
2. Set how many companies receive additional metrics and how many appear in the final output.
3. Choose **RSI period** if using momentum filters.
4. Under **Post-screen metric filters**, enable filtering when wanted.
5. Set valuation, leverage, liquidity, profitability, dividend, RSI, 52-week-high and moving-average ranges as appropriate.
6. Review **Ignore missing metric values**. Allowing missing values can retain a company without evidence that it meets a criterion.
7. Click **Run Screener**.

### Example: a quality-company shortlist

Start with a familiar U.S. sector, minimum market cap of $10B and price above $5. Enrich a manageable number of companies, then investigate operating margin, return on capital and leverage. If few names remain, relax one criterion at a time and check missing coverage.

### Step 3: Use the results

1. Sort the final table and inspect coverage/partial-result notices.
2. Download the available CSV to share the shortlist.
3. Choose **Open screener company**, then **Open Market Brief chart**.
4. Alternatively, enter selected tickers in Equity Report or use **Use top screener results** in Standard Deep Research.

A screen identifies candidates; it is not a recommendation. A failed or empty rerun can preserve the earlier table. Confirm which run you are viewing before sharing it.

## 6. Research

**Use it for:** financial questions, follow-up conversations or a guided one-company investigation.

### Option A: Chat

1. Select **Research**, then **Chat** in **Research mode**.
2. In Settings, choose **Select Use Case**: **Basic Finance Chat**, **Single Company Analysis**, **Compare Companies**, **News and Earnings Review** or **Full Company Research Report**.
3. Enter or edit **Research request draft**. A request brought from another page still requires submission.
4. Click **Submit research request**.
5. Read the answer and supporting references. Continue with a more specific follow-up.
6. Inspect **Saved conversation and details**, where shown.
7. If model/use-case settings change, use **New thread** when requested.

Example prompts:

> Analyze MSFT's business quality, recent financial performance and valuation. Identify the strongest evidence for and against the case, and date the key inputs.

> Compare AAPL and MSFT for a three-to-five-year horizon. Focus on growth, margins, capital spending, cash generation and valuation. What uncertainties could change the comparison?

> Review recent earnings and news for CVX. Distinguish reported developments from assumptions about the oil cycle.

> What evidence would invalidate the thesis above, and what should I check after the next earnings release?

Use Deep Research for a longer structured report once the question is clear.

### Option B: Guided research

1. Choose **Guided research**.
2. Open **Configure guided research**; enter **One company ticker** and a **Focused research question**.
3. In **Spend limits and pricing**, set the estimated ceiling. Enter known model prices, or acknowledge that unknown pricing prevents a guaranteed dollar ceiling.
4. Click **Prepare new plan** and read it.
5. Keep the company, question and settings aligned with that plan, then click **Run plan**.
6. Review the answer and **Provider evidence, dates and usage**.
7. Use **Download saved evidence and answer**, or **Open Deep Research** for a broader investigation.

> For COST, what do annual financials and recent news establish about profitability, growth and valuation? Identify the missing information preventing a stronger conclusion.

Preparing and running a plan are separate actions. After changing inputs, prepare a matching plan before running again.

## 7. Equity Report

**Use it for:** comparing peers, reviewing a scorecard and preparing a research pack.

### Step 1: Set up the comparison

1. Select **Equity Report**.
2. Enter comma-separated **Tickers**, such as `AAPL, MSFT, GOOGL`.
3. Leave **Auto-detect sector framework** selected for a starting analysis. For an intentional manual comparison, inspect **Manual sector / peer framework**; mixed-sector comparisons need particular care.
4. Set **Price history from** and optional **Price history to** using the displayed date format.
5. Decide whether to enable **Use OpenAI final recommendation**. Leave it off for a financial scorecard without that AI recommendation.
6. Click **Run analysis**.

Use a coherent peer group when possible. A favorable score against a small or mixed group does not automatically establish an attractive investment.

### Step 2: Read the five tabs

| Tab | What to do |
| --- | --- |
| **THESIS** | Read the decision summary, ranking context and supporting recommendation |
| **PERFORMANCE** | Compare available price history and periods; check whether the apparent winner depends on the window |
| **FINANCIALS / VALUATION** | Examine profitability, growth, leverage and valuation comparisons |
| **SOURCES / AUDIT** | Check source coverage, dates, sector applicability and score inputs |
| **EXPORTS** | Download PDF Report, Excel Research Pack, Display CSV, Raw CSV and Ranking CSV where available |

Open available supporting notes and score/coverage explanations before relying on a rating. Missing or sector-inapplicable metrics should not be read as zero.

### Step 3: Request the optional committee

1. In the decision area, click **Run CrewAI best-buy debate**.
2. Read the competing views, selected company or ?none qualifies? outcome, risks and limitations.
3. Use **Run debate again** only when intentionally requesting another AI committee run.

The committee considers the saved comparison. It is an additional interpretation, not a fresh data collection or an instruction to place a trade.

### Example exercise

Run `JPM, BAC, WFC`, inspect book-value and return measures, then request a debate about the saved scorecard. Separately run a technology peer group; do not assume scores from these different groups are interchangeable.

## 8. AI Valuation

**Use it for:** a dated three-to-five-year price range and the business assumptions required to support it.

### Step 1: Generate the cases

1. Select **AI Valuation**.
2. Enter **Company ticker**, such as `MSFT`, `JPM`, `CVX` or a shortlisted company.
3. Select **Target horizon (years)**: **3**, **4** or **5**.
4. Click **Generate AI Valuation**. It loads available inputs and creates three cases in one action.
5. Check the reference price, earnings/book-value basis, method, quote date and currency.
6. Read **What the AI is using** to see the available company inputs.

Dated inputs from a recent Equity Report can be reused; missing inputs load separately. **Refresh company metrics** updates evidence without creating a new AI opinion. After refreshing, use Generate when you want cases rebuilt from the new evidence.

### Step 2: Interpret the range

Read each **Bear**, **Base** and **Bull** target with its upside/downside, annualized price return, growth, exit multiple and explanation. These are conditional future prices, not guaranteed outcomes. Dividends and changes in share count, currency or capital structure are not included in the price-return illustration.

Check the earnings anchor: a case may start from a dated annual consensus forecast, reported annual earnings or book value. Growth applies after that anchor, so do not add the same forecast growth again.

| Company situation | Framework you may see |
| --- | --- |
| Profitable operating company | Earnings-based P/E cases |
| Financial company with usable common book value | P/B cases; earnings fallback when book inputs are unusable |
| Energy or Materials | Conditional earnings cases with commodity-cycle limitations |
| REIT / real estate | Provisional earnings cases with missing FFO/AFFO/property-value limitations |
| Unknown sector | Company-specific earnings cases with limited sector context |
| Missing diluted EPS but usable annual income/share data | A labeled earnings-per-share proxy |

Broader coverage does not make all methods equally reliable. A usable positive annual basis, compatible currency and sufficiently dated evidence are still required. A company profitable only on recent-quarter or forward estimates may not qualify for this annual framework.

### Step 3: Challenge the assumptions

1. Read the **AI investment view**, catalysts, risks and conditions for reconsidering the thesis.
2. Open **Growth and valuation drivers** for the earnings path and exit multiple.
3. Inspect **Price targets versus current price** and **Growth and valuation sensitivity**.
4. Open **What would it take for the stock to double?** for the required growth under the displayed multiples. This is a hypothetical hurdle, not a forecast that the stock will double.
5. Open **Adjust scenario assumptions**, edit growth/multiples, then click **Recalculate scenarios**.
6. Distinguish edited targets from the original saved AI rationale. Recalculation does not request another AI opinion.
7. Inspect **Metrics, sources & valuation assumptions**, or choose **Continue in Deep Research**.

Changing the horizon reuses current saved cases and recalculates the target window. If the app flags older evidence, methodology or model settings, explicitly Generate again to rebuild them.

### Example exercise

Generate five-year `CVX` cases, read the cycle limitation, then reduce the Base exit multiple. Compare how much the target changes. Repeat for a profitable company in another sector and inspect why the method differs.

## 9. Deep Research

**Use it for:** a report tailored to a specific investment decision, with evidence, comparisons and an optional committee conclusion.

### Step 1: Choose the format

Open **Deep Research**, then choose **Research format**:

- **Standard format:** the main executive report workflow.
- **Low cost format:** the experimental alternative with additional cost/provider controls and its own saved run history.

Both complete report generation in a single research run; no separate user approval or editorial-review step is required to receive the executive report. The optional investment committee is a separate decision feature.

### Step 2: Run Standard format

1. Open **Configure new research**.
2. Enter one to four comma-separated symbols in **Companies**, or use **Use equity report tickers** / **Use top screener results**.
3. Write the **Research question** around the decision you need to make.
4. Choose **Investment horizon**, **Research depth** and **Financial statements**.
5. Set **News lookback (days)** and decide whether to include **Serper news and web research**. A requested window does not guarantee every story has a verified publication date.
6. Optionally select **Enable CrewAI investment committee** to request a decision with the run.
7. Click **Start deep research** and allow it to finish.

**Standard** and **Extended** are depth choices within a format; they differ from the Standard/Low cost format selector. Extended permits more investigation and can take longer or cost more.

**Include saved data from other tabs** is currently disabled. Importing tickers chooses companies; it does not mean every figure from another page has been accepted into this research.

### Questions that produce more useful reports

Name the company/comparison, horizon, decision and issues to resolve. Report sections can adapt to the question rather than follow one generic outline.

**Company comparison**

> Compare AAPL and MSFT over three to five years. Assess business quality, earnings growth, capital spending, free cash flow and valuation. Explain which case is stronger at the available prices, the main contrary evidence and what would invalidate the preference.

**Valuation**

> Assess whether COST's current valuation can be supported by available growth and profitability evidence. Explain assumptions, downside risks and milestones to monitor. Separate reported results from forecasts.

**Earnings review**

> Review NVDA's latest available results and forward expectations. Focus on growth durability, margins, investment requirements and risks to the earnings trajectory.

**Cyclical business**

> Examine CVX through a commodity cycle. Evaluate cash generation, capital discipline, dividend support and balance-sheet resilience. Identify conclusions depending on oil and gas assumptions not established by the evidence.

**Risk review**

> Write a downside-focused report on MSFT. Prioritize valuation compression, capital spending, competition and execution risk. Define concrete developments requiring us to revisit the thesis.

Prompts request an investigation; they do not establish that every specialist metric or source is available.

### Step 3: Read the Standard result

| Tab | How to use it |
| --- | --- |
| **Investment thesis** | Read the executive report, recommendation conditions, uncertainty and risks |
| **Company comparison** | Inspect Overview, TTM performance, Reported period, Forward & valuation, Sector metrics and Price trend where available |
| **CrewAI decision** | Read a saved conclusion or explicitly run a committee on an eligible completed report |
| **Sources & evidence** | Filter evidence, select an Evidence item and inspect dates/coverage |
| **Research notebook** | Inspect plan/run details and ask follow-ups about saved research |
| **Investment brief & scenarios** | Review saved excerpts and test eligible earnings/multiple sensitivities |

Use **Research history** to reopen runs. **Overview only**, **partial** or **incomplete** means the evidence/report did not support a full delivery. Inspect limitations and available sources before treating it as an investment conclusion.

### Step 4: Use committee and follow-ups

If no conclusion is saved, open **CrewAI decision** and click **Run CrewAI investment committee** when the completed report is eligible. Read recommendations, confidence, disagreements and conditions for changing the view.

In **Research notebook**, enter a **Follow-up question**, then click **Ask about this research**:

> What is the strongest argument against the preferred company, and which evidence would most change your conclusion?

> Create a monitoring agenda for the next earnings release using this report's risks.

Follow-ups and committees use saved research and are additional AI actions; they do not refresh market evidence. Start a new research run when the evidence itself needs updating.

### Step 5: Export the report

- **Download executive PDF:** a presentation-friendly report.
- **Download research memo:** an editable text document.
- **Download evidence & report:** the saved evidence/report record.
- **Download comparison CSV:** the comparison table.
- **Download metric audit CSV**, where offered: detailed financial inputs.

For the committee conclusion in the PDF, finish the committee first, then download the PDF for that same saved run. An earlier downloaded PDF does not acquire a later decision automatically.

### Low cost format

1. Switch to **Low cost format** and open its configuration area.
2. Enter **Companies** and the research question; set horizon, depth and statements.
3. Choose **Cost mode**: **Economy**, **Balanced** or **Maximum quality**. These are workflow choices, not guarantees of accuracy or savings.
4. Keep your team's **Light-stage provider/model** initially. OpenAI, Groq and a locally managed Ollama service are available when configured. Ask the app owner before changing an unfamiliar service address.
5. Set **Maximum estimated model cost (USD)**, **Include news** and **News lookback**.
6. Choose **Decision stage**: **None**, **Quick decision** or **Full committee**.
7. Select **Use saved result** to reuse a compatible run, or **Force fresh research** for a new investigation.
8. Click **Run V2 pilot**; this button name remains visible inside Low cost format.
9. Read **Report**, **Decision**, **Comparison**, **Sources**, **Performance** and **Investment brief & scenarios**.
10. Use **V2 run history** to select the result. Use **Retry decision** or **Run saved decision stage** when offered for an unfinished requested decision.
11. Use **Download PDF**, **Download memo** or **Download audit JSON**. The PDF includes a saved quick/committee decision once available.

**Performance** shows estimated usage, cost and elapsed time. Unknown pricing and incomplete coverage limit what these establish. **Use saved app data** remains disabled; saved-result reuse does not make evidence current.

### Investment brief and sensitivity scenarios

Available for saved Standard and Low cost research:

1. Read the saved excerpts and choose **Scenario company**.
2. With eligible inputs, edit each case's **earnings change (%)** and **P/E (user assumption)**.
3. Compare hypothetical **total equity value** with saved market capitalization and inspect the sensitivity chart.
4. Open **Saved scenario provenance** for dates and evidence.
5. Click **Download brief/scenarios JSON** or **Download brief/scenarios CSV**.

These user-entered sensitivities differ from AI Valuation's future per-share targets. Defaults are demonstrations; case names do not enforce outcome ordering. Eligibility is stricter here: scenarios can be unavailable even when AI Valuation offers a provisional method. Editing assumptions neither refreshes data nor requests a new AI forecast.

## 10. Portfolio Lab

**Use it for:** testing historical allocations or discussing portfolio changes. Start with **Optimizer**, or choose **AI Portfolio Manager**. For prompt-led portfolio construction, open **AI Robo Advisor** in the sidebar. None of these workflows places real trades.

### Option A: Optimizer

1. Select **Portfolio Lab**, then **Optimizer**.
2. Enter **Tickers (comma / space / newline separated)**. Start with a small set you understand, such as `SPY, QQQ, TLT, GLD`.
3. Choose **Analysis period**: **Custom period**, **2008-2009 Financial Crisis** or **2020 COVID Crash**.
4. For Custom period, set **Start date** and **End date**. Check the end date explicitly; its default may precede the latest market data.
5. Set **Number of random portfolios**. A smaller trial can help check your assumptions before a larger search.
6. Enter the **Risk-free rate (annual, %)** for your analysis assumption.
7. Choose **Test portfolio**: **None**, **Equal-weight (1/N)** or **Custom weights**. Custom weights follow ticker order; `0.40, 0.35, 0.25` means 40%, 35% and 25% for three tickers.
8. Click **Run Portfolio Analysis**.

Read the results in order:

- **Price Data:** confirm the actual period and any tickers dropped for missing history.
- **Efficient Frontier:** compare historical return/volatility combinations and locate Max Sharpe, Min Volatility and your optional test portfolio.
- **Risk / Return Table:** compare reported return, volatility, Sharpe and drawdown measures.
- **Crisis Fingerprint Roles:** examine how holdings behaved in the selected stress periods.
- **Key Portfolio Weights:** review concentration instead of choosing a portfolio solely for its highest historical statistic.

Historical optimization is not a forecast. The sample period, risk-free assumption and asset list can materially change the result. Returning without running again shows saved analysis where available; retain important findings before ending the session.

### Option B: AI Portfolio Manager

1. Select **AI Portfolio Manager**.
2. Choose **Analyze portfolio / uploaded holdings**, **Analyze entered tickers** or **Screen companies**.
3. For holdings, choose **Use example portfolio**, **Type holdings in app** or **Upload file**. Click **Download holdings template** if needed.
4. Use required `ticker` and `shares` columns and check every row in the editable table. The example remains a starting point until replaced; a missing upload does not create an empty portfolio.
5. Add **Optional watchlist tickers to analyze alongside holdings** if desired. Entered-ticker mode instead accepts a direct candidate list.
6. In Screen companies mode, set filters and how many returned names to analyze. The screened-candidate preview appears with the results after the run.
7. In the Portfolio Manager sidebar, set **Benchmark**, **Price history window**, **Risk profile**, **Maximum position weight**, **Maximum sector weight**, **Target cash buffer** and **Ignore trades smaller than**.
8. If a weight control shows decimals, `0.18` means 18% and `0.35` means 35%. Choose constraints consistent with your candidate list and acceptable concentration.
9. Click **Run hybrid AI committee**.

A simple holdings file looks like this:

```csv
ticker,shares
MSFT,10
JPM,15
CVX,12
```

This demonstrates the file format, not a proposed allocation.

### Read and challenge the proposal

| Tab | What to inspect |
| --- | --- |
| **Recommendations** | Proposed actions, target weights, conviction and company rationale |
| **Rebalance Trades** | Indicative share/weight changes relative to the supplied holdings |
| **Agent Debate** | Agreement and disagreement in the investment discussion |
| **Evidence Scores** | Evidence supporting the assessment |
| **Sector Exposure** | Concentration and the effect of sector limits |
| **Monitoring** | Developments that could trigger another review |
| **Diagnostics** | Missing inputs, constraints and qualifications |
| **AI Chat** | Questions about the saved portfolio analysis |

Use **Download recommendation table CSV** and **Download rebalance table CSV** for working copies. Review indicative trades against current holdings, prices, liquidity and costs before any execution outside the app. Residual cash can remain when constraints prevent full allocation.

In **AI Chat**, enter a **Question**, then click **Ask Portfolio Manager**:

> Which holdings contribute most to concentration risk, and why were their target weights chosen?

> Explain the strongest committee disagreement. What evidence would change the proposed allocation?

> Which monitoring triggers should we review after the next earnings season?

Chat uses saved analysis. Rerun the committee when you want a proposal based on newly collected evidence or changed portfolio settings.

### AI Robo Advisor

1. Open **AI Robo Advisor** and configure your FMP key in Settings. The page opens directly to portfolio construction.
2. Enter an objective, click **Interpret mandate**, review **Investment style** (choose **Growth** for a growth portfolio), holdings, asset types, cash, sector and position limits, then click **Build portfolio**. Optional AI uses the shared model and OpenAI key only for explicit actions.
3. Review **Holding research** for company descriptions, measured strengths, counterarguments, annual revenue growth and dated news. Read sector and market sensitivities before treating a possible catalyst as a reason to invest.
4. Open **Evidence & exports** for the S&P 500 screening audit and Market Brief indicators. Scores rank available sector metrics; they do not guarantee the best future performers. ETFs have a separate curated universe and no company-fundamental ranking.
5. With OpenAI configured, **Use bounded AI interpretation and specialist review** starts selected. Explicit **Interpret mandate** and **Build portfolio** actions produce a reviewed mandate and cited sector-aware AI theses. Read each holding's AI risks, missing evidence, portfolio role and thesis-break condition in **Holding research**. Invalid AI output preserves a local portfolio.
6. Choose **AI conviction + covariance risk budgets**, **Equal covariance risk budgets**, **Constrained minimum variance** or **Equal weight** in **Sizing method**, then **Build portfolio**. The first method uses bounded AI conviction to set relative historical risk budgets. In **Allocation**, compare capital weights with achieved risk contributions, target risk budgets, effective holdings and diversification ratio. Cash and hard caps take precedence; risk-budget caps can prevent exact target risk shares. Sparse or unstable history produces a disclosed equal-weight fallback. These methods do not forecast returns or enforce a future loss ceiling.
7. Use **Latest collection diagnostics** if provider or eligibility checks prevent a result. Collection pauses thirty seconds between batches of one hundred requests; a full screen can take several minutes. If FMP reports HTTP 429, wait for its limit to reset, then enable **Refresh provider evidence on next Build** and click **Build portfolio**. Download CSV, JSON or HTML, or save a session snapshot. Download important work before closing the app.

For a growth/AI objective, stock candidates need positive comparable three-year annual revenue growth; supported AI relevance and growth receive priority over a generic value score. Sector limits are enforced without adding unrelated sectors merely for variety. The universe stays current S&P 500 stocks plus curated ETFs. Business-description and curated theme matches are research clues, not measured AI revenue exposure.

The **Conviction / AI rationale** column includes a brief saved AI explanation with each validated rating. A status above the table says whether AI completed, failed or was not requested. If no validated review exists, the table says so; it does not invent an AI rationale. Older saved balanced results remain unchanged: explicitly choose **Growth** and **Build portfolio** to apply the new selection logic.

See the [Robo Advisor portfolio guide](docs/portfolio_architect/USER_GUIDE.md) for constraints, data limitations and recovery.

## 11. Put the workspaces together

### A morning investment meeting

1. Refresh **Market Brief** and read the market/news briefings.
2. Ask which observed developments deserve investigation without assuming headlines caused the moves.
3. Open **Top Movers**, compare Leaders/Laggards over 1D and 5D, then select a company.
4. Check its news and analyst coverage before sending a focused question to Research.

### A company-selection decision

1. Build a shortlist in **Stock Screener**.
2. Compare coherent peers in **Equity Report**.
3. Generate **AI Valuation** cases for a leading candidate and challenge Base assumptions.
4. Ask **Deep Research** to resolve the key uncertainty or compare finalists.
5. Run the optional committee, then download the executive PDF after its decision is saved.

### A portfolio review

1. Use **Optimizer** to understand historical diversification and stress behavior.
2. Upload checked holdings in **AI Portfolio Manager**, set limits and run the committee.
3. Review trades alongside concentration, evidence and monitoring triggers.
4. Send consequential company-level uncertainty to Research or Deep Research before acting.

## 12. When something is missing or does not work

| What you see | What to do |
| --- | --- |
| Empty Market Brief or Top Movers | Use Refresh; check data access and the coverage notice |
| An AI action is disabled | Check Settings, model and required inputs; load evidence first where requested |
| Missing news, social or analyst history | Check provider/company coverage; missing data is not a neutral result |
| Old or mismatched saved analysis | Confirm ticker, dates and settings; explicitly Generate or Run when you want to replace it |
| Failed refresh with older results visible | Inspect saved-result notices and original dates; retry the relevant refresh when access is restored |
| No valuation target | Inspect Metrics, sources & valuation assumptions for missing positive annual data, currency conflicts or stale/invalid evidence |
| An overview rather than a full recommendation | Inspect gaps/sources; refine the question or run fresh research when the information is available |
| Deep Research sensitivity scenarios unavailable | Read the reason; eligibility differs from provisional AI Valuation |
| Low cost decision did not finish | Keep the report and use the offered decision retry; a new report may be unnecessary |
| Fewer chart observations than expected | Check ticker/range, stated coverage and provider notices; use Refresh chart history to retry |
| Too few screened companies | Relax criteria one at a time, broaden coverage where appropriate and check missing-value handling |
| Portfolio result seems too concentrated | Review inputs, position/sector limits, the available universe and constraint warnings |

Before sharing a conclusion, check identities, source dates, financial periods, currency, assumptions and evidence gaps. Keep the supporting download with the executive summary. Axiom Research supports investment research and discussion; its output is not personalized financial advice or a guarantee of returns.

Large AI Robo Advisor evidence downloads use **Evidence JSON (.gz)** when needed. Extract the file to read the complete JSON; all saved evidence is retained. If compressed evidence still exceeds the download limit, the report, Allocation CSV and Research HTML remain available. Downloads reuse saved results.

If a saved Robo Advisor result says AI review was unavailable, click **Retry AI review using saved evidence** when OpenAI is configured. This explicit action reuses collected company evidence without repeating provider collection. If the saved quotes are too old, the app keeps your result and asks you to refresh and Build instead. Downloads and ordinary reruns never retry AI automatically.
