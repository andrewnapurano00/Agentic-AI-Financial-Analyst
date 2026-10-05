# Introduction technical chart feature team

Mode: build. Run ID: 2026-10-04-introduction-technical-chart-team.

Outcome: eight requested ranges on market and company charts; configurable technical indicators and windows; deterministic summary and explicit-action bounded technical analysis agent; sensible date/price axes. Local delivery only; no commit/push.

Baseline: 7a0026487644c9f273f4767b7348d11cf9740fad

Existing Deep Research delivery changes are pre-existing and preserved.

Acceptance: all requested ranges, provider/basis/timezone/partial and missing disclosures, indicator arithmetic/window tests, no AI calls on ordinary reruns, period-appropriate axes, fresh health/browser verification, independent review.

Jira creation ledger: no attempts yet (maximum five). Initial implementation ticket explicitly requested before coding; coordinator owns initial ticket exception.

## Initial working tree
```
 M DEEP_RESEARCH.md
 M PLAN.md
 M README.md
 M app.py
 M src/langgraphagenticai/deep_research/crew_committee.py
 M src/langgraphagenticai/deep_research/data.py
 M src/langgraphagenticai/deep_research/manager.py
 M src/langgraphagenticai/deep_research/presentation.py
 M src/langgraphagenticai/deep_research/prompt_context.py
 M src/langgraphagenticai/deep_research/quarterly_ttm.py
 M src/langgraphagenticai/deep_research/v2.py
 M src/langgraphagenticai/deep_research/v2_data.py
 M src/langgraphagenticai/deep_research/v2_workflow.py
 M src/langgraphagenticai/ui/deep_research_tab.py
 M src/langgraphagenticai/ui/deep_research_v2_tab.py
 M tests/test_deep_research_recovery.py
 M tests/test_deep_research_v2_recovery.py
 M tests/test_deep_research_v2_timestamps.py
 M tests/test_quarterly_ttm.py
?? docs/features/2026-10-04-sector-aware-research-ttm-team.md
?? src/langgraphagenticai/deep_research/model_packets.py
?? src/langgraphagenticai/deep_research/quarterly_data.py
?? src/langgraphagenticai/deep_research/research_metrics.py
?? src/langgraphagenticai/deep_research/research_workflow.py
?? tests/fixtures/sector_quarterly_recorded_20261003.json
?? tests/test_sector_research_audit.py
```

## Jira initial ticket
Duplicate check: AAFA-1 through AAFA-6 all statuses; no matching chart feature. Create permission and Task metadata verified via MCP stdio.
Attempt 1: pending. Payload:
```json
{
  "cloudId": "https://bigmeatpete717.atlassian.net",
  "projectKey": "AAFA",
  "issueType": "Task",
  "summary": "Improve Introduction price charts with extended ranges and configurable technical analysis",
  "description": "Run: 2026-10-04-introduction-technical-chart-team. Initial implementation ticket explicitly requested before coding. Current Introduction market chart supports 1D/5D/1M/3M/1Y; company chart only 1M/3M/1Y and no configurable technical summary. Implement both with 1D,5D,1M,3M,1Y,3Y,5Y,10Y, configurable technical indicators/windows, sensible period-aware date/time and price axes, deterministic dated technical summary, and explicit-action bounded technical analysis agent. Preserve partial provider coverage and original source/basis; no model calls on normal reruns. Add offline arithmetic/provider/UI/agent tests, fresh health and browser checks, independent review and documentation. Local code delivery only, no GitHub push or hosted deployment. Acceptance includes all eight requested horizons (1d,5d,1m,3m,1y,3yr,5yr,10yr)."
}
```

Create response:
```
Connected: atlassian-mcp-server
Tools: 21
{"content": [{"type": "text", "text": "{\"data\":{\"id\":\"10110\",\"key\":\"AAFA-7\"}}"}], "isError": false}

```

Confirmed attempt1 created AAFA-7 (10110), https://bigmeatpete717.atlassian.net/browse/AAFA-7. Remaining attempts4. MCP helper C:/Users/andna/.codex/mcp/atlassian/check.py; authenticated direct stdio; no browserlogin.

