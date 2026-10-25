"""Maintained report-to-evidence map. Metadata only; never load consumers/providers."""
from copy import deepcopy
from .data_validation_catalog import endpoints

REPORTS = ("Market Brief", "Top Movers", "Stock Screener", "Research", "Equity Report",
           "AI Valuation", "Deep Research - Standard format", "Deep Research - Low cost format",
           "Portfolio Lab - Optimizer", "Portfolio Lab - AI Portfolio Manager", "AI Robo Advisor", "Data Validation")
_ROWS = []

def _add(report, family, places, ids, fields, calculation, basis, kind, sources):
    _ROWS.append(dict(report=report, family=family, places=places, endpoints=ids.split(),
                      fields=fields, calculation=calculation, basis=basis, kind=kind, sources=sources.split()))

# Metric-family contracts name active consumers; compatible endpoints are alternatives,
# not an assertion that every route is requested or every field exists in a response.
_add("Market Brief", "Macro / sector returns", "Executive market brief; heatmap; macro and sector tables",
 "fmp.v3.quote fmp.v3.history", "price, previousClose, changesPercentage, historical date/adjClose",
 "Return = (end price / baseline - 1) x 100. 5D uses observed sessions; 1M/3M use calendar anniversaries with a prior observation within seven days.",
 "Adjusted dashboard history; quote date compatibility checked; price-return diagnostics, not verified dividend cash flows.", "Provider + local calculation",
 "providers/market_dashboard.py providers/fmp_daily_prices.py analysis/market_dashboard.py analysis/sector_heatmap.py")
_add("Market Brief", "Market ribbon / membership", "Five-index ribbon; constituent ticker",
 "fmp.stable.batch-index-quotes fmp.v3.quote fmp.stable.sp500-constituent fmp.v3.sp500_constituent",
 "symbol, price, change, changesPercentage, previousClose; constituent symbol/name",
 "Provider percent aliases normalized; previous-close arithmetic only when valid. Current membership is not point-in-time.",
 "Quote timestamps retained; stale/undated status separate from page render time.", "Provider + local calculation",
 "providers/market_strip.py providers/ticker_ribbon.py")
_add("Market Brief", "Market news / executive interpretation", "Market news and sentiment; AI executive summaries",
 "fmp.stable.news/general-latest fmp.stable.fmp-articles marketaux.market serper.news",
 "title, url, publishedDate/published_at, source, description/content",
 "Normalize and deduplicate news; AI summarizes saved dated evidence only after explicit action. Narrative is not a provider metric.",
 "Publication time differs from retrieval time; incomplete coverage retained.", "Provider + AI interpretation",
 "providers/market_brief_news.py analysis/market_news_ai.py analysis/market_brief_ai.py")
_add("Top Movers", "Rankings / participation", "Leaders and laggards; sector concentration",
 "fmp.v3.stock-screener fmp.v3.stock-price-change fmp.v3.quote",
 "symbol, sector, marketCap, price changes (1D/5D/1M/ytd)",
 "Sort capped screen by selected horizon; sector counts/shares describe the screened set, not whole-market breadth.",
 "Provider horizon fields; current eligible universe, not historical membership.", "Provider + local calculation",
 "providers/discovery.py ui/top_movers_data.py ui/top_movers_tab.py")
_add("Top Movers", "Analyst expectations / social", "Selected company analyst targets and social activity",
 "fmp.v4.price-target-consensus fmp.v4.price-target-summary fmp.v4.upgrades-downgrades-consensus fmp.v4.historical/social-sentiment",
 "targetConsensus, targetHigh/Low, analyst counts; social activity fields",
 "Target upside = (target / compatible current quote - 1) x 100 where available. Analyst opinion and social activity are not realized returns.",
 "Dated provider consensus/activity; do not substitute missing counts with zero.", "Provider + local calculation",
 "providers/price_targets.py providers/analyst_consensus.py providers/social_sentiment.py")
