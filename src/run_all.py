"""Rebuild everything from the source workbooks in one command.

    python src/run_all.py --project-root .

Three stages, in dependency order. They are separate files rather than one
script so that a failure names the stage it happened in, and so a single stage
can be re-run without redoing the ones before it.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_marts  # noqa: E402
import parse_source  # noqa: E402
import publish_indexed  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--project-root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    args = parser.parse_args()
    root = args.project_root.resolve()

    missing = [
        name
        for name in (
            parse_source.WORKBOOK_CHANNEL,
            parse_source.WORKBOOK_MKT,
            parse_source.WORKBOOK_CPC,
        )
        if not (root / "data" / "source" / name).exists()
    ]
    if missing:
        raise SystemExit(
            "Missing source workbooks in data/source/:\n  "
            + "\n  ".join(missing)
            + "\n\nThese are BE Group's own files and are deliberately not in the\n"
            "repository. The indexed outputs in data/published/ were built from\n"
            "them and are committed."
        )

    print("1/3  parsing source workbooks")
    tables = parse_source.run(root)
    print(f"     {len(tables)} tidy tables, {sum(len(f) for f in tables.values()):,} rows")

    print("2/3  building marts and checks")
    counts = build_marts.run(root)
    print(f"     {len(counts)} tables, {sum(counts.values()):,} rows")

    print("3/3  publishing indexed outputs")
    published = publish_indexed.run(root)
    print(f"     {len(published)} tables written to data/published/")

    print("\ndone.")


if __name__ == "__main__":
    main()
