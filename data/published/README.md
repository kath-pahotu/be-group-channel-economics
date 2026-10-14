# Published data - indexed, not real

Every numeric column in this folder has been transformed. No figure here is a
real BE Group number, and none can be recovered from what is published.

- Columns ending `_index` on a LEVEL (GMV, cost, users, orders, commission)
  are rescaled so the first period of the series equals 100.
- Columns ending `_index` on a RATIO (CAC, CIR, take rate, margin rate,
  conversion, retention) are multiplied by one undisclosed constant per metric
  family.

## Where the line is, precisely

Both transforms are designed so the analysis still says something, which means
some quantities are unchanged by them. Being exact about which:

**Hidden — not recoverable from anything published**

- every currency amount: GMV, spend, budget, commission, discount, margin per trip
- every count: users, installs, signups, orders, trips, merchants
- every rate expressed as a level: CAC, CIR, take rate, margin rate, retention

**Real — and deliberately so, because without them there is no analysis**

- shares and mixes (a channel's % of acquisition, a party's % of discount funding)
- ratios between two indexed figures (channel A's CAC relative to channel B's)
- rankings and orderings
- counts of things, not of money: 54 weeks checked, 7 brands negative, 8 of 8 days
- rates of change in percentage points, and the day a series crosses zero

A reader can therefore learn that one channel delivers two thirds of acquisition
at a fraction of the cost of another. They cannot learn what either cost.

The real values stay in `data/private/`, which is git-ignored.