_add("Stock Screener", "Universe / enrichment", "Universe filters; metric columns; post-filters",
 "fmp.v3.stock-screener fmp.v3.profile fmp.v3.quote fmp.v3.ratios-ttm fmp.v3.key-metrics-ttm fmp.v3.stock-price-change fmp.v3.rsi",
 "sector, industry, marketCap, price, ratios TTM, key metrics, price changes, RSI",
 "Server filters select a universe; optional enrichment/post-filters operate on fetched rows. Provider ratios are distinct from audited four-quarter research metrics.",
 "Provider TTM/quote dates and missing values remain separate; sector applicability varies.", "Provider + local filtering",
 "ui/stock_screener_tab.py")
_add("Research", "Chat evidence tools", "Research chat and tool responses",
 "mcp.quote mcp.profile mcp.income_statement mcp.balance_sheet mcp.cashflow_statement mcp.key_metrics mcp.metrics_ratios mcp.analyst_estimates mcp.stock_news marketaux.news",
 "Tool-selected provider quote, statements, ratios, forecasts and news fields",
 "Agent selects evidence tools for the explicit query. Tool availability is not proof of invocation; inspect each saved tool response and citation.",
 "Tool-dependent annual/quarter/TTM/forecast bases; never assume all tools share one period.", "Provider + AI interpretation",
 "tools/fmp_mcp_client.py tools/news_chat_tools.py")
_add("Research", "Guided evidence / exact citations", "Guided research plan, evidence and answer",
 "fmp.stable.quote fmp.stable.profile fmp.stable.income-statement marketaux.news",
 "Quote/profile identity; annual financial fields; article identity/date",
 "Explicit Prepare/Run dispatches allowlisted tools; exact cited fields/currency/date/basis are checked. Does not certify prose semantics or audited TTM.",
 "Annual FY facts distinct from quote point-in-time and news publication.", "Provider + validated references + AI interpretation",
 "providers/guided_research.py research/guided_workflow.py")
_add("Equity Report", "Company financials / growth", "Financials / Valuation; raw combined scorecard; research note",
 "fmp.v3.income-statement fmp.v3.balance-sheet-statement fmp.v3.cash-flow-statement fmp.v3.income-statement-as-reported fmp.v3.balance-sheet-statement-as-reported fmp.v3.ratios-ttm fmp.v3.key-metrics-ttm fmp.v3.ratios",
 "revenue, netIncome, cash flow, debt/cash/equity, provider ratios and fiscal dates",
 "Scorecard combines reported annual statements, provider TTM ratios and local growth/financial ratios. Trace each named column to its scorecard function; these are not universally audited research TTM.",
 "Annual, provider TTM and latest balance bases coexist with labels; missing and zero differ.", "Provider + local calculation",
 "ui/equity_report_tab.py deep_research/sector.py")
_add("Equity Report", "Sector scoring / rankings", "Recommendation snapshot; factor grades; sector coverage audit",
 "fmp.v3.profile fmp.v3.quote fmp.v3.ratios-ttm fmp.v3.key-metrics-ttm fmp.v3.analyst-estimates fmp.v4.price-target-consensus",
 "Sector, applicable factor inputs, forward estimates and targets",
 "Sector-specific applicability, weighted factor/peer rankings and decision rules; recommendation is relative to the compared peer set. Missing specialist data is not inferred.",
 "Provider annual/TTM/forward facts retain different meanings; scores are local outputs, not provider facts.", "Local scoring",
 "ui/equity_report_tab.py deep_research/sector.py")
_add("Equity Report", "Summary / CrewAI decision", "THESIS; executive PDF; CrewAI best-buy debate",
 "fmp.v3.profile fmp.v3.quote fmp.v3.ratios-ttm fmp.v3.key-metrics-ttm",
 "Saved scorecard ticker, factor scores and dated financial context",
 "Deterministic executive summary and optional AI note/debate use saved scorecard. Committee ticker/evidence checks do not certify prose. PDF includes only matching saved decision; no metric table or recollection.",
 "Saved input fingerprint ties committee to scorecard; generation date is not evidence freshness.", "Local summary + AI interpretation",
 "equity_committee.py analysis/equity_report_pdf.py ui/equity_report_tab.py")
