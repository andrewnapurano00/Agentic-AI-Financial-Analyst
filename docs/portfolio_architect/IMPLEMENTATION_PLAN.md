# AI Portfolio Architect implementation plan — 2026-10-19

## Initial repository discovery / design decision (placement superseded below)

The actual root `app.py` loads the full Axiom application through `main.py`; it does not call the trading renderer directly. Portfolio Lab currently mounts Portfolio Ideas, Optimizer and AI Portfolio Manager. The paper trading/replay modules exist but are unrouted legacy code. The earlier ZIP contains a different, standalone launcher. Preserve all existing routes, session keys, experiments and export contracts; add an independent **AI Portfolio Architect** tab and a focused `portfolio_architect_app.py` launcher for standalone use. Do not remount replay or change paper order logic.

Reusable boundaries: `providers/fmp_http.py` (TLS, bounded retries, sanitized exceptions), `providers/openai_client.py` (timeouts/retries), `state/research_context.py` (symbol validation), `utils/{safety,export_csv}.py` (credential/formula filtering), `ui/app_shell.py` (shared presentation). `paper_market.py` and `paper_history.py` have nine-symbol/replay-specific contracts and cannot directly serve a 15-holding discovery workflow. New adapters must remain under providers. Existing portfolio engines have different execution/objective contracts; do not pass recommendations into them.

Final validation interpreter located at the parent project's `venv/python.exe`: Python3.12.0, Streamlit1.61.1, pytest9.1.1, Pydantic2.12.5. Initial exploration used Anaconda Python3.12.7 / Streamlit1.64.0 / pytest7.4.4; default shell Python lacks pandas. No new dependencies installed (NumPy/pandas/Pydantic/Streamlit already present). The working tree already contains unrelated tracked and untracked edits; preserve them. The attachment's trailing browser/session dump is unrelated and must not enter source/docs/exports.

## Concrete phases / acceptance

- [x] P1: typed versioned mandate/evidence/result/error contracts; explicit Interpret then editable mandate then Build; bounded documented curated US universe; offline synthetic demo; live credential preflight and partial recovery (mocked verification, no live entitlement certification).
- [x] P1: deterministic 5–15 holding selection, exclusion/eligibility checks, position/sector/cash feasibility and audited dollar/cash reconciliation. No broker/order dependency.
- [x] P2: aligned observed dates with no filling, sample covariance and disclosed diagonal shrinkage, inverse-volatility and conviction-risk sizing alongside equal weight, honest unavailable risk states, static-mix historical diagnostics and benchmark context.
- [x] P3: one bounded structured interpretation call and at most one combined specialist review call; grounded reason/citation enums, mechanical risk challenge and final committee; invalid AI preserves local construction. No arbitrary model numerical claims.
- [x] P3: shared institutional UI, allocation/sector charts, per-holding pros/cons/sizing, rejected alternatives/dissent/thesis breakers, session-only snapshots and safe CSV/JSON/HTML exports.
- [x] Verification: offline domain/provider/AI/UI tests; existing paper regressions; full suite1046 passed; compile/import, both Streamlit health endpoints, desktop/mobile demo and navigation reuse. Missing-key/error/recovery paths are AppTest/mocked, not real live browser/provider checks. Exact results in VALIDATION.md.
- [x] Documentation: data dictionary, user guide, validation record, README and PLAN R01/R02/R04/R06/R07/R08 scoped update. Phase4 extension contracts documented, not implemented services.

## Files / boundaries

`portfolio_architect/{schemas,universe,mandate,research,risk,optimizer,committee,workflow,export}.py`; `providers/portfolio_architect.py`; `ui/portfolio_architect_tab.py`; `main.py` (one new tab); `portfolio_architect_app.py`; `tests/test_portfolio_architect*.py`; this directory, README and PLAN. Tests mock all providers/models; no paid/live calls are authorized by a test.

## Budgets / extension hooks

Universe capped at 40 names plus benchmark; primary quote batch plus profile/ratios/history per name, concurrency three, shared safe GET retries may add HTTP attempts. Cache quotes/fundamentals five minutes and history six hours with credential-scoped cache keys and original retrieval times. Exact snapshot hash covers all retained evidence. At most two model calls over Interpret + Build, 90 seconds and no SDK retries per call; bounded input/output tokens, no dollar-cost guarantee with unknown pricing. Ordinary reruns/downloads/navigation make no new feature calls. No scheduler, broker, durable storage, point-in-time backtest, news, fund look-through or fabricated forecasts. Future persistence/review adapters should consume immutable saved recommendations and require explicit user actions; do not build them now.

## User routing correction - 2026-10-19

Dedicated Axiom sidebar page **AI Robo Advisor**, with conditional Portfolio architect / Agent traders renderers in `ui/robo_advisor_tab.py`. Initial fourth Portfolio Lab tab removed; original three tabs remain. Shared Axiom Settings provide credentials/model. Legacy trader workspace names migrate to the new route. Architect results and trader accounts retain session keys. The standalone launcher/ZIP is a dated artifact, not the primary integration. R03/R06/R08 remain partial.

## Portfolio Lab simplification - 2026-10-19

User-directed final navigation: Portfolio Lab has Optimizer and AI Portfolio Manager only. Portfolio Ideas is removed from active UI and entry-point reload behavior; its source/tests remain legacy. AI Robo Advisor retains Portfolio architect and Agent traders, unchanged. This supersedes earlier notes about three Portfolio Lab tabs. Publication of accumulated portfolio work is explicitly authorized; no deployment is implied.
