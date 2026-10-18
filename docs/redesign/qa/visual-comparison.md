# Redesign visual baseline — 2026-10-13

Baseline source: `be858cd6b8660c02de84bcb1a9561d73575d86ce`. The browser used an isolated agent-browser session against the actual `app.py` / `main.py` Streamlit entry point on local port 8579. API-key environment variables were empty and an external temporary `sitecustomize.py` blocked Requests, httpx, curl_cffi and non-loopback socket connections. Streamlit health returned `ok`. No paid model action was clicked. The screenshots show configuration-missing/empty states, **not** successful financial evidence or saved reports.

An initial port-8578 guard only wrapped Python sockets. yfinance's curl_cffi transport attempted external requests and hit certificate failures before the server was stopped. This run is not counted as offline browser evidence. The guard was expanded and a fresh 8579 server was used for the captures below; its stderr showed provider transport blocked. No live financial values were used in the captures.

| Route or mode | Baseline capture | State and limitation |
| --- | --- | --- |
| Market Brief | [1440](screenshots/baseline-market-1440.png), [1920](screenshots/baseline-market-1920.png), [1024](screenshots/baseline-market-1024.png), [390](screenshots/baseline-market-390.png) | Missing/partial market evidence; no success-state chart parity. |
| Top Movers | [1440](screenshots/baseline-movers-1440.png) | Missing FMP key; ranking unavailable. |
| Research Chat | [1440](screenshots/baseline-research-chat-1440.png) | Draft and disabled submit without OpenAI. |
| Research Guided | [1440](screenshots/baseline-research-guided-1440.png) | Prepare disabled without OpenAI. |
| Equity Report | [1440](screenshots/baseline-equity-1440.png) | Configuration/input state. |
| Stock Screener | [1440](screenshots/baseline-screener-1440.png) | Configuration/input state. |
| Portfolio Optimizer | [1440](screenshots/baseline-portfolio-1440.png), [1920](screenshots/baseline-portfolio-1920.png), [1024](screenshots/baseline-portfolio-1024.png), [390](screenshots/baseline-portfolio-390.png) | Configuration state, no backtest result. |
| AI Portfolio Manager | [1440](screenshots/baseline-portfolio-manager-1440.png), [390](screenshots/baseline-portfolio-manager-390.png) | Example holdings and disabled AI action; no recommendation result. |
| Deep Research | [1440](screenshots/baseline-deep-1440.png), [1920](screenshots/baseline-deep-1920.png), [1024](screenshots/baseline-deep-1024.png), [390](screenshots/baseline-deep-390.png) | Configuration state, no saved report. |
| Deep Research V2 | [1440](screenshots/baseline-deep-v2-1440.png) | Pilot configuration, no saved report. |

Reference images: [Market Brief](../references/market-brief.png), [Deep Research](../references/deep-research.png), [Portfolio Lab](../references/portfolio-lab.png). They contain illustrative data and unsupported controls. Before/after composition, accessibility, content and export parity still need acceptance checks; the initial missing-configuration captures alone do not pass Gate 1 or ACC-01–ACC-12.

## Fixture-backed saved and partial baseline

A separate temporary Streamlit harness on port 8580 called the actual `main.load_langgraph_agenticai_app()` and seeded session state with synthetic results built from the repository's offline Deep Research/V2 test fixtures plus a one-row synthetic Portfolio Manager bundle. The same expanded transport guard blocked provider/model network calls. The fixture is **not production code**, and its values and narrative are not investment facts. All three isolated browser sessions were closed and the server stopped after capture.