_add("AI Valuation", "Conditional valuation / sensitivities", "Bull/Base/Bear cases; growth/multiple edits; horizon recalculation",
 "fmp.stable.quote fmp.stable.profile fmp.stable.income-statement fmp.stable.balance-sheet-statement fmp.stable.balance-sheet-statement-as-reported fmp.stable.analyst-estimates",
 "Dated annual diluted EPS, net income/diluted shares proxy, common book/share, quote and consensus EPS",
 "Projected per-share basis x exit multiple; growth compounds over the dated projection bridge. Financial P/B preference with earnings fallback; AI proposes assumptions and local code calculates prices.",
 "Annual reported/proxy EPS, eligible dated annual consensus and point-in-time quote are separate. No fabricated FFO/AFFO or NAV.", "Provider + local pricing + AI assumptions",
 "providers/valuation.py valuation/framework.py valuation/model.py valuation/projection.py valuation/book_value.py")
for report in ("Deep Research - Standard format", "Deep Research - Low cost format"):
    _add(report, "Audited financial metrics", "Financial evidence; quarterly audit; comparisons; reader report",
     "fmp.stable.income-statement fmp.stable.balance-sheet-statement fmp.stable.cash-flow-statement mcp.income_statement mcp.balance_sheet mcp.cashflow_statement",
     "Four fiscal quarters: revenue/net income/operating cash flow/capex; beginning/end asset/equity balances",
     "TTM flows sum four validated consecutive quarters. Latest balance sheet is independent; ROE/ROA use matched beginning/end average balances. Annual CAGR and forecasts stay separate.",
     "Standalone-quarter assumption disclosed; preserve fiscal periods, currency, formulas and raw inputs; incomplete series stays unavailable.", "Audited local calculation",
     "deep_research/quarterly_data.py deep_research/quarterly_ttm.py deep_research/research_metrics.py")
    _add(report, "Provider valuation / forecast context", "Valuation comparison; estimates; technical evidence",
     "mcp.metrics_ratios_ttm mcp.key_metrics_ttm mcp.analyst_estimates mcp.price_target_consensus mcp.historical_price_full",
     "Provider P/E, P/S, P/B, FCF yield, dated annual/quarterly consensus, targets and historical prices",
     "Provider valuation ratios and forecasts remain labeled context alongside independently audited financial metrics. Do not silently substitute provider TTM into an audited four-quarter measure.",
     "Actuals, consensus forecasts and price history use separate dates/bases; sector applicability and currency checks matter.", "Provider context + local normalization",
     "deep_research/data.py deep_research/research_metrics.py")
    _add(report, "Narrative / news / scenarios", "Executive report; committee; saved memo and earnings sensitivities",
     "mcp.profile mcp.quote mcp.analyst_estimates mcp.stock_news serper.news serper.search",
     "Dated quote/profile, forecast context, normalized news/search evidence; audited earnings/cap for eligible saved scenarios",
     "AI synthesizes saved evidence. Optional local earnings-multiple sensitivities use audited TTM total-company earnings and compatible dated market cap; distinct from per-share AI Valuation targets.",
     "V1/V2 engines remain separate; saved generation date is not source date; selected claim checks do not validate all prose.", "Provider + AI interpretation + local sensitivity",
     "deep_research/presentation.py analysis/investment_brief.py analysis/scenarios.py")
_add("Portfolio Lab - Optimizer", "Historical allocation / risk", "Optimizer weights, frontier, risk buckets and crisis analysis",
 "yahoo.history", "Adjusted Close history, benchmark history, user weights, risk-free assumption",
 "Returns from successive prices; weighted mean/covariance portfolio statistics, annualization and Sharpe use selected assumptions. Drawdown measures loss from prior cumulative peak; constraints and cash affect allocation.",
 "Adjusted-price history via Yahoo; historical statistics are not forecasts. Check window, benchmark, annualization and risk-free input.", "Local optimization / calculation",
 "ui/portfolio_optimizer_tab.py")
