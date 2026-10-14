# BE Group — marketing channel economics and promotion unit economics

Channel P&L, promotion margin and brand-level take rate for a Vietnamese
mobility and delivery platform, rebuilt from the operating workbooks into a
reproducible pipeline with its own checks.

*Originally a business-analysis exercise answered in Excel. The three reports
that were submitted are described in
[`docs/original_submission.md`](docs/original_submission.md); they are not
published here, because they quote real figures.*

> ### Every number in this repository is indexed. None of them is real.
>
> The source is BE Group's own operating data, provided for a business-analysis
> exercise. Nothing real is published here and nothing real can be recovered
> from what is.
>
> **Levels** — GMV, cost, users, orders, commission — are rescaled so the first
> period of each series equals 100. **Ratios** — CAC, CIR, take rate, margin,
> conversion, retention — are multiplied by one undisclosed constant per metric
> family.
>
> **Hidden** — every currency amount, every count, and every rate as a level:
> GMV, spend, budget, commission, discount, users, installs, orders, merchants,
> CAC, CIR, take rate, margin rate, retention.
>
> **Still real, deliberately** — shares and mixes, ratios between two indexed
> figures, rankings, counts of things rather than of money (54 weeks checked,
> 7 brands negative, 8 of 8 days loss-making), and rates of change in percentage
> points. Without those there is no analysis left to read.
>
> So a reader can learn that one channel delivers two thirds of acquisition at a
> fraction of the cost of another. They cannot learn what either cost. See
> [`src/publish_indexed.py`](src/publish_indexed.py) for the method and
> [`data/published/README.md`](data/published/README.md) for the rule applied to
> each column.

---

## What the data is

| Source | Grain | Span | Rows |
|---|---|---|---|
| Channel performance | channel × week × metric | 54 weeks, Dec 2024 – Dec 2025 | 6,959 |
| Company topline | week × metric | same 54 weeks | 1,996 |
| Brand economics | brand × city × month | 5 months, Jan – May 2025 | 679 |
| Promotion case (beAirport) | day × metric | 12 days, Jan 2024 | 12 |
| M1 retention | segment × month | 6 months, 2025 | 18 |
| Promo per trip | segment × cohort × month | 6 months, 2025 | 464 |
| Cancellations | reason × service × month × user type | — | 907 |

9 acquisition channels · 57 restaurant brands · 3 city scopes.

**The three files cover three different periods.** That is the single most
important constraint on this project, and it is why the payback model in
[`docs/assumptions.md`](docs/assumptions.md) is labelled a model rather than a
measurement.

---

## The work

### 1 · Making the data readable at all

The workbooks are reporting outputs, not datasets: metrics down the rows, dates
across the columns, merged headers, a second grouping key hiding in column B,
blank spacer rows, and section banners inside the data.

[`src/parse_source.py`](src/parse_source.py) unpivots all of it reproducibly.
Three things it has to get right that a naive read misses:

| Trap | What happens if you miss it |
|---|---|
| **Inline subtotals** — "beBike Total" sits in the same column as "beBike" | every aggregate double-counts. 80 rows of 544 |
| **Two dimensions stacked** — service types and rider personas share one block | you average a persona against a product line |
| **Metric labels that differ by row** — `CAC (=Budget RFT_raw / RFT)` on the first row of a block, `CAC` on the next seven | `GROUP BY metric` splits one series into two |
| **Reporting lags in the label** — `(Lag T-2)` on installs, `(lag T-1)` on new installs | any week-on-week ratio across differently-lagged metrics is wrong |

The lag is kept as a column rather than stripped, because it is part of the
metric's definition. So are the accounting qualifiers: `n/VAT`, `w/Fee`,
`n/CIT` move into a `basis` column instead of being deleted.

### 2 · Four decision tables

| Mart | Question it answers |
|---|---|
| `mart.channel_week_pnl` | what does each channel cost, and what does it return? |
| `mart.brand_month_economics` | what does BE keep per brand, after funding its own share of the discount? |
| `mart.promo_unit_economics` | what does one airport trip earn, and how fast is promotion spending the margin? |
| `mart.channel_payback` | how long before an acquired user repays what they cost? |

### 3 · Four checks, run before anything was quoted

| Check | Result |
|---|---|
| Does the channel split sum back to the company total? | **pass** — 54 of 54 weeks, worst delta **0.00004%** |
| Does reported CAC match its stated formula? | **pass** — 311 of 317 channel-weeks agree to within one cent |
| Do the two cities sum to "All Việt Nam"? | **exactly 100.000%** — and that is a finding, not a pass. See below |
| Are the measures complete? | 3 of 679 brand rows carry no commission or discount |

---

## What it found

### The label says national; the data is two cities

