from __future__ import annotations

import logging
from typing import Iterable, Tuple


def is_sprint_weekend(available_sessions: Iterable[str]) -> bool:
    """Return True if the available sessions indicate a sprint weekend.

    Heuristic: presence of the session name "SprintQualifying" indicates a
    sprint-format weekend. This keeps the detection robust to minor
    variations in other session names.
    """
    return "SprintQualifying" in set(available_sessions)


def determine_practice_sessions(available_sessions: Iterable[str]) -> Tuple[str, str]:
    """Determine which two sessions to use for practice-based metrics.

    Normal weekends: use ("FP2", "FP3").
    Sprint weekends: use ("FP1", "SprintQualifying").

    If the required sessions are not present in ``available_sessions``, a
    ``RuntimeError`` is raised so callers can stop gracefully after
    logging the problem.
    """
    sessions = set(available_sessions)
    if is_sprint_weekend(sessions):
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
