from __future__ import annotations

import logging
from datetime import datetime
from typing import Iterable

import pandas as pd


def is_sprint_weekend(available_sessions: Iterable[str]) -> bool:
    """Return True if the available sessions indicate a sprint weekend.

    Heuristic: presence of a session that sets the sprint grid -
    "SprintQualifying", or "SprintShootout" in 2023 - indicates a
    sprint-format weekend. This keeps the detection robust to minor
    variations in other session names.
    """
    sessions = set(available_sessions)
    return "SprintQualifying" in sessions or "SprintShootout" in sessions


def determine_practice_sessions(available_sessions: Iterable[str]) -> tuple[str, ...]:
    """Determine which sessions to use for practice-based metrics.

    Normal weekends: use ("FP2", "FP3").
    Sprint weekends: use ("FP1", "SprintQualifying").
    2023 sprint weekends: use ("FP1",). Fantasy teams locked at Friday's
    Grand Prix qualifying, which ran before Saturday's Sprint Shootout, so
    FP1 is the only session run before lock.

    If the required sessions are not present in ``available_sessions``, a
    ``RuntimeError`` is raised so callers can stop gracefully after
    logging the problem.
    """
    sessions = set(available_sessions)
    if "SprintShootout" in sessions:
        required = ("FP1",)
    elif is_sprint_weekend(sessions):
        required = ("FP1", "SprintQualifying")
    else:
        required = ("FP2", "FP3")

    missing = [s for s in required if s not in sessions]
    if missing:
        msg = f"Missing required sessions for weekend detection: {missing}"
        logging.error(msg)
        raise RuntimeError(msg)

    logging.debug("Determined practice sessions: %s", required)
    return required


# FastF1's schedule names for the sessions a weekend's practice metrics can need
_SCHEDULE_NAMES = {
    "Practice 1": "FP1",
    "Practice 2": "FP2",
    "Practice 3": "FP3",
    "Sprint Qualifying": "SprintQualifying",
    "Sprint Shootout": "SprintShootout",
}
# Session codes, where a session's name above is not its own code
_SESSION_CODES = {"SprintQualifying": "SQ", "SprintShootout": "SS"}
# A session is taken to have run this long after it starts; practice runs an hour,
# Sprint Qualifying less
SESSION_LENGTH = pd.Timedelta(hours=1)
# A schedule row lists at most this many sessions
_MAX_SESSIONS = 5


def unrun_sessions(event: pd.Series, now: datetime) -> dict[str, datetime]:
    """The sessions a weekend's practice metrics need that have not run by `now`.

    Read from the schedule alone, so nothing is fetched: a session counts as run
    ``SESSION_LENGTH`` after its start. Whether FastF1 has published its laps yet is
    a separate question, answered only by loading them.

    Args:
        event: One row of FastF1's event schedule, with ``Session1`` to ``Session5``
            and their ``DateUtc`` start times, naive in UTC.
        now: The time to judge by, timezone-aware.

    Returns:
        Each needed session not yet run, by code, with its start in UTC, in weekend
        order. Empty once all have run.

    Raises:
        RuntimeError: The weekend lacks a session its format needs.
    """
    starts = {}
    for i in range(1, _MAX_SESSIONS + 1):
        name = _SCHEDULE_NAMES.get(event.get(f"Session{i}"))
        if name is not None:
            starts[name] = pd.Timestamp(event[f"Session{i}DateUtc"]).tz_localize("UTC")

    unrun = {}
    for name in determine_practice_sessions(starts):
        if starts[name] + SESSION_LENGTH > now:
            unrun[_SESSION_CODES.get(name, name)] = starts[name]
    return unrun
