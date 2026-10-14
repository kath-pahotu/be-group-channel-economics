"""Build the decision tables from the tidy source.

Four marts, one business question each:

    channel_week_pnl     what does each acquisition channel cost and return?
    brand_month_economics what does BE actually keep per brand, after it funds
                          its own share of the discount?
    promo_unit_economics  what does one airport trip earn, and how fast is
                          promotion spending the margin the commission increase
                          created?
    channel_payback       how long before a channel's customers pay back what
                          they cost to acquire?

Plus a qa schema, because a mart nobody checked is a claim, not a result.

Run:
    python src/build_marts.py --project-root .
"""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb
import pandas as pd

# "AllBe" is the company total; "CPC (excl. AFF)" is a grouping of the paid
# channels, not a channel. Summing either with the detail double-counts.
TOTAL_CHANNEL = "AllBe"
GROUPING_CHANNELS = {"CPC (excl. AFF)"}

# The commission rate on the beAirport route was raised partway through the
# observed window. Everything before and after is a different economics.
COMMISSION_CHANGE = "2024-01-09"


def connect(project_root: Path) -> duckdb.DuckDBPyConnection:
    database = project_root / "artifacts" / "be_commercial.duckdb"
    database.parent.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(str(database))
    private = (project_root / "data" / "private").as_posix()
    for name in (
        "topline_week", "channel_week", "promo_day", "brand_month",
        "retention_month", "promo_usage_month", "cancellation", "service_volume",
    ):
        connection.execute(
            f"CREATE OR REPLACE VIEW stg_{name} AS "
            f"SELECT * FROM read_parquet('{private}/{name}.parquet')"
        )
    for schema in ("mart", "qa"):
        connection.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
    return connection


def build_channel_pnl(connection) -> None:
    """One row per channel per week, with the economics on the same row.

    The source stores every metric as its own block of rows, so the first job
    is to pivot it back into a record. Only then can cost sit next to what the
    cost bought, which is the whole point of a channel P&L.
    """
    connection.execute(
        f"""
        CREATE OR REPLACE TABLE mart.channel_week_pnl AS
        WITH wide AS (
            SELECT
                channel,
                week_start,
                MAX(CASE WHEN metric = 'Install (UA)'       THEN value END) AS installs,
                MAX(CASE WHEN metric = 'SU'                 THEN value END) AS signups,
                MAX(CASE WHEN metric = 'RFT'                THEN value END) AS first_trip_users,
                MAX(CASE WHEN metric = 'Requests'           THEN value END) AS requests,
                MAX(CASE WHEN metric = 'Booking_Completed'  THEN value END) AS completed_bookings,
                MAX(CASE WHEN metric = 'CR'                 THEN value END) AS completion_rate,
                MAX(CASE WHEN metric = 'GMV'                THEN value END) AS gmv,
                MAX(CASE WHEN metric = 'AOV'                THEN value END) AS aov,
                MAX(CASE WHEN metric = 'Digital Cost'       THEN value END) AS digital_cost,
                MAX(CASE WHEN metric = 'Budget RFT'         THEN value END) AS budget_first_trip,
                MAX(CASE WHEN metric = 'Budget Trip'        THEN value END) AS budget_trip,
                MAX(CASE WHEN metric = 'CAC'                THEN value END) AS cac_reported,
                MAX(CASE WHEN metric = 'CPA'                THEN value END) AS cpa_reported,
                MAX(CASE WHEN metric = 'CIR'                THEN value END) AS cir_reported
            FROM stg_channel_week
            GROUP BY channel, week_start
        )
        SELECT
            channel,
            week_start,
            CASE WHEN channel = '{TOTAL_CHANNEL}' THEN 'company total'
                 WHEN channel IN ('{"','".join(GROUPING_CHANNELS)}') THEN 'grouping'
                 WHEN channel = 'Organic' THEN 'unpaid'
                 ELSE 'paid channel' END                       AS channel_role,
            installs, signups, first_trip_users, requests, completed_bookings,
            gmv, aov, digital_cost, budget_first_trip, budget_trip,
            -- Reported figures, kept as delivered so they can be checked.
            cac_reported, cpa_reported, cir_reported, completion_rate,
            -- Recomputed from the components. Where these disagree with the
            -- reported column, the definition differs - and that is worth
            -- knowing before either number reaches a slide.
            budget_first_trip / NULLIF(first_trip_users, 0)    AS cac_recomputed,
            budget_trip       / NULLIF(completed_bookings, 0)  AS cpa_recomputed,
            digital_cost      / NULLIF(gmv, 0)                 AS cir_recomputed,
            -- Funnel, step by step.
            signups           / NULLIF(installs, 0)            AS install_to_signup,
            first_trip_users  / NULLIF(signups, 0)             AS signup_to_first_trip,
            completed_bookings/ NULLIF(requests, 0)            AS request_to_booking,
            gmv               / NULLIF(first_trip_users, 0)    AS gmv_per_first_trip_user
        FROM wide
        ORDER BY channel, week_start
        """
    )


