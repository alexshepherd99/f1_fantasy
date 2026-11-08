"""Decide what a run writes to the archive, or refuse.

The target race is the latest race of BoxBox's season in the archive. If
BoxBox shows it held, the run *captures*: it fills the target's empty points
from BoxBox's results and adds the next race at BoxBox's current prices. If
not, the run *corrects*: it rewrites the target's line-up and prices from the
current prices, which is how a driver change after capture is put right.

A run refuses (``CaptureRefused``) rather than write anything doubtful. It
does not write files; it returns a ``Change`` holding complete replacement
rows for each race it touches.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import pandas as pd

from boxbox.mapping import constructor_code, driver_code, results_by_driver_code, round_for_race
from boxbox.source import BoxBoxData

logger = logging.getLogger(__name__)

CAPTURE = "capture"
CORRECT = "correct"


class CaptureRefused(Exception):
    """The run cannot write safely; nothing is written."""


@dataclass(frozen=True)
class ArchiveRow:
    """One row of an archive CSV. ``driver`` is None for a constructor row."""

    season: int
    race: int
    constructor: str
    driver: str | None
    points: float | None
    price: float


@dataclass(frozen=True)
class Change:
    """Complete replacement rows for each race the run writes, per asset type."""

    mode: str
    season: int
    target_race: int
    driver_rows: dict[int, list[ArchiveRow]]
    constructor_rows: dict[int, list[ArchiveRow]]
    warnings: list[str] = field(default_factory=list)


def _refuse(message: str) -> None:
    logger.error(message)
    raise CaptureRefused(message)


def _rows(df: pd.DataFrame, is_driver: bool) -> list[ArchiveRow]:
    return [
        ArchiveRow(
            season=int(r.Season), race=int(r.Race), constructor=r.Constructor,
            driver=r.Driver if is_driver else None,
            points=None if pd.isna(r.Points) else float(r.Points), price=float(r.Price),
        )
        for r in df.itertuples(index=False)
    ]


def _key(row: ArchiveRow) -> str:
    return row.driver if row.driver is not None else row.constructor


def _boxbox_results(data: BoxBoxData) -> tuple[dict[str, dict[int, float]], dict[str, dict[int, float]]]:
    drivers = results_by_driver_code(data)
    constructors = {constructor_code(slug): by_round for slug, by_round in data.constructor_results.items()}
    return drivers, constructors


def _current_prices(data: BoxBoxData, season: int, race: int) -> tuple[list[ArchiveRow], list[ArchiveRow]]:
    drivers = [
        ArchiveRow(season, race, constructor_code(slug), driver_code(key), None, price)
        for key, (slug, price) in data.driver_prices.items()
    ]
    constructors = [
        ArchiveRow(season, race, constructor_code(slug), None, None, price)
        for slug, price in data.constructor_prices.items()
    ]
    return drivers, constructors


def _in_season_order(new_rows: list[ArchiveRow], season_rows: list[ArchiveRow]) -> list[ArchiveRow]:
    """Assets already in the season first, in their file order; new assets after, as given."""
    order = {}
    for row in season_rows:
        order.setdefault(_key(row), len(order))
    return sorted(new_rows, key=lambda row: order.get(_key(row), len(order)))


def _earlier_differences(
    season_rows: list[ArchiveRow], results: dict[str, dict[int, float]], data: BoxBoxData, before_race: int
) -> list[str]:
    warnings = []
    for row in season_rows:
        if row.race >= before_race or row.points is None:
            continue
        boxbox = results.get(_key(row), {}).get(round_for_race(data, row.race))
        if boxbox != row.points:
            warnings.append(
                f"{_key(row)} race {row.race}: archive has {row.points:g}, BoxBox has "
                f"{'no result' if boxbox is None else f'{boxbox:g}'}; the archive is kept"
            )
    return warnings


def _fill_points(target: list[ArchiveRow], results: dict[str, dict[int, float]], round_number: int,
                 race: int, what: str) -> list[ArchiveRow]:
    in_race = {_key(row) for row in target}
    with_result = {key for key, by_round in results.items() if round_number in by_round}
    if in_race != with_result:
        _refuse(
            f"The {what} captured for race {race} differ from those BoxBox has results for: "
            f"no BoxBox result for {sorted(in_race - with_result)}, "
            f"BoxBox result but no row for {sorted(with_result - in_race)}. Fix the race's rows by hand."
        )
    return [
        ArchiveRow(row.season, row.race, row.constructor, row.driver, results[_key(row)][round_number], row.price)
        for row in target
    ]


def decide_change(
    drivers: pd.DataFrame, constructors: pd.DataFrame, data: BoxBoxData, golden_last_race: dict[int, int]
) -> Change:
    """Decide the rows to write for BoxBox's season, or refuse.

    Args:
        drivers: The driver archive as stored (``read_archive_file``).
        constructors: The constructor archive as stored.
        data: BoxBox's parsed files.
        golden_last_race: Per season, the last race whose values came from the
            workbook; a correction never rewrites those.

    Returns:
        The change, with a warning for each earlier race of the season whose
        points BoxBox disagrees with. The archive's values are kept.

    Raises:
        CaptureRefused: As set out in ``plan.md``, *How a run works*.
    """
    season = data.season
    season_drivers = _rows(drivers[drivers["Season"] == season], True)
    season_constructors = _rows(constructors[constructors["Season"] == season], False)
    if not season_drivers or not season_constructors:
        _refuse(f"Season {season} is not in the archive; starting a new season is not built yet")

    target = max(row.race for row in season_drivers)
    if target != max(row.race for row in season_constructors):
        _refuse(f"Drivers and constructors end at different races in season {season}")

    target_round = round_for_race(data, target)
    for race in range(1, target):
        if not data.rounds[race - 1].has_actual:
            _refuse(f"BoxBox shows round {data.rounds[race - 1].number} (race {race}) not held, "
                    f"but the archive goes on to race {target}")

    target_drivers = [row for row in season_drivers if row.race == target]
    target_constructors = [row for row in season_constructors if row.race == target]
    if any(row.points is not None for row in target_drivers + target_constructors):
        _refuse(f"Race {target} already has points: there is nothing waiting to be captured")

    driver_results, constructor_results = _boxbox_results(data)
    warnings = (_earlier_differences(season_drivers, driver_results, data, target)
                + _earlier_differences(season_constructors, constructor_results, data, target))

    if not data.rounds[target - 1].has_actual:
        if target <= golden_last_race.get(season, 0):
            _refuse(f"BoxBox does not show race {target} (round {target_round}) held yet, so there are no "
                    f"results to capture: run again once it does. A correction is not possible either, as race "
                    f"{target} of {season} came from the workbook; change it by hand if it must change")
        new_drivers, new_constructors = _current_prices(data, season, target)
        return Change(
            mode=CORRECT, season=season, target_race=target,
            driver_rows={target: _in_season_order(new_drivers, season_drivers)},
            constructor_rows={target: _in_season_order(new_constructors, season_constructors)},
            warnings=warnings,
        )

    driver_rows = {target: _fill_points(target_drivers, driver_results, target_round, target, "drivers")}
    constructor_rows = {target: _fill_points(target_constructors, constructor_results, target_round, target,
                                             "constructors")}

    if target < len(data.rounds):
        next_drivers, next_constructors = _current_prices(data, season, target + 1)
        # Only assets priced in both races count: a newly listed driver is not evidence of an update
        held_prices = {_key(row): row.price for row in target_drivers + target_constructors}
        moved = [row for row in next_drivers + next_constructors
                 if _key(row) in held_prices and held_prices[_key(row)] != row.price]
        if not moved:
            _refuse(f"BoxBox has race {target}'s results but no price has moved since: "
                    "its prices are not updated yet. Run again later")
        driver_rows[target + 1] = _in_season_order(next_drivers, season_drivers)
        constructor_rows[target + 1] = _in_season_order(next_constructors, season_constructors)

    return Change(mode=CAPTURE, season=season, target_race=target, driver_rows=driver_rows,
                  constructor_rows=constructor_rows, warnings=warnings)
