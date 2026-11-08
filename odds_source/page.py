"""Read race-winner odds from an Oddschecker page saved by a browser as ``.mhtml``.

The page carries its odds as JSON in the props of an Astro component, the
``GridGroupIsland``, with a price from every bookmaker for every driver. Astro
wraps each value as ``[type, value]``, where type 1 is an array and 0 a plain
value.
"""

from __future__ import annotations

import email
import email.policy
import email.utils
import json
import logging
import statistics
from dataclasses import dataclass
from datetime import datetime
from fractions import Fraction
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_GRID_COMPONENT = "GridGroupIsland"
_WINNER_BET_TYPE = "Win Market"
_ACTIVE = "ACTIVE"
_ASTRO_ARRAY = 1


@dataclass(frozen=True)
class SavedOddsPage:
    """One race's winner odds as a saved page shows them.

    ``prices`` maps each driver's name, as the page spells it, to the median of
    the bookmakers' fractional odds, written as ``a/b``.
    """

    race_name: str
    race_start: datetime
    saved_at: datetime
    prices: dict[str, str]


class _ComponentProps(HTMLParser):
    """Collects the ``props`` attribute of each ``astro-island`` by component name."""

    def __init__(self) -> None:
        super().__init__()
        self.props: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "astro-island":
            return
        named = dict(attrs)
        export, props = named.get("component-export"), named.get("props")
        if export and props is not None:
            self.props[export] = props


def _fail(msg: str) -> None:
    logger.error(msg)
    raise ValueError(msg)


def _unwrap(node: Any) -> Any:
    """Strip Astro's ``[type, value]`` wrapping from a props value."""
    if isinstance(node, list) and len(node) == 2 and isinstance(node[0], int):
        kind, value = node
        if kind == _ASTRO_ARRAY:
            return [_unwrap(item) for item in value]
        return _unwrap(value)
    if isinstance(node, dict):
        return {key: _unwrap(value) for key, value in node.items()}
    return node


def _read_page(path: Path) -> tuple[str, datetime]:
    """The page's HTML and the time the browser saved it."""
    with path.open("rb") as handle:
        message = email.message_from_binary_file(handle, policy=email.policy.default)
    saved_at = email.utils.parsedate_to_datetime(message["Date"])
    for part in message.walk():
        if part.get_content_type() == "text/html":
            # The page declares UTF-8 in a meta tag, not in the MIME header
            return part.get_payload(decode=True).decode("utf-8"), saved_at
    _fail(f"No HTML in saved page {path}")


def _winner_market(props: dict) -> tuple[dict, list[dict]]:
    """The Winner market's details and its bets, one per driver."""
    args = props.get("componentArgs", {})
    for markets in args.get("marketGroups", {}).values():
        for market in markets:
            if market.get("betTypeName") == _WINNER_BET_TYPE:
                grid = args.get("oddsGrids", {}).get(str(market["ocMarketId"]), {})
                bets = [
                    bet
                    for query in grid.get("queries", [])
                    for bet in query["state"]["data"].get("bets", [])
                ]
                return market, bets
    _fail("No Winner market in the saved page's odds grid")


def _median_prices(bets: list[dict]) -> dict[str, str]:
    """Each driver's median fractional odds across the bookmakers pricing them.

    A driver priced by fewer than half the bookmakers active in the market is
    dropped with a warning: in practice that is a driver not in the race.
    """
    active = {
        bet["name"]: [Fraction(odds["fractional"]) for odds in bet["odds"] if odds["status"] == _ACTIVE]
        for bet in bets
    }
    bookmakers = {
        odds["bookmakerCode"] for bet in bets for odds in bet["odds"] if odds["status"] == _ACTIVE
    }
    prices = {}
    for name, quoted in active.items():
        if len(quoted) * 2 < len(bookmakers):
            logger.warning(
                "Dropping %s, priced by %s of %s bookmakers", name, len(quoted), len(bookmakers)
            )
            continue
        median = statistics.median(quoted)
        prices[name] = f"{median.numerator}/{median.denominator}"
    return prices


def read_saved_page(path: Path | str) -> SavedOddsPage:
    """Read a saved Oddschecker race page and price each driver to win.

    Raises:
        ValueError: The page has no odds grid or no Winner market, for example
            a bot-check page saved in place of the odds.
    """
    path = Path(path)
    html, saved_at = _read_page(path)
    parser = _ComponentProps()
    parser.feed(html)
    if _GRID_COMPONENT not in parser.props:
        _fail(f"No odds grid ({_GRID_COMPONENT}) in saved page {path}")
    market, bets = _winner_market(_unwrap(json.loads(parser.props[_GRID_COMPONENT])))
    return SavedOddsPage(
        race_name=market["subeventName"],
        race_start=datetime.fromisoformat(market["subeventStartTime"]),
        saved_at=saved_at,
        prices=_median_prices(bets),
    )