def build_brand_economics(connection) -> None:
    """Brand x city x month, with discount decomposed by who funded it.

    The column that matters is net_take_rate. A brand can show a healthy
    commission rate and still lose money for the platform once BE's own share
    of the discount is netted off - and the delivered table cannot show that,
    because the two sit in different columns and are never subtracted.
    """
    connection.execute(
        """
        CREATE OR REPLACE TABLE mart.brand_month_economics AS
        SELECT
            brand_name,
            city,
            month_start,
            nb_online_merchant                                   AS merchants_listed,
            nb_active_merchant                                   AS merchants_active,
            nb_active_merchant / NULLIF(nb_online_merchant, 0)   AS merchant_activation_rate,
            nb_total_order                                       AS orders,
            nb_trip                                              AS trips,
            gmv,
            gfv,
            gmv / NULLIF(nb_total_order, 0)                      AS average_order_value,
            total_commission,
            total_commission / NULLIF(gmv, 0)                    AS take_rate,
            -- Who paid for the discount
            COALESCE(be_discount_amount_food, 0)
              + COALESCE(be_discount_amount_delivery, 0)         AS discount_funded_by_be,
            COALESCE(merchant_discount_amount_food, 0)
              + COALESCE(merchant_discount_amount_delivery, 0)   AS discount_funded_by_merchant,
            COALESCE(partner_discount, 0)                        AS discount_funded_by_partner,
            COALESCE(be_discount_amount_food, 0)
              + COALESCE(be_discount_amount_delivery, 0)
              + COALESCE(merchant_discount_amount_food, 0)
              + COALESCE(merchant_discount_amount_delivery, 0)
              + COALESCE(partner_discount, 0)                    AS discount_total,
            (COALESCE(be_discount_amount_food, 0)
              + COALESCE(be_discount_amount_delivery, 0))
              / NULLIF(gmv, 0)                                   AS be_subsidy_rate,
            -- What BE actually keeps
            (total_commission
              - COALESCE(be_discount_amount_food, 0)
              - COALESCE(be_discount_amount_delivery, 0))        AS net_contribution,
            (total_commission
              - COALESCE(be_discount_amount_food, 0)
              - COALESCE(be_discount_amount_delivery, 0))
              / NULLIF(gmv, 0)                                   AS net_take_rate,
            dd
        FROM stg_brand_month
        ORDER BY city, month_start, gmv DESC
        """
    )


