from __future__ import annotations

import logging
from typing import Any, Iterable, Tuple

import fastf1
import pandas as pd

from fast_f1.weekend import determine_practice_sessions

logger = logging.getLogger(__name__)

# Session codes that might be available on any weekend
_KNOWN_SESSION_CODES = ["FP1", "FP2", "FP3", "SQ", "SS", "Q", "R"]
# Friendly names for known session codes
_SESSION_CODE_NAMES = {
    "FP1": "FP1",
    "FP2": "FP2",
    "FP3": "FP3",
    "SQ": "SprintQualifying",  # Sprint Qualifying session
    "SS": "Sprint",             # Sprint race (may not exist in all sprint weekends)
    "Q": "Qualifying",
    "R": "Race",
}


def _get_event_for_race(season_year: int, race_num: int) -> Any:
    schedule = fastf1.get_event_schedule(season_year, include_testing=False)
    event_rows = schedule[schedule["RoundNumber"] == race_num]
    if event_rows.empty:
        raise ValueError(f"No event found for season {season_year}, race {race_num}")
    return event_rows.iloc[0]


def get_race_results(season_year: int, race_num: int) -> pd.DataFrame:
    """Return race results for a given season and race.

    The returned dataframe includes the driver abbreviation, status, position,
    classified position, grid position, points, and the season/race metadata.
    """
    try:
        event = _get_event_for_race(season_year, race_num)
        race = event.get_session("R")
        race.load()
        results = race.results
        results = results[
            [
                "Abbreviation",
                "Status",
                "Position",
                "ClassifiedPosition",
                "GridPosition",
                "Points",
            ]
        ].copy()
        results["Season"] = season_year
        results["Race"] = race_num
        return results
    except (fastf1.SessionNotAvailableError, ValueError) as exc:
        logger.warning(
            "Could not load race results for season %s race %s: %s",
            season_year,
            race_num,
            exc,
        )
        return pd.DataFrame(
            columns=[
                "Season",
                "Race",
                "Abbreviation",
                "Status",
                "Position",
                "ClassifiedPosition",
                "GridPosition",
                "Points",
            ]
        )


def get_session_laps(season_year: int, race_num: int, session_type: str) -> pd.DataFrame:
    """Return session laps for a given season, race, and session."""
    try:
        event = _get_event_for_race(season_year, race_num)
        session = event.get_session(session_type)
        session.load()
        session_laps = session.laps
    except (fastf1.SessionNotAvailableError, ValueError) as exc:
        logger.warning(
            "Could not load session laps for season %s race %s session %s: %s",
            season_year,
            race_num,
            session_type,
            exc,
        )
        return pd.DataFrame(columns=["Season", "Race", "SessionType"])

    session_laps = session_laps[
        [
            "Driver",
            "LapTime",
            "LapNumber",
            "Stint",
            "PitOutTime",
            "PitInTime",
            "Compound",
            "TyreLife",
            "FreshTyre",
        ]
    ].copy()
    session_laps["Season"] = season_year
    session_laps["Race"] = race_num
    session_laps["SessionType"] = session_type
    return session_laps


def get_available_sessions_from_event(event: Any) -> list[str]:
    """Extract available session type names from a FastF1 Event object.

    This function attempts to load each known session code (FP1, FP2, FP3, SQ, SS, Q, R)
    and builds a list of friendly session names that are actually available for the event.

    Args:
        event: A FastF1 Event object from the schedule.

    Returns:
        A list of session type names (e.g., ["FP1", "FP2", "FP3", "Qualifying", "Race"]
        or ["FP1", "SprintQualifying", "Sprint", "Race"] for sprint weekends).

    Raises:
        AttributeError: If the event object does not have a ``get_session`` method.
    """
    if not hasattr(event, "get_session"):
        msg = f"Event object does not have a 'get_session' method: {type(event)}"
        logger.error(msg)
        raise AttributeError(msg)

    available_sessions = []
    for code in _KNOWN_SESSION_CODES:
        try:
            session = event.get_session(code)
            friendly_name = _SESSION_CODE_NAMES.get(code, code)
            available_sessions.append(friendly_name)
            logger.debug(f"Session {code} ({friendly_name}) is available")
        except Exception as exc:
            # Catch all exceptions from get_session - could be ValueError, SessionNotAvailableError, etc.
            logger.debug(f"Session {code} is not available: {type(exc).__name__}")

    logger.info(f"Available sessions for event: {available_sessions}")
    return available_sessions


def select_practice_sessions_from_event(event: Any) -> Tuple[str, str]:
    """Return the pair of practice/session names to use for metric calculations.

    Extracts available sessions from the FastF1 Event object and determines
    which pair to use based on weekend format (normal vs sprint).

    Args:
        event: A FastF1 Event object from the schedule.

    Returns:
        A tuple of two session type names (e.g., ("FP2", "FP3") or ("FP1", "SprintQualifying")).

    Raises:
        RuntimeError: If required sessions are missing from the event.
        AttributeError: If the event object structure is unexpected.
    """
    available_sessions = get_available_sessions_from_event(event)
    return determine_practice_sessions(available_sessions)


def select_practice_sessions_from_available(available_sessions: Iterable[str]) -> Tuple[str, str]:
    """Return the pair of practice/session names to use for metric calculations.

    This is a thin wrapper around ``fast_f1.weekend.determine_practice_sessions``
    so higher-level code in this package can import the helper from
    ``fast_f1.api``.

    Args:
        available_sessions: An iterable of session type names.

    Returns:
        A tuple of two session type names (e.g., ("FP2", "FP3") or ("FP1", "SprintQualifying")).

    Raises:
        RuntimeError: If required sessions are missing.
    """
    return determine_practice_sessions(available_sessions)