## Financial specialist handoff
D01: FMP135 stable 5min AAPL saved five OHLCV rows, timezone/adjustment unknown, no index or30min confirmed coverage. D02: FMP136 stable full daily AAPL five OHLCV rows; long range/index entitlement and completeness unverified; current legacy routes are distinct. Evidence fmp_data_reference/samples/FMP-{135,136}/20261003T044241108241Z/AAPL-default.json and context_index/collection_report/endpoint_inventory/coverage_matrix/data_dictionary.
D03: FMP close adjustment unverified; Yahoo explicitly auto-adjusted whole-series fallback, no provider stitching; matched profilecurrency or unknown; expose date/basis/interval/retrieval/coverage.
D04: local SMA/EMA/WilderRSI/MACD/Bollinger with validated configurable barwindows and warmup; distinct oscillator panels; no provider indicator equivalence claim.
D05: existing portfolio technical agent assumes different inputs; dedicated bounded structured explicit-action chart-evidence agent with fingerprinted saved results. Missing selected indicators disclosed.
D06: time labels1D, date/time5D, short daily month/day, long monthly/year ticks; finite padded priceaxis and independent oscillatoraxis. Mock provider/model arithmetic/UI tests; no paid/livecalls. Specialist read-only completed.

Jira progress response:
```
Connected: atlassian-mcp-server
Tools: 21
{"content": [{"type": "text", "text": "{\"data\":{\"message\":\"Comment added to AAFA-7 successfully\",\"commentId\":\"10114\",\"body\":\"Discovery complete: both Introduction chart surfaces are in scope with eight distinct requested horizons. Saved FMP OHLCV contracts inspected; timezone, adjustment and ten-year entitlement are not inferred from short samples. Implementation will calculate configurable indicators on one consistently labelled provider series, preserve partial/missing coverage, and keep technical AI analysis behind an explicit action. Existing Deep Research changes remain preserved. Planning and implementation verification will be recorded before local handoff.\",\"appliedContentFormat\":\"markdown\",\"jsmCommentType\":\"publicComment\"}}"}], "isError": false}

```

## Planner selected build
P01: shared symbol-aware history and all eight ranges, latest1D/five-observed-session5D, partialhistory. P02: explicit provider/basis/currency/timezone/asof/retrieval, independent whole-series fallback and recovery. P03: local configurable SMA/EMA/WilderRSI/MACD/Bollinger, warmup and separatepanels. P04: deterministic summary and adaptive finite axes. P05: explicit structured boundedAItechnicalanalysis, validated evidenceIDs/fingerprint and retained mismatchnotice. Tests: provider/formula/axis/agent/AppTest, fullpytest, compile/import, fresh health/browser.
Team: current financial specialist chart_data_specialist and planner chart_planner completed. Fresh builder spawn failed because threadlimit; reused existing distinct serper_data_specialist as builder with explicit newrun handoff (freshfork unavailable). Fourth distinct verifier remains required; no successful fresh delegation invented.

D01-D03 selected-route recheck: specialist confirms builder stable FMP135 five-minute and FMP136 fullEOD symbol/from/to names match savedAAPL contract. Thirty-day/12year generalized requests remain unverified entitlement/completeness; no index/tz/adjustment guarantee. This does not block if actualcoverage/unknownbasis disclosed and fallback uses one Yahooauto-adjustedseries. No livecalls.

## Coordinator interim checks (not final acceptance)
Temporary external offlineharness8537 blocksrequests/httpx/curl_cffi and supplies synthetic rawFMP histories and modelresponses; actualIntroduction renderers exercised. Market1D/10Y/5D and allfiveindicatorselection/SMA50, company1Y/10Y, priceaxes/datelabels and summaryretention passed; explicitmockAIcall1 remained1 on controls, savedmismatch disclosed. Browsererrors none. Caught five-daymidnightticklabels and unstable Closecolor withadditionalindicators; builderaskedtofixandfinalchecks willrerun. Unsupported retrieskeyword spotted/removed before test. Screenshots outside repo at Temp/axiom-intro-chart-verification.

## Builder handoff and independent review
Distinct reusedbuilder completed P01-P05 source/tests/README/PLAN preserving priorDeepResearchchanges. Focused50passed23.54s; compile/import/diffcheckpassed. Python3.12.0,pandas3.0.5,Pydantic2.12.5,Streamlit1.61.1. Earlier AppTestprotocol assertion failure was test-only; actual renderedframeverification replaced it.
Fourthdistinctagent financial_verifier read exactFMP135/136 samples and scopeddelta,50guardedtests passed33.80s. FID-I01medium: futurepricesaccepted by normalize_history,2099pricecorruptsendpoint/AIhistory. In-scopefixsentbuilder; pendingrecheckapproval. No followupticketsneededifcorrected. Freshforkthreadlimit persists; fourthdistinctexistingthreadreused withcompletecurrenthandoff.
Coordinator pre-fixfullpytest318passed135.77s withrequests/httpx/curl_cffi guard; compileallapp/src,app/main/chart/agentimports passed; freshroothealth8536 andofflineharnesshealth8537ok. Sourcechangefuturefixrequiresrefreshedverification,do not treatpre-fixinventoryasfinal.

