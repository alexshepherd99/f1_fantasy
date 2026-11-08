"""Write one race's captured odds into the betting odds CSV.

The file is read and written as text with the ``csv`` module, never through
pandas, so a row this run does not touch is written back exactly as it was.
"""

from __future__ import annotations

import csv
import logging
import os
from pathlib import Path

from odds_source.drivers import OddsEntry
from odds_source.schedule import SNAPSHOT_COLUMNS, CapturePoint

logger = logging.getLogger(__name__)


def _read(path: Path) -> tuple[list[str], list[list[str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    return rows[0], rows[1:]


def _write(path: Path, header: list[str], body: list[list[str]]) -> None:
    """Write through a temporary file, so a failure part way leaves the file whole."""
    temporary = path.with_name(f".{path.name}.tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(body)
    os.replace(temporary, path)


def write_race_odds(path: Path | str, point: CapturePoint, entries: list[OddsEntry]) -> None:
    """Put a capture run's odds into the odds file for one race.

    Each priced driver's ``Odds`` and ``point.column`` are set, overwriting what
    was there (D8, D9); nothing else in an existing row changes, so a constructor
    fixed by hand stays fixed. A driver already in the file for the race but not priced
    by this run keeps the row, with both blanked. A new driver is added after the
    race's rows, and a race with no rows goes after the races before it. Any
    snapshot column the file lacks is added, all at once, after the existing
    columns.
    """
    path = Path(path)
    header, body = _read(path)
    header = header + [column for column in SNAPSHOT_COLUMNS if column not in header]
    body = [row + [""] * (len(header) - len(row)) for row in body]
    at = {name: i for i, name in enumerate(header)}
    key = (point.season, point.race)

    def race_of(row: list[str]) -> tuple[int, int]:
        return int(row[at["Season"]]), int(row[at["Race"]])

    by_driver = {entry.driver: entry for entry in entries}
    written = set()
    race_rows = [i for i, row in enumerate(body) if race_of(row) == key]
    for i in race_rows:
        row = body[i]
        entry = by_driver.get(row[at["Driver"]])
        if entry is None:
            row[at["Odds"]] = row[at[point.column]] = ""
            continue
        row[at["Odds"]] = row[at[point.column]] = entry.odds
        written.add(entry.driver)

    new_rows = []
    for entry in entries:
        if entry.driver in written:
            continue
        row = [""] * len(header)
        row[at["Driver"]], row[at["Constructor"]] = entry.driver, entry.constructor
        row[at["Season"]], row[at["Race"]] = str(point.season), str(point.race)
        row[at["Odds"]] = row[at[point.column]] = entry.odds
        new_rows.append(row)

    if race_rows:
        insert_at = race_rows[-1] + 1
    else:
        insert_at = next((i for i, row in enumerate(body) if race_of(row) > key), len(body))
    body[insert_at:insert_at] = new_rows

    _write(path, header, body)
    logger.info(
        "Wrote %s odds for season %s race %s into %s (%s new rows)",
        point.column, point.season, point.race, path, len(new_rows),
    )
