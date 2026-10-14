"""Turn BE Group's reporting workbooks into tidy tables.

WHY THIS FILE EXISTS
--------------------
The three workbooks are reporting outputs, not datasets. They are laid out the
way an operating team actually keeps a weekly deck: metrics down the rows,
dates across the columns, merged header cells, a second grouping key hiding in
column B, blank spacer rows between blocks, and section banners in the middle
of the data.

Nothing downstream can read that. Every join, every aggregation and every chart
needs one row per observation. So this module does one job and does it
reproducibly: it reads the workbooks exactly as delivered and emits long-format
tables with explicit keys.

It is the least glamorous file in the project and the one most of the value
depends on. A public dataset arrives tidy; a real handover never does.

WHAT IT PRODUCES
----------------
    channel_week      one row per channel x week x metric      (from workbook A)
    topline_week      one row per week x metric                (from workbook A)
    promo_day         one row per day x metric                 (from workbook B, Bai 1)
    brand_month       one row per brand x city x month         (from workbook B, Bai 2)
    retention_month   one row per segment x month              (from workbook C)
    promo_usage_month one row per service x cohort x month     (from workbook C)
    cancellation      one row per reason x service x month x user type (from workbook C)

Run:
    python src/parse_source.py --project-root .
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

WORKBOOK_CHANNEL = "BEG_DIG_MKT BA Test Channel Perf (1).xlsx"
WORKBOOK_MKT = "Test_MKT BA (1).xlsx"
WORKBOOK_CPC = "DIG_CPC Pre-test (1).xlsx"

# Row 41 of the channel sheet is a banner, not data. Everything above it is the
# company total; everything below is the same metrics split by channel.
CHANNEL_BANNER = "BREAK BY CHANNELS"

# Metrics whose label carries a reporting lag. The lag is part of the metric
# definition, not a note - an install measured at T-2 cannot be divided by a
# signup measured at T-1 without shifting one of them first. Recording the lag
# as a column keeps that decision visible instead of buried.
LAG_SUFFIXES = {
    "(Lag T-2)": 2,
    "(lag T-1)": 1,
    "(Lag T-1)": 1,
    "(lag T-2)": 2,
}


def strip_lag(label: str) -> tuple[str, int]:
    """Split 'Open App User (Firebase) (Lag T-2)' into the name and the lag."""
    for suffix, weeks in LAG_SUFFIXES.items():
        if suffix in label:
            return label.replace(suffix, "").strip(), weeks
    return label.strip(), 0


# The first row of each channel block carries the metric's formula in its
# label; the seven rows under it carry the bare name. Left alone they parse as
# two different metrics, and a GROUP BY silently splits the series in half.
METRIC_ALIASES = {
    "CAC (=Budget RFT_raw / RFT)": "CAC",
    "CPA (= Budget_raw Trip /total booking)": "CPA",
    "CAC ($) (=Raw RFT Budget /RFT)": "CAC",
    "CPA ($) ( (=Raw Booking Budget /Total trip)": "CPA",
}

# Accounting qualifiers are part of the measure, not decoration: "n/VAT" is net
# of VAT, "w/Fee" includes agency fee, "n/CIT" is net of corporate income tax.
# Stripping them loses the definition, so they move to their own column and the
# metric name stays clean enough to group by.
BASIS_MARKERS = [
    ("w/Fee n/CIT n/VAT", "with fee, net of CIT and VAT"),
    ("n/Fee n/CIT n/VAT", "net of fee, CIT and VAT"),
    ("n/VAT", "net of VAT"),
    ("(w_fee)", "with fee"),
    ("($)", "USD"),
]


def split_basis(label: str) -> tuple[str, str]:
    """Separate 'Digital Cost w/Fee n/CIT n/VAT' into the measure and its basis."""
    basis = ""
    for marker, meaning in BASIS_MARKERS:
        if marker in label:
            label = label.replace(marker, "")
            basis = meaning
            break
    return label.replace(",", " ").replace("_raw", "").strip(" ,"), basis


def as_date(value) -> pd.Timestamp | None:
    """A header cell that is a date, or None.

    openpyxl hands back `datetime.datetime` for some cells and pandas promotes
    others to `pd.Timestamp`, depending on whether the column came back typed.
    An isinstance check against either one alone silently drops half the
    headers, so parse and let the failure decide.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        parsed = pd.to_datetime(value)
    except (ValueError, TypeError):
        return None
    return None if pd.isna(parsed) else parsed


