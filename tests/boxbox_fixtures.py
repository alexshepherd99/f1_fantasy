"""Hand-written BoxBox files and a matching archive, for the boxbox tests.

A two-team 2026 season. Round 3 was cancelled, so BoxBox's rounds are 1, 2, 4
and 5, which the archive numbers races 1 to 4. By default it is the day of a
capture: round 4 (archive race 3) has been held and BoxBox has its results and
the new prices, for round 5. The archive holds race 3's prices and empty
points, waiting for those results. Prices are read from ``predictions``;
``season_summary`` carries the same ones.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

SEASON = 2026


def season_summary() -> dict:
    """``season_summary.json`` after round 4: ``current_price`` is round 5's price."""
    return {
        "season": SEASON,
        "generated_at": "2026-11-10T07:00:00+00:00",
        "rounds": [
            {"round": 1, "name": "One GP", "date": "2026-03-01", "has_actual": True},
            {"round": 2, "name": "Two GP", "date": "2026-03-08", "has_actual": True},
            {"round": 4, "name": "Four GP", "date": "2026-03-22", "has_actual": True},
            {"round": 5, "name": "Five GP", "date": "2026-03-29", "has_actual": False},
        ],
        "driver_prices": {
            "VER": {"name": "Max", "constructor": "red_bull", "current_price": 28.8, "starting_price": 27.7},
            "HAD": {"name": "Isack", "constructor": "red_bull", "current_price": 10.0, "starting_price": 9.0},
            "RUS": {"name": "George", "constructor": "mercedes", "current_price": 27.3, "starting_price": 27.4},
            "ANT": {"name": "Kimi", "constructor": "mercedes", "current_price": 20.0, "starting_price": 21.0},
        },
        "constructor_prices": {
            "red_bull": {"name": "Red Bull", "current_price": 30.4, "starting_price": 28.2},
            "mercedes": {"name": "Mercedes", "current_price": 31.2, "starting_price": 29.3},
        },
    }


def _rounds(points: dict[int, float], dnf: bool | None = False) -> dict:
    return {"rounds": [
        {"round": r, "circuit_id": f"c{r}", "points": p, **({} if dnf is None else {"is_dnf": dnf})}
        for r, p in points.items()
    ]}


def driver_history() -> dict:
    """``driver_history.json`` with results for rounds 1, 2 and 4."""
    return {
        "season": SEASON,
        "drivers": {
            "VER": _rounds({1: 50, 2: 49.0, 4: 31}),
            "HAD": _rounds({1: 5, 2: -3, 4: 7.5}),
            "RUS": _rounds({1: 30, 2: 12, 4: 25}),
            "ANT": _rounds({1: 20, 2: 8, 4: -2}),
        },
        "constructors": {
            "red_bull": _rounds({1: 70, 2: 60, 4: 44}, dnf=None),
            "mercedes": _rounds({1: 55, 2: 33, 4: 28}, dnf=None),
        },
    }


def _predicted_driver(driver_id: str, constructor: str, price: float) -> dict:
    return {"driver_id": driver_id, "name": driver_id.title(), "constructor": constructor,
            "current_price": price, "price_provisional": False, "expected_points": 10.0}


def predictions() -> dict:
    """``predictions.json`` before round 5, at the same prices as ``season_summary``."""
    return {
        "race": "Five GP",
        "round": 5,
        "season": SEASON,
        "generated_at": "2026-11-10T07:00:01+00:00",
        "drivers": [
            _predicted_driver("VER", "red_bull", 28.8),
            _predicted_driver("HAD", "red_bull", 10.0),
            _predicted_driver("RUS", "mercedes", 27.3),
            _predicted_driver("ANT", "mercedes", 20.0),
        ],
        "constructors": [
            {"constructor_id": "red_bull", "name": "Red Bull", "current_price": 30.4, "expected_points": 20.0},
            {"constructor_id": "mercedes", "name": "Mercedes", "current_price": 31.2, "expected_points": 20.0},
        ],
    }


# Race 3's prices in the fixture archive, as BoxBox would show them before its update.
RACE_3_PRICES = {"VER": 28.5, "HAD": 9.8, "RUS": 27.1, "ANT": 20.2, "red_bull": 30.0, "mercedes": 31.0}


def set_prices(prediction: dict, prices: dict[str, float]) -> None:
    """Set ``current_price`` in ``prediction`` for each driver id or constructor slug in ``prices``."""
    for entry in prediction["drivers"] + prediction["constructors"]:
        key = entry.get("driver_id", entry.get("constructor_id"))
        if key in prices:
            entry["current_price"] = prices[key]


def swap_driver(prediction: dict, old: str, new: str, price: float) -> None:
    """Replace driver ``old`` in ``prediction`` with ``new`` at ``price``, in the same team."""
    [entry] = [d for d in prediction["drivers"] if d["driver_id"] == old]
    entry.update(driver_id=new, name=new.title(), current_price=price)


def raw_files(summary: dict | None = None, history: dict | None = None,
              prediction: dict | None = None) -> dict[str, bytes]:
    """The three files as downloaded bytes, from the defaults or the given dicts."""
    return {
        "driver_history": json.dumps(history if history is not None else driver_history()).encode(),
        "season_summary": json.dumps(summary if summary is not None else season_summary()).encode(),
        "predictions": json.dumps(prediction if prediction is not None else predictions()).encode(),
    }


def modified(base: dict, change) -> dict:
    """A deep copy of ``base`` with ``change`` applied to it."""
    result = copy.deepcopy(base)
    change(result)
    return result


DRIVERS_CSV = """Season,Race,Constructor,Driver,Points,Price
2025,1,RED,VER,10,30
2026,1,RED,VER,50,27.7
2026,2,RED,VER,49,28
2026,3,RED,VER,,28.5
2026,1,RED,HAD,5,9
2026,2,RED,HAD,-3,9.5
2026,3,RED,HAD,,9.8
2026,1,MER,RUS,30,27.4
2026,2,MER,RUS,12,27.3
2026,3,MER,RUS,,27.1
2026,1,MER,ANT,20,21
2026,2,MER,ANT,8,20.5
2026,3,MER,ANT,,20.2
"""

CONSTRUCTORS_CSV = """Season,Race,Constructor,Points,Price
2025,1,RED,20,30
2026,1,RED,70,28.2
2026,2,RED,60,29
2026,3,RED,,30
2026,1,MER,55,29.3
2026,2,MER,33,30
2026,3,MER,,31
"""


def write_archive(directory: Path, drivers: str = DRIVERS_CSV, constructors: str = CONSTRUCTORS_CSV) -> Path:
    """Write the fixture archive CSVs into ``directory`` and return it."""
    (directory / "f1_fantasy_drivers.csv").write_text(drivers)
    (directory / "f1_fantasy_constructors.csv").write_text(constructors)
    return directory