| State | Browser evidence | Boundary |
| --- | --- | --- |
| V1 saved complete | [configuration above the result](screenshots/baseline-deep-saved-1440.png), [comparison with saved result](screenshots/baseline-deep-comparison-1440.png), [sources](screenshots/baseline-deep-sources-1440.png) | The comparison capture visibly shows the saved result and tabs; synthetic evidence. The first capture does not show the thesis below the fold. |
| V2 saved complete | [report](screenshots/baseline-deep-v2-saved-1440.png), [sources](screenshots/baseline-deep-v2-sources-1440.png) | Actual V2 result path; separate saved V2 status. |
| Portfolio Manager saved result | [input and holdings above the result](screenshots/baseline-portfolio-saved-1440.png) | One-row synthetic bundle was seeded, but the recommendation table is below the captured viewport; runtime output remains unverified visually. |
| V1/V2 partial | [V1 configuration above result](screenshots/baseline-deep-partial-1440.png), [V2 visible review-needed state](screenshots/baseline-deep-v2-partial-1440.png) | V2 visibly shows the synthetic evidence gap and review-needed status; V1's warning is below the captured viewport. |
| Research mismatch | [saved chat](screenshots/baseline-research-mismatch-1440.png) | Deliberately mismatched `config_fingerprint` with saved chat; the warning is outside the captured viewport and is not visually verified here. |

This covers representative saved and partial paths for Gate 0 discovery. The Research mismatch warning and Portfolio recommendation result still need focused browser capture in Gate 3. It does not verify every result tab, export payload, or all 714 active preservation rows. Those remain Gate 3 release checks.

## P02 shared-shell comparison

A fresh guarded `app.py` process on port 8582 returned Streamlit health `ok`. In an isolated browser session the single sidebar selector reached all eight routes, and the Settings disclosure showed the existing model/use-case selectors, five password inputs and debug toggle. No paid action was clicked. These screenshots show the configuration-missing/empty state only; they do not establish saved-result or export parity after the shell edit.

| Viewport / route | After P02 capture | Observation |
| --- | --- | --- |
| 1440 Market Brief | [after](screenshots/final-market-1440.png), [before](screenshots/baseline-market-1440.png) | Navy/gold shell, separate Discover/Analyze/Allocate headings, existing search, refresh, evidence warning and research draft action visible. |
| 1440 Top Movers | [after](screenshots/final-movers-1440.png), [before](screenshots/baseline-movers-1440.png) | Missing-key and recovery states remain visible. |
| 1440 Research, Equity, Screener, Portfolio, V1 and V2 | [Screener](screenshots/final-screener-1440.png), [Equity](screenshots/final-equity-1440.png), [Deep Research](screenshots/final-deep-1440.png), [V2](screenshots/final-deep-v2-1440.png), [Portfolio](screenshots/final-portfolio-1440.png) | Routes render under the shared shell; page bodies remain their pre-redesign layouts. Research Chat was inspected in the browser, including the Settings disclosure. |
| 1920 / 1024 Research | [1920](screenshots/final-research-1920.png), [1024](screenshots/final-research-1024.png) | Shared shell and Research configuration rendered. These captures alone do not prove interaction parity. |
| 390 Market Brief | [after](screenshots/final-market-390.png), [before](screenshots/baseline-market-390.png) | After the provider-unavailable state settled, controls, evidence/recovery notices and status text were readable without visible page-level horizontal clipping. |

The original `final-market-390.png` was mistakenly captured during a route/viewport transition and showed Portfolio Lab. It was replaced with a settled Market Brief capture and independently rechecked. Earlier transient viewport screenshots are not acceptance evidence. The independent verifier found no confirmed P02 code regression and noted that older conditional opening-page CSS still needs page-slice consolidation; P02 is a shared-shell delivery, not completion of the full visual system.

## RDS-03 Market Brief and Top Movers populated-state check

A separate local Streamlit process on port 8584 used a temporary, offline-only fixture to supply synthetic market quotes, chart bars, a three-company Top Movers screen, a selected-company quote and an unavailable-news result. It called the actual `main.load_langgraph_agenticai_app()` route. The external transport guard and empty API-key environment prevented provider and model traffic; Streamlit health returned `ok`. This is visual and interaction evidence for the page layout, not live market correctness or full financial parity.

