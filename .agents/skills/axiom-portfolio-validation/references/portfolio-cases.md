# Portfolio invariant fixtures

Weights in the current constraint validator are fractions. Inspect the active schema before carrying that convention to another boundary.

## Infeasible position capacity

Two securities capped at 0.30 each, with no required cash buffer, can invest at most 0.60. The coherent result has at least 0.40 cash.

Renormalizing the two final positions to 0.50 each violates the cap. Test the final security rows, cash row, diagnostics, and exported allocation.

## Sector and cash constraints

Two Technology securities plus one Healthcare security, position cap 0.40 and sector cap 0.50, cannot allocate all capital to Technology. Assert each position <= 0.40 and Technology total <= 0.50 after adjustments.

A cash buffer of 0.10 gives an investable ceiling of 0.90, not a requirement to invest exactly 0.90. Capacity constraints may create additional residual cash.

Choose a numerical tolerance, for example 1e-9 for a small deterministic fixture, and state it in the assertion. Do not round weights before enforcing constraints.

## Trade reconciliation

Portfolio value 1,000, current security weight 0.20, target weight 0.30, and price 10:
- Current value 200, target value 300, proposed buy value 100.
- Current shares 20, target shares 30, share change +10.
- With no fees or other trades, cash must fall by 100.

For price zero/missing, preserve value-level research if useful but mark share counts unavailable. Fees, slippage, whole-share rounding, or suppressed small trades require recalculating achievable cash and weights.

## Risk checks

Use a known sequence with an independently computed result:
- A flat return sequence gives zero volatility; Sharpe is undefined unless a documented convention says otherwise.
- Wealth path 100 -> 80 -> 90 has a maximum drawdown of -20%.
- Starting with a -20% return needs the initial wealth point included in the drawdown definition; a cumprod series starting after that loss can miss the initial drawdown.
- Sample and population covariance differ; preserve and label the estimator.
- Convert an annual risk-free rate consistently to the sampling period before computing excess returns.
- Align asset and benchmark dates; do not interpret missing quotes as zero returns.

One security, zero proposed weights, sparse history, unknown sector, duplicate holdings, mixed currencies, and nonfinite model weights are useful targeted cases. Confirm whether duplicate holdings should be aggregated or rejected.
