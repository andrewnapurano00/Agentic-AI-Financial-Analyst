# P03: visible, bounded agentic research

Run ID: 2026-10-07-p03-guided-research-team
Mode: build. Local implementation and Jira tracking/completion explicitly authorized. No commit/push/deployment or paid/live financial calls.
Baseline: 77f7275070790cda4ec18754f3dfa01258ef3e9c. Existing P01/P02 changes preserved.

Scope: Day 3 in docs/features/2026-10-04-five-day-predeployment-plan.md; opt-in one-company Guided research, explicit plan/run, max three approved tools/two model calls/12 steps, bounded evidence and spend reservations, validated citations, partial recovery, fingerprinted session reuse.

Initial working-tree hashes:
```json
{
  "docs/features/2026-10-04-five-day-predeployment-plan.md": "d0b7cca5d92fa95e30cb2325b9cf7ce95ac09a1f3a4a2e551cb6bf393f5148d0",
  "docs/features/2026-10-05-p01-connected-context-team.md": "65f3200cf79855f9a283ae4bc88a57239ca140a17279e49c06ffb40cd74ec46e",
  "docs/features/2026-10-06-p02-terminal-ui-team.md": "413db3e37854b4e7e45aa799c4e98a16ab12d2b6b4cb758ea903c8174ed464b8",
  "src/langgraphagenticai/state/research_context.py": "549d9de2e7397c5f04bca5448a1cdd00228a262d000b26de0be9d86985afc2b7",
  "src/langgraphagenticai/ui/workspace_handoff.py": "932e649a2b564c0eefe027912702181f2e6af279e9fa27cd74b5d9f256e07496",
  "src/langgraphagenticai/ui/workspace_presentation.py": "ebf65f697eacf428a885079b61d5b0e5301a4ea29da7b0d75fda1dbc6520f60e",
  "tests/test_workspace_handoffs.py": "3ab8c6d3f068c1f1059706c9745c555ef27cd71a4f9bb2f18e7a0fbe10afd253",
  "tests/test_workspace_presentation.py": "c15cce8edce3cda5bde28e9233df2ab9efabb8bc2408ca4b42cceefbe7debde2",
  "PLAN.md": "56a64256dd085e40f359075d3ed48a9348916c5b2487cea48ff38685ed5bb937",
  "README.md": "ff0c3607f5e54e7bf855e2ebf1324990664ba6eef66f6d098b7144ebc43427a2",
  "src/langgraphagenticai/main.py": "a097b797d5f0dd02ec4c45585b8acd6d0599fdfe74522d85db961a4648c36862",
  "src/langgraphagenticai/ui/ai_portfolio_manager_tab.py": "56cf99e38e881b8d7e150af01b60accfc0f74d56c42bd7b908a506b88716f820",
  "src/langgraphagenticai/ui/app_shell.py": "a2f23c65176c9e5257369f7a70068732262e8971e9b287d2781def2aefbdc0fe",
  "src/langgraphagenticai/ui/deep_research_tab.py": "6effa39d99f06b85809d08f4956c944cb4ea74c03fc2ff08c984993a7947afb4",
  "src/langgraphagenticai/ui/deep_research_v2_tab.py": "c1c160a92fe09af783cd9be58f26859dedef94de3fa20d9bbde2315b2fdcaf63",
  "src/langgraphagenticai/ui/equity_report_tab.py": "6398a626e595e8d9ec8ffaad486163271dc3a91fa6c16e7abbd63a294cbcd84e",
  "src/langgraphagenticai/ui/introduction_tab.py": "c0efe434bda8679878ea4af5c9a6d4f306155f2a6e2eeb7e5b3d8742c8277800",
  "src/langgraphagenticai/ui/stock_screener_tab.py": "bdda4abcc31a71e9f1a1aa9ab030c5a6e2096dd38d9c2e44a8ea7297aafda267",
  "src/langgraphagenticai/ui/streamlitui/loadui.py": "9eb3f1d0fcf962d8819e66bc8cbb0c82b4dd766b48ed2ea76ccbb6789a251276",
  "src/langgraphagenticai/ui/top_movers_tab.py": "7ade0f968e7c40bb3f3e37e91e431fe7a93c3d8f448407a4adda3ba13a4a3399"
}
```

