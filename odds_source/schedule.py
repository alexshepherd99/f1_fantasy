"""Place a saved odds page in the season: which race, and which snapshot column.

Both come from the page and FastF1's event schedule rather than the clock, so a
rerun of the same page always gives the same answer.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

import pandas as pd

from odds_source.page import SavedOddsPage

logger = logging.getLogger(__name__)

PRE_FP1_COLUMN = "Odds_PreFP1"
# Snapshot column for each session FastF1 names, in weekend order
SESSION_COLUMNS = {
    "Practice 1": "Odds_FP1",
    "Practice 2": "Odds_FP2",
    "Practice 3": "Odds_FP3",
    "Sprint Qualifying": "Odds_SQ",
    "Sprint": "Odds_Sprint",
    "Qualifying": "Odds_Q",
}
SNAPSHOT_COLUMNS = (PRE_FP1_COLUMN, *SESSION_COLUMNS.values())

_RACE_SESSION = "Race"
_SESSION_SLOTS = range(1, 6)
# Oddschecker's start time for a race need not be FastF1's: Brazil 2026 was
# three hours apart. Race weekends are a week or more apart, so this cannot
# pick the wrong race.
_RACE_MATCH_TOLERANCE = timedelta(hours=12)
# A session counts as done this long after its scheduled start
_SESSION_DONE_AFTER = timedelta(hours=1)


@dataclass(frozen=True)
class CapturePoint:
    """Where a page's odds belong: the race, and the snapshot column to fill."""

    season: int
    race: int
    column: str


def _fail(msg: str) -> None:
    logger.error(msg)
    raise ValueError(msg)


def _sessions(event: pd.Series) -> list[tuple[str, datetime]]:
    """An event's sessions in schedule order, with their starts as aware UTC times."""
    sessions = []
    for slot in _SESSION_SLOTS:
        name = event.get(f"Session{slot}")
        start = event.get(f"Session{slot}DateUtc")
        if isinstance(name, str) and name and not pd.isna(start):
            sessions.append((name, pd.Timestamp(start).tz_localize("UTC").to_pydatetime()))
    return sessions


def _race_start(event: pd.Series) -> datetime | None:
    return next((start for name, start in _sessions(event) if name == _RACE_SESSION), None)


def find_capture_point(page: SavedOddsPage, schedule: pd.DataFrame) -> CapturePoint:
    """Find the race a saved page prices, and the column its odds go in.

    The race is the one whose start is within 12 hours of the page's. The column
    is that of the last session to have started an hour or more before the page
    was saved, or ``Odds_PreFP1`` when none has.

    Raises:
        ValueError: No race starts near the page's, the page was saved after the
            race started, or the weekend holds a session with no column.
    """
    matches = [
        (event, start)
        for _, event in schedule.iterrows()
        if (start := _race_start(event)) is not None
        and abs(start - page.race_start) <= _RACE_MATCH_TOLERANCE
    ]
    if len(matches) != 1:
        _fail(f"No race in the schedule starts near {page.race_start} ({page.race_name})")
    event, race_start = matches[0]

    if page.saved_at >= race_start:
        _fail(f"Page for {page.race_name} was saved at {page.saved_at}, after the race started at {race_start}")

    weekend = [(name, start) for name, start in _sessions(event) if name != _RACE_SESSION]
    unknown = [name for name, _ in weekend if name not in SESSION_COLUMNS]
    if unknown:
        _fail(f"No odds column for session {', '.join(unknown)} at {page.race_name}")

    column = PRE_FP1_COLUMN
    for name, start in weekend:
        if start + _SESSION_DONE_AFTER <= page.saved_at:
            column = SESSION_COLUMNS[name]
    return CapturePoint(season=race_start.year, race=int(event["RoundNumber"]), column=column)