def build_promo_economics(connection) -> None:
    """The beAirport route, daily, with per-trip economics made explicit.

    The delivered sheet gives percentages of GMV. A commercial conversation
    happens in currency per trip, so every rate is multiplied back up by AOV.
    """
    connection.execute(
        f"""
        CREATE OR REPLACE TABLE mart.promo_unit_economics AS
        SELECT
            day,
            CASE WHEN day < DATE '{COMMISSION_CHANGE}'
                 THEN 'before commission increase'
                 ELSE 'after commission increase' END       AS period,
            "GMV"                                           AS gmv,
            "Trip"                                          AS trips,
            "Eyeball"                                       AS eyeballs,
            "Request"                                       AS requests,
            "AOV"                                           AS average_fare,
            "RE"                                            AS eyeball_to_request,
            "CR"                                            AS request_to_trip,
            "Distance"                                      AS average_distance_km,
            "%Total Commission"                             AS commission_rate,
            "%promo"                                        AS promo_rate,
            "%CM"                                           AS contribution_margin_rate,
            -- Per trip, in currency.
            "AOV" * "%Total Commission"                     AS commission_per_trip,
            "AOV" * "%promo"                                AS promo_per_trip,
            "AOV" * "%CM"                                   AS contribution_margin_per_trip,
            -- Headroom: what the commission earns, less what promotion spends.
            "%Total Commission" - "%promo"                  AS gross_spread_rate,
            "AOV" * ("%Total Commission" - "%promo")        AS gross_spread_per_trip,
            -- Total, not just per unit.
            "Trip" * "AOV" * "%CM"                          AS contribution_margin_total,
            "Trip" * "AOV" * "%promo"                       AS promo_spend_total
        FROM stg_promo_day
        ORDER BY day
        """
    )


def build_payback(connection, assumptions: dict[str, float]) -> None:
    """Months for a channel's acquired user to repay their acquisition cost.

    This is a MODEL, not a measurement, and the three inputs come from three
    different files covering three different periods. Every assumption is
    written into the table as its own column so no reader has to take the
    result on trust - and so that changing one is a one-line edit, not an
    archaeology exercise.
    """
    connection.execute(
        f"""
        CREATE OR REPLACE TABLE mart.channel_payback AS
        WITH channel_cost AS (
            SELECT channel,
                   SUM(budget_first_trip)                        AS budget,
                   SUM(first_trip_users)                         AS first_trip_users,
                   SUM(budget_first_trip) / NULLIF(SUM(first_trip_users), 0) AS cac,
                   SUM(gmv) / NULLIF(SUM(first_trip_users), 0)   AS gmv_per_user_window
            FROM mart.channel_week_pnl
            WHERE channel_role = 'paid channel'
            GROUP BY channel
        ),
        retention AS (
            SELECT AVG(m1_retention_rate) AS m1_rate
            FROM stg_retention_month WHERE segment = 'RFT'
        )
        SELECT
            c.channel,
            c.cac,
            c.first_trip_users,
            c.gmv_per_user_window,
            r.m1_rate                                            AS assumed_m1_retention,
            {assumptions['contribution_margin_rate']}            AS assumed_margin_rate,
            {assumptions['trips_per_month']}                     AS assumed_trips_per_month,
            c.gmv_per_user_window / NULLIF(c.first_trip_users, 0) * 0 +
              {assumptions['average_fare']}                      AS assumed_average_fare,
            -- Monthly contribution from one retained user.
            {assumptions['average_fare']} * {assumptions['trips_per_month']}
              * {assumptions['contribution_margin_rate']}        AS monthly_contribution,
            -- Decayed over months at the observed M1 retention rate.
            c.cac / NULLIF({assumptions['average_fare']} * {assumptions['trips_per_month']}
              * {assumptions['contribution_margin_rate']}, 0)    AS payback_months_no_churn,
            c.cac / NULLIF({assumptions['average_fare']} * {assumptions['trips_per_month']}
              * {assumptions['contribution_margin_rate']} * r.m1_rate, 0)
                                                                 AS payback_months_with_churn
        FROM channel_cost c CROSS JOIN retention r
        ORDER BY payback_months_with_churn
        """
    )