Jira connection: native mcp__atlassian tools; verified resource fa84d787-6378-47fc-bac7-60e49031f5ef, AAFA. Initial P03 duplicate query found no matching P03 task. Creation ledger: 0/5 attempts.

Stages: specialist completed; planner completed; builder pending; independent verifier pending.

## Jira durable attempt ledger

Attempt 1/5, 2026-10-07: pending. Items P03-01 through P03-05. Scope snapshot unchanged since planner; duplicate check empty; coordinator approves this individual tracking-task create under explicit user request. Exact payload:

```json
{
  "cloudId": "fa84d787-6378-47fc-bac7-60e49031f5ef",
  "projectKey": "AAFA",
  "issueType": "Task",
  "summary": "P03: Add explicit bounded Guided research with validated evidence and session reuse",
  "description": "Implement Day 3 P03 from Axiom: five improvements in five days as a local working-tree delivery. Research currently offers chat but lacks an inspectable approved-tool plan and separately bounded execution. Add opt-in one-company Guided research: explicitly prepare a structured plan, inspect steps and limits, explicitly run approved read-only tools, and receive an evidence-linked answer with partial failures and usage visible.\n\nRun 2026-10-07-p03-guided-research-team; baseline 77f7275070790cda4ec18754f3dfa01258ef3e9c. Preserve existing P01/P02 local changes. Source boundaries: main.py, tools/finance_tool_registry.py, existing FMP transport and bounded OpenAI clients; focused new provider/domain/UI modules.\n\nD01-D06: strict ticker and returned-row identity; independent FMP stable profile/quote; explicitly annual income revenue/operatingIncome/netIncome with FY/date/currency; bounded Marketaux news metadata, no article fetching. Saved AAPL FMP018/045/061 samples from 20261003T044241108241Z support offline contracts only. Quote currency is profile-reported, unknown dates stay unknown, annual is not TTM. No unsafe broad MCP summaries, shares fallback, ratios/growth or fiscal substitutions.\n\nAcceptance P03-01 through P03-05: maximum three approved dispatches, two total model attempts including retries and twelve graph steps; bounded contexts/output and pre-call token/configured-price reservations. Unknown prices explicitly lack guaranteed dollar cap. Unapproved/oversized plans rejected before dispatch. Partial failures preserve successful evidence. Material structured facts reproduce cited field/value/currency/period; invalid claims withheld, prose validation limits disclosed. Input/plan/evidence fingerprints preserve saved work and mark mismatch. Ordinary reruns/navigation/downloads make zero new provider/model calls; two sessions/tickers isolated. Prepare calls planner only; Run executes bounded tools and synthesis. Existing chat/P01/P02 retained; explicit Deep Research navigation only.\n\nPlanned offline verification (not yet completion evidence): saved/synthetic adapter fixtures; hostile plan/budget/citation cases; session call-counter interactions; full guarded pytest; compile/import; fresh Streamlit health; synthetic browser plan -> run -> partial -> reopen/download -> mismatch -> explicit new run. README/PLAN record actual results.\n\nExcluded: autonomous browsing, long-running jobs, committees, durable restart checkpoints, live financial/model verification, commits/pushes and deployment. User explicitly requested Jira tracking and completion. Local completion is distinct from hosted release. Local report docs/features/2026-10-07-p03-guided-research-team.md."
}
```

Initial source/test/document snapshot directory (outside repository): C:\Users\andna\AppData\Local\Temp\axiom-p03-baseline-8jawq1oi

