# Engineering Prompt: Bloomberg-Style Introduction, Top Movers & Sector Heatmap

## Mission
Redesign the existing Streamlit Introduction, Top Movers and Sector Heatmap workspaces into a cohesive, dense financial terminal using the three attached screenshots as the visual specification. Implement working screens backed by the app's actual data. Match the screenshot's structure, metric labels, typography, chart treatment, spacing, and information density while retaining our own branding.

Start implementation after inspecting the repository and creating a short implementation plan. This is an implementation task, not just a design proposal. Read applicable AGENTS.md instructions first.

## Reference inputs
- image(20261013-024941).png: main company overview, quote header, price chart, key statistics, growth and profitability.
- image(20261013-025159).png: earnings history, peer comparison, bottom drill-in actions.
- introduction_tab(1).py: supplied copy of the Introduction renderer.
- top_movers_tab(1).py: supplied copy of the Top Movers renderer.
- top_movers_data(1).py: compatibility facade exporting collect_discovery as load_top_movers.

Find the canonical modules in the repository; do not create duplicate modules using the uploaded filenames. Screenshots define visual goals; numbers shown in them are sample values and must never become production defaults. Both images depict a company overview, not a dedicated Top Movers screen. Apply their visual system to Top Movers using the existing discovery workflow specified below.

- image(20261013-025728).png: sector tiles, selected-sector industry drill-down and Day/Week/YTD performance table.
- Sector Heatmap implementation was not included in the uploaded Python files; locate its canonical renderer/providers in the repository before changing it.

## Scope and architecture
Keep Streamlit and the current application architecture. Preserve public renderer signatures and existing state, navigation, saved evidence, explicit AI generation, research drafts, and provider caching behavior unless a documented change is necessary.

Inspect these existing integrations before editing:
- ui.opening_presentation: opening_styles, heading, cards, number, terminal_chart.
- ui.app_shell and ui.workspace_presentation.
- ui.company_snapshot: load_company_snapshot and summary generation.
- providers.symbol_history, providers.market_history, ui.technical_chart.
- providers.discovery: collect_discovery, rank_discovery, sector_summary, PERIODS, selected quote/news loaders.
- state.discovery, state.research_context, ui.workspace_handoff.

The uploaded files do not contain all provider implementations. Trace the actual repository rather than assuming fields or endpoints exist. Keep HTTP collection, normalization and financial calculations in the provider/data layer. top_movers_data.py should remain a compatibility facade unless there is a concrete architectural reason to change it.

Build reusable terminal components for panel headings, quote headers, metric grids, compact evidence displays, charts and tables. Scope CSS to these workspaces where possible. Avoid brittle generated Streamlit class selectors and global styles that break other workspaces.

