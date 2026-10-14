# Data dictionary

The source workbooks ship no dictionary. Every abbreviation below was either
confirmed arithmetically against the data or inferred from context, and each
entry says which.

**Confirmed** means the definition was tested and reproduces the delivered
column. **Inferred** means it is consistent with the data and with industry
convention, but nothing in the files proves it. **Unidentified** means I could
not establish it, and the column is excluded from every calculation rather than
guessed at.

---

## Funnel and user stages

| Term | Meaning | Basis |
|---|---|---|
| `UA` | user acquisition — the paid-media layer | inferred |
| `Install (UA)` | app installs attributed to acquisition activity | inferred |
| `Installs (non PA)` | installs *excluding* paid acquisition, i.e. organic | inferred |
| `NNI` | net new installs | inferred |
| `SU` | signup — account created | inferred |
| `RFT` | **r**ide **f**irst **t**ime: a user taking their first trip. The conversion event the marketing budget is measured against | inferred, and consistent across all three workbooks |
| `EC` | existing customer — a user beyond their first trip | inferred |
| `PA` | paid acquisition | inferred |
| `Eyeball` | a user who viewed the booking screen | inferred |
| `Request` | a booking request submitted | confirmed by position in the funnel |
| `Completed Trip` | a request that became a completed ride | confirmed |

### Funnel ratios — confirmed arithmetically

| Term | Definition | Check |
|---|---|---|
| `RE` | Request ÷ Eyeball | **confirmed** — reproduces the delivered column to 3 dp on every day |
| `CR` | Trip ÷ Request | **confirmed** — reproduces the delivered column to 3 dp on every day |
| `%Install2SU` | Signup ÷ Install | inferred |
| `%SU2RFT` | first-trip users ÷ Signup | inferred |
| `%NNI2RFT` | first-trip users ÷ net new installs | inferred |

---

## Money

| Term | Meaning | Basis |
|---|---|---|
| `GMV` | gross merchandise value — the total transaction value | confirmed by use |
| `GFV` | gross **food** value: the merchandise component, excluding the delivery fee | **inferred, and supported** — GFV averages 86.4% of GMV, and the 13.6% gap behaves like a delivery charge |
| `AOV` | average order value = GMV ÷ orders | confirmed |
| `Total Commission` | what the platform charges merchants and riders | confirmed by use |
| `take rate` | commission ÷ GMV | derived here, not in the source |
| `partner_discount` | discount funded by a partner (a bank, a campaign sponsor) | inferred |
| `merchant_discount_amount_*` | discount funded by the merchant | inferred from the column name |
| `be_discount_amount_*` | **discount funded by BE itself** — the platform's own subsidy | inferred from the column name |
| `net take rate` | (commission − BE-funded discount) ÷ GMV. **Derived here.** The source never subtracts the two, so a brand can show a healthy take rate while costing the platform money | derived |
| `dd` | **unidentified.** Averages 11.0% of GMV, correlates 0.963 with GMV, and is exactly zero in 94 of 679 rows. Tested against delivery fee, delivery discount and demand metrics; none fits. **Excluded from every calculation** | unidentified |

### Accounting qualifiers

These are part of a measure's definition, not decoration, so they are kept in a
`basis` column rather than stripped from the metric name.

| Suffix | Meaning |
|---|---|
| `n/VAT` | net of value-added tax |
| `w/Fee` | includes agency fee |
| `n/Fee` | excludes agency fee |
| `n/CIT` | net of corporate income tax |

A figure `w/Fee` and a figure `n/Fee` are different numbers for the same thing.
Comparing them without noticing is the easiest error in this dataset.

---

## Cost and efficiency

| Term | Definition in the source | Note |
|---|---|---|
| `CAC` | Budget RFT_raw ÷ RFT | **confirmed** — recomputing it reproduces the delivered column to within one cent in 311 of 317 channel-weeks. It assumes 100% of first trips were caused by the spend; see `measurement_design.md` |
| `CPA` | Budget Trip_raw ÷ total bookings | confirmed by the same method |
| `CIR` | cost-to-income ratio: marketing cost ÷ GMV | inferred, consistent with the delivered values |
| `Budget RFT_raw` | media budget attributed to first-trip acquisition | inferred |
| `Budget Trip_raw` | media budget attributed to completed trips | inferred |
| `Digital Cost` | digital media spend | confirmed by use |
| `Marketing Expenses` | total marketing cost, split `Brand` and `Digital` | confirmed by use |

---

## Reporting lags

Three metrics carry a lag in their label. The lag is **part of the metric**, not
a footnote: an install measured at T−2 cannot be divided by a signup measured at
T−1 without shifting one of them first.

| Metric | Lag |
|---|---|
| `Open App User (Firebase)` | T−2 |
| `#Open App (Firebase)` | T−2 |
| `Android` / `IOS` install splits | T−2 |
| `NNI` | T−1 |
| everything else | none |

The parser records the lag in its own column so the decision is visible. Any
week-on-week ratio built across differently-lagged metrics is wrong, and this is
the only thing in the file that warns you.

---

## Segments

| Term | Meaning |
|---|---|
| `beBike`, `beCar`, `beDelivery`, `beFood`, `beClean` | the platform's service lines |
| `M0`, `M1` | cohort months — the acquisition month, and the month after |
| `M1-RR` | M1 retention rate: share of a cohort still active one month later |
| `AllBe` | the company total. **Not a channel** — including it with the detail double-counts |
| `CPC (excl. AFF)` | a grouping of paid channels excluding affiliate. **Not a channel** either |
| Rider personas | Office Worker, University Student, Parent, Housewife, Labour, Shoppertainer, On-Demand, Other. Stacked in the same block as the service lines in the source, and separated by the parser |

---

## Scope

| | |
|---|---|
| `All Việt Nam` | **equals Ha Noi + Ho Chi Minh exactly**, to 100.000%, in all five months. It is the sum of two cities, not a national figure. Reading it as national overstates coverage |
| Cities present | Ha Noi, Ho Chi Minh |
| Channels | 9, of which 7 are real channels, 1 is the company total and 1 is a grouping |
| Brands | 57 restaurant brands |

---

## What "indexed" means in the published files

Every numeric column in `data/published/` has been transformed. See
[`../data/published/README.md`](../data/published/README.md) for the rule
applied to each one. No figure there is a real BE Group number, and none can be
recovered from what is published.
