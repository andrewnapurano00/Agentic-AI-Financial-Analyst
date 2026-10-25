# AX-05 portfolio risk policy ? 2026-10-23

## Baseline and scope
Inspected working tree at e94c677 with existing AX-01?04 changes retained. Existing optimizer validates positive weights, count, position/category caps and minimum cash; covariance sizing and risk preference do not enforce future risk. Saved reports and exports are session-backed; explicit Build collects evidence and optionally requests one AI review. No new provider/model actions are added.

Scoped plan: preserve existing allocation math, add an opt-in reject-only historical-volatility gate, publish saved machine-readable policy, show explicit top-level stress arithmetic and unknown exposure/cost states. No automatic cash, cap or policy relaxation. AX-04's company-earnings family does not validate portfolio histories; this slice uses existing aligned price-return evidence and its disclosed adjustment limitations.

## Delivery
`portfolio_architect/risk_policy.py` validates final weights through the existing validator. Historical ceiling uses sample daily price-return volatility (ddof=1, 252 sessions; no shrinkage), 60 returns and 90% common-date coverage. It requires history end within ten calendar days and history retrieval within thirty days of the saved snapshot; future/naive retrievals fail. Historical policy is checked before paid review and on the final result. A failed AI proposal falls back to the already compliant local selection. No future volatility/loss ceiling or suitability certification follows.

The advanced editor explicitly enables and sets the ceiling. Failed construction retains the saved report. Existing mandates default to no ceiling; legacy reports remain readable with an unavailable audit notice, without recomputation. Policy includes checked caps/count/cash/budget, descriptive preferences, concentration warnings at 20% position / 40% category, three explicit fractional price-shock scenarios and USD changes. Cash has zero shock. These are educational assumptions without probabilities or forecasts.

No eligible dated ETF constituent holdings, benchmark constituent weights, current account holdings or execution-cost assumptions exist at this boundary. Those outputs remain unknown/unavailable with null quantities, never reassuring zeros. Existing category duplication/high-correlation warnings remain. Numerical scenarios do not infer ETF constituents. JSON and HTML use the existing sanitized saved export path; allocation CSV remains unchanged.

Sources: schemas.py, workflow.py, risk_policy.py, ui/advisor_mandate_editor.py and ui/portfolio_architect_tab.py. Tests: tests/test_portfolio_risk_policy.py plus existing Architect and guided UI suites.

## Verification
- Focused: `../venv/python.exe -m pytest tests/test_portfolio_risk_policy.py tests/test_portfolio_architect.py tests/test_advisor_guided_ui.py -q --tb=short`: 73 passed in 50.41s on final UI/policy source. The initial new UI fixture had sufficiently diversified synthetic volatility to pass its supposed failing ceiling; made those synthetic histories perfectly correlated, then verified rejection and retained result. No product limit was changed to fit the test.
- Compileall app.py/src, app/main import, final policy/editor/page imports passed. Project Python 3.12.0, pytest 9.1.1, Streamlit 1.61.1.
- Actual app `/_stcore/health` on 8587 and guarded synthetic harness health on 8586 returned ok. Browser used agent-browser session ax05-20261023 with requests/httpx external calls blocked. Built once, enabled 1% historical ceiling, verified 9.05% rejection with previous portfolio retained; two explicit collections total, unchanged after tab/rerun actions. Risk panel, saved checks/unknowns/scenarios, desktop 1440px and narrow 390px screenshots inspected. Browser errors empty. Temporary harness/screenshots outside repo; own server PIDs 28344/22632 stopped and browser closed.
- Full offline inventory: `../venv/python.exe -m pytest -q --tb=short --durations=5` with PYTHONPATH=src: **1224 passed in 548.74s**. The final UI-only table labels/number formatting were additionally covered by the final 73-test focused run, final compilation/imports and browser checks above.
- Diff whitespace check passed (existing CRLF normalization notices only). Offline synthetic fixtures only; no live providers, paid model, commit, publication or deployment.

## Remaining
AX-05 is a bounded risk-policy slice: forecast/ex-ante risk constraints, eligible ETF look-through, benchmark-relative holdings, account-aware turnover/cost estimation and universal Portfolio Lab policy adoption remain open. Existing engines remain separate. Historical price adjustment and source coverage limitations still apply; no broad financial correctness certification.