Jira progress:
```
Connected: atlassian-mcp-server
Tools: 21
{"content": [{"type": "text", "text": "{\"data\":{\"message\":\"Comment added to AAFA-7 successfully\",\"commentId\":\"10115\",\"body\":\"Implementation is complete for both Introduction charts: eight ranges, configurable SMA/EMA/Wilder RSI/MACD/Bollinger, deterministic summary, separate oscillators, date-aware price axes, provider/basis/coverage labels, and explicit bounded structured technical AI. 318 guarded offline tests passed before independent review; 50 scoped tests passed independently. Fresh app and offline UI harness health checks passed; all eight market ranges exercised with zero model calls. Independent review identified future-dated price validation as one in-scope blocker; fixing it and adding regression coverage before final verification. No substantive follow-up ticket is needed. No live financial/provider/model calls, commits or hosted deployment.\",\"appliedContentFormat\":\"markdown\",\"jsmCommentType\":\"publicComment\"}}"}], "isError": false}

```

## Final local verification
P01-P05 delivered locally. FID-I01 corrected and independently approved; no substantive unresolved follow-up tickets. Builder54 guarded cases passed34.30s. Independent53passed/one3-second AppTest timeout under concurrent load; isolated failed interaction andfourfuture regressions5passed32.70s. No productexception or paidcallfailure.

Fresh full inventory aftercorrection:322passed241.76s. Command PYTHONPATH=src;Temp/axiom-intro-chart-verification python -m pytest -q -p offline_guard, actualprojectPython3.12.0,Streamlit1.61.1,pytest9.1.1,pandas3.0.5,Pydantic2.12.5,Altair6.2.2. GuardblocksRequests/httpx/curl_cffi; provider/model boundaries mocked. compileallapp/src andapp/main/history/chart/agentimports passed. Fresh finalrootapp8536andexternalharness8537health ok.

Finalbrowser actualroot Introduction renderers: all16ranges (eight per market/company), allfiveindicators/SMA50, separateoscillators/timeframeaxes, explicitmockagentoncepersurface(total2), ordinarycontrols no extracalls, old-analysis mismatchnotice andcompanysummaryretained; browsererrorsnone. SyntheticrawFMPmock andrecordedmodeloutput; no livefinancial/paidmodelcalls. Artifacts outside repo Temp/axiom-intro-chart-verification. Automationcoldloadtimeout, stickytoolbarcoverage andpremature streamed-rerunassertion corrected bywaitingactualrenderedstate/scrolling Streamlitcontainer; actualfinalstatesverified.

Baselinepreservation/hygiene: 5 baselinefileschangedonlyauthorizedtarget/docs; 7 newcode/testfiles. All other files in the 134-file baseline remain unchanged,includingpriorDeepResearch andapp.py. NewUTF8 andcredentialpattern checks passed; diffcheckpassed. Localuncommitteddelivery,noGitHubpushorhosteddeployment. Liveentitlement/completebars/unknownsourceadjustment/timezone/modelnarrativenumericalaccuracy/cleaninstallremainunverified.

Scopedpaths:
```
PLAN.md
README.md
tests\test_market_tabs.py
src\langgraphagenticai\providers\market_history.py
src\langgraphagenticai\ui\introduction_tab.py
src\langgraphagenticai\providers\symbol_history.py
src\langgraphagenticai\technical_analysis\agent.py
src\langgraphagenticai\technical_analysis\evidence.py
src\langgraphagenticai\technical_analysis\indicators.py
src\langgraphagenticai\technical_analysis\__init__.py
src\langgraphagenticai\ui\technical_chart.py
tests\test_introduction_technical.py
```