## Financial specialist completed (read-only)
D01 strict security validation and returned-row identity; fact envelopes retain source route, retrieval/date, status, unit, basis and missing/zero distinction. D02 narrow stable profile FMP-018 and quote FMP-045 via shared fmp_http: two independent requests, preserve partial, omit percentage scaling and invalid shares fallbacks. Saved AAPL samples: fmp_data_reference/samples/{FMP-018,FMP-045}/20261003T044241108241Z/AAPL-default.json. Profile undated; quote epoch-seconds as-of; currency explicitly profile-reported. D03 annual income FMP-061 stable/income-statement limit1; saved sample AAPL-annual.json at same run directory used limit5, FY2025 end2025-09-27. Require symbol/date/FY/currency; revenue/operatingIncome/netIncome raw monetary amounts only; no TTM/growth/specialist metric inference. D04 Marketaux existing /v1/news/all one page five records seven-day requested window, matching entities, safe URLs, explicit error versus empty; no article browsing or news model. Synthetic fixtures, no live coverage proof. D05 structured field/value/basis validation and retained partial facts; no claim that valid citations prove prose. D06 max3 dispatches,2 model attempts,12 graphsteps; bounded contexts/outputs, before-call reservations, configured price assumptions and unknown pricing explicit; fingerprints/session reuse. Detailed specialist handoff retained in conversation and passed intact to dependent roles; no financial/model calls or source edits made.

Jira live metadata: AAFA project10066 is create-eligible; supported Task type10074. Required fields issue type, project, reporter, summary; native create uses current reporter. User explicitly requests Jira tracking and completion, overriding default skill restriction on modifying/transitions and permitting one implementation task before work. No completed-work placeholder tickets. Planner will validate requested scope before coordinator creates tracking task; independent verifier will approve completion evidence. No priorities/assignments assumed.

Verification environment: ../venv/python.exe Python3.12.0, Streamlit1.61.1, pytest9.1.1. Baseline full suite started with PYTHONPATH=src plus external temporary autouse network guard and -p offline_guard. Result pending; no new test claims yet.

Framework reference read: official https://docs.langchain.com/oss/python/langgraph/graph-api; typed state/nodes/edges and recursion_limit bound graph steps, separate counters still required. Existing installed bounded OpenAI client and explicit structured technical-analysis pattern inspected; no model migration or price claims. Browser skill agent-browser read including CLI core workflow; installed available, use named session and synthetic services.

## Planner completed (read-only)
P03-01 focused providers/guided_research.py adapters D01-D04; P03-02 strict bounded schemas and sequential LangGraph research workflow D05-D06; P03-03 exact field/value/currency/period grounded facts with invalid claims withheld; P03-04 explicit opt-in Research mode, prepare/run, session fingerprints and Deep Research navigation preserving P01/P02; P03-05 focused/full guarded tests, compile/import, fresh health and synthetic browser, actual README/PLAN evidence. All Day3 acceptance applies, no breadth expansion. Coordinator independently compared proposed scope to Day3 and data handoff and approves the implementation tracking payload.

Attempt1 confirmed created AAFA-10 https://bigmeatpete717.atlassian.net/browse/AAFA-10. One of five attempts used; no failed/uncertain creates. Initial failed report patch made no Jira call and consumed no creation attempt.

AAFA-10 transition21 verified In Progress. Builder started after preceding handoffs. Fresh guarded baseline full pytest:367 passed in100.07s before P03 implementation. Independent completion remains pending.

Coordinator direct sample confirmation: FMP018/045/061 saved files are JSON row lists; profile has selected symbol/business/currency, quote has price/marketCap/timestamp and lacks its own currency, annual income has FY/date/reportedCurrency. This corroborates specialist D01-D03 without live collection. Current and latest FY are distinct. Builder instructed to count conservative full request/token reservations including schema/system overhead, no char/4 guaranteed cap, zero SDK retries, preserve failed reservations, enforce fingerprints at server boundary and strip configured credential values beyond regex.

## Acceptance checklist (final local evidence recorded October 8)
- [x] Opt-in Guided research beside preserved Chat; Prepare plan explicit, no providers.
- [x] Inspect up to3 unique approved read-only steps and limits before explicit Run plan.
- [x] Focused typed LangGraph workflow <=12steps, <=3logical dispatches, <=2total model attempts; complete serialized budgets and pre-call reservations.
- [x] Underlying request/retry limits honest; unknown pricing/date/currency meaning explicit.
- [x] Partial failures retain source facts, missing inputs, sanitized status/progress/usage.
- [x] Structured factual values/currency/as-of/basis match existing evidence IDs; unsupported claims withheld.
- [x] Fingerprint request/config/plan/evidence; mismatch notices preserve valid saved work.
- [x] Session and ticker isolation; navigation/rerun/download zero new provider/model calls; new explicit run separately counted.
- [x] Explicit Deep Research handoff only; no automatic launch.
- [x] Secrets/private prompts excluded from diagnostics/session artifacts/downloads.
- [x] Focused/full offline tests, compile/import, fresh health, synthetic browser changed interaction and independent verification.
- [x] README/PLAN actual dated records; broad milestones and deployment remain pending.

