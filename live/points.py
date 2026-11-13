"""Calculate a played team's points from the archive's points for the race (D24)."""

from __future__ import annotations

import logging

from live.team_file import AUTOPILOT, EXTRA_DRS, FINAL_FIX, TeamRow
from races.season import Race

logger = logging.getLogger(__name__)


def calculate_points(row: TeamRow, race: Race, final_fix: tuple[str, str] | None = None) -> int:
    """The points the archive gives the team in `row` for `race`, with its chip modelled.

    Every driver and constructor scores their points, and the DRS driver's count twice.
    Extra DRS makes it three times; Autopilot gives DRS to the team's highest-scoring
    driver. Final Fix swaps one driver for another and, if the one swapped out held DRS,
    gives DRS to the one swapped in. No Negative works per scoring category, which the
    archive does not hold, so it is left out; the app's figure has to be entered for it.

    Args:
        row: The team played.
        race: The race, with its points.
        final_fix: For a Final Fix race, the driver swapped out and the driver swapped in.

    Raises:
        ValueError: If `final_fix` is given for a race without the chip or missing for one
            with it, or does not swap a driver of the team for one outside it.
    """
    drivers, drs = list(row.drivers), row.drs
    if (final_fix is not None) != (row.chip == FINAL_FIX):
        _fail(f"Race {row.race}: a Final Fix swap is given if and only if the chip is Final Fix")
    if final_fix is not None:
        out, swapped_in = final_fix
        if out not in drivers:
            _fail(f"Race {row.race}: Final Fix swaps out {out}, who is not in the team")
        if swapped_in in drivers or swapped_in not in race.drivers:
            _fail(f"Race {row.race}: Final Fix swaps in {swapped_in}, who is in the team or not in the race")
        drivers[drivers.index(out)] = swapped_in
        if drs == out:
            drs = swapped_in

    if row.chip == AUTOPILOT:
        drs = max(drivers, key=lambda d: race.drivers[d].points)
    drs_extra = 2 if row.chip == EXTRA_DRS else 1

    points = sum(race.drivers[d].points for d in drivers) + sum(race.constructors[c].points for c in row.constructors)
    return points + drs_extra * race.drivers[drs].points


def _fail(message: str) -> None:
    logger.error(message)
    raise ValueError(message)