| Route | Populated capture | Observation |
| --- | --- | --- |
| Market Brief | [1440](screenshots/rds03-market-populated-1440-final.png), [1920](screenshots/rds03-market-populated-1920.png), [1024](screenshots/rds03-market-populated-1024-final.png), [390 first viewport](screenshots/rds03-market-populated-390.png), [390 observations](screenshots/rds03-market-populated-390-observations-final.png), [390 sectors](screenshots/rds03-market-populated-390-sector-final.png), [390 candidates](screenshots/rds03-market-populated-390-candidates-final.png) | At desktop width, chart, vertically stacked deterministic observations and sector bars occupy the intended main/secondary row. A later responsive correction gives the 1024px summary row three then two cards and places the chart and two rails on separate rows; 390px observations, sector chart and candidate actions were reached by scrolling in the settled app. |
| Top Movers | [1440](screenshots/rds03-movers-populated-1440-final.png), [1920](screenshots/rds03-movers-populated-1920-final.png), [1024](screenshots/rds03-movers-populated-1024-final.png), [390 first viewport](screenshots/rds03-movers-populated-390-final.png), [390 selected company](screenshots/rds03-movers-populated-390-selected-final.png), [390 sector/news/actions](screenshots/rds03-movers-populated-390-sector-final.png) | Ranking table and selected-company rail render side by side at desktop widths; narrow widths retain the native table's local horizontal scroll. Scrolling at 390px reached the selected quote/chart, news-unavailable notice, handoff actions and sector context. The route-local quote spacing correction is visible in the selected-company capture. |

In the browser, switching Top Movers from Leaders to Laggards changed the ranked heading and table order without a model action. The selected-company rail, chart basis and Research/Open snapshot actions remained in the rendered tree. The fixture did not exercise live provider responses, every filter combination, every lower mobile panel, exports or the 211 active RDS-03 inventory rows. Those checks remain open in the preservation map and acceptance matrix.

## RDS-06 Deep Research saved and partial layout check

A guarded Streamlit harness on port 8585 seeded the actual `main.load_langgraph_agenticai_app()` route with the repository's synthetic V1/V2 saved-result fixtures. `?variant=partial` changed both saved results to needs-review and added a synthetic warning and evidence gap. External transports remained blocked and API-key environment variables empty; health returned `ok`. No Start, Run, retry, committee, decision or export action was invoked in this browser pass. These screenshots demonstrate layout and reachable controls only; they do not establish model quality, live evidence freshness or 224-row parity.

| Route/state | After capture | Observation |
| --- | --- | --- |
| V1 saved complete | [1440 first screen](screenshots/rds06-deep-v1-saved-1440-final.png), [1440 thesis/rail](screenshots/rds06-deep-v1-thesis-1440.png), [390 first screen](screenshots/rds06-deep-v1-saved-390.png), [390 thesis/rail](screenshots/rds06-deep-v1-thesis-390.png) | The selected history, dated saved-evidence status and review cards precede a collapsed new-run disclosure. Full thesis prose sits beside the evidence rail at desktop width; the rail stacks below it on mobile. The shared header and retained status/news blocks push the V1 thesis below the first 900px screen, a material composition difference from the illustration. |
| V1 partial | [1440 header](screenshots/rds06-deep-v1-partial-1440.png), [1440 warning/report](screenshots/rds06-deep-v1-partial-report-1440.png), [1024](screenshots/rds06-deep-v1-partial-1024.png), [1920](screenshots/rds06-deep-v1-partial-1920.png) | Needs Review, partial news and financial warnings, evidence gaps and the explicit finalize-with-caveats action remain ahead of the original thesis and saved-evidence rail. |
| V2 saved complete | [1440 first screen](screenshots/rds06-deep-v2-saved-1440.png), [1440 Report/rail](screenshots/rds06-deep-v2-report-1440.png), [390 first screen](screenshots/rds06-deep-v2-saved-390.png), [390 Report/rail](screenshots/rds06-deep-v2-report-390.png) | Saved AI findings precede the retained history/configuration disclosures; Report prose and rail render side by side on desktop and stack on mobile. The synthetic fixture's legacy generation timestamp is labeled unavailable instead of presented as evidence freshness. |
| V2 partial | [1440 header](screenshots/rds06-deep-v2-partial-1440.png), [1440 warning/report](screenshots/rds06-deep-v2-partial-report-1440.png), [1024](screenshots/rds06-deep-v2-partial-1024.png), [1920](screenshots/rds06-deep-v2-partial-1920.png) | Needs Review, synthetic partial warning, gap disclosure, unresolved-issue notice and finalize-with-caveats remain visible; Report and rail show the saved status without a false complete badge. |