def build_qa(connection) -> None:
    """Checks that have to pass before any of the above is quotable."""
    connection.execute(
        f"""
        CREATE OR REPLACE TABLE qa.channel_reconciliation AS
        WITH detail AS (
            SELECT week_start, SUM(first_trip_users) AS detail_rft,
                   SUM(gmv) AS detail_gmv, SUM(digital_cost) AS detail_cost
            FROM mart.channel_week_pnl
            WHERE channel_role IN ('paid channel', 'unpaid')
            GROUP BY week_start
        ),
        total AS (
            SELECT week_start, first_trip_users AS total_rft,
                   gmv AS total_gmv, digital_cost AS total_cost
            FROM mart.channel_week_pnl WHERE channel = '{TOTAL_CHANNEL}'
        )
        SELECT t.week_start,
               t.total_rft, d.detail_rft,
               d.detail_rft - t.total_rft                                AS rft_delta,
               (d.detail_rft - t.total_rft) / NULLIF(t.total_rft, 0)     AS rft_delta_pct,
               t.total_gmv, d.detail_gmv,
               (d.detail_gmv - t.total_gmv) / NULLIF(t.total_gmv, 0)     AS gmv_delta_pct
        FROM total t JOIN detail d USING (week_start)
        ORDER BY ABS((d.detail_rft - t.total_rft) / NULLIF(t.total_rft, 0)) DESC
        """
    )
    connection.execute(
        """
        CREATE OR REPLACE TABLE qa.metric_definition_check AS
        SELECT channel, week_start,
               cac_reported, cac_recomputed,
               cac_recomputed - cac_reported                             AS cac_delta,
               cir_reported, cir_recomputed,
               cir_recomputed - cir_reported                             AS cir_delta
        FROM mart.channel_week_pnl
        WHERE channel_role = 'paid channel'
          AND cac_reported IS NOT NULL AND cac_recomputed IS NOT NULL
        ORDER BY ABS(cac_recomputed - cac_reported) DESC
        """
    )
    connection.execute(
        """
        CREATE OR REPLACE TABLE qa.city_reconciliation AS
        WITH city_detail AS (
            SELECT month_start, SUM(gmv) AS city_gmv, SUM(total_commission) AS city_commission
            FROM mart.brand_month_economics
            WHERE city IN ('Ha Noi', 'Ho Chi Minh') GROUP BY month_start
        ),
        national AS (
            SELECT month_start, SUM(gmv) AS national_gmv, SUM(total_commission) AS national_commission
            FROM mart.brand_month_economics
            WHERE city = 'All Việt Nam' GROUP BY month_start
        )
        SELECT n.month_start, n.national_gmv, c.city_gmv,
               c.city_gmv - n.national_gmv                               AS gmv_delta,
               c.city_gmv / NULLIF(n.national_gmv, 0)                    AS city_share_of_national
        FROM national n JOIN city_detail c USING (month_start)
        ORDER BY month_start
        """
    )
    connection.execute(
        """
        CREATE OR REPLACE TABLE qa.completeness AS
        SELECT 'brand_month' AS table_name, 'discount and commission columns' AS field,
               COUNT(*) FILTER (WHERE total_commission IS NULL) AS null_rows,
               COUNT(*) AS total_rows
        FROM stg_brand_month
        UNION ALL
        SELECT 'channel_week', 'digital_cost',
               COUNT(*) FILTER (WHERE digital_cost IS NULL), COUNT(*)
        FROM mart.channel_week_pnl WHERE channel_role = 'paid channel'
        UNION ALL
        SELECT 'channel_week', 'first_trip_users',
               COUNT(*) FILTER (WHERE first_trip_users IS NULL), COUNT(*)
        FROM mart.channel_week_pnl WHERE channel_role = 'paid channel'
        """
    )


# The three inputs the payback model cannot read from any single file.
ASSUMPTIONS = {
    "average_fare": 11.0,            # mart.promo_unit_economics, stable 10.8-11.1
    "trips_per_month": 4.0,          # placeholder - see docs/assumptions.md
    "contribution_margin_rate": 0.04,  # post-increase beAirport CM, conservative
}


def run(project_root: Path) -> dict[str, int]:
    connection = connect(project_root)
    try:
        build_channel_pnl(connection)
        build_brand_economics(connection)
        build_promo_economics(connection)
        build_payback(connection, ASSUMPTIONS)
        build_qa(connection)
        tables = connection.execute(
            """
            SELECT schema_name || '.' || table_name AS name
            FROM duckdb_tables() WHERE schema_name IN ('mart', 'qa')
            ORDER BY 1
            """
        ).fetchall()
        counts = {
            name: connection.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
            for (name,) in tables
        }
    finally:
        connection.close()
    return counts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--project-root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    args = parser.parse_args()
    counts = run(args.project_root.resolve())
    width = max(len(name) for name in counts)
    for name, rows in counts.items():
        print(f"{name:<{width}}  {rows:>6,} rows")


if __name__ == "__main__":
    main()
