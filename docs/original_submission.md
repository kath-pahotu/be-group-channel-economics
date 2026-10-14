# The original submission

*What was delivered to BE Group, and how this repository relates to it.*

---

The three workbooks in this project were supplied as a business-analysis
exercise, with four questions attached. Three written reports were submitted in
response, in Vietnamese and English.

**Those reports are not in this repository, and will not be.** They quote real
figures from BE Group's operating data and include screenshots of it. They are
kept locally under `private_review/`, which is git-ignored, and are available on
request from the author if a reader has a legitimate reason and BE Group has no
objection.

What *is* published here is the rebuild: the same data, parsed reproducibly,
analysed further, and written out with every figure indexed.

---

## What the three reports covered

### Report 1 — GMV, discount and brand growth

Brand-level performance across the restaurant portfolio: which brands were
growing, how much of that growth was bought with discount, and how dependent
each was on subsidy. Separated scale from subsidy intensity, segmented brands
by GMV quartile, built a weighted forecast and a subsidy-dependence matrix.

Included a data-quality correction: alert logic that was producing false
positives, found and fixed before any of the analysis was interpreted.

### Report 2 — First-trip retention and user flow

M1 retention decomposed by acquisition source, city, service and rider persona.
Diagnosed promotion dependency in the retained cohort, and identified re-entry
and checkout drop-off points in the Bike and Food journeys.

### Report 3 — Marketing channel performance and measurement

Channel-level acquisition efficiency, the divergence between installs and
app-opens, and a measurement framework: channel scorecards, CAC and CIR with
guardrails, and a roadmap toward incrementality testing.

---

## What this repository adds

The reports answered the questions as asked, in Excel. This repository takes
the same source and does four things the original could not.

| | |
|---|---|
| **Reproducible parsing** | the workbooks are reporting outputs - metrics down the rows, dates across the columns, merged headers, inline subtotals. `src/parse_source.py` unpivots all of it so the analysis rebuilds from source with one command instead of being reassembled by hand |
| **Checks that run every build** | the channel split reconciles to the company total, reported CAC is verified against its own formula, and the city total is tested rather than assumed - which is how the "All Việt Nam" finding surfaced |
| **Net take rate** | commission and BE-funded discount sit in different columns in the source and are never subtracted. Doing so shows seven brands carrying 11.2% of GMV at a negative net take |
| **A measurement design** | the brief asked how to estimate incrementality from this data. The honest answer is that you largely cannot, so `docs/measurement_design.md` specifies the test that would, with the sample constraint that decides whether it is even viable |

The reports were the deliverable. This is what the deliverable should have been
built on.
