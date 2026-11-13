"""Download, save and parse three of BoxBox F1 Fantasy's published JSON files.

BoxBox publishes its data for scripted use: its ``robots.txt`` allows every
agent on ``/data/``. Only the current season is served, and prices only as
they stand now, so every download is saved as it was received
(``save_copy``) to keep a history.

Results and the round list come from ``driver_history.json`` and
``season_summary.json``. Prices come from ``predictions.json``, which holds
the prices the app shows: ``season_summary.json``'s went back to the previous
race's after a rebuild on 2026-11-09 (``docs/data_capture_v2/log.md``). Its
prices are still read, to check against.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

DRIVER_HISTORY = "driver_history"
SEASON_SUMMARY = "season_summary"
PREDICTIONS = "predictions"
BOXBOX_URLS = {
    DRIVER_HISTORY: "https://boxboxf1fantasy.com/data/driver_history.json",
    SEASON_SUMMARY: "https://boxboxf1fantasy.com/data/season_summary.json",
    PREDICTIONS: "https://boxboxf1fantasy.com/data/predictions.json",
}
DEFAULT_COPY_DIR = "outputs/boxbox"

_USER_AGENT = "f1-fantasy-capture"
_TIMEOUT_SECONDS = 30
_COPY_FOLDER_FORMAT = "%Y-%m-%dT%H%M%SZ"


class BoxBoxDataError(ValueError):
    """BoxBox's files are not in the structure the fetcher expects."""


@dataclass(frozen=True)
class BoxBoxRound:
    """One calendar round BoxBox lists, and whether its results are in."""

    number: int
    has_actual: bool


@dataclass(frozen=True)
class BoxBoxData:
    """What the fetcher reads from BoxBox's files, keyed as BoxBox keys it.

    Drivers are keyed by BoxBox's driver key (``VER``, or ``HIR_HAAS`` where it
    disambiguates), constructors by slug (``red_bull``). Results map a calendar
    round to points; prices are each asset's ``current_price``, and a driver's
    price comes with the constructor slug BoxBox lists for them. The prices
    are ``predictions.json``'s, for calendar round ``prices_round``, and
    ``provisional_prices`` lists the drivers whose price it marks provisional;
    ``summary_*`` hold ``season_summary.json``'s.
    """

    season: int
    generated_at: str
    rounds: list[BoxBoxRound]
    driver_results: dict[str, dict[int, float]]
    constructor_results: dict[str, dict[int, float]]
    driver_prices: dict[str, tuple[str, float]]
    constructor_prices: dict[str, float]
    summary_driver_prices: dict[str, tuple[str, float]]
    summary_constructor_prices: dict[str, float]
    prices_round: int
    prices_generated_at: str
    provisional_prices: list[str]


