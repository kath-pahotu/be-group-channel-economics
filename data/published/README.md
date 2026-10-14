# Published data - indexed, not real

Every numeric column in this folder has been transformed. No figure here is a
real BE Group number, and none can be recovered from what is published.

- Columns ending `_index` on a LEVEL (GMV, cost, users, orders, commission)
  are rescaled so the first period of the series equals 100.
- Columns ending `_index` on a RATIO (CAC, CIR, take rate, margin rate,
  conversion, retention) are multiplied by one undisclosed constant per metric
  family.

Every conclusion in the analysis survives both transforms exactly: growth
rates, shares, rankings, and the day a margin crosses zero are all unchanged.
Only the levels are hidden.

The real values stay in `data/private/`, which is git-ignored.
