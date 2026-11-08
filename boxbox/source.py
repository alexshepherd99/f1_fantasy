"""Download, save and parse BoxBox F1 Fantasy's two published JSON files.

BoxBox publishes its data for scripted use: its ``robots.txt`` allows every
agent on ``/data/``. Only the current season is served, and prices only as
they stand now, so every download is saved as it was received
(``save_copy``) to keep a history.
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
BOXBOX_URLS = {
    DRIVER_HISTORY: "https://boxboxf1fantasy.com/data/driver_history.json",
    SEASON_SUMMARY: "https://boxboxf1fantasy.com/data/season_summary.json",
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
    """What the fetcher reads from BoxBox's two files, keyed as BoxBox keys it.

    Drivers are keyed by BoxBox's driver key (``VER``, or ``HIR_HAAS`` where it
    disambiguates), constructors by slug (``red_bull``). Results map a calendar
    round to points; prices are each asset's ``current_price``, and a driver's
    price comes with the constructor slug BoxBox lists for them.
    """

    season: int
    generated_at: str
    rounds: list[BoxBoxRound]
    driver_results: dict[str, dict[int, float]]
    constructor_results: dict[str, dict[int, float]]
    driver_prices: dict[str, tuple[str, float]]
    constructor_prices: dict[str, float]


def _http_get(url: str) -> bytes:
    response = requests.get(url, headers={"User-Agent": _USER_AGENT}, timeout=_TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.content


def download_files(fetch: Callable[[str], bytes] | None = None) -> dict[str, bytes]:
    """Download both files, returning their bytes keyed by name.

    Args:
        fetch: Returns a URL's body; defaults to an HTTP GET that raises on an
            error status. Any failure propagates.
    """
    fetch = fetch or _http_get
    return {name: fetch(url) for name, url in BOXBOX_URLS.items()}


def save_copy(raw: dict[str, bytes], copy_dir: Path | str, now: datetime) -> Path:
    """Save both files as received into a new folder named for ``now`` (UTC).

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


def parse_files(raw: dict[str, bytes]) -> BoxBoxData:
    """Parse and check both files.

    Raises:
        BoxBoxDataError: If either file is unreadable, lacks a field the
            fetcher relies on, holds a non-number where it expects one, lists
            a round twice, lists rounds out of order, or the two files name
            different seasons.
    """
    history = _load_json(raw, DRIVER_HISTORY)
    summary = _load_json(raw, SEASON_SUMMARY)

    season = _field(summary, "season", SEASON_SUMMARY)
    if _field(history, "season", DRIVER_HISTORY) != season:
        _fail(f"season differs between files: {SEASON_SUMMARY} {season}, {DRIVER_HISTORY} {history['season']}")

    rounds = [
        BoxBoxRound(int(_number(_field(r, "round", f"{SEASON_SUMMARY} rounds"), f"{SEASON_SUMMARY} rounds")),
                    bool(_field(r, "has_actual", f"{SEASON_SUMMARY} rounds")))
        for r in _field(summary, "rounds", SEASON_SUMMARY)
    ]
    numbers = [r.number for r in rounds]
    if numbers != sorted(set(numbers)):
        _fail(f"{SEASON_SUMMARY}: rounds are not in strictly increasing order: {numbers}")

    driver_prices = {
        key: (
            _field(entry, "constructor", f"{SEASON_SUMMARY} driver_prices {key}"),
            _number(_field(entry, "current_price", f"{SEASON_SUMMARY} driver_prices {key}"),
                    f"{SEASON_SUMMARY} driver_prices {key} current_price"),
        )
        for key, entry in _field(summary, "driver_prices", SEASON_SUMMARY).items()
    }
    constructor_prices = {
        slug: _number(_field(entry, "current_price", f"{SEASON_SUMMARY} constructor_prices {slug}"),
                      f"{SEASON_SUMMARY} constructor_prices {slug} current_price")
        for slug, entry in _field(summary, "constructor_prices", SEASON_SUMMARY).items()
    }

    return BoxBoxData(
        season=season,
        generated_at=_field(summary, "generated_at", SEASON_SUMMARY),
        rounds=rounds,
        driver_results=_results(_field(history, "drivers", DRIVER_HISTORY), f"{DRIVER_HISTORY} drivers"),
        constructor_results=_results(_field(history, "constructors", DRIVER_HISTORY),
                                     f"{DRIVER_HISTORY} constructors"),
        driver_prices=driver_prices,
        constructor_prices=constructor_prices,
    )
