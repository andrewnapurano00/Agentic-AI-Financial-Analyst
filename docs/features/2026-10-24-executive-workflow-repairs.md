# Executive workflow repairs - 2026-10-24

Working-tree delivery over the existing AX-01 through AX-10 changes. No commit, publication, deployment or paid/live research was performed.

## User outcomes

1. Market Brief constituent ribbon moves left to right with hidden overflow. It remains decorative, uses saved quotes, pauses on hover/focus and respects reduced motion. No timer requests or provider calls were added.
2. Market news is presented as a consolidated executive briefing with market implications and qualitative tone. Visible citation IDs/buttons and verbal attribution are removed from summaries; exact source-ID/fingerprint validation remains internal. Descriptions, snippets and Marketaux entity highlights are retained together instead of choosing only one field. Existing FMP article bodies are retained. Provider previews are not relabeled as complete publisher articles.
3. The Market Brief daily-chart section includes **Ask historical technical questions** with ticker, From/Through dates and a question. Only explicit **Ask technical AI** requests daily history and one bounded model answer. Locally computed SMA/EMA/RSI/MACD/Bollinger and common 7/14/21/50/200-bar SMAs accompany dated prices. Unsupported periods, volume/intraday requests, partial coverage and excessive context cannot be represented as observed facts. This is bounded daily-history Q&A, not unlimited lifetime or arbitrary-market-data access. Current answer budget is 400,000 serialized characters and 4,000 completion tokens; provider history retains the existing available-history bounds.
4. Active Top Movers routing replaces the social chart with an explicit text-only Positive/Negative/Neutral assessment of collected observations. At most five provider pages and one model call per explicit action; platform/date aggregates preserve zero versus missing. Unknown score calibration cannot become an absolute bullish threshold. Missing observations produce an unavailable state, not fabricated neutral sentiment. Retained legacy chart helpers remain outside active routing.
5. Company news uses a company-focused query and falls back from the Serper news index to the ordinary web index when fewer than three news results are available. At most one news and one web request; only this fallback explicitly opts into a seven-day web filter. Publication dates are still checked where supplied; undated/relative items retain their coverage warning. FMP/Marketaux successes survive another feed failing. The briefing stays tied to the selected ticker and saved articles.
6. The CrewAI error matches an installed agent timeout path that embeds the full task in its exception. Four agents remain separate. Specialist responses are limited to 180 words, final response to 500 words; each agent uses at most two iterations, 180 seconds, no agent retry, with a 60-second HTTP timeout and no SDK retry. GPT-5 uses the installed native Responses adapter so low reasoning and 4,000 output tokens are actually carried through; store=False. This bounds work, not guaranteed live-model latency. Timeout and other execution failures return safe recovery text without the task packet; saved report/decision remains intact. No automatic paid fallback.
7. Advisor opens with ticker/name/allocation/short reason, then bounded holding theses and roles. It distinguishes saved AI review from local selection reasons. Operational eligibility is excluded from local investment reasons. Detailed existing risk/research/committee/export controls remain behind a collapsed section. Its executive PDF projects only selected holdings, short explanations, risk and assumptions, never the full research universe or daily histories. Original evidence exports remain separate. A multi-megabyte-universe fixture no longer causes the two-million-character memo failure.

## Design boundary

`analysis/executive_text.py` and `analysis/portfolio_summary.py` provide display-only cleanup/projection. Original saved evidence, narrative and citation fields are not mutated. Evidence validation remains independent of presentation. No universal numerical or prose-semantic correctness claim follows. News wording and technical/committee reasoning remain model interpretations.

## Source and tests

- Ribbon: `ui/ticker_ribbon.py`.
- News: `providers/{news_content,ticker_news,market_brief_news}.py`, `tools/serper_tools.py`, `analysis/{market_news_ai,ticker_news_ai}.py`, corresponding UI renderers.
- Technical: `technical_analysis/questions.py`, `ui/technical_questions.py`, `ui/{market_dashboard,technical_chart}.py`.
- Social: `analysis/social_brief.py`, `ui/social_brief.py`, `ui/top_movers_tab.py`.
- Committee: `equity_committee.py`, existing Equity Report renderer.
- Advisor/PDF: `analysis/{portfolio_summary,investment_memo,memo_pdf}.py`, `ui/portfolio_architect_tab.py`.
- Regressions: `tests/test_executive_repairs.py` plus updated `tests/test_investment_memo.py` and existing provider/model/UI contracts. Eleven new cases cover ribbon escaping/direction, retained previews, web-index recovery, citation-free news, historical request/indicator bounds, explicit UI call counts, text social recovery, safe committee timeout, installed CrewAI parameter propagation and oversized advisor-universe exclusion.

Verification results and remaining limitations are recorded separately in PLAN.md. Live provider entitlement/search coverage, paid-model output quality and paid committee completion were not certified. R01/R02/R05/R07/R08 repairs do not close all broader roadmap acceptance or AX-10 production gates.


Final evidence: full offline rerun 1347 passed in 526.11s; supplemental final artifact/provider/UI inventory 59 passed in 99.45s, including the subsequently added metric-tag presentation case. Final PDF four pages / 47,120 bytes, all ten selected tickers extracted, first two pages visually checked. Actual app and guarded fixture health passed; explicit mocked browser interactions and laptop/narrow review passed. Final compile/import, document links, UTF-8 and diff checks passed. Temporary browser/servers closed. See PLAN for exact staging and earlier corrected failures.