_add("Portfolio Lab - AI Portfolio Manager", "Holding evidence / scoring", "Recommendations; Evidence Scores; Agent Debate",
 "fmp.v3.profile fmp.v3.quote fmp.v3.income-statement fmp.v3.balance-sheet-statement fmp.v3.cash-flow-statement fmp.stable.company-screener yahoo.info yahoo.history",
 "Holdings/shares/cost basis; quotes, statements, ratios and price history",
 "Hybrid workflow combines saved fundamentals, valuation, momentum and risk features with explicit committee opinions. Inspect evidence scores and validator notes; missing provider inputs are not independently audited facts.",
 "Per-adapter FMP/Yahoo provenance and fiscal/price basis; no silent cross-provider series stitching.", "Provider + local scoring + AI interpretation",
 "portfolio_manager/research_snapshot.py portfolio_manager/scoring.py portfolio_manager/data_sources.py ui/ai_portfolio_manager_tab.py")
_add("Portfolio Lab - AI Portfolio Manager", "Target weights / trades / exposure", "Rebalance Trades; Sector Exposure; Monitoring; Diagnostics",
 "fmp.v3.quote yahoo.history", "Shares, current quote, portfolio value, target weights, sector/category",
 "Current value = shares x price; trade value = target value - current value. Position/sector/cash/trade thresholds and validation govern targets; committee narrative is separate.",
 "Hypothetical allocation; no broker execution; inspect residual cash, quote currency and historical risk assumptions.", "Local allocation / trade calculation",
 "portfolio_manager/portfolio_reporting.py ui/ai_portfolio_manager_tab.py")
_add("AI Robo Advisor", "S&P screen / mandate eligibility", "Latest collection diagnostics; sector screen; candidate selection",
 "fmp.stable.sp500-constituent fmp.v3.sp500_constituent fmp.stable.ratios-ttm fmp.stable.key-metrics-ttm fmp.stable.profile fmp.stable.news-stock fmp.stable.income-statement",
 "Current membership, sector, provider TTM ratios, sector percentiles, comparable annual revenue history, issuer tags/news",
 "Sector-priority weighted peer percentiles; required coverage/peer counts and positive margin/ROA gates; growth mandate needs positive comparable annual growth. Curated theme tags are not measured revenue exposure.",
 "Current S&P universe has survivorship bias; annual growth differs from provider TTM; one-hour screen reuse does not establish freshness.", "Provider + local screening",
 "providers/advisor_screen.py providers/advisor_research.py portfolio_architect/screening.py portfolio_architect/mandate_fit.py")
_add("AI Robo Advisor", "ETF allocation thesis", "Holding research; ETF roles and limits",
 "fmp.stable.profile fmp.stable.quote fmp.stable.historical-price-eod/full",
 "Fund identity/category, dated price and historical daily closes",
 "Funds receive role/conditional driver/risk assessments instead of company profitability valuation. Historical volatility/drawdown describe price behavior; missing fees, holdings overlap, duration and NAV stay unverified.",
 "Curated ETF universe separate from S&P stocks; FMP adjustment basis unverified; price returns exclude dividend cash flows.", "Local fund classification + AI interpretation",
 "portfolio_architect/etf_assessment.py portfolio_architect/screening.py")
_add("AI Robo Advisor", "Construction / risk / AI review", "Allocation; risk contributions; committee; stress assumptions; saved memo",
 "fmp.stable.quote fmp.stable.batch-quote fmp.stable.historical-price-eod/full",
 "Saved eligible candidates, daily prices, covariance, mandate caps/cash, subjective conviction",
 "Sector metrics and mandate rules select holdings; local allocation enforces hard caps and cash using the chosen sizing method. Active Robo Advisor AI only explains the fixed holdings and cannot change their weights. Earlier saved selection-review results retain their original behavior.",
 "Annualized daily price-risk statistics use 252 sessions; unstable history can trigger labeled fallback. No future loss/outperformance guarantee; AI review is optional.", "Local optimization + AI interpretation",
 "portfolio_architect/workflow.py portfolio_architect/construction.py portfolio_architect/risk.py portfolio_architect/risk_policy.py portfolio_architect/committee.py portfolio_architect/executive.py ui/advisor_executive.py")
