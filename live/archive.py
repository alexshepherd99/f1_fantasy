"""What the archive says about the season's races: which is next, and which have points.

Read from the raw driver file (`read_archive_file`), as the season loader turns a
race's empty points into 0.
"""

from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def next_race(drivers: pd.DataFrame) -> tuple[int, int]:
    """The race to pick for: the first race of the archive's latest season with prices and no points (D15).

    Args:
        drivers: The driver archive as `read_archive_file` gives it.

    Returns:
        The season and race.

    Raises:
        ValueError: If every race of the latest season has points.
    """
    season = int(drivers["Season"].max())
    rows = drivers[drivers["Season"] == season]
    scored = rows.groupby("Race")["Points"].apply(lambda points: points.notna().any())
    unscored = sorted(int(race) for race, has_points in scored.items() if not has_points)
    if not unscored:
        message = f"Every race of season {season} in the archive has points: there is no priced race to pick for"
        logger.error(message)
        raise ValueError(message)
    return season, unscored[0]


def race_scored(drivers: pd.DataFrame, season: int, race: int) -> bool:
    """Whether the archive holds points for the race."""
    rows = drivers[(drivers["Season"] == season) & (drivers["Race"] == race)]
    return bool(rows["Points"].notna().any())
