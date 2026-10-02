# Hand-checkable financial cases

Use an independent expectation and retain the input basis in each test. These fixtures illustrate contracts; they do not define every product policy.

## TTM and growth

Four consecutive quarters with revenues 10, 20, 30, and 40 produce TTM revenue 100. Four comparable prior quarters totaling 80 produce TTM growth 100 / 80 - 1 = 0.25.

A duplicate Q2, missing Q3, mixed currencies, or annual row among the quarters should not produce apparently complete TTM. Check actual fiscal year/quarter identity, not merely approximately 90-day date gaps. A 52/53-week fiscal calendar may need a documented date tolerance.

A prior revenue of zero has undefined ordinary percentage growth. Negative prior revenue requires an explicit comparison policy rather than a visually plausible percentage. Do not pick that policy incidentally in a formatter.

## Ratios and percentages

Net income 10 divided by revenue 100 gives a 0.10 margin, displayed as 10%. A provider changesPercentage of 2.5 is already percentage points, displayed as 2.5%, not 250%.

A real zero margin displays as 0%; a missing margin stays unavailable. A zero denominator is undefined. NaN and infinity are not valid numeric metrics.

## Historical prices

Closing prices 100 and 110 imply a 10% price return. If a 2-for-1 split occurs between observations, raw closes 100 and 50 alone do not prove a 50% economic loss. Use a coherent adjusted series or disclose the raw-price limitation.

Test the difference between calendar ranges and trading-session windows. A 1Y return requiring 252 prior sessions needs 253 observations; insufficient history must remain unavailable. Do not forward-fill across an unknown coverage gap without a documented policy.

Order and deduplicate dates before calculations. Never compare a current intraday quote with an old historical endpoint while describing both as the same as-of window.

## Valuation and peer scoring

A P/E with negative earnings is not a bargain just because it is numerically below positive P/Es. Define applicability/handling with the metric registry and sector rules.

Missing peer inputs should reduce visible coverage rather than secretly become zeros or favorable ranks. Keep score weights and normalization reproducible from the saved scorecard and configuration.

Do not compare TTM revenue with forward revenue in the same unlabeled price-to-sales ranking. Currency conversion, when requested, needs a dated FX rate and a declared reporting currency.

## Edge cases to select

Test zero, None, nonfinite values, numeric strings, short history, duplicate dates, duplicate quarters, restated statements, mismatched currencies/periods, and sector-inapplicable metrics when those cases can affect the changed function.