# Shared company charts are reachable in these workspaces, but each retains its own raw evidence.
for report, places in (("Market Brief", "Daily company/index/ETF chart"), ("Top Movers", "Selected company chart"), ("Equity Report", "Performance; technical scorecard")):
    _add(report, "Price returns / technical indicators", places,
     "fmp.v3.history" if report == "Equity Report" else "fmp.stable.historical-price-eod/full fmp.stable.historical-chart/5min fmp.v3.history yahoo.history",
     "Timestamp, close/adjClose, volume and indicator window settings",
     "Price return = end/start - 1. Equity Report calculates its own return, moving-average and RSI signals; inspect its technical scorecard definitions." if report == "Equity Report" else "Price return = end/start - 1; local SMA/EMA, Wilder RSI, MACD and Bollinger calculations use observed bars and warmup.",
     "Whole-series fallback; never stitch providers. Use returned adjustment/timezone/coverage metadata; price return is not verified total return.", "Provider + local calculation",
     "ui/equity_report_tab.py" if report == "Equity Report" else "providers/symbol_history.py providers/fmp_daily_prices.py technical_analysis/indicators.py")
for report in ("Top Movers", "Market Brief"):
    _add(report, "Selected company fundamentals / news", "Selected-company panel; explicit company summary",
     "fmp.stable.profile fmp.stable.quote fmp.stable.ratios-ttm fmp.stable.key-metrics-ttm fmp.stable.income-statement fmp.v3.news marketaux.news serper.news",
     "Quote/profile/TTM fields, statements and dated company articles",
     "Snapshot normalizes company context; news merged/deduplicated. Explicit AI summary uses the saved packet and is labeled interpretation.",
     "Provider TTM and independently collected financial statements may differ; inspect per-metric basis and dates.", "Provider + local normalization + AI interpretation",
     "providers/company_terminal.py ui/company_snapshot.py providers/ticker_news.py")
_add("Data Validation", "Raw endpoint inspection", "Data table; JSON response; Request details",
 " ".join(e["id"] for e in endpoints()), "Selected provider response fields, exact requested parameters and retrieval timestamp",
 "No investment calculations or AI calls. Sanitized bounded raw preview; field filtering is display-only. Map is maintained metric-family documentation, not per-cell runtime lineage.",
 "Raw endpoint response is not automatically validated financial evidence; zero/null retained; preview may be truncated.", "Raw provider / metadata",
 "providers/data_validation.py ui/data_validation_tab.py")


def usages(report="All reports", family="All metric families", endpoint_id=None):
    return deepcopy([row for row in _ROWS if (report == "All reports" or row["report"] == report)
                     and (family == "All metric families" or row["family"] == family)
                     and (endpoint_id is None or endpoint_id in row["endpoints"])])


def endpoint_ids(report="All reports", family="All metric families"):
    if report == "All reports" and family == "All metric families":
        return {e["id"] for e in endpoints()}
    return {identifier for row in usages(report, family) for identifier in row["endpoints"]}


def calculation_index(report="All reports", family="All metric families"):
    """Index actual definitions without importing or executing financial/provider code.

    Includes helpers in referenced modules. A definition is not proof of runtime use.
    Later same-name module definitions supersede retained legacy definitions.
    """
    import ast
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    paths = sorted({path for row in usages(report, family) for path in row["sources"]})
    result = []
    for relative in paths:
        tree = ast.parse((root / relative).read_text(encoding="utf-8-sig"))
        definitions = {}
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                definitions[node.name] = node
            elif isinstance(node, ast.ClassDef):
                for method in node.body:
                    if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        definitions[node.name + "." + method.name] = method
        for name, node in sorted(definitions.items()):
            result.append({"Source file":relative, "Definition":name, "Line":node.lineno,
                           "Description":(ast.get_docstring(node) or "No function docstring; inspect source for implementation.").splitlines()[0][:240]})
    return result
