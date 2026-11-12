"""Capture fantasy points and prices from BoxBox F1 Fantasy into the archive CSVs.

Run a few days after a race weekend::

    PYTHONPATH=. venv/bin/python -m boxbox.cli

It downloads BoxBox's two files, saves a copy under ``outputs/boxbox/``, and
either fills the race just held's points and prices the next race, or, before
a race is held, corrects its line-up and prices. It prints each asset's
previous and new values, and refuses with exit 1, writing nothing, when the
data is not updated yet or does not add up. Review the CSVs' git diff before
committing. ``--from-copy`` re-runs on a saved copy; ``--dry-run`` writes
nothing. See ``docs/data_capture_v2/plan.md``, *How a run works*.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Callable, Sequence
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from boxbox.archive_file import write_change
from boxbox.change import CAPTURE, ArchiveRow, CaptureRefused, Change, decide_change
from boxbox.source import (
    DEFAULT_COPY_DIR,
    DRIVER_HISTORY,
    SEASON_SUMMARY,
    BoxBoxData,
    BoxBoxDataError,
    download_files,
    parse_files,
    save_copy,
)
from common import F1_SEASON_CONSTRUCTORS, AssetType, setup_logging
from import_data.import_history import _DIR_ARCHIVE_INPUTS, read_archive_file

logger = logging.getLogger(__name__)

# The last race of each season whose values came from the hand-kept workbook. A
# correction never rewrites these; they are changed by hand if they must change.
# Earlier seasons need no entry: BoxBox serves only the current season.
WORKBOOK_LAST_RACE = {2026: 20}


def parse_arguments(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture fantasy points and prices from BoxBox F1 Fantasy")
    parser.add_argument("--archive-dir", default=_DIR_ARCHIVE_INPUTS, help="directory holding the archive CSVs")
    parser.add_argument("--copy-dir", default=DEFAULT_COPY_DIR, help="where each download is saved")
    parser.add_argument("--from-copy", help="read a saved copy's folder instead of downloading")
    parser.add_argument("--dry-run", action="store_true", help="show the change but write nothing")
    return parser.parse_args(argv)


def _read_copy(folder: Path) -> dict[str, bytes]:
    return {name: (folder / f"{name}.json").read_bytes() for name in (DRIVER_HISTORY, SEASON_SUMMARY)}


def _label(row: ArchiveRow) -> str:
    return f"{row.driver}@{row.constructor}" if row.driver is not None else row.constructor


def _held(drivers: pd.DataFrame, constructors: pd.DataFrame, season: int, race: int) -> dict[str, float]:
    """Each asset's archived price for ``race``, keyed by its label."""
    prices = {}
    for df, is_driver in [(drivers, True), (constructors, False)]:
        for r in df[(df["Season"] == season) & (df["Race"] == race)].itertuples(index=False):
            prices[f"{r.Driver}@{r.Constructor}" if is_driver else r.Constructor] = float(r.Price)
    return prices


def _price_lines(rows: list[ArchiveRow], before: dict[str, float]) -> list[str]:
    """One line per asset: old price, new price and the change, in columns to check against the app."""
    lines = [f"    {'':<10} {'old':>6}    {'new':>6}  {'change':>6}"]
    for row in rows:
        old = before.get(_label(row))
        if old is None:
            lines.append(f"    {_label(row):<10} {'new':>6} -> {row.price:>6.1f}")
        else:
            lines.append(f"    {_label(row):<10} {old:>6.1f} -> {row.price:>6.1f}  {row.price - old:>+6.1f}")
    labels = {_label(row) for row in rows}
    lines += [f"    {label:<10} {before[label]:>6.1f} -> dropped" for label in before if label not in labels]
    return lines


def describe(change: Change, drivers: pd.DataFrame, constructors: pd.DataFrame, data: BoxBoxData) -> list[str]:
    """The lines reporting a change: each asset's previous and new values, then any warnings."""
    target = change.target_race
    rows = {race: change.driver_rows.get(race, []) + change.constructor_rows.get(race, [])
            for race in sorted(change.driver_rows)}
    lines = [f"BoxBox data generated {data.generated_at}",
             f"Season {change.season}, race {target}: {change.mode}"]
    if change.mode == CAPTURE:
        lines.append(f"  Race {target} points:")
        lines += [f"    {_label(row):<10} {row.points:g}" for row in rows[target]]
        if target + 1 in rows:
            lines.append(f"  Race {target + 1} prices, against race {target}'s:")
            lines += _price_lines(rows[target + 1], _held(drivers, constructors, change.season, target))
        else:
            lines.append("  No race follows: the season's last race")
    else:
        lines.append(f"  Race {target} prices, against those captured:")
        lines += _price_lines(rows[target], _held(drivers, constructors, change.season, target))
    lines += [f"WARNING: {warning}" for warning in change.warnings]
    return lines


def capture(archive_dir: str, copy_dir: str, fetch: Callable[[str], bytes] | None = None,
            season_constructors: dict[int, int] | None = None, from_copy: str | None = None,
            dry_run: bool = False) -> Change:
    """Run one capture, printing what it does, and return the change written.

    Args:
        archive_dir: The directory holding the archive CSVs.
        copy_dir: Where a download is saved.
        fetch: Returns a URL's body; defaults to an HTTP GET.
        season_constructors: Constructors per season, for the integrity checks.
        from_copy: A saved copy's folder to read instead of downloading.
        dry_run: Show the change but write nothing.

    Raises:
        CaptureRefused: If the change is doubtful; `CaptureNotYet` if BoxBox is not updated yet.
        BoxBoxDataError: If BoxBox's files are not as expected.
        OSError: If a download, read or write fails.
    """
    if from_copy:
        raw = _read_copy(Path(from_copy))
        print(f"Read the saved copy in {from_copy}")
    else:
        raw = download_files(fetch)
        print(f"Saved a copy to {save_copy(raw, copy_dir, datetime.now(timezone.utc))}")
    data = parse_files(raw)
    drivers = read_archive_file(AssetType.DRIVER, archive_dir)
    constructors = read_archive_file(AssetType.CONSTRUCTOR, archive_dir)
    change = decide_change(drivers, constructors, data, WORKBOOK_LAST_RACE)
    print("\n".join(describe(change, drivers, constructors, data)))
    if dry_run:
        print("Dry run: nothing written.")
        return change
    write_change(change, archive_dir, season_constructors or F1_SEASON_CONSTRUCTORS)
    print(f"Wrote to {archive_dir}. Review the CSVs' git diff before committing.")
    return change


def main(argv: Sequence[str] | None = None, fetch: Callable[[str], bytes] | None = None,
         season_constructors: dict[int, int] | None = None) -> int:
    """Run one capture. Returns the exit code: 0 written (or dry run), 1 refused or failed."""
    args = parse_arguments(argv)
    try:
        capture(args.archive_dir, args.copy_dir, fetch, season_constructors, args.from_copy, args.dry_run)
    except (CaptureRefused, BoxBoxDataError, OSError) as exc:
        logger.error(f"Nothing written: {exc}")
        print(f"Nothing written: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    setup_logging()
    sys.exit(main())
