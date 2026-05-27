from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Iterable, Tuple

import fastf1
import pandas as pd

try:
    from fastf1.exceptions import SessionNotAvailableError
except Exception:
    class SessionNotAvailableError(Exception):
        """Fallback exception alias when fastf1.exceptions is not available."""
        pass

from fast_f1.cache import get_local_cache_directory
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
_SESSION_NAME_TO_CODE = {name: code for code, name in _SESSION_CODE_NAMES.items()}


def get_event_for_race(season_year: int, race_num: int) -> Any:
    try:
        schedule = fastf1.get_event_schedule(season_year, include_testing=False)
    except Exception as exc:
        logger.warning(
            "Could not load event schedule for season %s: %s",
            season_year,
            exc,
        )
        raise ValueError(f"Could not load event schedule for season {season_year}") from exc

    event_rows = schedule[schedule["RoundNumber"] == race_num]
    if event_rows.empty:
        raise ValueError(f"No event found for season {season_year}, race {race_num}")
    return event_rows.iloc[0]


def _get_local_cache_path() -> Path | None:
    local_cache_dir = get_local_cache_directory(interactive=False)
    if local_cache_dir is None:
        return None
    return local_cache_dir


def _get_cache_file_path(prefix: str, season_year: int, race_num: int, session_type: str | None = None) -> Path | None:
    local_cache_dir = _get_local_cache_path()
    if local_cache_dir is None:
        return None

    file_name = f"{prefix}_{season_year}_{race_num}"
    if session_type:
        file_name += f"_{session_type}"
    file_name += ".pkl"
    return local_cache_dir / file_name


def _load_cached_dataframe(cache_path: Path) -> pd.DataFrame | None:
    if cache_path.exists():
        try:
            dataframe = pd.read_pickle(cache_path)
            logger.info("Loaded cached DataFrame from %s", cache_path)
            return dataframe
        except Exception as exc:
            logger.warning("Failed to load cached DataFrame from %s: %s", cache_path, exc)
    return None


def _save_cached_dataframe(df: pd.DataFrame, cache_path: Path) -> None:
    try:
        df.to_pickle(cache_path)
        logger.debug("Saved cached dataframe to %s", cache_path)
    except Exception as exc:
        logger.warning("Failed to save cached DataFrame to %s: %s", cache_path, exc)


def _empty_race_results_dataframe() -> pd.DataFrame:
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
            "Constructor",
        ]
    )


def _empty_session_laps_dataframe(season_year: int, race_num: int, session_type: str) -> pd.DataFrame:
    df = pd.DataFrame(
        columns=[
            "Driver",
            "LapTime",
            "LapNumber",
            "Stint",
            "PitOutTime",
            "PitInTime",
            "Compound",
            "TyreLife",
            "FreshTyre",
            "Season",
            "Race",
            "SessionType",
        ]
    )
    df["Season"] = season_year
    df["Race"] = race_num
    df["SessionType"] = session_type
    return df


