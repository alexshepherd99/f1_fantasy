"""Translate BoxBox's rounds, driver keys and constructor slugs into the archive's terms.

BoxBox numbers races by calendar round and leaves cancelled rounds out of its
list (2026 has no rounds 4 or 5); the archive numbers the races held from 1.
So archive race N is the Nth round BoxBox lists.
"""

from __future__ import annotations

import logging
import re

from boxbox.source import BoxBoxData, BoxBoxDataError

logger = logging.getLogger(__name__)

TEAM_CODES: dict[str, str] = {
    "mercedes": "MER",
    "ferrari": "FER",
    "red_bull": "RED",
    "racing_bulls": "VRB",
    "haas": "HAA",
    "alpine": "ALP",
    "williams": "WIL",
    "mclaren": "MCL",
    "audi": "AUD",
    "cadillac": "CAD",
    "aston_martin": "AST",
}

_DRIVER_CODE = re.compile(r"[A-Z]{3}")


def _fail(message: str) -> None:
    logger.error(message)
    raise BoxBoxDataError(message)


def constructor_code(slug: str) -> str:
    """The archive's code for a BoxBox constructor slug.

    Raises:
        BoxBoxDataError: For a slug not in ``TEAM_CODES``; a new team is added by hand.
    """
    if slug not in TEAM_CODES:
        _fail(f"Unknown BoxBox constructor '{slug}': add it to boxbox.mapping.TEAM_CODES")
    return TEAM_CODES[slug]


def driver_code(key: str) -> str:
    """The three-letter driver code in a BoxBox driver key (``HIR_HAAS`` is ``HIR``).

    Raises:
        BoxBoxDataError: If the key does not start with a three-letter code.
    """
    code = key.split("_")[0]
    if not _DRIVER_CODE.fullmatch(code):
        _fail(f"BoxBox driver key '{key}' does not start with a three-letter driver code")
    return code


def round_for_race(data: BoxBoxData, race: int) -> int:
    """BoxBox's calendar round for archive race ``race``.

    Raises:
        BoxBoxDataError: If BoxBox lists fewer than ``race`` rounds, or ``race`` is below 1.
    """
    if not 1 <= race <= len(data.rounds):
        _fail(f"No BoxBox round for race {race}: BoxBox lists {len(data.rounds)} rounds")
    return data.rounds[race - 1].number


def results_by_driver_code(data: BoxBoxData) -> dict[str, dict[int, float]]:
    """Each driver's results, keyed by driver code rather than BoxBox's key.

    Raises:
        BoxBoxDataError: If two BoxBox keys share a driver code, which would
            make it ambiguous whose results are whose.
    """
    results: dict[str, dict[int, float]] = {}
    for key, by_round in data.driver_results.items():
        code = driver_code(key)
        if code in results:
            _fail(f"Two BoxBox driver keys share the code {code}; cannot tell their results apart")
        results[code] = by_round
    return results