The evidence above does not cover no-history, cached V2 reuse, every conditional tab, failed decision, eligible/ineligible brief scenarios, exports, or all mobile lower controls. Those are explicit Gate 3 checks in the RDS-06 readback and acceptance matrix. The earlier V1 saved screenshot before preamble compaction is retained as a diagnostic, not the final comparison.

## RDS-07 Portfolio Lab saved-result and setup check

A second guarded Streamlit harness on port 8586 called the actual main route with a synthetic one-row `pm_hybrid_bundle_v1` and a two-sector current/proposed allocation table. External transports were blocked, API-key environment variables empty and health returned `ok`. No optimizer Run, hybrid Run, Ask or download was clicked. The fixture values are layout data, not live holdings or a recommendation.

| State | After capture | Observation |
| --- | --- | --- |
| AI Portfolio Manager saved result | [1440 recommendations/rail](screenshots/rds07-portfolio-manager-recommendations-1440.png), [1920](screenshots/rds07-portfolio-manager-recommendations-1920.png), [1024 recommendation grid](screenshots/rds07-portfolio-manager-recommendations-1024-final.png), [1024 sector/committee panels](screenshots/rds07-portfolio-manager-rail-1024-final.png), [390 recommendation grid](screenshots/rds07-portfolio-manager-recommendations-390.png), [390 sector/committee panels](screenshots/rds07-portfolio-manager-rail-390.png) | At wide widths the native recommendation table sits beside saved current/target sector and committee panels; local table scroll retains its full columns. An initial 1024px capture clipped proposed weights in a narrow rail. The page-scoped responsive correction stacks the rail below the grid at <=1100px, and the final 1024px capture shows both weight columns. The 390px capture reaches the lower panels by scrolling. |
| Optimizer setup | [1440](screenshots/rds07-portfolio-optimizer-1440.png), [390](screenshots/rds07-portfolio-optimizer-390.png) | The existing form, assumptions and explicit Run control remain in a bordered local setup card. These are pre-run screens; the full optimizer result was not generated in this guarded browser pass. |

The saved Manager result remains below the long holdings editor and watchlist block, unlike the reference image's first-screen result. Moving its unkeyed controls into a conditional disclosure would risk remount/reset; that state change is outside this bounded presentation slice. The Optimizer's full result still disappears on ordinary rerun under its existing `if not run_btn: return` path, so no saved-result behavior is claimed. Browser evidence does not prove every Manager mode, failed/partial bundle, all eight tabs, three CSV payloads, optimizer result charts, or 145-row parity; the map and acceptance matrix retain those checks.

## RDS-05 Equity Report saved-thesis layout check

A guarded Streamlit harness on port 8587 called the actual main route with a synthetic saved one-security Equity result. The fixture rejected fresh financial collection, external transports were blocked, API-key environment variables were empty and health returned `ok`. No Run, committee or export action was clicked. The captures verify layout of the saved path, not live provider accuracy or all Equity result states.

