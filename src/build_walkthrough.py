"""Generate notebooks/00_walkthrough.ipynb.

The notebook is generated rather than hand-edited so it cannot drift from the
pipeline: change a mart, regenerate, re-execute, and the walkthrough is correct
again.

It reads data/published/ - the INDEXED outputs - never the warehouse. That is
deliberate. The executed notebook is committed, so whatever it prints is
published, and nothing real should be.

Run:
    python src/build_walkthrough.py --project-root .
    jupyter nbconvert --execute --to notebook --inplace notebooks/00_walkthrough.ipynb
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def md(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": text.splitlines(keepends=True)}


def code(text: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": text.splitlines(keepends=True),
    }


def section(number: str, title: str, what: str, built_by: str, written_to: str) -> dict:
    return md(
        f"---\n\n## {number} - {title}\n\n{what}\n\n"
        f"| | |\n|---|---|\n"
        f"| **Built by** | {built_by} |\n"
        f"| **Written to** | {written_to} |\n"
    )


def conclusion(text: str) -> dict:
    return md(f"> **Conclusion.** {text}\n")


SETUP = '''import json
import sys
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
PUBLISHED = ROOT / "data" / "published"
sys.path.insert(0, str(ROOT / "src"))

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 60)
pd.set_option("display.max_colwidth", 46)
# Previews show at least 10 rows throughout. Three rows is not enough to see a
# pattern, a null cluster, or a grain finer than you assumed.
pd.set_option("display.max_rows", 40)
pd.set_option("display.min_rows", 20)

db = duckdb.connect(":memory:")
for parquet in sorted(PUBLISHED.glob("*.parquet")):
    db.execute(
        f"CREATE OR REPLACE VIEW {parquet.stem} AS "
        f"SELECT * FROM read_parquet('{parquet.as_posix()}')"
    )


def q(sql):
    """Run a query and return a DataFrame."""
    return db.execute(sql).fetchdf()


def show_py(filename, func, lines=None):
    """Print the production function that builds something, read at run time.

    Nothing here is a copy of the code. It is the code, read out of src/ as the
    cell runs, so it cannot fall out of step with what actually executed.
    """
    path = ROOT / "src" / filename
    rows = path.read_text(encoding="utf-8").splitlines()
    start = next(
        (i for i, row in enumerate(rows)
         if row.startswith((f"def {func}(", f"{func} = ", f"{func} = {{", f"{func}: "))),
        None,
    )
    if start is None:
        print(f"{func} not found in {filename}")
        return
    end = start + 1
    while end < len(rows) and not rows[end].startswith(("def ", "class ", "@")):
        end += 1
    body = rows[start:end]
    if lines:
        body = body[:lines]
    print(f"# {filename}, line {start + 1}\\n")
    print("\\n".join(body).rstrip())


print("views:", ", ".join(sorted(p.stem for p in PUBLISHED.glob("*.parquet"))))
'''


def build(project_root: Path) -> Path:
    cells: list[dict] = []

    # ================================================================ OPENING
    cells += [
        md(
            "# BE Group - marketing channel economics\n"
            "\n"
            "### Read this top to bottom and you have the whole project\n"
            "\n"
            "Every table, every check and every finding is in here, with the code that\n"
            "produced it. Nothing requires opening another file.\n"
            "\n"
            "**What this is.** Three operating workbooks from a Vietnamese mobility and\n"
            "delivery platform, handed over as a business-analysis exercise. They were\n"
            "originally answered in Excel. This is the rebuild: parsed reproducibly,\n"
            "analysed further, and checked before anything was quoted.\n"
        ),
        md(
            "> ## Every number below is indexed. None of them is real.\n"
            ">\n"
            "> The source is BE Group's own operating data. Nothing real is published in\n"
            "> this repository and nothing real can be recovered from what is.\n"
            ">\n"
            "> - **Levels** - GMV, cost, users, orders, commission - are rescaled so the\n"
            ">   first period of each series equals 100.\n"
            "> - **Ratios** - CAC, CIR, take rate, margin, conversion, retention - are\n"
            ">   multiplied by one undisclosed constant per metric family.\n"
            ">\n"
            "> **Hidden:** every currency amount, every count, and every rate as a level -\n"
            "> GMV, spend, budget, commission, users, installs, CAC, CIR, take rate,\n"
            "> margin rate, retention.\n"
            ">\n"
            "> **Still real, deliberately:** shares and mixes, ratios between two indexed\n"
            "> figures, rankings, counts of things rather than of money (54 weeks checked,\n"
            "> 7 brands negative, 8 of 8 days), and rates of change in percentage points.\n"
            "> Without those there is no analysis left to read.\n"
            ">\n"
            "> So you can learn here that one channel delivers two thirds of acquisition at a\n"
            "> fraction of the cost of another. You cannot learn what either cost.\n"
            "> Part 11 shows the mechanism and proves the findings survive it.\n"
        ),
        md(
            "### The route through\n"
            "\n"
            "| Part | | \n"
            "|---|---|\n"
            "| 1 | What the source actually looks like, and why nothing can read it |\n"
            "| 2 | The parser, and the four traps in it |\n"
            "| 3 | What came out |\n"
            "| 4 | Channel P&L |\n"
            "| 5 | Check: does the channel split sum to the company total? |\n"
            "| 6 | Check: does reported CAC match its own formula? |\n"
            "| 7 | Check: do the two cities sum to \"All Viet Nam\"? **This one found something** |\n"
            "| 8 | Brand economics, and the take rate the source cannot show |\n"
            "| 9 | The promotion case: what a commission increase bought, and how fast it went |\n"
            "| 10 | Payback, and every assumption behind it |\n"
            "| 11 | The indexing layer |\n"
            "| 12 | What this data cannot answer |\n"
        ),
        code(SETUP),
    ]

    # ================================================================= PART 1
    cells += [
        section(
            "Part 1", "What the source actually looks like",
            "**The problem.** These are not datasets. They are reporting outputs - the\n"
            "weekly deck an operating team actually keeps - and nothing downstream can\n"
            "read them.",
            "nothing yet - this is the input",
            "`data/source/*.xlsx` (git-ignored, never published)",
        ),
        md(
            "The channel workbook is **186 rows by 56 columns**, and laid out like this:\n"
            "\n"
            "```\n"
            "       col 0                       col 1        col 2        col 3    ...\n"
            "row 0  weekly                                   Mon          Mon\n"
            "row 1                                           2024-12-23   2024-12-30\n"
            "row 2  TOP LINES                      <- a banner, not data\n"
            "row 3  Open App User (Lag T-2)                   2060798      2179423\n"
            "row 4  Installs (non PA)                          1413086      1079737\n"
            "...\n"
            "row 40                                 <- a blank spacer row\n"
            "row 41 BREAK BY CHANNELS               <- another banner\n"
            "row 42 Install (UA)                AllBe         ...\n"
            "row 43 Install (UA)                Affiliate     ...   <- same metric,\n"
            "row 44 Install (UA)                Google Ads    ...      second key in col 1\n"
            "...\n"
            "row 141 CAC (=Budget RFT_raw / RFT)  AllBe        ...   <- formula in the label\n"
            "row 142 CAC                          Affiliate    ...   <- bare name below it\n"
            "```\n"
            "\n"
            "Six separate problems in one sheet:\n"
            "\n"
            "| | |\n"
            "|---|---|\n"
            "| Metrics run **down** the rows, dates run **across** the columns | the opposite of what any join needs |\n"
            "| A second grouping key hides in **column B** | the channel, present only below row 41 |\n"
            "| **Section banners** sit inside the data | `TOP LINES`, `BREAK BY CHANNELS` |\n"
            "| **Blank spacer rows** separate blocks | row 40, row 50, row 59... |\n"
            "| The **first row of each block** carries the formula in its label | `CAC (=Budget RFT_raw / RFT)` vs `CAC` |\n"
            "| **Reporting lags** are written into the metric name | `(Lag T-2)`, `(lag T-1)` |\n"
        ),
        conclusion(
            "This is what a real handover looks like. A public dataset arrives tidy; an "
            "operating team's workbook never does. Turning it into something that can be "
            "joined is the least glamorous part of the project and the part everything "
            "else depends on."
        ),
    ]

    # ================================================================= PART 2
    cells += [
        section(
            "Part 2", "The parser, and the four traps in it",
            "**What it does.** Reads the workbooks exactly as delivered and emits long-format\n"
            "tables with explicit keys. Four things it has to get right that a naive read\n"
            "misses - each one silently corrupts a downstream number.",
            "`src/parse_source.py`",
            "`data/private/*.parquet` (git-ignored - these hold real values)",
        ),
        md(
            "| # | Trap | What happens if you miss it |\n"
            "|---|---|---|\n"
            "| 1 | **Inline subtotals** - `beBike Total` sits in the same column as `beBike` | every aggregate double-counts. **80 rows of 544** |\n"
            "| 2 | **Two dimensions stacked** - service lines and rider personas share one block | you average a persona against a product line |\n"
            "| 3 | **Metric labels that differ by row** - the formula on row 1 of each block, the bare name on rows 2-8 | `GROUP BY metric` splits one series into two |\n"
            "| 4 | **Reporting lags in the label** - `(Lag T-2)` on installs, `(lag T-1)` on new installs | any week-on-week ratio across differently-lagged metrics is wrong |\n"
        ),
        md("### Trap 1 and 2, handled - this is the production code, read at run time\n"),
        code('show_py("parse_source.py", "parse_promo_usage", lines=46)'),
        md(
            "### Trap 3 and 4\n"
            "\n"
            "The lag is kept as a **column** rather than stripped, because it is part of the\n"
            "metric's definition. So are the accounting qualifiers - `n/VAT`, `w/Fee`,\n"
            "`n/CIT` - which move to a `basis` column instead of being deleted.\n"
            "\n"
            "A figure `w/Fee` and a figure `n/Fee` are different numbers for the same thing.\n"
            "Delete the suffix and they look identical.\n"
        ),
        code('show_py("parse_source.py", "split_basis")'),
        conclusion(
            "None of these four is visible unless you look. All four change a number. "
            "That is the argument for parsing a workbook in code rather than by hand: the "
            "decisions get written down, and they get made the same way every time."
        ),
    ]

    # ================================================================= PART 3
    cells += [
        section(
            "Part 3", "What came out",
            "**Eight tidy tables.** One row per observation, explicit keys, nothing merged.",
            "`src/parse_source.py`",
            "`data/private/` then, indexed, `data/published/`",
        ),
        code(
            'print("Published tables (the indexed versions this notebook reads):\\n")\n'
            "for parquet in sorted(PUBLISHED.glob(\"*.parquet\")):\n"
            "    frame = pd.read_parquet(parquet)\n"
            '    print(f"  {parquet.stem:<34} {len(frame):>6,} rows   {frame.shape[1]:>2} cols")'
        ),
        md("### What one of them looks like\n"),
        code('q("SELECT * FROM mart_channel_week_pnl ORDER BY channel, week_start LIMIT 12")'),
        conclusion(
            "Every metric that was a block of rows is now a column on a record. Cost sits "
            "next to what the cost bought, which is the whole point of a channel P&L and "
            "is impossible in the source layout."
        ),
    ]

    # ================================================================= PART 4
    cells += [
        section(
            "Part 4", "Channel P&L",
            "**The question.** What does each acquisition channel cost, and what does it return?\n"
            "\n"
            "Nine channels appear in the source, but only seven are channels. `AllBe` is the\n"
            "company total and `CPC (excl. AFF)` is a grouping of the paid ones. Including\n"
            "either with the detail double-counts, so each row carries a `channel_role`.",
            "`src/build_marts.py` - `build_channel_pnl()`",
            "`mart.channel_week_pnl` - 486 rows",
        ),
        code('show_py("build_marts.py", "build_channel_pnl", lines=30)'),
        md("### Each channel over the whole 54 weeks\n"),
        code(
            'q("""\n'
            "    SELECT channel, channel_role,\n"
            "           COUNT(*)                                   AS weeks,\n"
            "           ROUND(SUM(first_trip_users_index))         AS first_trip_users_idx,\n"
            "           ROUND(SUM(budget_first_trip_index))        AS budget_idx,\n"
            "           ROUND(AVG(cac_reported_index), 1)          AS cac_idx,\n"
            "           ROUND(AVG(install_to_signup_index), 1)     AS install_to_signup_idx,\n"
            "           ROUND(AVG(signup_to_first_trip_index), 1)  AS signup_to_rft_idx\n"
            "    FROM mart_channel_week_pnl\n"
            "    GROUP BY channel, channel_role\n"
            "    ORDER BY first_trip_users_idx DESC\n"
            '""")'
        ),
        md(
            "### Share of acquisition against share of budget\n"
            "\n"
            "Shares are ratios, so the indexing does not touch them. These are the real\n"
            "percentages.\n"
        ),
        code(
            'q("""\n'
            "    WITH paid AS (\n"
            "        SELECT channel,\n"
            "               SUM(first_trip_users_index)  AS rft,\n"
            "               SUM(budget_first_trip_index) AS budget\n"
            "        FROM mart_channel_week_pnl\n"
            "        WHERE channel_role = 'paid channel'\n"
            "        GROUP BY channel\n"
            "    )\n"
            "    SELECT channel,\n"
            "           ROUND(100.0 * rft    / SUM(rft)    OVER (), 1) AS pct_of_first_trips,\n"
            "           ROUND(100.0 * budget / SUM(budget) OVER (), 1) AS pct_of_budget,\n"
            "           ROUND(100.0 * rft / SUM(rft) OVER ()\n"
            "               - 100.0 * budget / SUM(budget) OVER (), 1) AS efficiency_gap_pts\n"
            "    FROM paid ORDER BY pct_of_first_trips DESC\n"
            '""")'
        ),
        conclusion(
            "Affiliate delivers 66.6% of paid first-trip users on 41.8% of the budget - 25 "
            "points of positive gap. Facebook Ads and Google Ads together are 20.4% of "
            "first trips on 38.8% of budget. Read at face value the budget decision looks "
            "obvious. Part 12 is about why it should not be read at face value."
        ),
    ]

    # ================================================================= PART 5
    cells += [
        section(
            "Part 5", "Check: does the channel split sum to the company total?",
            "**Why it matters.** Every share in Part 4 assumes the per-channel rows add up to\n"
            "the company row. If they do not, every percentage above is computed on a base\n"
            "that does not exist.\n"
            "\n"
            "This is the first thing to test on any table that carries both a total and its\n"
            "components, and the source does not test it.",
            "`src/build_marts.py` - `build_qa()`",
            "`qa.channel_reconciliation` - one row per week",
        ),
        code(
            'q("""\n'
            "    SELECT week_start,\n"
            "           ROUND(total_rft_index, 2)   AS company_total_idx,\n"
            "           ROUND(detail_rft_index, 2)  AS sum_of_channels_idx,\n"
            "           ROUND(rft_delta_pct * 100, 6) AS delta_pct,\n"
            "           ROUND(gmv_delta_pct * 100, 6) AS gmv_delta_pct\n"
            "    FROM qa_channel_reconciliation\n"
            "    ORDER BY ABS(rft_delta_pct) DESC LIMIT 12\n"
            '""")'
        ),
        code(
            'q("""\n'
            "    SELECT COUNT(*)                                        AS weeks_checked,\n"
            "           ROUND(MAX(ABS(rft_delta_pct)) * 100, 6)         AS worst_delta_pct,\n"
            "           COUNT(*) FILTER (WHERE ABS(rft_delta_pct) < 0.0001) AS within_0_01_pct,\n"
            "           ROUND(MAX(ABS(gmv_delta_pct)) * 100, 6)         AS worst_gmv_delta_pct\n"
            "    FROM qa_channel_reconciliation\n"
            '""")'
        ),
        conclusion(
            "**Pass.** 54 of 54 weeks, worst delta 0.00004% - a rounding difference of one "
            "or two users on a base of tens of thousands. The shares in Part 4 stand."
        ),
    ]

    # ================================================================= PART 6
    cells += [
        section(
            "Part 6", "Check: does reported CAC match its own formula?",
            "**Why it matters.** The sheet states `CAC = Budget RFT_raw / RFT` in the label of\n"
            "the first row of its block. A stated formula is a claim, and a claim can be\n"
            "tested: recompute it from the components and compare.\n"
            "\n"
            "If they disagree, either the formula is not what the column does, or one of the\n"
            "components is not what its name says.",
            "`src/build_marts.py` - `build_qa()`",
            "`qa.metric_definition_check`",
        ),
        code(
            'q("""\n'
            "    SELECT channel, week_start,\n"
            "           ROUND(cac_reported_index, 2)   AS reported_idx,\n"
            "           ROUND(cac_recomputed_index, 2) AS recomputed_idx,\n"
            "           ROUND(cac_recomputed_index - cac_reported_index, 3) AS delta_idx\n"
            "    FROM mart_channel_week_pnl\n"
            "    WHERE channel_role = 'paid channel'\n"
            "      AND cac_reported_index IS NOT NULL\n"
            "      AND cac_reported_index > 0\n"
            "    ORDER BY ABS(cac_recomputed_index - cac_reported_index) DESC\n"
            "    LIMIT 12\n"
            '""")'
        ),
        conclusion(
            "**Pass.** 311 of 317 channel-weeks agree to within one cent on the real figures. "
            "The formula is what the column does. That matters for Part 12, because it means "
            "the assumption buried in the metric - that 100% of first trips were caused by "
            "the spend - is genuinely the assumption in force."
        ),
    ]

    # ================================================================= PART 7
    cells += [
        section(
            "Part 7", "Check: do the two cities sum to \"All Viet Nam\"?",
            "**Why it matters.** The brand table carries three city scopes: Ha Noi, Ho Chi Minh,\n"
            "and `All Viet Nam`. The natural reading is that the third is a national figure in\n"
            "which the two named cities are the largest part.\n"
            "\n"
            "That reading is testable, and testing it is where this project found something.",
            "`src/build_marts.py` - `build_qa()`",
            "`qa.city_reconciliation`",
        ),
        code(
            'q("""\n'
            "    SELECT month_start,\n"
            "           ROUND(national_gmv_index, 3)         AS all_vietnam_idx,\n"
            "           ROUND(city_gmv_index, 3)             AS hanoi_plus_hcmc_idx,\n"
            "           ROUND(city_share_of_national * 100, 4) AS cities_as_pct_of_national\n"
            "    FROM qa_city_reconciliation ORDER BY month_start\n"
            '""")'
        ),
        md(
            "### 100.0000%. Every month. Exactly.\n"
            "\n"
            "Not 97%, not 99.4% - **exactly 100%**, in all five months, on GMV and on\n"
            "commission. There is no residual, which means there is no third city.\n"
            "\n"
            "`All Viet Nam` is not a national total dominated by two cities. It is the sum of\n"
            "exactly those two and nothing else.\n"
        ),
        conclusion(
            "**The label overstates the coverage.** Any share, growth rate or ranking taken "
            "from `All Viet Nam` describes two cities. Presented as national - which the "
            "label invites - it would be wrong in every slide it reached. A check that "
            "passes tells you a number is safe; this one failed usefully, and it only "
            "surfaced because the obvious assumption was tested rather than accepted."
        ),
    ]

    # ================================================================= PART 8
    cells += [
        section(
            "Part 8", "Brand economics, and the take rate the source cannot show",
            "**The question.** What does the platform actually keep per brand?\n"
            "\n"
            "The source gives commission and discount, with discount split by who funded it:\n"
            "the partner, the merchant, or BE itself. It never subtracts BE's own share from\n"
            "the commission, because the two sit in different columns.\n"
            "\n"
            "`net_take_rate = (commission - BE-funded discount) / GMV` is derived here, and it\n"
            "changes the answer.",
            "`src/build_marts.py` - `build_brand_economics()`",
            "`mart.brand_month_economics` - 679 rows",
        ),
        md("### Who funds the discount\n"),
        code(
            'q("""\n'
            "    SELECT month_start,\n"
            "           ROUND(SUM(discount_funded_by_be_index))       AS funded_by_be_idx,\n"
            "           ROUND(SUM(discount_funded_by_merchant_index)) AS funded_by_merchant_idx,\n"
            "           ROUND(SUM(discount_funded_by_partner_index))  AS funded_by_partner_idx,\n"
            "           ROUND(100.0 * SUM(discount_funded_by_be_index)\n"
            "               / NULLIF(SUM(discount_total_index), 0), 1) AS be_share_of_discount_pct\n"
            "    FROM mart_brand_month_economics WHERE city = 'All Việt Nam'\n"
            "    GROUP BY month_start ORDER BY month_start\n"
            '""")'
        ),
        md("### Take rate, against take rate net of BE's own subsidy\n"),
        code(
            'q("""\n'
            "    SELECT brand_name,\n"
            "           ROUND(gmv_index, 1)            AS gmv_idx,\n"
            "           ROUND(take_rate_index, 2)      AS take_rate_idx,\n"
            "           ROUND(be_subsidy_rate_index, 2) AS be_subsidy_idx,\n"
            "           ROUND(net_take_rate_index, 2)  AS net_take_idx\n"
            "    FROM mart_brand_month_economics\n"
            "    WHERE city = 'All Việt Nam'\n"
            "      AND month_start = (SELECT MAX(month_start) FROM mart_brand_month_economics)\n"
            "    ORDER BY net_take_rate_index LIMIT 12\n"
            '""")'
        ),
        code(
            'q("""\n'
            "    SELECT COUNT(*)                                            AS brands,\n"
            "           COUNT(*) FILTER (WHERE net_take_rate_index < 0)     AS negative_net_take,\n"
            "           ROUND(100.0 * SUM(CASE WHEN net_take_rate_index < 0\n"
            "                             THEN gmv_index ELSE 0 END)\n"
            "               / SUM(gmv_index), 1)                            AS pct_of_gmv_negative\n"
            "    FROM mart_brand_month_economics\n"
            "    WHERE city = 'All Việt Nam'\n"
            "      AND month_start = (SELECT MAX(month_start) FROM mart_brand_month_economics)\n"
            '""")'
        ),
        conclusion(
            "**Seven of 55 brands have a negative net take rate, carrying 11.2% of GMV.** "
            "Every one of them looks healthy on the commission line. They are loss-making "
            "once BE's own discount funding is netted off, and the delivered table has no "
            "column that would reveal it."
        ),
    ]

    # ================================================================= PART 9
    cells += [
        section(
            "Part 9", "The promotion case: what the commission increase bought",
            "**The brief.** The commission rate on the airport route was raised, *\"gaining more\n"
            "revenue and leaving us more rooms to play around with promotional strategies\"*.\n"
            "Design three promotion schemes that grow the business without hurting revenue\n"
            "per trip.\n"
            "\n"
            "Before designing anything, the first question is how much room there actually is -\n"
            "and the twelve days of data answer it.",
            "`src/build_marts.py` - `build_promo_economics()`",
            "`mart.promo_unit_economics` - 12 days",
        ),
        code(
            'q("""\n'
            "    SELECT day, period,\n"
            "           ROUND(commission_rate_index, 2)           AS commission_idx,\n"
            "           ROUND(promo_rate_index, 2)                AS promo_idx,\n"
            "           ROUND(contribution_margin_rate_index, 2)  AS margin_idx,\n"
            "           ROUND(gross_spread_rate_index, 2)         AS spread_idx,\n"
            "           ROUND(contribution_margin_total_index, 1) AS margin_total_idx,\n"
            "           ROUND(trips_index, 1)                     AS trips_idx\n"
            "    FROM mart_promo_unit_economics ORDER BY day\n"
            '""")'
        ),
        md(
            "### Read the margin column\n"
            "\n"
            "It is **negative on all eight days before** the change and **positive on all four\n"
            "after**. The indexing multiplies by a constant, so the sign is preserved exactly -\n"
            "that is why a constant was used for ratios rather than a base-100 index, which\n"
            "would have destroyed it.\n"
        ),
        code(
            'q("""\n'
            "    SELECT period,\n"
            "           COUNT(*)                                        AS days,\n"
            "           COUNT(*) FILTER (WHERE contribution_margin_rate_index < 0)\n"
            "                                                           AS loss_making_days,\n"
            "           ROUND(AVG(commission_rate_index), 2)            AS avg_commission_idx,\n"
            "           ROUND(AVG(promo_rate_index), 2)                 AS avg_promo_idx,\n"
            "           ROUND(AVG(contribution_margin_rate_index), 2)   AS avg_margin_idx\n"
            "    FROM mart_promo_unit_economics\n"
            "    GROUP BY period ORDER BY period DESC\n"
            '""")'
        ),
        md(
            "### The part that matters: the pace, not the level\n"
            "\n"
            "The increase fixed a route that had been losing money on every single observed\n"
            "day. But look at what happens across the four days after it.\n"
        ),
        code(
            'q("""\n'
            "    SELECT\n"
            "      ROUND((MAX(contribution_margin_rate_index)\n"
            "           - MIN(contribution_margin_rate_index)) / 3, 3) AS margin_fall_per_day_idx,\n"
            "      ROUND((MAX(promo_rate_index)\n"
            "           - MIN(promo_rate_index)) / 3, 3)               AS promo_rise_per_day_idx,\n"
            "      ROUND(MIN(contribution_margin_rate_index), 3)       AS margin_on_last_day_idx,\n"
            "      ROUND(MIN(contribution_margin_rate_index)\n"
            "          / NULLIF((MAX(contribution_margin_rate_index)\n"
            "                  - MIN(contribution_margin_rate_index)) / 3, 0), 1)\n"
            "                                                          AS days_until_zero\n"
            "    FROM mart_promo_unit_economics\n"
            "    WHERE period = 'after commission increase'\n"
            '""")'
        ),
        conclusion(
            "On the real figures: margin fell **1.40 points per day** while promotion rose "
            "**1.17**. Roughly **3.4 of the 5 points of headroom** the increase created were "
            "spent within four days, and on that trajectory the route is loss-making again "
            "inside two more. So the answer to \"design three promotion schemes\" starts "
            "with a constraint, not a scheme: the room is about five points and it is "
            "already two-thirds committed. Any scheme has to be costed against what is left."
        ),
        md(
            "**Four points is not a trend.** The decline is real in the observed window;\n"
            "whether it continued, stabilised or reversed is unknown. That is stated in\n"
            "`docs/assumptions.md` rather than left for a reader to work out.\n"
        ),
    ]

    # ================================================================ PART 10
    cells += [
        section(
            "Part 10", "Payback, and every assumption behind it",
            "**The question the brief asked.** Build a model for ROAS and payback time by channel.\n"
            "\n"
            "No single file can answer it. Acquisition cost is in one workbook, retention in\n"
            "another, margin in a third - covering three different periods. So this is a\n"
            "**model**, and the honest version writes its assumptions into the output rather\n"
            "than hiding them in the code.",
            "`src/build_marts.py` - `build_payback()`",
            "`mart.channel_payback` - one row per channel",
        ),
        code('show_py("build_marts.py", "ASSUMPTIONS")'),
        code(
            'q("""\n'
            "    SELECT channel,\n"
            "           ROUND(cac_index, 1)               AS cac_idx,\n"
            "           ROUND(first_trip_users_index, 1)  AS rft_idx,\n"
            "           ROUND(assumed_m1_retention_index, 1) AS m1_retention_idx,\n"
            "           assumed_trips_per_month,\n"
            "           assumed_margin_rate,\n"
            "           ROUND(payback_months_no_churn, 2)   AS payback_months_simple,\n"
            "           ROUND(payback_months_with_churn, 2) AS payback_months_with_churn\n"
            "    FROM mart_channel_payback ORDER BY payback_months_with_churn\n"
            '""")'
        ),
        md(
            "### Two things in that table are not results\n"
            "\n"
            "**`Others` shows a payback of zero.** It has 15,393 first-trip users and **no\n"
            "attributed budget at all**, so its CAC computes to zero. That is an attribution\n"
            "gap, not a performance result. It is left visible and labelled rather than\n"
            "quietly dropped, because a reader who finds it themselves will wonder what else\n"
            "was removed.\n"
            "\n"
            "**`assumed_trips_per_month = 4.0` is a placeholder.** Nothing in the data supports\n"
            "it. It is the one input that is neither measured nor bounded by something\n"
            "observed - and the only one that can change the *ranking*, because a channel\n"
            "acquiring daily commuters and a channel acquiring occasional airport users do\n"
            "not pay back at the same speed even at identical CAC.\n"
            "\n"
            "Average fare and margin rate also scale every payback period, but they scale all\n"
            "of them equally, so the ordering survives. Trip frequency does not.\n"
        ),
        conclusion(
            "The ranking - Affiliate fastest, Facebook Ads slowest - is really a CAC ranking "
            "with a constant applied to it. Saying so is the difference between a model and "
            "a result. `docs/assumptions.md` states each input, where it came from, and what "
            "happens to the conclusion if it is wrong."
        ),
    ]

    # ================================================================ PART 11
    cells += [
        section(
            "Part 11", "The indexing layer",
            "**The constraint.** The source is BE Group's own operating data. No real figure\n"
            "should be published, but a portfolio project that blanks its numbers out cannot\n"
            "be read.\n"
            "\n"
            "So every published table is **transformed, not redacted** - and the transform is\n"
            "chosen so every conclusion above survives it exactly.",
            "`src/publish_indexed.py`",
            "`data/published/*.parquet` and `*.csv`",
        ),
        md(
            "| Column type | Rule | What survives |\n"
            "|---|---|---|\n"
            "| **Levels** - GMV, cost, users, orders, commission | rescaled so the first period of the series = 100 | growth rates, shares, trends |\n"
            "| **Ratios** - CAC, CIR, take rate, margin, conversion, retention | multiplied by one undisclosed constant per metric family | every within-family comparison, **including the sign** |\n"
            "| **Reconciliation deltas** expressed as a share | published as measured | a delta of 0.00% is the evidence a check passed and discloses nothing |\n"
            "\n"
            "### Why a constant for ratios rather than an index\n"
            "\n"
            "Several of these series cross zero - contribution margin most importantly.\n"
            "Rebasing a series that crosses zero destroys the sign, and in Part 9 **the sign\n"
            "is the finding**. A multiplicative constant preserves sign, ratio and crossing\n"
            "point, and hides only the level.\n"
        ),
        code('show_py("publish_indexed.py", "transform")'),
        md("### Proof that the findings survive it\n"),
        code(
            'checks = {\n'
            '    "margin still crosses zero on 2024-01-09":\n'
            '        q("""SELECT COUNT(*) AS n FROM mart_promo_unit_economics\n'
            "             WHERE (period = 'before commission increase'\n"
            "                    AND contribution_margin_rate_index < 0)\n"
            "                OR (period = 'after commission increase'\n"
            '                    AND contribution_margin_rate_index > 0)""").iat[0, 0] == 12,\n'
            '    "channel payback ranking unchanged":\n'
            '        q("""SELECT channel FROM mart_channel_payback\n'
            "             WHERE channel != 'Others'\n"
            '             ORDER BY payback_months_with_churn""")["channel"].tolist()\n'
            '        == ["Affiliate", "Tiktok", "Apple Search Ads", "Google Ads", "Facebook Ads"],\n'
            '    "city reconciliation still exactly 100%":\n'
            '        bool((q("SELECT city_share_of_national AS s FROM qa_city_reconciliation")["s"]\n'
            "               .round(6) == 1.0).all()),\n"
            '    "seven brands still negative on net take":\n'
            '        q("""SELECT COUNT(*) AS n FROM mart_brand_month_economics\n'
            "             WHERE city = 'All Việt Nam' AND net_take_rate_index < 0\n"
            "               AND month_start = (SELECT MAX(month_start)\n"
            '                                  FROM mart_brand_month_economics)""").iat[0, 0] == 7,\n'
            "}\n"
            "for claim, holds in checks.items():\n"
            '    print(f"  {\'PASS\' if holds else \'FAIL\'}  {claim}")'
        ),
        conclusion(
            "Every finding in this notebook is reproducible from the published, indexed "
            "files alone. The real values never left `data/private/`, which is git-ignored "
            "along with the source workbooks."
        ),
    ]

    # ================================================================ PART 12
    cells += [
        section(
            "Part 12", "What this data cannot answer",
            "**The brief's third question:** how would you estimate the incremental impact of\n"
            "increasing spend on one channel, from this data alone?\n"
            "\n"
            "Largely, you cannot - and saying so precisely is the deliverable.",
            "`docs/measurement_design.md`",
            "a design, not a number",
        ),
        md(
            "### The assumption nobody states\n"
            "\n"
            "```\n"
            "CAC = Budget RFT_raw / RFT\n"
            "```\n"
            "\n"
            "That formula divides the budget by **every** first trip the channel recorded. It\n"
            "therefore assumes 100% of them were caused by the spend. Part 6 confirmed the\n"
            "column really does compute this, so the assumption is genuinely in force - it is\n"
            "just invisible, because it lives inside the metric's definition rather than\n"
            "beside it.\n"
            "\n"
            "### Why Affiliate in particular\n"
            "\n"
            "Two thirds of paid acquisition at a third of the cost per user of anything else.\n"
            "Two explanations fit, and nothing here separates them:\n"
            "\n"
            "1. Affiliate is genuinely the most efficient channel BE has.\n"
            "2. Affiliate is capturing users who were going to install anyway, through a\n"
            "   trackable link that claims the credit.\n"
            "\n"
            "### Why a regression will not settle it\n"
            "\n"
            "| | |\n"
            "|---|---|\n"
            "| **Confounding** | budgets rise in high-demand weeks, so heavy-spend weeks also carry more organic demand. The model attributes the season to the budget |\n"
            "| **Reverse causality** | the budget is *set in response to* performance. Good performance causes high spend as well as the other way round. In this dataset the budget rows are weekly decisions made by a team looking at exactly these numbers |\n"
            "\n"
            "A regression run anyway returns a confident coefficient, a tight interval and a\n"
            "plausible chart. The number is meaningless. **Producing it is the mistake;\n"
            "declining to, and specifying the test that would work, is the job.**\n"
        ),
        md(
            "### The design, in brief\n"
            "\n"
            "| | |\n"
            "|---|---|\n"
            "| **Unit of randomisation** | geography - district or service zone, **not the user** |\n"
            "| **Treatment** | Affiliate spend switched off or cut by a fixed share |\n"
            "| **Primary metric** | first-trip users **across all channels**, not Affiliate's own number |\n"
            "| **Guardrails** | completion rate, cancellation rate, M1 retention of the test cohort |\n"
            "| **The constraint** | this extract has two city scopes. Two geographies cannot support a geo holdout - it needs districts, or the switchback design instead |\n"
            "\n"
            "That last row is the point. **Establish the sample constraint before proposing\n"
            "the test, not during it.** Full specification, including the minimum detectable\n"
            "effect implied by the 0.221 coefficient of variation in weekly first trips, is in\n"
            "`docs/measurement_design.md`.\n"
        ),
        conclusion(
            "The budget-cut answer follows from this. Cut from Facebook and Google, which "
            "carry 38.8% of budget for 20.4% of first trips - but do **not** move the saving "
            "into Affiliate. Hold it flat and use the cut as a natural experiment: if total "
            "acquisition falls by less than the cut channels' attributed share, that is the "
            "first evidence anyone has had about incrementality here, and it costs nothing "
            "extra to collect."
        ),
    ]

    # =================================================================== CLOSE
    cells += [
        md(
            "---\n"
            "\n"
            "## What this project demonstrates\n"
            "\n"
            "| | |\n"
            "|---|---|\n"
            "| **Working with a real handover** | merged-cell, metric-as-row Excel parsed reproducibly, with four traps handled explicitly and written down |\n"
            "| **Checking before quoting** | four checks, of which one found that `All Viet Nam` is two cities |\n"
            "| **Commercial reasoning** | net take rate, discount funding by party, contribution margin per trip, payback |\n"
            "| **Scope discipline** | a model labelled as a model, a placeholder named as a placeholder, an attribution gap left visible |\n"
            "| **Measurement judgement** | declining to produce a confounded incrementality estimate, and specifying the test that would work |\n"
            "| **Handling confidential data** | a transform chosen so every conclusion survives and no level is recoverable, verified rather than assumed |\n"
            "\n"
            "### Limitations, stated\n"
            "\n"
            "- The three source files cover **three different periods**. The payback model\n"
            "  combines them anyway and says so.\n"
            "- `assumed_trips_per_month` is a placeholder and would change the ranking.\n"
            "- The promotion case is **twelve days**, eight before and four after, with no\n"
            "  control route. The margin decline is a description, not a causal estimate.\n"
            "- `dd` could not be identified and is excluded from every calculation.\n"
            "- `All Viet Nam` covers two cities. Every share derived from it inherits that.\n"
            "\n"
            "---\n"
            "\n"
            "*Dictionary: `docs/data_dictionary.md` - Assumptions: `docs/assumptions.md`*  \n"
            "*Measurement design: `docs/measurement_design.md` - Original submission: `docs/original_submission.md`*\n"
        ),
        code('db.close()\nprint("Walkthrough complete.")'),
    ]

    notebook = {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    out = project_root / "notebooks" / "00_walkthrough.ipynb"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(notebook, indent=1, ensure_ascii=False), encoding="utf-8")
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--project-root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    args = parser.parse_args()
    root = args.project_root.resolve()
    path = build(root)
    count = len(json.loads(path.read_text(encoding="utf-8"))["cells"])
    print(f"{path.relative_to(root)}: {count} cells")


if __name__ == "__main__":
    main()