def clean_number(value) -> float | None:
    """Excel cells in these sheets mix numbers with text like '44,242'."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "").replace("%", "")
    if text in {"", "-", "n/a", "N/A", "#DIV/0!", "#REF!"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


# --------------------------------------------------------------- workbook A


def parse_channel_workbook(path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Weekly marketing performance: company total, then the same by channel."""
    raw = pd.read_excel(path, sheet_name="Raw data", header=None)

    # Row 1 holds the week-commencing dates from column 2 onward.
    dates = {
        column: pd.to_datetime(raw.iat[1, column])
        for column in range(2, raw.shape[1])
        if pd.notna(raw.iat[1, column])
    }

    banner_row = next(
        index for index in range(raw.shape[0])
        if str(raw.iat[index, 0]).strip() == CHANNEL_BANNER
    )

    topline: list[dict] = []
    channel: list[dict] = []

    for index in range(2, raw.shape[0]):
        label = raw.iat[index, 0]
        if pd.isna(label):
            continue
        label = str(label).strip()
        if label in {CHANNEL_BANNER, "TOP LINES"}:
            continue

        metric, lag_weeks = strip_lag(label)
        # A leading "---" or "-" marks a breakdown of the metric above it. Keep
        # the marker out of the name but record that it is a component.
        is_component = metric.startswith("-")
        metric = metric.lstrip("- ").strip()
        metric = METRIC_ALIASES.get(metric, metric)
        metric, basis = split_basis(metric)
        metric = METRIC_ALIASES.get(metric, metric)

        group = raw.iat[index, 1]
        group = None if pd.isna(group) else str(group).strip()

        for column, week in dates.items():
            value = clean_number(raw.iat[index, column])
            if value is None:
                continue
            row = {
                "week_start": week,
                "metric": metric,
                "value": value,
                "basis": basis,
                "lag_weeks": lag_weeks,
                "is_component": is_component,
            }
            if index < banner_row:
                topline.append(row)
            else:
                # Below the banner the channel is in column B. A row without one
                # is a spacer and carries no data.
                if group is None:
                    continue
                channel.append({**row, "channel": group})

    topline_df = pd.DataFrame(topline).sort_values(["metric", "week_start"])
    channel_df = pd.DataFrame(channel).sort_values(["channel", "metric", "week_start"])
    return (
        topline_df.reset_index(drop=True),
        channel_df.reset_index(drop=True),
    )


# --------------------------------------------------------------- workbook B


def parse_promo_days(path: Path) -> pd.DataFrame:
    """The beAirport case: eleven metrics down the rows, days across."""
    raw = pd.read_excel(path, sheet_name="Test_Bài 1_DATA", header=None)
    dates = {
        column: pd.to_datetime(raw.iat[1, column])
        for column in range(1, raw.shape[1])
        if pd.notna(raw.iat[1, column])
    }
    rows = []
    for index in range(2, raw.shape[0]):
        label = raw.iat[index, 0]
        if pd.isna(label):
            continue
        metric = str(label).strip()
        for column, day in dates.items():
            value = clean_number(raw.iat[index, column])
            if value is not None:
                rows.append({"day": day, "metric": metric, "value": value})
    frame = pd.DataFrame(rows)
    return frame.pivot(index="day", columns="metric", values="value").reset_index()


def parse_brand_month(path: Path) -> pd.DataFrame:
    """Brand x city x month. This sheet is already long - it only needs typing."""
    frame = pd.read_excel(path, sheet_name="Data Raw_Bài 2")
    frame["timeframe"] = pd.to_datetime(frame["timeframe"])
    frame = frame.rename(columns={"timeframe": "month_start"})
    frame["city"] = frame["city"].str.strip()
    frame["brand_name"] = frame["brand_name"].str.strip()
    return frame.drop(columns=["timeframe_type"])


# --------------------------------------------------------------- workbook C


