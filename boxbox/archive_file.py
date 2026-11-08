"""Write a decided change into the archive CSVs.

Rows of the races the change covers are taken out, and each new row goes
straight after the last row of the same asset earlier in the season, so a
capture lands beside each asset's previous race. An asset new to the season
goes after the season's last row. Every other line is written back exactly as
it was read.

Both files are written to a scratch folder first, loaded through
``load_archive_data_season`` and checked with the integrity checks. Only then
do they replace the archive's files.
"""

from __future__ import annotations

import csv
import io
import logging
import os
import tempfile
from pathlib import Path

from boxbox.change import ArchiveRow, CaptureRefused, Change
from common import F1_SEASON_CONSTRUCTORS, AssetType
from import_data.import_history import (
    _ARCHIVE_FILES,
    check_drivers_against_constructors,
    check_merged_integrity_constructors,
    check_merged_integrity_drivers,
    load_archive_data_season,
)

logger = logging.getLogger(__name__)


def _number(value: float | None) -> str:
    if value is None:
        return ""
    return str(int(value)) if float(value).is_integer() else repr(float(value))


def _fields(row: ArchiveRow) -> list[str]:
    ids = [row.constructor] if row.driver is None else [row.constructor, row.driver]
    return [str(row.season), str(row.race), *ids, _number(row.points), _number(row.price)]


def _asset(fields: list[str]) -> tuple[str, ...]:
    return tuple(fields[2:-2])


def _place_rows(lines: list[list[str]], season: int, rows_by_race: dict[int, list[ArchiveRow]]) -> list[list[str]]:
    season_text = str(season)
    kept = [f for f in lines if not (f[0] == season_text and int(f[1]) in rows_by_race)]
    for race in sorted(rows_by_race):
        for row in rows_by_race[race]:
            fields = _fields(row)
            same_asset_before = [i for i, f in enumerate(kept)
                                 if f[0] == season_text and _asset(f) == _asset(fields) and int(f[1]) < race]
            in_season = [i for i, f in enumerate(kept) if f[0] == season_text]
            if same_asset_before:
                position = same_asset_before[-1] + 1
            elif in_season:
                position = in_season[-1] + 1
            else:
                position = len(kept)
            kept.insert(position, fields)
    return kept


def _render(header: list[str], lines: list[list[str]]) -> str:
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(lines)
    return out.getvalue()


def _check(folder: str, season: int, num_constructors: int) -> None:
    drivers = load_archive_data_season(AssetType.DRIVER, season, fn=folder)
    constructors = load_archive_data_season(AssetType.CONSTRUCTOR, season, fn=folder)
    check_merged_integrity_drivers(drivers, num_constructors)
    check_merged_integrity_constructors(constructors, num_constructors)
    check_drivers_against_constructors(drivers, constructors)


def write_change(change: Change, fn: str, season_constructors: dict[int, int] = F1_SEASON_CONSTRUCTORS) -> None:
    """Write ``change`` into the archive CSVs in ``fn``, or write nothing.

    Args:
        change: The rows to write.
        fn: Directory holding the archive CSVs.
        season_constructors: Constructors expected per season, for the integrity checks.

    Raises:
        CaptureRefused: If the archive with the change applied fails to load or
            fails the integrity checks; the archive's files are left untouched.
    """
    texts = {}
    for asset_type, rows_by_race in [(AssetType.DRIVER, change.driver_rows),
                                     (AssetType.CONSTRUCTOR, change.constructor_rows)]:
        with open(Path(fn) / _ARCHIVE_FILES[asset_type], newline="") as f:
            header, *lines = list(csv.reader(f))
        texts[asset_type] = _render(header, _place_rows(lines, change.season, rows_by_race))

    with tempfile.TemporaryDirectory(dir=fn) as scratch:
        for asset_type, text in texts.items():
            Path(scratch, _ARCHIVE_FILES[asset_type]).write_text(text)
        try:
            _check(scratch, change.season, season_constructors[change.season])
        except (ValueError, KeyError) as exc:
            message = f"The archive with this change fails its integrity checks, so nothing was written: {exc}"
            logger.error(message)
            raise CaptureRefused(message) from exc
        for asset_type in texts:
            os.replace(Path(scratch, _ARCHIVE_FILES[asset_type]), Path(fn) / _ARCHIVE_FILES[asset_type])
    logger.info(f"Wrote season {change.season} races {sorted(change.driver_rows)} to {fn}")