## Approved final Jira payload
Snapshot hashes checked before mutation. Independent verifier completion draft plus measured coordinator results:
```json
{
  "cloudId": "https://bigmeatpete717.atlassian.net",
  "issueIdOrKey": "AAFA-7",
  "commentBody": "Completed and verified locally. Both Introduction market/company charts expose 1D, 5D, 1M, 3M, 1Y, 3Y, 5Y and 10Y; configurable SMA, EMA, Wilder RSI, MACD and Bollinger windows; separate oscillator panels; sensible temporal and padded price axes; provider/basis/timezone/as-of/retrieval/partial coverage; deterministic technical summary and explicit structured technical AI. Chart/settings reruns make no model calls. Saved company and technical interpretations remain visible, with mismatch notices when evidence changes.\n\nIndependent review approved FID-I01: future aware instants are excluded against UTC; timezone-unknown naive records use the documented calendar-date policy. No remaining substantive findings or follow-up tickets.\n\nFinal verification: 322 guarded offline tests passed in241.76s (Python3.12.0, Streamlit1.61.1, pytest9.1.1); builder54 focused passed34.30s. Independent focused run53 passed/one short AppTest timeout under concurrent load; isolated rerun of that interaction and four future regressions5 passed32.70s. Compileall app/src and app/main/history/chart/agent imports passed. Fresh root app8536 and offline UI harness8537 health endpoints returned ok. Actual root renderers exercised in browser: all eight horizons on both surfaces, all five indicators/SMA50, separate oscillator/date axes, saved summary, one explicit mock technical action per surface and no additional model calls on ordinary controls; mismatch notices and empty browser errors verified.\n\nSynthetic/recorded inputs and blocked external transports; no live financial provider or paid model calls. Saved FMP examples validate short AAPL schemas only; long/index entitlement, complete session coverage, adjustment/timezone and model numerical prose remain unverified. Previous Deep Research changes and user sessions preserved. README/PLAN updated (V-20261004-05); changes local/uncommitted, no GitHub push or hosted deployment. Run:2026-10-04-introduction-technical-chart-team."
}
```

Final comment response:
```
Connected: atlassian-mcp-server
Tools: 21
{"content": [{"type": "text", "text": "{\"data\":{\"message\":\"Comment added to AAFA-7 successfully\",\"commentId\":\"10116\",\"body\":\"Completed and verified locally. Both Introduction market/company charts expose 1D, 5D, 1M, 3M, 1Y, 3Y, 5Y and 10Y; configurable SMA, EMA, Wilder RSI, MACD and Bollinger windows; separate oscillator panels; sensible temporal and padded price axes; provider/basis/timezone/as-of/retrieval/partial coverage; deterministic technical summary and explicit structured technical AI. Chart/settings reruns make no model calls. Saved company and technical interpretations remain visible, with mismatch notices when evidence changes.\\n\\nIndependent review approved FID-I01: future aware instants are excluded against UTC; timezone-unknown naive records use the documented calendar-date policy. No remaining substantive findings or follow-up tickets.\\n\\nFinal verification: 322 guarded offline tests passed in241.76s (Python3.12.0, Streamlit1.61.1, pytest9.1.1); builder54 focused passed34.30s. Independent focused run53 passed/one short AppTest timeout under concurrent load; isolated rerun of that interaction and four future regressions5 passed32.70s. Compileall app/src and app/main/history/chart/agent imports passed. Fresh root app8536 and offline UI harness8537 health endpoints returned ok. Actual root renderers exercised in browser: all eight horizons on both surfaces, all five indicators/SMA50, separate oscillator/date axes, saved summary, one explicit mock technical action per surface and no additional model calls on ordinary controls; mismatch notices and empty browser errors verified.\\n\\nSynthetic/recorded inputs and blocked external transports; no live financial provider or paid model calls. Saved FMP examples validate short AAPL schemas only; long/index entitlement, complete session coverage, adjustment/timezone and model numerical prose remain unverified. Previous Deep Research changes and user sessions preserved. README/PLAN updated (V-20261004-05); changes local/uncommitted, no GitHub push or hosted deployment. Run:2026-10-04-introduction-technical-chart-team.\",\"appliedContentFormat\":\"markdown\",\"jsmCommentType\":\"publicComment\"}}"}], "isError": false}

```

Done transition response:
```
Connected: atlassian-mcp-server
Tools: 21
{"content": [{"type": "text", "text": "{\"data\":{\"message\":\"Issue AAFA-7 transitioned successfully\",\"transitionId\":31,\"statusName\":\"Done\"}}"}], "isError": false}

```

## Completion

AAFA-7 is **Done**, confirmed by transition31 after local verification. Final comment10116 records the measured results and limitations; progress comments10114/10115 retain discovery and correction history. Creation ledger: one confirmed attempt (AAFA-7), four remaining; no failed/uncertain creation attempts and no follow-up tickets.

All four distinct roles completed this run. Fresh context was available for the data specialist and planner; the builder and verifier reused existing distinct agent threads after the fresh-spawn thread limit. Their explicit current-run handoffs and actual verification are recorded above.

The change remains local and uncommitted. Both Introduction chart surfaces are ready after restarting Streamlit. Expand Technical indicators & settings to choose indicators/windows; technical AI runs only when its button is pressed and uses the configured OpenAI key/model. Prior Deep Research edits were preserved.

Only coordinator-owned verification servers8536/8537 and named browser axiom-intro-chart were stopped. Existing user Streamlit sessions were not stopped. Shutdown may emit a Windows connection-reset warning. Temporary harnesses, logs, screenshots and snapshots remain outside the repository for audit.
