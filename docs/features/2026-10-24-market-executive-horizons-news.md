# Market Brief horizon synthesis and executive news

Date: 2026-10-24. Local working-tree slice; no publication/deployment.

## User-facing change

Executive market brief now asks for a substantial market stance, separate 5-trading-day, calendar-month and three-calendar-month paragraphs, followed by three watchpoints. The 350-500 word target replaces the previous 160-word ceiling. Each horizon connects macro proxies, sector ETF leaders/laggards and technical confirmation without metric inventories or commentary about absent news. Price/technical evidence remains separate from news synthesis.

Market news & sentiment now leads with the overview as one or two connected executive paragraphs about dominant drivers, counterweights, risk appetite and conditional watchpoints. Structured thematic claims, model limitations and provider coverage sit behind a collapsed evidence panel. Existing headlines remain independently readable below the dashboard. Saved old results remain available without automatic model calls; explicit generation adopts the new formats.

## Domain and provider contracts

- `analysis/market_dashboard.py` adds 1M/3M comparisons using the latest observation on or before the calendar anniversary, within seven calendar days. Baseline value, actual date, target date and formula basis are saved; duplicate/missing/invalid or excessively old baselines stay unavailable. Existing 5/30/60-session measures, adjusted-close meaning and quote date policy remain unchanged.
- `providers/market_dashboard.py` supplies the new monthly columns. `analysis/market_brief_ai.py` includes dated monthly inputs and the existing return basis in its bounded context. Versions flag old saved formats without recollection or silent recalculation.
- All configured providers already contributed; the narrow Serper sample and short overview/display format constrained synthesis. `providers/market_brief_news.py` now makes at most three Serper searches (10 results each), one Marketaux request (3 requested stories), one FMP general-latest request (10) and one FMP articles request (5), on explicit evidence refresh only. Shared FMP retry policy remains independent. Failure preserves other routes.
- Safe-link/title deduplication retains provider attribution, longest preview and richer article body. Up to 50 unique stories are retained (at most 48 raw rows under the current configured request caps). Coverage records configured providers, returned rows and retained stories; these are samples, not whole-market completeness claims.
- `analysis/market_news_ai.py` sends up to 50 stories and five provider bodies, 6000 characters per body maximum. A fair per-body budget trims long bodies when necessary while preserving retained stories and explicit truncation. The serialized packet remains capped at 100000 characters. Headlines/previews are not called complete publisher articles. Requested lookback and retrieval time do not establish publication date.
- Request-bound fingerprint/citation schema and post-validation remain. Reader prose omits IDs; claims keep IDs separately. This validates source membership, not every causal/numerical semantic assertion.

## Evidence and remaining limits

See PLAN verification entry for focused/full offline, compile/import, health and guarded browser evidence. No real keys read or printed, no live news/model request or measured live summary-quality claim. News collection is a bounded current sample; it does not provide historical 1M/3M news causation. Missing providers, older FMP latest-route stories and article completeness remain visible in coverage diagnostics. Broad release/financial verification gates stay open.
