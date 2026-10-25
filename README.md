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
| What data is a provider returning? | [Data Validation](#data-validation) | One selected endpoint, request details, response inspection and JSON download |

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

Market Brief also has a decorative S&P 500 constituent ribbon that rotates left to right without a scrollbar. Hover over or focus it to pause; reduced-motion settings stop the animation.

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

1. Click **Generate / refresh market summary** for a fuller executive view of the past **5 trading days**, **month** and **3 months**: macro crosscurrents, sector leaders and laggards, technical confirmation and what to watch. Monthly comparisons use calendar months; they differ from the table's 30/60 trading-session figures.
2. Click **Generate / refresh news briefing** for one or two connected paragraphs on the main market drivers, crosscurrents and what could change the outlook. Open **Briefing evidence & coverage** to review provider coverage, supporting themes and limitations. Summaries omit citation numbers and verbal source references. Available descriptions, previews and article text inform the briefing; previews are not complete articles.
3. For optional reading beyond the summary, use **Read full story** in the separate news cards. An app preview may not contain the complete article.

The data summary and news briefing answer different questions. Read both when price behavior and headlines appear to disagree. Refresh market evidence before generating the updated formats when your saved dashboard predates the monthly comparisons. News refresh combines bounded searches for leadership, macro/rates and cross-asset risks with configured Marketaux and FMP coverage; it does not capture every market story.

If the news briefing reports a source or saved-snapshot mismatch, the attempted answer is rejected and any earlier saved briefing remains available. Click **Generate / refresh news briefing** to request another answer using the saved articles; no automatic retry occurs. Refresh market evidence separately only when you want new articles.

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
8. Open **Ask historical technical questions**. Enter a ticker, **From** and **Through** dates and a question, then click **Ask technical AI**. For example: "How did momentum and MACD change during the 2020 recovery?" Answers use available daily prices and indicators and explain missing history. Changing the draft or reopening the page does not commission another answer.


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
3. Read the consolidated company briefing, sentiment and investment implications. Citation numbers and source links do not interrupt the summary.

Selecting another company does not automatically commission its AI news summary.

If a company briefing is rejected for a stock, snapshot or source mismatch, click **Generate / refresh [ticker] AI news summary** again using the loaded news. Any existing summary for that stock remains available; there is no automatic retry or news refresh. Publication-timezone and missing-date warnings describe source coverage and may remain after a successful summary.

### Step 4: Check analyst views

1. Select a **Consensus stock**.
2. Click **Load / refresh [ticker] analyst consensus**.
3. Read the rating gauge alongside counts and coverage.
4. Inspect the available analyst target comparison with the current quote.

?Last month? and ?last quarter? describe target publication windows, not one-month or three-month investment forecasts. These targets are separate from AI Valuation's three-to-five-year cases.

### Step 5: Explore social activity

1. Configure FMP and OpenAI, then click **Generate / refresh [ticker] social summary**.
2. Read the **Positive**, **Negative** or **Neutral** assessment and short explanation of participation and direction.
3. Treat missing, stale or conflicting observations as uncertainty. More posts alone does not indicate positive sentiment. A failed refresh keeps your saved summary.


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

To include a committee opinion, select **Run CrewAI best-buy debate** in **THESIS**. Once it completes, open **EXPORTS** and select **Download PDF Report**. The PDF includes the complete saved executive summary, AI research note and matching CrewAI decision, including dissent, risks and invalidation signals. The PDF uses a portrait executive layout with clear headings and readable paragraphs; financial metrics tables remain in the app and Excel rather than this narrative PDF. Longer reports span multiple pages. Downloading does not rerun analysis. If the debate failed or belongs to an older scorecard, the PDF states that no matching decision is available; retry the debate explicitly to add one.

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

Open **Deep Research**. The unified research controls open by default for new sessions:

1. Choose **Quick Brief**, **Deep Dive**, or **Investment Committee**. Quick Brief uses the experimental Low cost workflow; Deep Dive uses Standard. Committee preselects additional committee analysis, which you can disable before starting.
2. Enter companies and your question. Open **Advanced settings** to change depth, news, committee options, providers or estimated budget. **Advanced settings ? engine and routing** lets you choose the other engine explicitly. Missing access is disclosed; the app does not switch engines automatically.
3. Submit the run form to start research. Selecting a goal does not spend credits. Committee can add model calls after a completed report. Standard has no enforced dollar ceiling; Low cost's estimated budget cannot guarantee a ceiling when pricing is unknown.
4. Read **Research overview**, then the full report, sources, gaps and optional decision below. Missing overview sections stay unavailable; they are not generated on display. Existing follow-ups, briefs and downloads remain in their original engine views.
5. Turn off **Use unified research controls** to return to **Research format**. Both engines retain their separate saved histories. Use **Saved research across all goals** to reopen either engine's saved report without starting research. For an unfinished report with usable evidence, open **Continue saved research**, acknowledge that its evidence will not refresh, then click **Continue report using saved evidence**. This may use model credits; it preserves source dates and does not run a committee. Failed continuation preserves the original report and downloads. Missing evidence or saved configuration requires an explicit fresh run.

For a saved one-company report, you can optionally open **Independent specialist review · experimental**. Review the disclosed limits, check **I understand the pilot limitations and additional model calls**, then click **Run independent specialists on saved evidence**. The fundamentals and valuation/risk specialists work separately; the summary preserves disagreements and partial failures. At most one additional call can resolve a named metric from the saved data. This action has its own limits outside the original report budget; unknown pricing prevents a guaranteed dollar ceiling. It does not refresh evidence, change portfolio constraints or launch a committee. Older, stale or incomplete financial contracts may make the pilot unavailable. The full source/check audit stays in the expander; these mechanical checks do not verify model prose. Reopening a review makes no calls.

Open **Earnings data quality** to compare the saved quarterly, annual and TTM net-income amounts and their validation states. The view keeps fiscal dates, original retrieval dates, reporting currencies and filing/acceptance metadata separate. Zero and losses remain values; missing, stale, inconsistent or unverifiable earnings are labeled. A TTM total requires four matching raw fiscal quarters. Failed validation preserves the original report amount and explains why it cannot support new earnings sensitivities or the specialist earnings review. No refresh or AI call occurs when opening this view. For newer evidence, explicitly start fresh research. **Download brief/scenarios JSON** and **Download brief/scenarios CSV** include the same earnings observation and source audit. These checks cover total company earnings, not EPS, FFO/AFFO or forecast accuracy.

With unified controls off, choose **Research format**:

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

1. Open **Executive investment memo** in either research format to review the saved thesis, evidence highlights, valuation, drivers, risks, quality and assumptions. Numerical highlights show their saved period and source IDs; this does not refresh evidence or certify AI conclusions.
2. Click **Executive investment memo PDF** for a concise first page followed by the retained narrative, decisions, detailed saved data and complete source records. Complete any optional committee first, then download again to include its decision. Existing report and evidence downloads remain available.
3. If the memo exceeds its PDF size limit, use the original report and evidence downloads. Unsupported PDF glyphs appear as explicit Unicode codes; original text remains in the other saved formats.

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
7. In **Portfolio settings** within the **AI Portfolio Manager** tab, set **Benchmark**, **Price history window**, **Risk profile**, **Maximum position weight**, **Maximum sector weight**, **Target cash buffer** and **Ignore trades smaller than**.
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

1. Open **AI Robo Advisor** and configure your FMP key in Settings.
2. Describe the objective and click **Interpret mandate**. Confirm style, horizon, risk preference and hypothetical amount in **2. Review your mandate**. Open **Advanced settings** for holdings, cash, limits, exclusions, themes, benchmark and sizing. Click **Build portfolio** to apply the reviewed settings.
3. Read **Portfolio recommendation** and **Recommendation snapshot**. The table shows allocations, sector framework, available sector score and coverage, main support and main concern. Sector scores describe saved peer comparisons, not expected returns or fair value. Missing scores remain unavailable.
4. Choose **Review a holding**. Read **Why included**, **Main risk** and **What would change the thesis**. Open **Sector metrics behind this recommendation** for saved values and priorities, then **Metric sources, periods and evidence IDs** for the calculation inputs. ETFs show an allocation role and fund risks rather than a company profitability score.
5. With **Use AI to interpret and explain** enabled, explicit Build sends the locally selected holdings to one analyst for a concise explanation. Sector metrics and your objective select holdings; local rules set weights. AI cannot add, replace or resize holdings. Invalid AI output leaves the local portfolio available.
6. Open **How allocations were determined** for sizing. **Covariance risk budgets**, **Equal covariance risk budgets**, **Constrained minimum variance** and **Equal weight** remain in Advanced settings. Cash and position/category caps take precedence; unstable history can produce a labeled equal-weight fallback. Historical methods do not enforce a future loss ceiling.
7. Open **Detailed research, risk & exports** for full holding research, risk checks, audit tables and exports; **Download concise portfolio memo** keeps the saved memo available. Use **Latest collection diagnostics** if collection or eligibility blocks the build. A full screen can take several minutes. If a run is interrupted within the same session, use **Retry AI review using saved evidence** when offered. Full browser-session/server restarts can lose session-only work; download completed results before closing.

For a growth/AI objective, stock candidates need positive comparable three-year annual revenue growth; supported AI relevance and growth receive priority over a generic value score. Sector limits are enforced without adding unrelated sectors merely for variety. The universe stays current S&P 500 stocks plus curated ETFs. Business-description and curated theme matches are research clues, not measured AI revenue exposure.

Earlier saved portfolios retain their original selection, sizing and AI results. The reader labels older AI selection workflows; explicitly Build to use metrics-led selection and explanation-only AI. The sector priorities are shared with Equity Report, but available provider TTM and annual evidence is narrower than the full Equity Report suite and is not independently audited TTM.

Changed inputs leave the last generated portfolio available with a mismatch notice. Interpret a revised objective and explicitly Build to apply reviewed controls; display changes and saving do not rebuild.

See the [Robo Advisor portfolio guide](docs/portfolio_architect/USER_GUIDE.md) for constraints, data limitations and recovery.

## Data Validation

1. Under the **Validate** sidebar ribbon, select **Data Validation** in the sidebar. Choose **Data provider**, then **Endpoint**. Stable and legacy FMP routes, retained FMP research tools, Marketaux, Serper and Yahoo operations are listed separately.
2. Enter one **Ticker**, such as `AAPL` or `SPY`. Market-wide endpoints ignore the ticker and say so. For Serper, optionally enter a **Search query**.
3. Open **Request parameters** when needed. For example, select **Income statement - stable** and use `{"period": "quarter", "limit": 8}` to inspect quarterly records. Dates use `YYYY-MM-DD`. Only the selected endpoint's listed parameters are accepted; credentials come from **Settings**.
4. Click **Fetch data**. This requests the selected operation only. Provider quotas may apply; opening this page and changing controls do not fetch data or run AI.
5. Review **Data table**, **JSON response** and **Request details**. Check ticker identity, provider dates, fiscal period, currency and zero versus missing values. Use **Filter field names** to focus the table. A successful request is not a financial-accuracy check.
6. Click **Download response JSON** to save the sanitized response and original request details. A large response may be limited; narrow the parameters if the page flags a preview limit. The table shows at most 500 rows; retained response lists are capped at 1000.
7. If a request fails, inspect **Failed request details**. HTTP 401 points to authentication; 402/403 indicate access restrictions; 429 indicates rate limiting. The last successful response remains visible with its original inputs. Changed inputs show a mismatch notice; changed credential settings require a new fetch before viewing prior data.

Open **Endpoint catalog & usage** to see the registered operations and their app usage. Catalog presence does not establish access on your provider plan. Yahoo and Serper return adapter output, and Yahoo history explicitly uses adjusted prices. Ticker-specific entitlement, data freshness and financial correctness still need your review.

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


### Optional portfolio risk policy

1. Open **AI Robo Advisor**, interpret the objective, then expand **Advanced settings** in **2. Review your mandate**.
2. To require a historical check, enable **Enforce historical-volatility ceiling** and set **Historical annualized volatility ceiling (%)**. Confirm with **Build portfolio**. This checks an aligned historical price-return estimate, not future losses or personal suitability.
3. If the ceiling fails or history is insufficient/stale, the build stops and the previous portfolio stays available. Explicitly change cash, sizing, holdings or the ceiling, then build again. Limits are never relaxed automatically.
4. In **Risk & tradeoffs**, review the saved policy checks, concentration warnings and hypothetical account shocks. Shocks use stated assumptions and unchanged cash; they are not forecasts. ETF underlying exposure, benchmark constituent weights and account turnover/costs are unavailable when supporting holdings and cost inputs are missing.
5. Use **Evidence JSON** or **Research HTML** to retain the saved policy and shock assumptions. Legacy results without this audit remain readable; explicitly build to create a new audit.


### Numerical claim checks in saved research

1. Open a saved **Deep Research** result in either **Standard format** or **Low cost format**. **Numerical claim checks** shows separate coverage, freshness and reconciliation counts. Interpretation remains unassessed.
2. Expand **Claim findings, evidence and verification limits** to inspect each extracted line, supporting inputs, status and remediation. A contradiction is a reason to inspect the original sources; the app keeps the report unchanged.
3. Read **verified numerical fact**, **derived calculation**, **assumption/opinion**, **contradicted** and **unverifiable** as distinct labels. A verified amount does not verify the thesis or a future price target. Zero matched lines means no numerical certification.
4. Use **Claim verification JSON** to save the dated checks and original report/evidence fingerprints. Opening the panel, rerunning and downloading make no provider or model calls.

The bounded checker supports explicit ticker, amount, currency, date and citation statements for company earnings, TTM revenue, price/market cap and dated P/E arithmetic. It does not infer meaning from ambiguous prose, certify every metric or rewrite unsupported claims. Extraction limits and unsupported text remain visible; fresh research remains a separate explicit action.


### Reuse saved verified research in AI Valuation

1. Explicitly run new **Deep Research** in **Standard format** or **Low cost format** with your configured FMP credential. Reopening an older run does not establish its originating credential.
2. Open **Reuse verified financial research** on the saved result and choose the company. Eligible data needs validated four-quarter earnings, compatible explicit quote currency, dated capitalization and matching provider sector information.
3. Click **Use saved verified research** to open **AI Valuation** with a local earnings sensitivity. Edit **Saved earnings change (%)** and **Saved earnings P/E assumption** to calculate hypothetical total-company equity value. These assumptions are not forecasts, per-share price targets or personalized advice.
4. Review the original earnings period, capitalization date and **Verified snapshot provenance**. Opening, navigating and editing reuse these inputs without provider/model calls. Annual per-share AI targets remain a separate explicit Generate action.
5. If the company, credential, session, original sources or freshness no longer qualify, financial reuse is rejected and the saved research stays available. Explicitly collect fresh research to prepare a new snapshot, or choose **Open AI Valuation with ticker only** to navigate without active financial reuse.

Reuse is limited to this browser session and originating FMP credential. It does not grant redistribution rights or enable advisor/portfolio reuse. Quote retrieval must be within one day and the quote observation within seven days; earnings/profile retrieval and fiscal dates retain their disclosed limits. Original timestamps are preserved.


### Prepare a disabled monitoring plan

1. In **AI Robo Advisor**, review a completed model portfolio and click **Save session snapshot**.
2. Expand **Monitoring plan ? activation unavailable** and check **Prepare a disabled plan for this saved portfolio**.
3. Click **Prepare monitoring plan**. Review the immutable holdings, constraints, benchmark, saved thesis and source timestamps. Up to six disabled plans are retained in the session; choose one with **Disabled monitoring plan**.
4. **Enable monitoring** remains unavailable. No scheduled refresh, paid analysis, alerts or trades start. Secure sign-in, protected background processing and eligible data access must be verified before activation.

The prepared plan starts no alerts or trades. Automatic earnings/estimate monitoring and ETF underlying exposure checks remain unavailable. Preparing a plan does not refresh old evidence or certify future risk.

### Review and export a saved portfolio memo

1. After **Build portfolio**, open **Executive investment memo** to review positions, weights, roles, sector concentration, available historical risk, assumptions and gaps. The figures describe the saved allocation and observation window. ETF look-through and future performance remain unverified.
2. Click **Executive investment memo PDF**. Full holding roles, citations, saved committee, risk conventions and source records follow its first page. Daily price series remain in **Evidence JSON**; **Allocation CSV** and **Research HTML** remain available. Downloads and reopening the memo reuse saved results without collecting data or calling AI.

### Access and saved sessions

1. Use the local application in your own research session. Separate browser sessions keep separate conversations and saved outputs; they are not a shared account or a durable report library.
2. Download important reports before restarting the server. Automatic recovery of research after restart is not available in the app.
3. If a deployment shows **Hosted access is disabled**, its operator must complete sign-in, data isolation and release verification before opening access. This message does not mean your provider key is invalid.


### Read your AI Robo Advisor result

1. Start with **Your portfolio at a glance** for tickers, names, allocation percentages and short selection reasons.
2. Read the holding summaries immediately below for the investment case and portfolio role. An allocation without a completed AI review uses its saved local selection reasons.
3. Open **Download concise portfolio memo** for the executive PDF. Open **Detailed research, risk & exports** for the existing review tabs; the concise PDF does not include the full research universe or daily price histories.

If an Equity Report committee analyst times out, the saved report remains available. Retry the explicit debate or choose a faster model. The app does not automatically commission another debate.


AI Robo Advisor collects the current S&P 500 screen using the same FMP key as Equity Report and regular company endpoints, paced in request groups. A fresh full screen can take several minutes; saved screen evidence is reused for up to one hour. Use **Refresh provider evidence on next Build** and **Build portfolio** to recollect explicitly. ETFs use separate allocation theses for core equity, growth/sector, dividends, small caps, Treasuries, bonds and gold. Review each fund's role, conditional drivers and risks. Available saved-history volatility and drawdown describe price returns only; fees, holdings overlap, tracking, duration and NAV valuation remain unavailable where evidence is missing.


In **Data Validation**, choose **Report / workspace** to focus on a report, then **Metric / calculation family** to narrow its inputs. Open **Report data & calculation map** for display locations, provider fields, calculation rules and period limitations. **Where this endpoint is used** explains the selected endpoint in context; **Calculation code index** lists current definitions and source lines. Download the report map as JSON for review. These filters make no requests; only **Fetch data** retrieves a provider response. The map documents metric families and source code, rather than certifying every value or AI conclusion.


For runtime, verification and retained-reference locations, see the [repository layout](docs/REPOSITORY_LAYOUT.md).


Executive investment memo PDFs are prepared when you click their download button. Opening a saved report or navigating does not generate the full memo appendices; repeated downloads reuse the same prepared content until the saved report or decision changes. No provider or AI call is made by the download.