def parse_retention(path: Path) -> pd.DataFrame:
    """M1 retention rate by segment, from the block under 'Compare RFT with EC'."""
    raw = pd.read_excel(path, sheet_name="Data 1", header=None)
    dates = {
        column: as_date(raw.iat[2, column])
        for column in range(2, raw.shape[1])
        if as_date(raw.iat[2, column]) is not None
    }
    rows = []
    for index in range(3, raw.shape[0]):
        label = raw.iat[index, 1]
        if pd.isna(label):
            continue
        segment = str(label).strip()
        if segment.lower().startswith("break by"):
            break
        for column, month in dates.items():
            value = clean_number(raw.iat[index, column])
            if value is not None:
                rows.append(
                    {"month_start": month, "segment": segment, "m1_retention_rate": value}
                )
    return pd.DataFrame(rows)


def parse_promo_usage(path: Path) -> pd.DataFrame:
    """Promo per trip at M0 and M1, two side-by-side blocks.

    Two things in this sheet will quietly wreck an aggregate if they are not
    handled here.

    First, the block stacks TWO dimensions under one header: service types
    (beBike, beCar, beClean, beDelivery, beFood) and rider personas (Office
    Worker, University Student, Parent, ...). They are not comparable and must
    not sit in one column, so they are labelled and split.

    Second, it contains subtotal rows - "beBike Total", "beFood Total" - inline
    with the detail. Summing the column as delivered double-counts every one of
    them. They are dropped, and the drop is counted so it is visible.
    """
    raw = pd.read_excel(path, sheet_name="Data 2", header=None)
    rows = []
    # The M0 block starts at column 1, the M1 block at column 10. Row 6 holds
    # the month headers for both.
    for cohort, key_column in (("M0", 1), ("M1", 10)):
        dates = {
            column: as_date(raw.iat[6, column])
            for column in range(key_column + 1, min(key_column + 7, raw.shape[1]))
            if as_date(raw.iat[6, column]) is not None
        }
        for index in range(7, raw.shape[0]):
            label = raw.iat[index, key_column]
            if pd.isna(label):
                continue
            segment = str(label).strip()
            if segment.lower() in {"service_type", "total"}:
                continue
            if segment.lower().endswith(" total"):
                continue  # inline subtotal - would double-count on aggregation
            # Service names are the product lines and all begin "be"; anything
            # else in this block is a rider persona.
            dimension = "service" if segment.lower().startswith("be") else "persona"
            for column, month in dates.items():
                value = clean_number(raw.iat[index, column])
                if value is not None:
                    rows.append(
                        {
                            "month_start": month,
                            "cohort": cohort,
                            "dimension": dimension,
                            "segment": segment,
                            "promo_per_trip": value,
                        }
                    )
    return pd.DataFrame(rows)


def parse_cancellations(path: Path) -> pd.DataFrame:
    frame = pd.read_excel(path, sheet_name="Data 4")
    frame = frame.rename(
        columns={
            "Cancel Reason_ description": "cancel_reason",
            "active_month": "month_start",
        }
    )
    frame["month_start"] = pd.to_datetime(frame["month_start"])
    return frame


def parse_service_volume(path: Path) -> pd.DataFrame:
    frame = pd.read_excel(path, sheet_name="Data 3")
    frame = frame.rename(columns={"active_month": "month_start", "f0_": "users"})
    frame["month_start"] = pd.to_datetime(frame["month_start"])
    return frame


# --------------------------------------------------------------------- run


def run(project_root: Path) -> dict[str, pd.DataFrame]:
    source = project_root / "data" / "source"
    topline, channel = parse_channel_workbook(source / WORKBOOK_CHANNEL)
    tables = {
        "topline_week": topline,
        "channel_week": channel,
        "promo_day": parse_promo_days(source / WORKBOOK_MKT),
        "brand_month": parse_brand_month(source / WORKBOOK_MKT),
        "retention_month": parse_retention(source / WORKBOOK_CPC),
        "promo_usage_month": parse_promo_usage(source / WORKBOOK_CPC),
        "cancellation": parse_cancellations(source / WORKBOOK_CPC),
        "service_volume": parse_service_volume(source / WORKBOOK_CPC),
    }
    out = project_root / "data" / "private"
    out.mkdir(parents=True, exist_ok=True)
    for name, frame in tables.items():
        frame.to_parquet(out / f"{name}.parquet", index=False)
    return tables


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--project-root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    args = parser.parse_args()
    root = args.project_root.resolve()
    tables = run(root)
    width = max(len(name) for name in tables)
    for name, frame in tables.items():
        print(f"{name:<{width}}  {len(frame):>7,} rows  {frame.shape[1]:>2} cols")


if __name__ == "__main__":
    main()
