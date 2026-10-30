from __future__ import annotations

import logging
from typing import Iterable


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
