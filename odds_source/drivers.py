"""Match the names on a saved odds page to driver and constructor codes.

Driver codes come from FastF1's driver list for the weekend; constructor codes
from a fixed table of FastF1 team names, as teams change rarely (D11).
"""

from __future__ import annotations

import logging
import unicodedata
from dataclasses import dataclass
from typing import Callable

import pandas as pd

from fast_f1.api import get_session_drivers
from odds_source.schedule import PRE_FP1_COLUMN, CapturePoint

logger = logging.getLogger(__name__)

# FastF1 team name to the constructor code the odds file uses
TEAM_CODES = {
    "Alpine": "ALP",
    "Aston Martin": "AST",
    "Audi": "AUD",
    "Cadillac": "CAD",
    "Ferrari": "FER",
    "Haas F1 Team": "HAA",
    "McLaren": "MCL",
    "Mercedes": "MER",
    "Racing Bulls": "VRB",
    "Red Bull Racing": "RED",
    "Williams": "WIL",
}

# FastF1 session code for the session each snapshot column follows
_SESSION_CODES = {
    "Odds_FP1": "FP1",
    "Odds_FP2": "FP2",
    "Odds_FP3": "FP3",
    "Odds_SQ": "SQ",
    "Odds_Sprint": "S",
    "Odds_Q": "Q",
}
_RACE_CODE = "R"
_ENTRY_COLUMNS = ["Abbreviation", "TeamName", "FirstName", "LastName"]


@dataclass(frozen=True)
class OddsEntry:
    """One driver's odds as the odds file holds them.

    ``driver`` is the driver code, or the page's name when it matched no driver,
    in which case ``constructor`` is blank.
    """

    driver: str
    constructor: str
    odds: str


def _fail(msg: str) -> None:
    logger.error(msg)
    raise ValueError(msg)


def _normalise(name: object) -> list[str]:
    """A name's words without accents or case, so "Câmara" matches "Camara"."""
    if not isinstance(name, str):
        return []
    plain = "".join(char for char in unicodedata.normalize("NFKD", name) if not unicodedata.combining(char))
    return plain.casefold().split()


def load_entry_list(
    point: CapturePoint,
    fetch: Callable[[int, int, str], pd.DataFrame] = get_session_drivers,
) -> pd.DataFrame:
    """The driver list the odds are matched against.

    That is the list for the session the odds follow. Before first practice, or
    while that session's list is not yet published, it is the previous race's,
    which misses a driver change; such a driver stays unmatched. The first race
    before practice has no list at all.
    """
    if point.column != PRE_FP1_COLUMN:
        entry_list = fetch(point.season, point.race, _SESSION_CODES[point.column])
        if not entry_list.empty:
            return entry_list
    if point.race == 1:
        logger.warning("No driver list before practice at race 1; every name stays unmatched")
        return pd.DataFrame(columns=_ENTRY_COLUMNS)
    return fetch(point.season, point.race - 1, _RACE_CODE)


def _team_code(team_name: object) -> str:
    if team_name not in TEAM_CODES:
        _fail(f"No constructor code for team {team_name}; add it to odds_source.drivers.TEAM_CODES")
    return TEAM_CODES[team_name]


def match_drivers(prices: dict[str, str], entry_list: pd.DataFrame) -> list[OddsEntry]:
    """Turn the page's prices into odds file entries, in the page's order.

    A name matches the driver with the same surname, ignoring accents and case,
    or, where two drivers share it, the same full name. A name matching no driver
    is kept as the page spells it, with a warning (D6, D15).

    Raises:
        ValueError: A matched driver's team is not in ``TEAM_CODES``, or two names
            match the same driver.
    """
    drivers = [
        (row.Abbreviation, row.TeamName, _normalise(row.LastName), _normalise(row.FirstName) + _normalise(row.LastName))
        for row in entry_list.itertuples(index=False)
    ]
    entries, matched = [], {}
    for name, odds in prices.items():
        words = _normalise(name)
        candidates = [driver for driver in drivers if driver[2] and words and driver[2][-1] == words[-1]]
        if len(candidates) > 1:
            candidates = [driver for driver in candidates if driver[3] == words]
        if len(candidates) != 1:
            logger.warning("No driver matches %s; kept by name with no constructor", name)
            entries.append(OddsEntry(name, "", odds))
            continue
        code, team_name = candidates[0][0], candidates[0][1]
        if code in matched:
            _fail(f"Both {matched[code]} and {name} match driver {code}")
        matched[code] = name
        entries.append(OddsEntry(code, _team_code(team_name), odds))
    return entries