Coordinator synthetic actual-main browser harness created outside repository at C:/Users/andna/AppData/Local/Temp/axiom-p03-verification/browser_harness.py. External HTTP blocked; only injected FMP/Marketaux/model fixtures. Harness Streamlit8523 fresh health returns ok; initial render pending. This is interim evidence, not completed browser acceptance.

## Interim coordinator acceptance corrections
Early code/browser inspection identified same-input plan regeneration reusing prior answer, workflow repetition not consuming stored execution, missing live progress, pending command ingestion after mode gate, pre-prompt credential scrubbing, date/unit/unknown-usage presentation and news malformed-row/dedup concerns. Sent to original builder; no separate review team, no premature Jira completion. Interim synthetic actual-main browser observed explicit planning with no providers, bounded execution/news failure preserving profile/quote/annual zero, and repeated Run/expander causing no new calls. These observations predate corrections and do not replace final browser verification.

Fresh actual app startup: ../venv/python.exe -m streamlit run app.py --server.headless true --server.port8524 --server.fileWatcherType none --browser.gatherUsageStats false; curl.exe --fail --silent --show-error http://localhost:8524/_stcore/health returned ok. Health only: actual app browser not opened because .env can enable live providers. Changed interaction is exercised through the actual-main synthetic harness instead. Final source/browser/independent verification pending.

## Independent review and correction round
Builder initial delivery:386 guarded offline tests passed159.93s (367 baseline+19P03), compileall/import/diff checks passed. This inventory predates the following corrections. Independent verifier initial focused19passed16.32s and independent hostile assertions confirmed spend reservation blocks synthesis before a second model call while preserving annual evidence; consumed replay rejected; currency/date/value/field mismatch withheld.
F01 introduced security: configured secret replacement after truncation could save a credential fragment at800character boundary. Builder corrected replacement before truncation and before generic redaction in both adapter/workflow; end-to-end boundary regression, initialfocused20passed14.22s.
F02 clarity: unknown pricing exported numeric0reservation without unknownflag. Builder asked to use reserved_cost=null and explicit pricing_status, known arithmetic only; final tests pending.
F03 live request contract: JSONmode json_object request lacked literalJSON instruction. Coordinator fetched official OpenAI structured outputs guide https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=chat, JSONmode section documents API error without JSONcontext. Independent SDK boundary fake reproduced one call rejected by contract; builder asked explicit JSONinstruction plus client-boundarytests/refusal/truncation/retrylimits. No live model call.
Browser tooling obstruction: generic scroll targeted window while Streamlit .stMain remained scrolled268px under fixedheader. Scrolling the correct .stMain container restored real modeclick; no source defect attributed. Final browser acceptance still pending correctedsource restart.


## October 8 completion resume
Build mode: user requested completion now and continued Jira tracking. Resume original run and original ledger (1/5 create attempts; AAFA-10 confirmed). No new feature scope, commits, pushes or deployment. Baseline HEAD remains 77f7275070790cda4ec18754f3dfa01258ef3e9c; existing P01/P02/P03 working-tree changes preserved. Resume scoped hashes/status saved outside repository at C:\Users\andna\AppData\Local\Temp\axiom-p03-completion-20261008. Live Jira read confirms AAFA-10 In Progress; AAFA-8 To Do and AAFA-9 Done remain tracked. Four required roles will refresh sequentially; final health/browser and independent corrected-source acceptance pending.