## Visual specification
- Near-black canvas (starting point #111111), charcoal panels (#1C1C1C), subtle borders (#303030), off-white primary text, muted gray labels.
- Red active controls and accents similar to the screenshots; green positive changes and red negative changes. Pair color with signs/text. Neutral values stay neutral.
- Compact uppercase panel headings, modest letter spacing, tabular or monospace numeric text, aligned decimals and right-aligned table numbers.
- Thin dividers, 4–6 px corners, minimal shadows, narrow 8–12 px gaps and compact panel padding. Avoid oversized headings, large rounded cards and excessive whitespace.
- Price chart with thin red line and restrained red area fill, subdued grid and readable axes. Preserve interactive tooltips, date/value accuracy and technical analysis access. Trend color may be consistent red as in the reference; do not confuse line color with today's gain/loss.
- Desktop company layout: full-width quote header, approximately 2:1 chart-to-statistics columns, two metric panels stacked at right, About below the chart, then a two-column earnings/peers row and compact drill-in action bar.
- Use existing navigation and branding. Do not reproduce Perplexity chrome, creator logos, subscriptions, YouTube feed or nonfunctional screenshot menu items.
- Fit 1440 and 1920 px desktop widths cleanly. At 1024 px reduce density sensibly; narrow layouts stack panels and let wide tables scroll without clipping controls or labels.

## Introduction: market view
Keep the market landing view and company search. Present it in the same terminal style:
1. Compact market header/search and an index strip with available index levels, signed quote changes, provider/as-of context.
2. S&P 500 chart beside sector ETF performance.
3. Deterministic market observations and research candidates as compact panels.
4. Macro context, refresh, and the existing AI research draft input.
5. Preserve View sector movers and company/research handoffs.

Retain the distinction between sector ETF quote changes and screened-stock sector averages. The fixed ten-company discovery list is not whole-market breadth. Add screenshot index instruments only where supported by verified repository providers; otherwise show Unavailable.

## Introduction: company view
Searching/selecting a company opens the terminal company overview.

### A. Quote header
Ticker, company name, sector badge, prominent latest price with actual quote currency, signed absolute and percentage daily change. Include premarket/after-hours prices only when supported with session and timestamp evidence. A full-width 52-week low/high rail displays the current price position; guard missing or equal endpoints, and indicate out-of-range values.

At right, show analyst consensus badge, analyst count, consensus price target and implied upside when reliable data exists. Do not hardcode Strong Buy. Price-target upside = (target / current price - 1) × 100 using compatible currency/basis and explicit dates.

### B. Chart
Large interactive company price chart with screenshot controls: 1M, 3M, 6M, YTD, 1Y, All. Preserve supported additional ranges and existing technical analysis controls. Map UI labels to actual provider range semantics. All means available history and must disclose truncation. Show compact provider, price basis, timezone and as-of evidence.

### C. Key Statistics
Render a two-column grid in this screenshot order:
| Left | Right |
| --- | --- |
| Market Cap | Enterprise Value |
| P/E (TTM) | P/E (FWD) |
| PEG | P/S |
| P/B | EV/EBITDA |
| Beta | Dividend Yield |
| Volume | Avg Volume |

### D. Growth & Profitability
Render a two-column grid in this screenshot order:
| Left | Right |
| --- | --- |
| Revenue Growth YoY | Revenue 3Y CAGR |
| Revenue 5Y CAGR | Gross Margin |
| Operating Margin | Net Margin |
| FCF Margin | ROIC |
| ROE | ROA |
| Debt/Equity | Current Ratio |

Use coherent financial periods and display the basis (TTM, annual, latest quarter, etc.) compactly. Document definitions when provider conventions differ. Revenue CAGR = ((latest revenue / revenue n years earlier)^(1/n) - 1) × 100 over comparable fiscal periods with positive valid inputs. FCF margin = FCF / revenue × 100 on a matching period. Avoid double-scaling percentages and do not fabricate ROIC or forward P/E.

### E. About and existing evidence
Compact company description with a safe company website link. Keep current revenue TTM, free cash flow TTM, return/performance, volatility, recent MarketAux news, source errors and saved AI interpretation accessible through supporting panels or expanders. Move lengthy evidence explanations out of prime chart space while retaining their substance.

### F. Earnings History
Four most recent reported quarters, grouped EPS actual vs estimate bars. Estimates gray; actual green for beat and red for miss, neutral for equal/unavailable comparison. Missing estimates must remain missing, not zero. Show fiscal-quarter labels, legend, tooltips, next earnings date and latest EPS surprise with source/date. Surprise = (actual - estimate) / abs(estimate) × 100 when estimate is finite and nonzero. Disclose provider EPS basis; avoid mixing adjusted and GAAP series.

### G. Peer Comparison
Selected company plus four verified peers; columns: Ticker, Revenue Growth YoY, Gross Margin, Operating Margin, P/E, ROIC. Highlight selected company. Use subtle in-cell comparison bars similar to the screenshot while keeping values readable. Compare compatible periods, currencies where relevant, and ratio definitions. Handle losses/negative P/E explicitly. Do not treat a high P/E as inherently favorable or positive margins as investment recommendations. Explain any scoring/color rule.

Use the existing peer selection/provider system if present. Do not hardcode NVDA/AMD/INTC/AVGO/TSM for every company. Show partial coverage clearly when fewer than four verified peers are available.

### H. Drill-in actions
Compact row for existing supported destinations: Valuation, Thesis & Notes, Ask AI about {ticker}, Set Alert, Research, and other relevant workspaces. Preserve ticker/context in each handoff. Only include working actions; label unavailable capabilities clearly rather than adding dead buttons.

## Top Movers: terminal discovery layout
Preserve its discovery purpose and use the same component system:
1. Compact heading, refresh, coverage/as-of strip.
2. Leaders/Laggards, sector and performance-period controls in a single desktop toolbar.
3. Small summary strip: usable filtered universe, advancing share, median selected-period change.
4. Main ranked table on the left (~two thirds) and selected-company detail on the right.
5. Screened sector context below; methodology/evidence expandable.

Ranked table: Rank, Ticker/Company, Sector, Last Price, 1D %, selected-period %, Market Cap, Volume and Avg Volume where supported. Avoid duplicate change columns when the selected period is 1D. Rank by the selected period, never silently by 5D. Missing numeric fields display an em dash/Unavailable, never an invented zero. Do not activate the unused legacy _rows helper without correcting its defaults, formatting and hardcoded 5D assumptions.

Retain selectable rows plus the keyboard-accessible selected-company control. Green/red signed returns, compact rows, aligned numbers and selected-row emphasis. Choose a supported Streamlit table/component that preserves real selection callbacks.

Selected-company panel: ticker/company/sector, dated quote, selected ranking-period return, chart, related news/potential catalysts, Open Snapshot and Research This Move. Reuse shared quote/metric components; offer additional company fundamentals through a compact disclosure or snapshot handoff rather than loading expensive full snapshots for all ranked rows.

Retain selected ticker identity through reruns, filter changes and empty results where appropriate. Scope figure/widget keys correctly. Test returning from empty filters and the existing one-time application of table selection.

Maintain the current screened universe: provider-requested U.S. stocks, market cap > $2B, volume > 500K provider units, active trading, exclude funds/ETFs, up to 500 requested records unless intentionally changed and documented. Its coverage is not the entire U.S. market. Benchmark/sector excess return and completed-session volume ratios remain unavailable until compatible dated bases are implemented. Related news does not establish what caused a move.

## Sector Heatmap: third screenshot specification
Implement the Sector Heatmap workspace using image(20261013-025728).png as its visual reference. Reuse the shared terminal styles and preserve existing navigation. Also reuse this component in Introduction if a sector heatmap is already embedded there, without replacing its existing ETF chart unless the product layout calls for it.

### A. Full-width sector tile panel
A compact SECTOR HEATMAP heading sits above a dense rectangular tile mosaic. Each tile shows ETF ticker in small muted text, sector name, prominent signed daily change and aggregate sector market capitalization in its lower-right corner. Technology is the selected tile in the reference, with a thin red outline. Selection outline is independent of positive/negative tile color.

Use a deterministic packed rectangular layout inspired by the screenshot: large Technology and Financial Services tiles near the top, remaining sectors below, narrow gaps and modest corners. The screenshot uses rows with unused right-side space; preserve that visual character where practical. If matching exact proportional area requires a treemap rather than row packing, use a real area-weighted layout and document the decision. Do not claim area represents market cap if dimensions are arbitrary. Never hardcode sample market caps, returns, industry values or ticker prices.

Tile area should represent aggregate market cap of the declared constituent universe, not the sector ETF's own market cap or AUM. Tile fill represents daily percentage change: dark green positive, dark red negative, neutral charcoal zero/unavailable. Use a consistent symmetric scale with disclosed clipping and an accessible signed value. Include a concise legend stating size basis and return basis. Missing market cap must not silently become zero; disclose omitted sizing coverage or use an explicitly labeled equal-size fallback.

Include all 11 supported equity sectors, including Real Estate and Energy. The screenshot visibly displays ten and omits Energy from its performance table; keep complete supported coverage rather than repeating this omission. Use canonical sector mapping and aliases:
| Sector label | ETF |
| --- | --- |
| Technology | XLK |
| Financial Services | XLF |
| Healthcare | XLV |
| Consumer Cyclical | XLY |
| Communication Services | XLC |
| Industrials | XLI |
| Consumer Defensive | XLP |
| Energy | XLE |
| Utilities | XLU |
| Materials / Basic Materials | XLB |
| Real Estate | XLRE |

Use the app's canonical taxonomy; map provider aliases explicitly and disclose unmapped constituents. Do not silently map a named sector to Other. Tile hover/accessible details should expose source, as-of time, size coverage and return methodology.

### B. Selected-sector industry detail, below left
Use a roughly 60:40 desktop split between industry detail and the performance table. Heading: INDUSTRIES · {SELECTED SECTOR}, with a small Drill-down detail caption.

Show a compact two-column grid of industry cards. Each has a green/red/neutral header with industry name and signed daily return; the dark body contains compact ticker rows showing ticker, latest price/currency and signed daily change. The reference Technology example includes Semiconductors, Software—Infrastructure, Software—Application, Internet Content & Information and Consumer Electronics. These are examples of provider taxonomy, not a fixed list for every sector. Load actual available industries and constituents for the selected sector.

Determine industry returns from compatible dated constituent returns, with an explicit documented weighting method. If market-cap weighted: sum(weight_i × return_i) / sum(weight_i) over eligible observations. Disclose count/coverage and excluded records. Do not average displayed top tickers and label it an entire-industry return. Verify industry membership against the chosen taxonomy; provider categories may not match ETF classification. Never copy contradictory screenshot values as business logic.

Display constituents in a deterministic documented order (such as market cap descending), with a compact Show more option for overflow. Selecting a ticker opens its existing company snapshot/research handoff with sector/industry context retained. Selecting a sector updates only its industry detail; filters and navigation must not regenerate AI or reload the full universe unnecessarily.

### C. Sector Performance, below right
Compact SECTOR PERFORMANCE heading and Today · Week · YTD caption. Columns: Sector (with ETF code beneath), Day, Week, YTD. Signed, right-aligned returns with green/red/neutral colors and thin separators. Include all supported sectors. Default order should be deterministic; offer numeric sorting without losing selected-sector identity.

Choose one return basis for both tile daily changes and this table: preferably sector ETF price returns, using existing supported providers. If using stock-universe aggregates instead, label that basis explicitly throughout. Size and returns may have different bases, but the legend must say so. Never relabel screened-stock averages as ETF returns or ETF market cap as constituent sector capitalization.

Day is the supported prior-close quote change; Week must define five trading sessions or the provider's documented weekly period; YTD uses the last available close of the prior calendar year through the current as-of close. Use compatible price adjustment bases and dates; do not assume a calendar-week or five-calendar-day lookback. Disclose any provider period whose dates/basis are unavailable. Missing periods display Unavailable, never zero. Selected-period table and tile values must agree when backed by the same evidence.

### D. Data and state requirements
Trace existing market_overview_data, discovery sector_summary and any dedicated heatmap provider. Neither the fixed ten-company Introduction list nor the capped Top Movers screen establishes full-sector market cap or comprehensive industry coverage. Use a declared constituent universe, exclude duplicate securities/share classes according to a documented rule, and report coverage. If only the capped screen is available, label sizes/industries as screened-universe aggregates until full coverage is implemented.

Normalize sector/industry memberships, market caps, dated quote changes and periods in providers. Reuse cached sector data; batch constituent requests and avoid one network request per tile/ticker on each rerun. Preserve selected sector through navigation and refresh, handle an empty industry gracefully and show partial provider failures inside the affected panel. Use genuine Streamlit/component events for clickable tiles, with keyboard-operable sector selection as a fallback; static HTML rectangles alone are insufficient.

### E. Heatmap acceptance criteria
- Desktop screenshot comparison confirms full-width tile mosaic, selected red outline, industry card grid below left, and dense Day/Week/YTD table below right.
- All 11 supported sectors are included with correct mappings; actual data or explicit missing states replace every sample value.
- Tile sizing, daily colors, industry returns and table returns have documented bases and visible coverage; sector size is never ETF AUM.
- Clicking/keyboard-selecting a sector updates the correct industries; ticker handoffs preserve identity; refresh retains selection without stale cross-sector data.
- Tests cover alias mapping, weighting, finite/missing values, coverage, return-period semantics and selection; browser QA covers desktop and stacked narrow layouts.

## Data work and performance
Before adding data, produce a metric coverage matrix: UI label, current normalized field, provider/module, verified endpoint, raw field, formula, unit, period, as-of semantics, cache, and missing-data behavior. Verify endpoints against repository implementation and official provider documentation as needed; never guess endpoint strings.

Reuse existing FMP integrations and configured credentials. Add only missing normalized fields/loaders needed for the specified panels. Do not expose keys in HTML, logs, URLs, screenshots or documentation. Escape external text and validate links.

Distinguish quote timestamp, statement period, filing/availability date and retrieval time. Cache TTL alone does not imply live data. Preserve zero as a valid value and reject NaN/infinity. Treat missing or invalid denominators safely. Compact source/basis disclosures must remain available even when the main screen is simplified.

Filters should reuse collected ranking data. Request history/news/fundamentals for the selected ticker only; batch peer data and reuse caches. Do not trigger LLM calls on chart changes, filters, refresh, row selection or navigation. AI interpretation remains explicit and saved; preserve snapshot/model mismatch handling.

## Team work packages
If working as an engineering team, use these task boundaries with one integration owner:
- Shared visual components/styles and responsive terminal layout.
- Introduction market/company composition and navigation.
- Missing metric normalization, earnings, peers and coverage dictionary.
- Top Movers presentation, selected-company detail and state behavior.
- Sector Heatmap tile layout, industry drill-down, performance table and provider contracts.
- Integration, regression tests and visual comparison.

Agree on shared component/data contracts first. Avoid simultaneous edits to shared shell/style modules. Each package should supply a focused change, validation and clear dependencies; the integration owner resolves shared interfaces.

## Implementation sequence and deliverables
1. Inspect canonical files and dependencies; record current behavior and data gaps.
2. Create implementation plan and metric coverage matrix.
3. Build shared styling/components, then Introduction, Top Movers and Sector Heatmap.
4. Add missing provider support and partial/loading/error states.
5. Run targeted tests and browser/visual QA; fix issues.
6. Deliver code, metric dictionary, short implementation notes, screenshots at target widths, test results and remaining genuine provider limitations.

If useful for Jira, split work packages into tickets with scope, dependencies, acceptance criteria and affected modules. Continue implementing authorized changes after planning.

## Acceptance criteria
- All three workspaces visibly match the supplied terminal aesthetic and density; company panel order and metric labels follow the screenshots.
- All screenshot metric positions exist, with actual values or explicit Unavailable states and no mock fallback.
- Price/history, earnings and peers are real, period-aware and traceable to provider fields/formulas.
- Search, chart ranges, refresh, Leaders/Laggards, sector/period filtering, row and keyboard selection, navigation and research drafts work.
- Table ranking follows the chosen period; missing returns are excluded and valid zeros retained.
- Existing technical analysis, news and saved interpretation remain accessible; no unintended AI generation occurs.
- Partial provider failures preserve usable panels and saved work without displaying another ticker's stale data.
- Keyboard controls and readable signed values work; 1440/1920 px layouts match the reference, 1024 px remains usable and narrow views stack without page overflow.
- Meaningful tests cover percentage units, metric formulas, invalid inputs, sorting, selection/state and navigation regressions. Use repository-required checks; do not add tests that merely mirror static CSS.
- Final review includes side-by-side visual comparison with all three screenshots and a concise list of unresolved data coverage limitations.

Begin by inspecting the repository and references, then implement the redesign.
