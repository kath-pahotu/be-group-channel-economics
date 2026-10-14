# Measuring channel incrementality

*What this data cannot tell you about marketing spend, why, and the test that
would.*

---

## 1 · The question, and the honest answer

The brief asks how to estimate the incremental impact of increasing spend on one
channel, from this data alone.

**Largely, you cannot.** This document explains why in enough detail to be
checkable, and then specifies the experiment that would.

Refusing the question is not the deliverable. The design is.

---

## 2 · The assumption nobody states

The channel sheet computes:

```
CAC = Budget RFT_raw / RFT
```

That formula divides the budget by every first trip the channel recorded. It
therefore assumes **100% of those first trips were caused by the spend.**

The assumption is invisible because it lives inside the metric's definition
rather than in a note beside it. And it is almost certainly wrong — for some
channels by a little, for at least one by a lot.

### Why one channel in particular

| Channel | Share of first-trip users | Share of budget |
|---|---|---|
| **Affiliate** | **66.6%** | 41.8% |
| Apple Search Ads | 11.4% | 18.2% |
| Facebook Ads | 11.1% | 21.9% |
| Google Ads | 9.2% | 16.9% |

Affiliate delivers two thirds of paid acquisition at roughly a third of the
cost per user of the next-cheapest channel.

There are two explanations and the data cannot distinguish them:

1. Affiliate is genuinely the most efficient channel BE has.
2. Affiliate is capturing users who were going to install anyway, through a
   trackable link that claims the credit.

**A gap that large is more commonly explanation 2 than explanation 1.** That is
not a claim about BE's affiliate programme; it is what the cost gap means in
general, and it is exactly the case where a measured answer is worth paying for.

---

## 3 · Why regression will not rescue it

The obvious move — regress first trips on channel spend across 54 weeks — fails
for two reasons. The second is the one most analyses miss.

**Confounding.** Spend and demand move together. Budgets rise in high-demand
weeks, so weeks with heavy spend also carry more organic demand. The model
attributes the season's effect to the budget.

**Reverse causality.** The budget is *set in response to* performance. A channel
that performed well last week gets more money this week, so good performance
causes high spend as well as the other way round. In this dataset the budget
rows are weekly decisions made by a team looking at precisely these numbers.
Cause and effect are entangled by construction, not by accident.

A regression run anyway would produce a confident coefficient, a tight interval
and a plausible chart. The number would be meaningless. Producing it is the
mistake; declining to, and explaining why, is the work.

### What the data *can* support

| Can | Cannot |
|---|---|
| Rank channels on reported cost per user | Say what any channel's users cost incrementally |
| Show spend and outcomes moving together | Attribute the movement to the spend |
| Flag which channel's reported efficiency is least credible | Quantify how much of it is capture |
| Size the test that would answer it | Answer it |

---

## 4 · The design

### Geo holdout — the recommended test

BE's data is already split Ha Noi / Ho Chi Minh, and a mobility marketplace is
geographically separable: a rider in Ha Noi does not substitute into a Ho Chi
Minh ride. That makes geography the natural randomisation unit.

| | |
|---|---|
| **Unit of randomisation** | city, or district within city — **not the user** |
| **Treatment** | Affiliate spend switched off, or cut by a fixed share |
| **Control** | matched geographies with spend unchanged |
| **Primary metric** | first-trip users, total across all channels |
| **Why "all channels"** | the question is whether total acquisition falls, not whether Affiliate's own number falls. It will |
| **Secondary** | completed trips, GMV, CAC across the whole portfolio |
| **Guardrails** | completion rate, cancellation rate, M1 retention of the cohort acquired during the test |

### The one thing that invalidates it

**Randomisation unit must match the analysis unit.** If spend is switched at
city level and the result is analysed per user, the standard errors are wrong
and the test will look significant more often than it should.

This is not hypothetical — it is the failure I found in a previous experiment
analysis, where 26,426 users appeared in both arms of what was reported as a
clean split. The uplift survived the correction at a third of its headline
size. Audit the assignment before analysing the outcome, every time.

### Alternatives, and when each is better

| Design | How it works | Use when |
|---|---|---|
| **Ghost ads / PSA** | the control group is served a placebo, so you observe who *would have been* reached | the ad platform supports it — strongest design available |
| **Switchback** | alternate on and off week by week within the same city | effects are short-lived and geography cannot be split |
| **Budget-split** | matched geographies at different spend levels | you want a response curve, not a single number |

---

## 5 · Sizing the test

### What the data implies

Weekly first-trip users vary considerably week to week — holidays, weather and
campaign timing all move it, and Tết in particular cuts the series sharply.
Across the 54 observed weeks the company-level series has a **coefficient of
variation of 0.221**: the week-to-week standard deviation is 22% of the mean.

That number is the floor on what any test can detect. An effect smaller than
the noise the series already carries cannot be separated from an ordinary week,
however the test is designed.

```python
# Minimum detectable effect, two-sided, alpha = 0.05, power = 0.80
#   mde = (z_alpha/2 + z_beta) * sd * sqrt(2 / n_per_arm) / mean
# where sd and mean come from mart.channel_week_pnl, and n_per_arm is
# geographies x weeks, NOT users.
```

The honest constraint: **BE has two city scopes in this data.** Two geographies
cannot support a geo holdout — the test needs enough units to randomise over,
which in practice means districts or service zones rather than cities. If the
finest geography available is the city, geo holdout is not viable and the
switchback design in the table above is the fallback.

That constraint should be established *before* the test is proposed, not
discovered during it.

### What to state before launch, every time

1. **The unit of randomisation**, and the check that confirms no unit appears in
   both arms.
2. **The minimum detectable effect** at the available sample. A test that cannot
   detect the effect size the decision needs should not be run.
3. **The stopping rule.** Decided in advance, or the test is a search for a
   significant week.
4. **The guardrails** and what level triggers an early stop.

---

## 6 · What this changes on Monday

The point of the design is not the experiment. It is what you say about the
numbers while you wait for one.

> "I can rank these channels on reported CAC, and I will — it is in
> `mart.channel_week_pnl`. But reported CAC assumes every first trip was caused
> by the spend, and for Affiliate specifically that assumption is carrying the
> entire conclusion. Here is the test that would replace the assumption with a
> measurement, what it needs to be valid, and the sample constraint that decides
> whether we can run it at all."

### The budget-cut question, answered with this in mind

Asked to cut 20% of channel budget, reported efficiency ranks the channels one
way. Incremental efficiency can rank them in a completely different order,
because the channel that looks cheapest is often the one capturing demand that
already existed.

So the recommendation has two parts, and the second is the real one:

1. **Cut from the channels with the weakest reported efficiency** — Facebook
   Ads and Google Ads together carry **38.8% of budget for 20.4% of first-trip
   users.**
2. **Do not increase Affiliate with what is saved.** Hold it flat and use the
   cut as the natural experiment: if total acquisition falls by less than the
   cut channels' attributed share, that is the first evidence anyone has had
   about incrementality here — and it costs nothing extra to collect.

The second point is how you run a measurement inside a budget decision that was
going to happen anyway.