### Refreshed specialist and planner handoffs
Specialist refreshed D01-D06 against current adapters, dictionary/coverage and exact saved AAPL samples. No new endpoint or financial basis required. Saved FMP-061 first row FY2025 ended2025-09-27: raw revenue416161000000/operatingIncome133050000000/netIncome112010000000. Folder stamp is not substituted for coverage retrieval timestamps. Required disclosure corrections: inferred Unix-seconds quote timestamp and independently unverified monetary scaling; builder added explicit evidence limitations and saved-sample assertions. Planner retained P03-01 through P03-05, with final corrected-source browser, guarded full suite, compile/import/health and independent F01-F03 review as acceptance gates. No broader roadmap completion claimed.


## October 8 final builder and coordinator verification
Builder resume delta is limited to provider timestamp/scaling limitation strings and saved-sample regression assertions. Full guarded command with `PYTHONPATH=src;C:/Users/andna/AppData/Local/Temp/axiom-p03-verification`: `../venv/python.exe -m pytest -q -p offline_guard` ? **389 passed in167.06s**; focused `tests/test_guided_research.py` ? **22 passed in25.75s**. Initial concurrent focused run had one existing AppTest3second timeout; full suite and sequential focused rerun passed without timeout changes. Python3.12.0 / pytest9.1.1 / Streamlit1.61.1. Compileall app.py/src, imports app/main/provider/schema/workflow/UI and diff checks passed. First import command named nonexistent research.guided; corrected actual-module import passed. Unmocked Requests/httpx/curl_cffi blocked; no paid or live financial/model calls.

Independent verifier read all P03 provider/schema/workflow/UI/main integration and exact saved AAPL contracts, rechecked F01-F03 and scoped hashes, and separately ran **22 guarded focused tests passed in18.35s**, exit0. No actionable remaining source defects or new-ticket candidates. Final completion approval follows coordinator browser/document evidence, rather than earlier interim checks.

Fresh actual app startup: `../venv/python.exe -m streamlit run app.py --server.headless true --server.port8534 --server.fileWatcherType none --browser.gatherUsageStats false`; `curl.exe --fail --silent --show-error http://localhost:8534/_stcore/health` returned **ok**. No actual-app page was opened because .env can enable live services. Final-source synthetic actual-main harness restarted on8533; its fresh health returned **ok**. Harness blocks external HTTP and injects only synthetic FMP/Marketaux/model fixtures. It invokes current actual main/sidebar/Guided workflow, with graph-building blocked.

Agent-browser isolated browser sessions exercised explicit preparation (model1/provider0), inspected approved plan, execution with failed news preserving financial facts/netIncome0 (model2/provider4), repeated Run, evidence expansion, download clicks and Chat/Guided return without new calls. Saved chat persisted. Ticker/model mismatch retained prior work and blocked execution; reverting restored matching. Explicit new plan/run incremented counters to3/4 then4/8, reflecting separately authorized runs rather than exceeding a single-run cap. A second MSFT session started0/0 and independently reached2/4 while first AAPL stayed4/8. Explicit Open Deep Research selected that workspace without starting collection or a model. Evidence displayed annual FY/date/units and the new timestamp/scaling caveats. Screenshots/assertions at1440x900,1280x800 and390x844 found no page overflow or Streamlit exception.

Tooling qualifications: cold app import exceeded initial25second browser wait; rechecked after render. CLI semantic label fill did not commit a ticker in this layout; fresh snapshot-reference fill plus Enter verified the actual control. Native `agent-browser download` save reported canceled twice; browser network showed HTTP200 from the actual JSON media endpoint, which was retrieved with curl and parsed. Export response checks passed MSFT identity, null/unknown pricing, two attempts, zero netIncome, partial news failure and absence of configured synthetic credentials. Browser download clicks/reruns preserved counters. Native browser file-save behavior remains unconfirmed; application response/export content is verified.

Artifacts outside repository: `C:/Users/andna/AppData/Local/Temp/axiom-p03-completion-20261008/{browser_harness.py,final_browser_checks.py,remaining_browser_checks.py,additional_browser_checks.py,final_browser_results.json,additional_browser_results.json,download-check.txt,guided-msft.json,guided-final-1440.png,guided-final-1280.png,guided-final-390.png,deep-handoff.png}`. No artifacts, caches or credentials introduced into source. No commit/push/deployment, live entitlement/freshness/model-quality or clean-install claim. Broad R04/R06/R07 remain partial.