def _http_get(url: str) -> bytes:
    response = requests.get(url, headers={"User-Agent": _USER_AGENT}, timeout=_TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.content


def download_files(fetch: Callable[[str], bytes] | None = None) -> dict[str, bytes]:
    """Download the files, returning their bytes keyed by name.

    Args:
        fetch: Returns a URL's body; defaults to an HTTP GET that raises on an
            error status. Any failure propagates.
    """
    fetch = fetch or _http_get
    return {name: fetch(url) for name, url in BOXBOX_URLS.items()}


def save_copy(raw: dict[str, bytes], copy_dir: Path | str, now: datetime) -> Path:
    """Save the files as received into a new folder named for ``now`` (UTC).

    Raises:
        FileExistsError: If that folder already exists; a copy is never overwritten.
    """
    folder = Path(copy_dir) / now.strftime(_COPY_FOLDER_FORMAT)
    folder.mkdir(parents=True, exist_ok=False)
    for name, body in raw.items():
        (folder / f"{name}.json").write_bytes(body)
    logger.info(f"Saved BoxBox copy to {folder}")
    return folder


def _fail(message: str) -> None:
    logger.error(message)
    raise BoxBoxDataError(message)


def _load_json(raw: dict[str, bytes], name: str) -> dict:
    try:
        document = json.loads(raw[name])
    except (KeyError, ValueError) as exc:
        _fail(f"{name}: not a readable JSON file ({exc})")
    if not isinstance(document, dict):
        _fail(f"{name}: expected a JSON object")
    return document


def _field(document: dict, key: str, where: str):
    if key not in document:
        _fail(f"{where}: missing '{key}'")
    return document[key]


def _number(value, where: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _fail(f"{where}: expected a number, found {value!r}")
    return float(value)


def _results(assets: dict, where: str) -> dict[str, dict[int, float]]:
    results = {}
    for key, asset in assets.items():
        by_round = {}
        for entry in _field(asset, "rounds", f"{where} {key}"):
            number = int(_number(_field(entry, "round", f"{where} {key}"), f"{where} {key} round"))
            if number in by_round:
                _fail(f"{where} {key}: round {number} listed twice")
            by_round[number] = _number(_field(entry, "points", f"{where} {key} round {number}"),
                                       f"{where} {key} round {number} points")
        results[key] = by_round
    return results


def _keyed(entries: list, id_field: str, where: str) -> dict[str, dict]:
    """A ``predictions.json`` array as a dict keyed by each entry's ``id_field``."""
    keyed = {}
    for entry in entries:
        key = _field(entry, id_field, where)
        if key in keyed:
            _fail(f"{where}: {key} listed twice")
        keyed[key] = entry
    return keyed


def _driver_prices(entries: dict[str, dict], where: str) -> dict[str, tuple[str, float]]:
    return {
        key: (
            _field(entry, "constructor", f"{where} {key}"),
            _number(_field(entry, "current_price", f"{where} {key}"), f"{where} {key} current_price"),
        )
        for key, entry in entries.items()
    }


def _constructor_prices(entries: dict[str, dict], where: str) -> dict[str, float]:
    return {
        slug: _number(_field(entry, "current_price", f"{where} {slug}"), f"{where} {slug} current_price")
        for slug, entry in entries.items()
    }


def _provisional(drivers: dict[str, dict], where: str) -> list[str]:
    """Drivers whose ``price_provisional`` is true; the flag is optional, and absent means not provisional."""
    provisional = []
    for key, entry in drivers.items():
        flag = entry.get("price_provisional", False)
        if not isinstance(flag, bool):
            _fail(f"{where} {key}: expected true or false for price_provisional, found {flag!r}")
        if flag:
            provisional.append(key)
    return provisional


def parse_files(raw: dict[str, bytes]) -> BoxBoxData:
    """Parse and check the three files.

    Raises:
        BoxBoxDataError: If any file is unreadable, lacks a field the fetcher
            relies on, holds a non-number where it expects one, lists a round
            or an asset twice, lists rounds out of order, or the files name
            different seasons.
    """
    history = _load_json(raw, DRIVER_HISTORY)
    summary = _load_json(raw, SEASON_SUMMARY)
    prediction = _load_json(raw, PREDICTIONS)

    season = _field(summary, "season", SEASON_SUMMARY)
    for name, document in [(DRIVER_HISTORY, history), (PREDICTIONS, prediction)]:
        if _field(document, "season", name) != season:
            _fail(f"season differs between files: {SEASON_SUMMARY} {season}, {name} {document['season']}")

    rounds = [
        BoxBoxRound(int(_number(_field(r, "round", f"{SEASON_SUMMARY} rounds"), f"{SEASON_SUMMARY} rounds")),
                    bool(_field(r, "has_actual", f"{SEASON_SUMMARY} rounds")))
        for r in _field(summary, "rounds", SEASON_SUMMARY)
    ]
    numbers = [r.number for r in rounds]
    if numbers != sorted(set(numbers)):
        _fail(f"{SEASON_SUMMARY}: rounds are not in strictly increasing order: {numbers}")

    predicted_drivers = _keyed(_field(prediction, "drivers", PREDICTIONS), "driver_id", f"{PREDICTIONS} drivers")
    predicted_constructors = _keyed(_field(prediction, "constructors", PREDICTIONS), "constructor_id",
                                    f"{PREDICTIONS} constructors")

    return BoxBoxData(
        season=season,
        generated_at=_field(summary, "generated_at", SEASON_SUMMARY),
        rounds=rounds,
        driver_results=_results(_field(history, "drivers", DRIVER_HISTORY), f"{DRIVER_HISTORY} drivers"),
        constructor_results=_results(_field(history, "constructors", DRIVER_HISTORY),
                                     f"{DRIVER_HISTORY} constructors"),
        driver_prices=_driver_prices(predicted_drivers, f"{PREDICTIONS} drivers"),
        constructor_prices=_constructor_prices(predicted_constructors, f"{PREDICTIONS} constructors"),
        summary_driver_prices=_driver_prices(_field(summary, "driver_prices", SEASON_SUMMARY),
                                             f"{SEASON_SUMMARY} driver_prices"),
        summary_constructor_prices=_constructor_prices(_field(summary, "constructor_prices", SEASON_SUMMARY),
                                                       f"{SEASON_SUMMARY} constructor_prices"),
        prices_round=int(_number(_field(prediction, "round", PREDICTIONS), f"{PREDICTIONS} round")),
        prices_generated_at=_field(prediction, "generated_at", PREDICTIONS),
        provisional_prices=_provisional(predicted_drivers, f"{PREDICTIONS} drivers"),
    )
