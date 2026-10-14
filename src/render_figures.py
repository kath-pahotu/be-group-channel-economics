"""Render the figures, from the INDEXED data only.

These charts are published, so they are built from data/published/ and never
from the warehouse. Levels on the axes are index points, not currency, and
every chart says so on its face - a reader should not have to find the README
to know that.

    promotion_headroom   the commission increase, and the pace at which
                         promotion spent what it created
    channel_efficiency   share of acquisition against share of budget
    channel_payback      months to repay acquisition cost, by channel

Run:
    python src/render_figures.py --project-root .
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

NAVY, BLUE, CYAN, ORANGE, GOLD, MUTED = (
    "#0b2545", "#1268d5", "#22b7c8", "#f47c48", "#e3a82b", "#64748b"
)
GRID = "#d6e4f0"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.edgecolor": GRID, "axes.labelcolor": NAVY, "axes.titlecolor": NAVY,
    "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.spines.top": False, "axes.spines.right": False,
    "figure.facecolor": "white", "axes.facecolor": "white",
})

INDEX_NOTE = ("All values are indexed. Levels are not real figures and cannot be "
              "recovered; shares, ratios and rates of change are unchanged.")


def stamp(fig) -> None:
    fig.text(0.0, -0.045, INDEX_NOTE, fontsize=8, color=MUTED, ha="left")


def save(fig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    stamp(fig)
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  {path.name:<30} {path.stat().st_size / 1024:>5.0f} KB")


def promotion_headroom(published: Path, out: Path) -> None:
    frame = pd.read_parquet(published / "mart_promo_unit_economics.parquet")
    frame = frame.sort_values("day").reset_index(drop=True)
    x = np.arange(len(frame))
    change = int((frame["period"] == "after commission increase").argmax())

    fig, ax = plt.subplots(figsize=(9.6, 5.8))
    ax.axvspan(-0.5, change - 0.5, color="#fdf0e6", zorder=0)
    ax.axvspan(change - 0.5, len(frame) - 0.5, color="#e6f7f0", zorder=0)

    ax.plot(x, frame["commission_rate_index"], marker="o", color=BLUE,
            linewidth=2.2, label="Commission rate")
    ax.plot(x, frame["promo_rate_index"], marker="o", color=ORANGE,
            linewidth=2.2, label="Promotion spend")
    ax.plot(x, frame["contribution_margin_rate_index"], marker="o", color=NAVY,
            linewidth=2.6, label="Contribution margin")

    ax.axhline(0, color=NAVY, linewidth=1.1, linestyle="-")
    ax.axvline(change - 0.5, color=MUTED, linewidth=1.3, linestyle="--")

    # Headroom is set before the annotations so the legend (upper left) and the
    # event label never land on the same space.
    low, high = ax.get_ylim()
    ax.set_ylim(low, high * 1.18)
    ax.text(change - 0.75, high * 0.88, "commission rate raised  ",
            fontsize=9.4, color=NAVY, fontweight="bold", va="center", ha="right")
    ax.annotate("", xy=(change - 0.5, high * 0.88), xytext=(change - 0.78, high * 0.88),
                arrowprops=dict(arrowstyle="->", color=NAVY, linewidth=1.2))

    ax.text(change / 2 - 0.5, low * 0.72,
            "every observed day\nloss-making", fontsize=9, color=ORANGE,
            ha="center", fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels([str(d)[5:10] for d in frame["day"]], fontsize=8, rotation=45)
    ax.set_ylabel("Index points  (% of revenue, scaled)")
    ax.set_title("The increase created about five points of headroom.\n"
                 "Promotion consumed three and a half of them in four days.",
                 loc="left", fontsize=12.5, pad=14)
    ax.legend(frameon=False, fontsize=9.4, ncol=3, loc="upper left")
    ax.grid(axis="y", color=GRID, linewidth=0.7)
    ax.set_axisbelow(True)
    save(fig, out / "promotion_headroom.png")


def channel_efficiency(published: Path, out: Path) -> None:
    frame = pd.read_parquet(published / "mart_channel_week_pnl.parquet")
    paid = frame[frame["channel_role"] == "paid channel"]
    agg = paid.groupby("channel")[["first_trip_users_index", "budget_first_trip_index"]].sum()
    agg["pct_users"] = 100 * agg["first_trip_users_index"] / agg["first_trip_users_index"].sum()
    agg["pct_budget"] = 100 * agg["budget_first_trip_index"] / agg["budget_first_trip_index"].sum()
    agg = agg.sort_values("pct_users", ascending=True)

    fig, ax = plt.subplots(figsize=(9.4, 5.4))
    y = np.arange(len(agg))
    ax.barh(y - 0.19, agg["pct_users"], height=0.36, color=BLUE,
            label="Share of first-trip users")
    ax.barh(y + 0.19, agg["pct_budget"], height=0.36, color=CYAN,
            label="Share of budget")
    for index, row in enumerate(agg.itertuples()):
        ax.text(row.pct_users + 0.8, index - 0.19, f"{row.pct_users:.1f}%",
                va="center", fontsize=8.6, color=NAVY)
        ax.text(row.pct_budget + 0.8, index + 0.19, f"{row.pct_budget:.1f}%",
                va="center", fontsize=8.6, color=MUTED)
    ax.set_yticks(y)
    ax.set_yticklabels(agg.index, fontsize=9.4)
    ax.set_xlabel("Share of the paid total  (%)")
    ax.set_title("One channel delivers two thirds of acquisition on 42% of the budget\n"
                 "Which is either the best channel on the market, or attribution capture",
                 loc="left", fontsize=12.5, pad=14)
    ax.legend(frameon=False, fontsize=9.4, loc="lower right")
    ax.grid(axis="x", color=GRID, linewidth=0.7)
    ax.set_axisbelow(True)
    save(fig, out / "channel_efficiency.png")


def channel_payback(published: Path, out: Path) -> None:
    frame = pd.read_parquet(published / "mart_channel_payback.parquet")
    frame = frame[frame["payback_months_with_churn"] > 0].sort_values(
        "payback_months_with_churn"
    )

    fig, ax = plt.subplots(figsize=(9.4, 4.8))
    colours = [BLUE if v < 7 else ORANGE for v in frame["payback_months_with_churn"]]
    ax.barh(frame["channel"], frame["payback_months_with_churn"], color=colours, height=0.6)
    for index, row in enumerate(frame.itertuples()):
        ax.text(row.payback_months_with_churn + 0.12, index,
                f"{row.payback_months_with_churn:.1f} months", va="center",
                fontsize=9, color=NAVY)
    ax.set_xlabel("Months to repay acquisition cost, at observed M1 retention")
    ax.set_title("Payback by channel — a model, not a measurement\n"
                 "Trips per month is a placeholder, and it is the only input that "
                 "changes this ranking",
                 loc="left", fontsize=12.5, pad=14)
    ax.set_xlim(0, frame["payback_months_with_churn"].max() * 1.22)
    ax.grid(axis="x", color=GRID, linewidth=0.7)
    ax.set_axisbelow(True)
    save(fig, out / "channel_payback.png")


def run(project_root: Path) -> None:
    published = project_root / "data" / "published"
    out = project_root / "artifacts" / "figures"
    promotion_headroom(published, out)
    channel_efficiency(published, out)
    channel_payback(published, out)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--project-root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    args = parser.parse_args()
    run(args.project_root.resolve())


if __name__ == "__main__":
    main()
