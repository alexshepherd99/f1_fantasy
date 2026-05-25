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


def get_race_results(season_year: int, race_num: int) -> pd.DataFrame:
    """Return race results for a given season and race.

    This is a placeholder for the eventual FastF1 wrapper. The legacy
    implementation in ``external_data.get_data`` should be used as the
    production reference when implementing this function.
    """
    raise NotImplementedError("get_race_results is not implemented yet")


def get_session_laps(season_year: int, race_num: int, session_type: str) -> pd.DataFrame:
    """Return session laps for a given season, race, and session."""
    raise NotImplementedError("get_session_laps is not implemented yet")


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