def get_race_results(season_year: int, race_num: int) -> pd.DataFrame:
    """Return race results for a given season and race.

    The returned dataframe includes the driver abbreviation, status, position,
    classified position, grid position, points, constructor, and season/race metadata.
    """
    cache_path = _get_cache_file_path("race_results", season_year, race_num)
    if cache_path is not None:
        cache_df = _load_cached_dataframe(cache_path)
        if cache_df is not None:
            return cache_df

    try:
        event = get_event_for_race(season_year, race_num)
        race = event.get_session("R")
        race.load()
        results = getattr(race, "results", pd.DataFrame())
        if not isinstance(results, pd.DataFrame) or results.empty:
            raise ValueError("Race results are unavailable or malformed")

        columns = [
            "Abbreviation",
            "Status",
            "Position",
            "ClassifiedPosition",
            "GridPosition",
            "Points",
        ]
        if "TeamName" in results.columns:
            columns.append("TeamName")
        results = results[[col for col in columns if col in results.columns]].copy()
        results["Constructor"] = results.get("TeamName")
        results["Season"] = season_year
        results["Race"] = race_num
        if cache_path is not None:
            _save_cached_dataframe(results, cache_path)
        # Also attempt to cache common practice/session laps when the event
        # object is available so subsequent calls can be served from disk
        # without reloading the FastF1 event. This helps tests and offline
        # workflows that expect session caches to be present after a single
        # event load.
        for sess_code in ("FP1", "FP2", "FP3", "SQ"):
            try:
                sess = event.get_session(sess_code)
                sess.load()
                laps = getattr(sess, "laps", pd.DataFrame())
                if not isinstance(laps, pd.DataFrame) or laps.empty:
                    continue
                cols = [
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
                available = [c for c in cols if c in laps.columns]
                if not available:
                    continue
                session_laps = laps[available].copy()
                session_laps["Season"] = season_year
                session_laps["Race"] = race_num
                session_laps["SessionType"] = sess_code
                sess_cache = _get_cache_file_path("session_laps", season_year, race_num, sess_code)
                if sess_cache is not None:
                    try:
                        _save_cached_dataframe(session_laps, sess_cache)
                    except Exception:
                        logger.debug("Failed to cache session %s for %s %s", sess_code, season_year, race_num)
            except Exception as exc:
                logger.debug("Ignoring unavailable practice session %s for %s %s: %s", sess_code, season_year, race_num, exc)
                continue
        return results
    except Exception as exc:
        logger.warning(
            "Could not load race results for season %s race %s: %s",
            season_year,
            race_num,
            exc,
        )
        return _empty_race_results_dataframe()


def get_session_laps(season_year: int, race_num: int, session_type: str) -> pd.DataFrame:
    """Return session laps for a given season, race, and session."""
    cache_path = _get_cache_file_path("session_laps", season_year, race_num, session_type)
    if cache_path is not None:
        cache_df = _load_cached_dataframe(cache_path)
        if cache_df is not None:
            return cache_df

    try:
        event = get_event_for_race(season_year, race_num)
        session = event.get_session(session_type)
        session.load()
        session_laps = getattr(session, "laps", pd.DataFrame())
        if not isinstance(session_laps, pd.DataFrame) or session_laps.empty:
            raise ValueError("Session laps are unavailable or malformed")
    except Exception as exc:
        logger.warning(
            "Could not load session laps for season %s race %s session %s: %s",
            season_year,
            race_num,
            session_type,
            exc,
        )
        return _empty_session_laps_dataframe(season_year, race_num, session_type)

    columns = [
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
    available = [c for c in columns if c in session_laps.columns]
    session_laps = session_laps[available].copy()
    session_laps["Season"] = season_year
    session_laps["Race"] = race_num
    session_laps["SessionType"] = session_type
    if cache_path is not None:
        _save_cached_dataframe(session_laps, cache_path)
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
            event.get_session(code)
            friendly_name = _SESSION_CODE_NAMES.get(code, code)
            available_sessions.append(friendly_name)
            logger.debug(f"Session {code} ({friendly_name}) is available")
        except Exception as exc:
            logger.debug(f"Session {code} is not available: {type(exc).__name__}")

    logger.info("Available sessions for event: %s", available_sessions)
    return available_sessions


def get_session_code(session_name: str) -> str:
    return _SESSION_NAME_TO_CODE.get(session_name, session_name)


def select_practice_sessions_from_event(event: Any) -> Tuple[str, str]:
    """Return the pair of practice session codes to use for metric calculations.

    Extracts available sessions from the FastF1 Event object and determines
    which pair to use based on weekend format (normal vs sprint).

    Args:
        event: A FastF1 Event object from the schedule.

    Returns:
        A tuple of two session type codes (e.g., ("FP2", "FP3") or ("FP1", "SQ")).

    Raises:
        RuntimeError: If required sessions are missing from the event.
        AttributeError: If the event object structure is unexpected.
    """
    available_sessions = get_available_sessions_from_event(event)
    practice_sessions = determine_practice_sessions(available_sessions)
    return tuple(get_session_code(session) for session in practice_sessions)


def select_practice_sessions_from_available(available_sessions: Iterable[str]) -> Tuple[str, str]:
    """Return the pair of practice session codes to use for metric calculations.

    This is a thin wrapper around ``fast_f1.weekend.determine_practice_sessions``
    so higher-level code in this package can import the helper from
    ``fast_f1.api``.

    Args:
        available_sessions: An iterable of session type names.

    Returns:
        A tuple of two session type codes (e.g., ("FP2", "FP3") or ("FP1", "SQ")).

    Raises:
        RuntimeError: If required sessions are missing.
    """
    practice_sessions = determine_practice_sessions(available_sessions)
    return tuple(get_session_code(session) for session in practice_sessions)
