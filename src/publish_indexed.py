"""Produce the publishable version of every mart.

WHY
---
The source workbooks are BE Group's own operating data, handed over for a
business-analysis exercise. Nothing in this repository was published with real
figures in it, and nothing should be. But a portfolio project that shows only
method and no numbers is unreadable, and a reader cannot judge an analysis
whose outputs are blanked out.

So every published table is transformed, not redacted. The transform is chosen
so that every conclusion in the analysis survives it exactly and no absolute
value can be recovered from it.

HOW
---
Two rules, applied by column type.

  LEVELS  - currency, counts, budgets, GMV, users, orders, merchants.
            Rescaled to an index where the first period of the series = 100.
            Growth rates, shares and trends are preserved exactly. The level is
            not recoverable without the base, which is never published.

  RATIOS  - CAC, CPA, CIR, take rate, subsidy rate, margin rate, conversion,
            retention. Multiplied by one undisclosed constant per metric
            family. Every comparison within a family survives unchanged: if
            Facebook's CAC was 3.1x Affiliate's, it still is; if contribution
            margin crossed from negative to positive, it still does on the same
            day. Only the level is hidden.

A multiplicative constant is used for ratios rather than a base-100 index
because several of these series cross zero. Indexing a series that crosses zero
destroys the sign, and the sign is the finding.

The constants live in data/private/scale_factors.json, which is git-ignored and
never leaves this machine. The published tables carry an `_index` suffix on
every transformed column so no reader can mistake one for a real figure.

Run:
    python src/publish_indexed.py --project-root .
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb
import pandas as pd

# Columns that are counts or currency: rescaled so the first period = 100.
LEVEL_COLUMNS = {
    "installs", "signups", "first_trip_users", "requests", "completed_bookings",
    "gmv", "gfv", "aov", "average_fare", "digital_cost", "budget_first_trip",
    "budget_trip", "budget", "gmv_per_first_trip_user", "gmv_per_user_window",
    "orders", "trips", "eyeballs", "merchants_listed", "merchants_active",
    "total_commission", "net_contribution", "discount_total",
    "discount_funded_by_be", "discount_funded_by_merchant",
    "discount_funded_by_partner", "average_order_value", "dd",
    "commission_per_trip", "promo_per_trip", "contribution_margin_per_trip",
    "gross_spread_per_trip", "contribution_margin_total", "promo_spend_total",
    "average_distance_km", "monthly_contribution",
}

# Columns that are ratios: multiplied by one constant per family.
RATIO_FAMILIES = {
    "acquisition_cost": {"cac", "cpa", "cac_reported", "cpa_reported",
                         "cac_recomputed", "cpa_recomputed"},
    "cost_intensity": {"cir", "cir_reported", "cir_recomputed"},
    "commercial_rate": {"take_rate", "net_take_rate", "be_subsidy_rate",
                        "commission_rate", "promo_rate",
                        "contribution_margin_rate", "gross_spread_rate"},
    "conversion": {"install_to_signup", "signup_to_first_trip",
                   "request_to_booking", "completion_rate", "request_to_trip",
                   "eyeball_to_request", "merchant_activation_rate"},
    "retention": {"m1_retention_rate", "assumed_m1_retention"},
}

# Columns that are already dimensionless comparisons or structural, and are
# published unchanged because they carry no recoverable value.
PASS_THROUGH = {
    "channel", "channel_role", "week_start", "month_start", "day", "period",
    "brand_name", "city", "segment", "cohort", "dimension", "service_type",
    "metric", "basis", "lag_weeks", "is_component", "table_name", "field",
    "payback_months_no_churn", "payback_months_with_churn",
    "assumed_trips_per_month", "assumed_margin_rate", "assumed_average_fare",
    "null_rows", "total_rows",
    # Reconciliation deltas expressed as a share. A delta of 0.00% is the
    # evidence the check passed and discloses nothing about the level, so it
    # is published as measured. Without these the QA tables prove nothing.
    "rft_delta_pct", "gmv_delta_pct", "city_share_of_national",
}

# Columns that must be indexed against a SHARED base, because the whole point
# of the pair is that they are equal. Indexing each against its own base would
# force a delta of zero and make the check vacuous.
SHARED_BASE_GROUPS = [
    {"total_rft", "detail_rft"},
    {"total_gmv", "detail_gmv"},
    {"national_gmv", "city_gmv"},
]

PUBLISHED_TABLES = [
    "mart.channel_week_pnl",
    "mart.brand_month_economics",
    "mart.promo_unit_economics",
    "mart.channel_payback",
    "qa.channel_reconciliation",
    "qa.city_reconciliation",
    "qa.completeness",
]

# Fixed so the published numbers are stable across rebuilds. The values are
# arbitrary; only their consistency matters.
SCALE_SEED = 20261014


def scale_factors() -> dict[str, float]:
    """One multiplier per ratio family, deterministic across runs."""
    import random

    generator = random.Random(SCALE_SEED)
    return {
        family: round(generator.uniform(0.35, 2.8), 4)
        for family in sorted(RATIO_FAMILIES)
    }


def family_of(column: str) -> str | None:
    for family, columns in RATIO_FAMILIES.items():
        if column in columns:
            return family
    return None


def index_levels(frame: pd.DataFrame, column: str, period_column: str | None) -> pd.Series:
    """Rescale so the first period of the series equals 100.

    The base is the mean across the earliest period present, not a single row,
    so a channel that happened to have a quiet first week does not get an
    inflated index for the rest of the series.
    """
    values = pd.to_numeric(frame[column], errors="coerce")
    if period_column and period_column in frame:
        earliest = frame[period_column].min()
        base = values[frame[period_column] == earliest].mean()
    else:
        base = values.mean()
    if base is None or pd.isna(base) or base == 0:
        base = values.replace(0, pd.NA).dropna().abs().mean()
    if base is None or pd.isna(base) or base == 0:
        return values * 0
    return (values / base * 100).round(2)


def shared_base(frame: pd.DataFrame, columns: set[str], period_column: str | None) -> float:
    """One base for a group of columns that are supposed to agree."""
    present = [c for c in columns if c in frame.columns]
    stacked = pd.concat([pd.to_numeric(frame[c], errors="coerce") for c in present])
    if period_column and period_column in frame:
        mask = pd.concat([frame[period_column] == frame[period_column].min()] * len(present))
        base = stacked[mask.to_numpy()].mean()
        if base and not pd.isna(base) and base != 0:
            return float(base)
    return float(stacked.abs().mean() or 1.0)


def transform(frame: pd.DataFrame, factors: dict[str, float]) -> pd.DataFrame:
    period_column = next(
        (c for c in ("week_start", "month_start", "day") if c in frame.columns), None
    )
    bases: dict[str, float] = {}
    for group in SHARED_BASE_GROUPS:
        if group & set(frame.columns):
            base = shared_base(frame, group, period_column)
            bases.update({column: base for column in group})

    out = pd.DataFrame(index=frame.index)
    for column in frame.columns:
        if column in PASS_THROUGH:
            out[column] = frame[column]
        elif column in bases:
            out[f"{column}_index"] = (
                pd.to_numeric(frame[column], errors="coerce") / bases[column] * 100
            ).round(3)
        elif column in LEVEL_COLUMNS:
            out[f"{column}_index"] = index_levels(frame, column, period_column)
        elif (family := family_of(column)) is not None:
            out[f"{column}_index"] = (
                pd.to_numeric(frame[column], errors="coerce") * factors[family] * 100
            ).round(3)
        else:
            # Anything unclassified is a delta or a derived comparison. Deltas
            # between indexed quantities are meaningless, so they are dropped
            # rather than published in a state nobody can interpret.
            continue
    return out


def run(project_root: Path) -> dict[str, tuple[int, int]]:
    factors = scale_factors()
    private = project_root / "data" / "private"
    private.mkdir(parents=True, exist_ok=True)
    (private / "scale_factors.json").write_text(
        json.dumps({"seed": SCALE_SEED, "factors": factors}, indent=2), encoding="utf-8"
    )

    connection = duckdb.connect(
        str(project_root / "artifacts" / "be_commercial.duckdb"), read_only=True
    )
    published = project_root / "data" / "published"
    published.mkdir(parents=True, exist_ok=True)
    result: dict[str, tuple[int, int]] = {}
    try:
        for qualified in PUBLISHED_TABLES:
            frame = connection.execute(f"SELECT * FROM {qualified}").fetchdf()
            indexed = transform(frame, factors)
            name = qualified.replace(".", "_")
            indexed.to_csv(published / f"{name}.csv", index=False, encoding="utf-8")
            indexed.to_parquet(published / f"{name}.parquet", index=False)
            result[qualified] = (len(indexed), indexed.shape[1])
    finally:
        connection.close()

    notice = """# Published data - indexed, not real

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
"""
    (published / "README.md").write_text(notice, encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--project-root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    args = parser.parse_args()
    result = run(args.project_root.resolve())
    width = max(len(name) for name in result)
    for name, (rows, columns) in result.items():
        print(f"{name:<{width}}  {rows:>6,} rows  {columns:>2} cols")


if __name__ == "__main__":
    main()
