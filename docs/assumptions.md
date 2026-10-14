# Assumptions

Every input this project used that the data did not supply, what it was set to,
and what happens to the conclusion if it is wrong.

The payback model is the only deliverable here that is a **model** rather than a
**measurement**, and this page exists because a model whose assumptions are
buried is indistinguishable from a guess.

---

## 1 · The three files cover three different periods

This is the binding constraint on the whole project, and no assumption can make
it go away.

| Source | Period |
|---|---|
| Channel performance | Dec 2024 – Dec 2025, weekly |
| Brand economics | Jan – May 2025, monthly |
| Promotion case (beAirport) | Jan 2024, daily, 12 days |
| Retention | Jan – Jun 2025, monthly |

The payback model needs an acquisition cost, a retention rate and a margin.
Each comes from a different file and a different period. **They are combined
anyway, because the question is worth a modelled answer — but the result is a
structure for thinking about payback, not a measured payback.**

If BE ran this internally they would pull all three from the same cohort over
the same window, and the model would become a measurement. That is the single
change that would most improve it.

---

## 2 · The payback model's inputs

Set in `ASSUMPTIONS` at the foot of [`../src/build_marts.py`](../src/build_marts.py),
and written into `mart.channel_payback` as columns so no reader has to go
looking.

| Input | Value | Where it came from | If it is wrong |
|---|---|---|---|
| **Average fare** | 11.0 | `mart.promo_unit_economics`, where AOV sits between 10.8 and 11.1 across all 12 days | Scales every payback period proportionally. The *ranking* of channels is unaffected, because the same fare applies to all of them |
| **Contribution margin rate** | 0.04 | the post-increase beAirport margin, taking the lower end of the observed 2.0–6.2% range | Same: scales all paybacks, preserves the ranking. Deliberately conservative — the pre-increase margin was **negative** |
| **Trips per month** | 4.0 | **a placeholder. Nothing in the data supports it.** | The one input that could change a decision. At 2 trips/month every payback doubles; at 8 it halves |
| **M1 retention** | measured, 0.342 | `stg_retention_month`, RFT segment, mean across six months | Measured rather than assumed, but it is the retention of a *different cohort in a different year* from the channels it is applied to |

### The one that matters

**Trips per month is a placeholder and should be replaced before anyone acts on
the output.** It is the only input that is neither measured nor bounded by
something observed, and the only one that affects the ranking — because if
trip frequency differs by acquisition channel, which is likely, the ranking
changes.

A channel that acquires commuters who ride daily and a channel that acquires
occasional airport users do not pay back at the same speed even at identical
CAC. That is precisely the comparison this model cannot currently make.

---

## 3 · The retention assumption is a simplification

The model applies M1 retention as a flat monthly survival rate. Real retention
curves are convex — the steepest drop is in month one and the curve flattens
after. Applying M1 as a constant therefore **understates** lifetime value and
**overstates** payback periods.

That direction is deliberate. A model that errs toward "this takes longer to pay
back than you think" is the safer error when the output is a budget decision.

The data could support better: the cancellation and promo-usage tables carry
monthly cohorts, and a proper survival curve is available from them. It was not
built because the channel data and the retention data do not share a cohort.

---

## 4 · Channels excluded from the ranking, and why

| Channel | Why excluded |
|---|---|
| `AllBe` | the company total, not a channel |
| `CPC (excl. AFF)` | a grouping of paid channels, not a channel |
| `Organic` | unpaid, so CAC is undefined rather than zero |
| `Others` | **15,393 first-trip users and zero attributed budget.** Its CAC computes to zero, which is an attribution gap, not a performance result. Flagged in the output rather than silently dropped |

---

## 5 · What was decided during parsing

These are judgement calls made in [`../src/parse_source.py`](../src/parse_source.py),
not data.

| Decision | Reasoning |
|---|---|
| **Inline subtotals dropped** — rows ending "Total" inside a data block | Summing the column as delivered double-counts every one of them. 80 rows of 544 |
| **Services split from personas** on whether the label starts with "be" | They are stacked in one block in the source and are not comparable. The rule is simple and the data obeys it, but it *is* a rule I imposed |
| **Reporting lags kept as a column** rather than applied | Shifting the series would be an interpretation. Recording the lag leaves the decision to whoever uses it, visibly |
| **Accounting qualifiers moved to `basis`** rather than stripped | `w/Fee` and `n/Fee` are different numbers for the same measure. Deleting the suffix makes them look identical |
| **`dd` excluded entirely** | Could not be identified. See `data_dictionary.md`. Excluding an unidentified column is safer than guessing at it and quietly including it in a total |

---

## 6 · What would change the conclusions

Honest short list, in order of how much it would move things.

1. **Trip frequency per channel.** Would make the payback ranking a real
   ranking rather than a CAC ranking with a constant applied to it.
2. **An incrementality test on Affiliate.** 66.6% of paid first-trip users at a
   third of the cost of anything else is either the best channel in the market
   or an attribution artefact. Nothing here can tell you which, and the answer
   changes the entire budget allocation. See
   [`measurement_design.md`](measurement_design.md).
3. **Whether `All Việt Nam` was always only two cities.** If BE operates in more
   and this extract is partial, every share in the brand analysis is computed
   on an incomplete base.
4. **More than four days after the commission change.** The margin decline of
   1.40 points per day is real in the observed window. Whether it continued,
   stabilised or reversed is unknown, and four points on a line is not a trend.