Ha Noi plus Ho Chi Minh equals "All Việt Nam" to **100.000%** in every month.
Not approximately — exactly. So "All Việt Nam" is not a national total that
happens to be dominated by two cities; it is the sum of exactly those two and
nothing else.

Any share, growth rate or ranking computed from it describes two cities. Read as
national, it would overstate coverage in every slide it appears in.

### The commission increase bought headroom; promotion spent it in four days

The beAirport route, before and after the commission rate was raised:

| | Commission | Promotion | Contribution margin | Loss-making days |
|---|---|---|---|---|
| **Before** (8 days) | 3.93% | 6.69% | **−3.06%** | **8 of 8** |
| **After** (4 days) | 14.13% | 11.00% | **+3.95%** | 0 of 4 |

Every single day before the change lost money on a contribution basis. The
increase fixed that. But across the four days after it:

- contribution margin **fell 1.40 points per day** — 6.2% → 2.0%
- promotion spend **rose 1.17 points per day** — 9.1% → 12.6%

Roughly 3.4 of the 5 points of headroom the commission increase created were
consumed within four days. On that trajectory the route returns to loss-making
in under two more days. **That is the finding, and it is about pace rather than
level** — which is why the indexing does not touch it.

### One channel is 67% of acquisition at a third of the cost

| Channel | Share of first-trip users | Share of budget | CAC (indexed) |
|---|---|---|---|
| **Affiliate** | **66.6%** | 41.8% | **338** |
| Apple Search Ads | 11.4% | 18.2% | 860 |
| Facebook Ads | 11.1% | 21.9% | 1,058 |
| Google Ads | 9.2% | 16.9% | 984 |
| Tiktok | 0.8% | 1.3% | 807 |
| Others | 0.7% | **0.0%** | — |

Affiliate delivers two thirds of paid acquisition at roughly a third of the cost
per user of the next channel. Read at face value, the budget decision is
obvious.

**It should not be read at face value.** A channel this much cheaper than every
alternative is the classic signature of attribution capture — demand that would
have converted anyway, arriving through a trackable link. Nothing in this data
can separate the two, which is the whole subject of
[`docs/measurement_design.md`](docs/measurement_design.md).

Separately: **"Others" has 15,393 first-trip users and zero attributed budget.**
Its CAC is therefore zero, which is not a performance result, it is a gap in
attribution. It is excluded from the payback ranking and flagged rather than
quietly dropped.

### Seven brands have a negative net take rate

Take rate looks healthy across the portfolio. Net of the discount BE itself
funds, **7 of 55 brands are negative, carrying 11.2% of GMV.** The delivered
table cannot show this, because commission and BE-funded discount sit in
different columns and are never subtracted from each other.

---

## What this data cannot answer

**Channel incrementality.** Spend and demand move together, and the budget is
set *in response to* last week's performance, so cause and effect are entangled
by construction. A regression of first trips on channel spend would return a
confident coefficient and a meaningless number.

The deliverable instead is a design that would measure it — geo holdout, with
the minimum detectable effect this data implies.
[`docs/measurement_design.md`](docs/measurement_design.md).

**A causal read of the commission change.** Eight days before, four days after,
no control route. The margin collapse above is a description of what happened,
not an estimate of what the change caused.

**Anything national.** See above.

---

## Running it

```bash
python src/parse_source.py     --project-root .   # workbooks  -> tidy tables
python src/build_marts.py      --project-root .   # tidy       -> marts + qa
python src/publish_indexed.py  --project-root .   # marts      -> indexed output
```

Or all three:

```bash
python src/run_all.py --project-root .
```

`data/source/` and `data/private/` are git-ignored. A clone of this repository
contains the pipeline and the indexed outputs, and will not run end to end
without the original workbooks — which is the intended behaviour.

---

## Layout

```
be_group_commercial/
├── src/
│   ├── parse_source.py      # wide, merged-cell Excel -> tidy long tables
│   ├── build_marts.py       # four decision tables + four checks
│   ├── publish_indexed.py   # the indexing layer, and why each rule applies
│   └── run_all.py
├── data/
│   ├── source/              # the workbooks as delivered   (git-ignored)
│   ├── private/             # tidy tables, real values     (git-ignored)
│   └── published/           # indexed outputs              (committed)
├── docs/
│   ├── data_dictionary.md    # every abbreviation, and which ones I inferred
│   ├── assumptions.md        # every input the payback model could not measure
│   ├── measurement_design.md # how BE should measure channel incrementality
│   └── original_submission.md# what was delivered to BE, and why it is not here
├── private_review/           # the original reports, real figures  (git-ignored)
├── notebooks/
│   └── 00_walkthrough.ipynb # the whole project, top to bottom
└── artifacts/
    └── be_commercial.duckdb # rebuilt by the pipeline       (git-ignored)
```
