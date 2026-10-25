# Advisor regular-endpoint screen and ETF allocation theses

Date: 2026-10-24. Working-tree delivery; no publication or deployment.

## User outcome

AI Robo Advisor uses the existing Settings FMP credential and regular ratios-ttm/key-metrics-ttm endpoints already used by Equity Report. It no longer probes premium bulk financial endpoints. Client-side batching means paced individual requests, not a claim that the provider supports multi-symbol financial calls. Full current membership (400?550 symbols) is screened; a bounded stock shortlist receives deeper collection and curated ETFs are considered separately.

## Collection contract

- Three workers share the existing 100-logical-request gate and 30-second cooldown. A screen needs up to two requests per member plus membership; transport retries remain independently bounded. This can take several minutes.
- Successful screen evidence retains the one-hour credential-scoped Streamlit cache and original collection timestamp. Explicit refresh clears the saved screen. No automatic model action or cross-workspace financial-packet reuse was introduced.
- Authentication/access failure stops queued requests for that endpoint; at most the three in-flight workers can reach it. HTTP 429 stops the shared collection. Independent metric routes retain partial successful evidence with summarized sanitized coverage diagnostics.
- Stable membership and batch quotes retain their existing disclosed compatibility paths. This delivery does not remove every possible HTTP 402 message or certify live plan access.

## ETF assessment contract

New `portfolio_architect/etf_assessment.py` maps curated categories to core equity, dividend, small-cap, growth/sector, Treasury, bond and gold allocation hypotheses. Saved daily price observations support sample standard deviation times sqrt(252) and running-peak maximum drawdown with at least 61 valid prices. Original provider, price basis, retrieval time and observed window accompany model-context history statistics. These are historical price-return descriptions, not total returns, expected alpha or fair value.

Company ratios are neither requested nor normalized into newly collected ETF evidence. Separate fund roles/conditional drivers/risks reach local selection explanations, holding tradeoffs, the bounded specialist packet and existing exports. Fund thesis-break conditions refer to allocation role, fees/tracking and exposure changes. Company scores, allocation/cash/cap math and explicit AI boundaries are preserved.

Missing fees, constituents/overlap, tracking, NAV valuation, bond duration/credit/yield and underlying equity valuation remain explicit gaps. Curated category labels are not verified constituent exposure. This is a bounded allocation-thesis improvement, not completed ETF valuation or look-through risk-policy adoption (AX-05 remains partial).

## Verification

Offline provider, screening, cache isolation, pacing, arithmetic, packet, selection and UI checks; detailed commands/results in PLAN. Browser verification used a temporary synthetic five-ETF saved result with provider collection and specialist calls blocked. Core and guarded-fixture Streamlit health returned `ok`; browser opened holding research and GLD details with the distinct fund thesis, missing valuation inputs and historical risk statistics. No live provider/model call, account entitlement check, deployment or real model-quality certification.