Final source/test snapshot SHA256:
- providers/guided_research.py:9a4ff557ee804f23f3163b0c9acedecdba7f9678b54d44916620dad6e2f64afd
- tests/test_guided_research.py:4d1c3dd6addadb8afb1a41cb130dd47ba1daad0901ba8eb5e3f43c2b5c3b911f

Jira completion publication is pending final independent browser-artifact acceptance. Existing create ledger remains1/5; AAFA-10 is the existing implementation ticket, not a new create. AAFA-8/AAFA-9 statuses are preserved.


## Final independent completion approval
Independent verifier approved P03 local completion after reviewing final browser scripts/results and independently validating MSFT export. F01-F03 closed; zero actionable unresolved findings or new-ticket candidates. Native browser file-save remains a documented tool-limited check, not claimed verified. Four distinct specialist/planner/builder/verifier roles completed sequentially on resume. All P03-01 through P03-05 local acceptance approved; broad roadmap and deployment remain pending. Final source hashes saved outside repository and rechecked unchanged before Jira publication.

### Authorized Jira completion update ledger
Existing AAFA-10 completion comment and transition31 (live metadata target Done) approved by coordinator after independent acceptance. Pending publication; no new create attempt. Original create ledger remains1/5. User request to complete P03 and ensure Jira tracking authorizes this scoped update; AAFA-8/AAFA-9 unchanged. Exact independently verified payload is retained below before sending.

```json
{
  "cloudId": "fa84d787-6378-47fc-bac7-60e49031f5ef",
  "issueIdOrKey": "AAFA-10",
  "commentBody": "P03-01 through P03-05 completed as a local working-tree delivery in run 2026-10-07-p03-guided-research-team. Research now provides explicit one-company Prepare/Run, three allowlisted tool dispatches, two model attempts without SDK retries, bounded graph execution, pre-call reservations, validated structured citations, partial recovery and fingerprinted session reuse.\n\nIndependent guarded focused tests: 22 passed in 18.35s. Fresh builder full suite: 389 passed in 167.06s; compilation, imports and diff checks passed. Python 3.12.0, pytest 9.1.1, Streamlit 1.61.1. F01 credential-boundary, F02 unknown-cost export and F03 JSON request-contract corrections independently approved.\n\nCorrected-source actual-main synthetic browser checks passed explicit planning without providers, partial execution, repeated Run/download/navigation without additional calls, ticker/model mismatch, separately counted new runs, isolated AAPL/MSFT sessions and explicit Deep Research navigation. Three viewport checks showed no overflow or Streamlit exceptions. Fresh actual app and synthetic harness health returned ok.\n\nBrowser-requested JSON endpoint returned HTTP 200; independently decoded export preserved MSFT identity, zero net income, unknown pricing as null, partial failure and credential exclusion. Native agent-browser file saving reported cancellation twice and remains unverified; no application/export-response failure observed.\n\nSaved AAPL provider samples and synthetic services were used. Inferred quote timestamps and unverified monetary scaling are disclosed. No live financial/model calls, commit/push, clean-install certification or hosted deployment. Broad R04/R06/R07 remain partial. Zero new follow-up issues; original creation ledger remains 1/5."
}
```

Jira completion comment confirmed: AAFA-10 comment10122, native addOrEditJiraIssueComment isError=false. Transition31 to Done pending; create ledger remains1/5.

Jira transition confirmed: AAFA-10 transition31 succeeded, returned statusName Done (isError=false). Verified completion record https://bigmeatpete717.atlassian.net/browse/AAFA-10 with comment10122. Zero new issues;1/5 original create attempts. P03 is complete locally, working tree only; deployment pending. AAFA-8/AAFA-9 left unchanged.

Final Jira read-back verified AAFA-8 To Do, AAFA-9 Done, AAFA-10 Done; final source hashes unchanged after publication. Temporary verification browser sessions/servers stopped; artifacts retained outside repository.
