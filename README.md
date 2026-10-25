# Axiom Research

Research markets, compare companies, challenge valuations and review portfolios in one workspace.

**[Open Axiom Research on Hugging Face](https://huggingface.co/spaces/andrewnap211/Agentic-AI-Financial-Analyst-v2)**

The hosted app requires the owner's sign-in password. Contact the owner for access; never put passwords or API keys into research questions.

## Start here

1. Open the app, sign in, and expand the sidebar on a small screen.
2. Open **Settings** to check services. FMP supplies most financial data; OpenAI powers the main AI actions; Serper adds web research; Marketaux adds news. Groq is optional for Low cost Deep Research. A blank key field can still mean a service is configured by the owner.
3. Pick a workspace below. **Refresh** loads evidence; **Generate**, **Analyze** and **Run** explicitly request the associated analysis. AI actions can incur charges.
4. Check company identity, source dates, currency and financial period before using a result. Annual, quarterly, TTM and forward estimates are different bases; unavailable does not mean zero.
5. Download important work before signing out or restarting. Saved results usually stay in the current browser session; navigation does not make their evidence fresh.

## Market Brief

1. Click **Refresh market evidence**. Read the market ribbon, sector heatmap, macro/sector table and headlines.
2. Use **Generate / refresh market summary** and **Generate / refresh news briefing** for interpretation. Open **Ask AI about this dashboard** for a follow-up.
3. Under **Daily price chart**, enter a ticker, click **Update chart**, choose a range and open **Technical indicators & settings**. AI technical analysis is a separate action.

**Try:** chart `MSFT` over **1Y** with SMA and RSI, then ask: "Which sectors are leading over the past month, and what could challenge that trend?"

Check actual chart coverage and saved-data notices. Use **Refresh chart history** to reload prices; a new AI briefing alone does not refresh the dashboard.

## Top Movers

1. Click **Refresh movers**, then choose **Direction**, **Sector**, **Performance period** and **Ranking size**.
2. Select a company and inspect its quote, chart, news and available analyst coverage.
3. Use **Research this move** to prepare a Research draft, or **Open daily chart** for a closer chart view.

**Try:** compare technology **Leaders** over **1D** and **5D**, then investigate whether the available news supports a selected company's move.

Rankings describe the available capped screen, not the whole market. Missing news or analyst coverage is a data gap.

## Stock Screener

1. Set your universe and financial filters, then run the screen.
2. Review available metrics and optional post-filters; relax one filter at a time if too few companies qualify.
3. Download the CSV or use **Open Market Brief chart** for a selected company.

**Try:** screen profitable large-cap technology companies, shortlist three names, then compare them in Equity Report. Check missing-value handling before interpreting the shortlist.

## Research

1. Enter a question in **Research request draft**, then click **Submit research request**. Incoming company handoffs prepare a draft for you to review.
2. Continue the conversation with specific follow-ups. Use **New thread** when starting a separate topic or applying changed chat settings.
3. For **Guided research**, prepare a one-company plan, review its tools and cost assumptions, then explicitly run it. Inspect citations, missing evidence and any partial results.

**Try:** "Research MSFT's growth, cash generation and valuation. Separate reported facts from forecasts and identify the biggest evidence gaps."

Navigation preserves the thread. If a tool fails, keep successful facts and retry intentionally rather than assuming the whole answer is complete.

## Equity Report

1. Enter comma-separated **Tickers**, leave **Auto-detect sector framework** selected, choose the price-history dates and click **Run analysis**. The final OpenAI recommendation is optional.
2. Read **THESIS**, **PERFORMANCE**, **FINANCIALS / VALUATION** and **SOURCES / AUDIT**. Compare coherent peers and check sector applicability.
3. Optionally click **Run CrewAI best-buy debate**. In **EXPORTS**, download the PDF, Excel research pack or CSVs. Download the PDF after the debate to include its saved decision.

**Try:** `JPM, BAC, WFC`. Compare book value, returns and leverage before asking the committee which case is strongest.

A score depends on the chosen peers and available evidence. If a debate fails, the saved report remains available; retry the debate explicitly.

## AI Valuation

1. Enter **Company ticker**, choose **Target horizon (years)** and click **Generate AI Valuation**.
2. Read Bear/Base/Bull cases with their earnings or book-value anchor, growth, exit multiple, quote date and currency.
3. Open **Adjust scenario assumptions**, edit the inputs and click **Recalculate scenarios**. Review **Metrics, sources & valuation assumptions** or **Continue in Deep Research**.

**Try:** generate five-year `CVX` cases, reduce the Base exit multiple and compare the target change. Read the commodity-cycle limitations.

Targets are conditional price scenarios, not promises or total returns. Local assumption edits reuse saved cases. If no target is available, inspect missing positive annual inputs, currency or freshness notices before refreshing.

## Deep Research

1. Choose **Quick Brief**, **Deep Dive** or **Investment Committee**, enter companies and a decision-focused question, then review **Advanced settings** and submit the run form.
2. Quick Brief uses experimental **Low cost format**; Deep Dive uses **Standard format**. You can choose the engine explicitly in advanced settings or turn off **Use unified research controls**. The engines keep separate histories.
3. Read **Research overview**, the full report, sources, evidence gaps and any saved committee decision. Inspect **Numerical claim checks** for selected figures; these checks do not certify every statement or conclusion.
4. Reopen results through **Saved research across all goals**. For an interrupted eligible run, **Continue saved research** can reuse dated evidence with an explicit model action. Download the PDF, memo and available evidence/audit files.

**Try:** "Compare AAPL and MSFT over three to five years. Assess earnings growth, capital spending, free cash flow and valuation. Explain the main contrary evidence and what would invalidate your preference."

Under **Investment brief & scenarios**, eligible audited earnings support editable total-company equity sensitivities. These differ from AI Valuation's future per-share targets. **Use saved verified research** can transfer a qualified sensitivity to AI Valuation within the same session and FMP credential.

Low cost remains a pilot; displayed cost estimates are not guaranteed ceilings. Missing evidence can prevent scenarios or continuation. Refresh through a new research run when you need new facts.

## Portfolio Lab

### Optimizer

1. Enter tickers, select **Analysis period**, check dates and set the **Risk-free rate (annual, %)** and optional test weights.
2. Click **Run Portfolio Analysis**. Compare **Efficient Frontier**, **Risk / Return Table**, **Crisis Fingerprint Roles** and **Key Portfolio Weights**.

**Try:** `SPY, QQQ, TLT, GLD` over a custom period, then compare equal weights with the historical optimized allocation. Check dropped tickers and concentration; historical results are not forecasts.

### AI Portfolio Manager

1. Choose holdings, entered tickers or screening. For holdings, use the example, type positions or upload a file with `ticker` and `shares` columns.
2. Set benchmark, history and allocation limits in **Portfolio settings** inside this tab, then click **Run hybrid AI committee**.
3. Review **Recommendations**, **Rebalance Trades**, **Agent Debate**, **Sector Exposure** and **Diagnostics**. Download recommendation and rebalance CSVs.

**Try:** upload `MSFT,10` and `JPM,15` beneath the `ticker,shares` header, then examine how position/sector caps affect the proposal. These rows demonstrate the file format, not an allocation recommendation.

Trades are illustrative; nothing is sent to a broker. If constraints cannot be met, inspect diagnostics and residual cash rather than assuming full investment.

## AI Robo Advisor

1. Enter your objective and click **Interpret mandate**. Review the amount, horizon, preferences and **Advanced settings** before clicking **Build portfolio**.
2. Read **Your portfolio at a glance**, holding roles, risks and the **Executive investment memo**. Optional AI explains the fixed allocation; it does not choose new weights or holdings.
3. Download the concise memo PDF, Allocation CSV, Research HTML or Evidence JSON. Large evidence files may download as `.gz`; extract them to read the JSON.

**Try:** "Research a $25,000 portfolio for five years, with diversified equity exposure and a cash buffer." Confirm the interpreted amount and horizon before building.

The screen uses S&P 500 stocks plus curated ETFs and may take several minutes. **Enforce historical-volatility ceiling** checks historical price-return volatility, not future losses. A rejected build preserves the previous result. **Retry AI review using saved evidence** retries only the explicit explanation stage when eligible. Monitoring plans remain disabled; no scheduled alerts or trades run.

## Data Validation

1. Select **Report / workspace**, **Metric / calculation family** and an endpoint. Review **Report data & calculation map** and **Where this endpoint is used**.
2. Enter the required parameters and click **Fetch data**. Inspect **Response table**, **JSON response** and **Request details**; narrow the view with **Filter field names**.
3. Use **Download response JSON** or download the report map for review. Browsing the catalog makes no provider requests.

**Try:** fetch a supported income-statement endpoint for `AAPL`, then compare fiscal dates, currency and net-income fields with the metric-family explanation.

A successful response is not an accuracy certificate. For failures, inspect status: 401 suggests credentials, 402/403 access restrictions and 429 rate limits. A previous successful response retains its original inputs.

## A useful end-to-end exercise

1. **Market Brief**: identify a sector worth investigating.
2. **Top Movers / Stock Screener**: build a shortlist.
3. **Equity Report**: compare peers, then **AI Valuation**: challenge assumptions.
4. **Deep Research**: investigate the uncertainty that matters most.
5. **Portfolio Lab / AI Robo Advisor**: examine allocation and risk; download the saved result before ending the session.

If a page is empty, use its explicit Refresh/Run action and check Settings. If evidence is stale or an action failed, read the notice before retrying. Changed input drafts can differ from the last saved result. Sign-out clears the current session's work; the app is not a durable report library.

Axiom supports investment research, not personalized financial advice or guaranteed returns. Review sources, dates, assumptions and gaps before acting.

For operators: [Hugging Face setup](docs/HUGGING_FACE.md) and [deployment verification](docs/DEPLOYMENT.md).