| State | After capture | Observation |
| --- | --- | --- |
| Saved Equity result | [1440 first screen](screenshots/rds05-equity-saved-1440.png), [1440 thesis/rail](screenshots/rds05-equity-thesis-1440-final.png), [1920 thesis/rail](screenshots/rds05-equity-thesis-1920-final.png), [1024 thesis/rail](screenshots/rds05-equity-thesis-1024-final.png), [390 thesis/rail](screenshots/rds05-equity-thesis-390-final.png) | The existing analysis form and five result tabs remain available. The saved deterministic thesis occupies the main column with a saved-comparison rail at wide widths; the rail stacks below it on narrow screens. The active Equity presentation cards use the shared navy/gold palette. The synthetic result begins below the retained configuration form, rather than at the very top of the reference illustration. |

The browser pass did not verify multi-security comparisons, every conditional sector framework, committee responses, failed or partial collection, exports, or all 84 Equity preservation rows. The Gate 1 map and acceptance matrix retain those checks.

## RDS-04 Research saved Chat and Guided layout check

A guarded Streamlit harness on port 8588 called the actual main route with a synthetic two-message Chat thread and a synthetic Guided plan/result containing an explicit partial-evidence warning. External transports were blocked, API-key environment variables were empty, and health returned `ok`. No Submit, Prepare, Run or download action was clicked. The fixture's Guided model fingerprint intentionally differs from the UI model, so the visible mismatch and disabled run are expected recovery states, not a failed model call.

| Mode | After capture | Observation |
| --- | --- | --- |
| Chat saved conversation | [1440](screenshots/rds04-research-chat-saved-1440.png), [390](screenshots/rds04-research-chat-saved-390.png) | Saved AI findings and expandable conversation precede the editable draft and disabled explicit Submit action; the saved thread survives toggling to Guided and back. |
| Guided saved partial result | [1440](screenshots/rds04-research-guided-saved-1440.png), [1920](screenshots/rds04-research-guided-saved-1920.png), [1024](screenshots/rds04-research-guided-saved-1024.png), [390](screenshots/rds04-research-guided-saved-390.png) | Saved interpretation, mismatch warning, partial-evidence warning and evidence detail precede a collapsed Configure guided research disclosure. On mobile the saved interpretation is readable in the first viewport. |

This browser pass does not verify a matching Guided plan, successful paid execution, the exact JSON download payload, every Chat configuration mismatch transition, or all 80 Research preservation rows. Focused offline AppTests cover the saved-result/no-call and configuration paths separately; the preservation map retains unverified rows.

## RDS-08 Stock Screener saved and empty layout check

A guarded Streamlit harness on port 8589 called the actual main route with an offline synthetic two-company saved screener result and a synthetic FMP configuration key. A separate fresh browser session used `?variant=empty` for the no-saved state. External transports were blocked and health returned `ok`; no Run or download was clicked. The saved values are layout fixtures, not provider facts. The initial browser pass found a duplicate local Stock Screener heading below the shared H1; the page-only correction removed it before the final captures.

| State | After capture | Observation |
| --- | --- | --- |
| Saved result | [1440 setup](screenshots/rds08-screener-saved-1440.png), [1440 result](screenshots/rds08-screener-results-1440.png), [1920 result/actions](screenshots/rds08-screener-results-1920.png), [1024 result](screenshots/rds08-screener-results-1024.png), [390 setup](screenshots/rds08-screener-saved-390.png), [390 table](screenshots/rds08-screener-results-390.png), [390 CSV/company actions](screenshots/rds08-screener-actions-390.png) | Base filters precede the three original disclosures, with Server-side and Enrichment collapsed for a nonempty saved result. The saved generation timestamp remains labeled separately from retrieval time. The native table scrolls locally at narrow widths; CSV, keyboard company selector and Introduction handoff are reachable below it. |
| No saved result | Guarded browser tree at 1440 verified the Server-side and Enrichment disclosures expanded with all original slider groups; no result panel was invented. | The original explicit Run gate remains. A dedicated settled screenshot was not retained for this state. |

This pass did not execute FMP collection, verify CSV bytes, every empty/partial branch, all 24 optional display columns, or all 71 Screener preservation rows. The map and acceptance matrix retain those checks. The earlier duplicate-heading capture is diagnostic only.
