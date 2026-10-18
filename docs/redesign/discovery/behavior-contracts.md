# Behavior contracts and route trace — 2026-10-13

`app.py` calls `main.load_langgraph_agenticai_app`; `LoadStreamlitUI` injects `app_shell` CSS, applies discovery and pending handoff, resolves eight-route sidebar navigation and configuration. `main.py` validates readiness before routing. Introduction and Top Movers use early returns; all other routes receive shared command bar, market strip and page header. This is a presentation difference, not a separate route identity.

| Route/mode | Active entry and relevant helpers | State/provider boundary to preserve |
| --- | --- | --- |
| Introduction / market + company | `introduction_tab.render_introduction_tab`, `_dashboard`, `_render_market_chart`, `_render_company_snapshot`; `company_snapshot`, `company_terminal`, `technical_chart`, `opening_presentation` | `state.discovery`, `state.research_context`; `market_overview_data`, `providers.symbol_history`, company terminal adapter, Marketaux; explicit technical/company AI only |
| Top Movers | `top_movers_tab.render_top_movers_tab`, `ranked_display`; `top_movers_data`, `research_news` | Capped discovery screen, selected period/sector/company, one-time native table selection and keyboard alternative, saved identity, FMP/Serper partial states |
| Research Chat | `main.py` else branch, `_maybe_reset_thread_for_config_change`, `_render_prior_chat`, `_render_assistant_response` | `research_mode`, draft, thread/history/fingerprint, typed context metadata; explicit submit/chat input invokes graph; debug trace conditional |
| Research Guided | `guided_research_tab.render_guided_research_tab` | Separate Prepare/Run controls, spend/price acknowledgement, saved plan/result, evidence field citations, JSON export and handoff |
| Equity Report | `equity_report_tab.render_equity_report_tab` | Active render path and its helpers, saved payload/tickers, peer/scoring/committee fingerprint, five report tabs and exports |
| Stock Screener | `stock_screener_tab.render_stock_screener_tab` | Server filters, enrichment/post filters, pagination and limits, explicit Run, saved table, CSV/handoff |
| Portfolio Lab / Optimizer | `portfolio_optimizer_tab.render_portfolio_optimizer_tab` | Inputs, regimes, histories, frontier, risk/return, weights and backtest output |
| Portfolio Lab / Manager | `ai_portfolio_manager_tab.render_ai_portfolio_manager_tab`, `components.pm_*` | Mode, holdings/candidates/watchlist, benchmark/risk/limits, explicit hybrid run, eight result tabs and saved output |
| Deep Research | `deep_research_tab.render_deep_research_tab`, `investment_brief` | V1 run/history/retry/finalization and six tabs; partial evidence, citations, exports, scenario eligibility |
| Deep Research V2 | `deep_research_v2_tab.render_deep_research_v2_tab`, `investment_brief` | Separate pilot run/decision/recovery/cost semantics and six tabs; saved generation time differs from evidence freshness |

Presentation changes cannot silently alter widget keys, event triggers, data packet bases or backend calls. Moving widgets among `st.tabs`, expanders or conditional containers requires state remount testing. The selected company remains typed navigation metadata, never a substitute financial packet. Existing saved financial results are reused without provider or model calls on ordinary navigation, downloads or formatting changes.

Failure/partial states: preserve successful provider records alongside warnings; leave missing values missing, show source/period/currency/retrieval when available, and retain old saved results behind a mismatch notice when relevant. Do not display one symbol's financial data under another symbol. Explicit AI actions enforce their current prerequisites; missing OpenAI must not globally block deterministic pages.

Baseline source snapshot: `git status --short` showed untracked `docs/features/2026-10-13-professional-redesign-team.md`, `docs/redesign/`, and `partial_redesign/`. No tracked source modifications were present at Gate 0. The current PLAN inventory reports 486 passing tests dated 2026-10-13 for the opening metric wiring delivery; that is historical evidence, not a redesign test result. No provider/model or Jira call was made for this discovery.
