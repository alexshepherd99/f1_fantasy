"""Showing picks with prices, and reading a team typed in (D13, D14, D23)."""

from __future__ import annotations

import logging

from live.team_file import NUM_CONSTRUCTORS, NUM_DRIVERS
from races.season import Race
from simulate.pick import Pick

logger = logging.getLogger(__name__)

_LABEL_WIDTH = len("Constructor")


def asset_price(asset: str, race: Race, race_prev: Race) -> float:
    """An asset's price at `race`, or for a driver no longer in it, at `race_prev`, as `Team` values it."""
    if asset in race.constructors:
        return race.constructors[asset].price
    if asset in race.drivers:
        return race.drivers[asset].price
    return race_prev.drivers[asset].price


def parse_team(drivers_text: str, constructors_text: str, known_drivers: set[str],
               known_constructors: set[str]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Read a team typed as comma-separated driver identifiers (`VER@RED`) and constructor codes.

    Returns:
        The drivers and constructors, each sorted.

    Raises:
        ValueError: If there are not five distinct known drivers and two distinct known constructors.
    """
    drivers = _parse_list(drivers_text, NUM_DRIVERS, "five", "drivers", known_drivers)
    constructors = _parse_list(constructors_text, NUM_CONSTRUCTORS, "two", "constructors", known_constructors)
    return drivers, constructors


def _parse_list(text: str, count: int, count_word: str, kind: str, known: set[str]) -> tuple[str, ...]:
    items = [item.strip() for item in text.split(",") if item.strip()]
    if len(items) != count or len(set(items)) != count:
        _fail(f"Expected {count_word} distinct {kind}, got {', '.join(items) or 'none'}")
    unknown = [item for item in items if item not in known]
    if unknown:
        _fail(f"Not {kind} of the race: {', '.join(unknown)}")
    return tuple(sorted(items))


def _fail(message: str) -> None:
    logger.error(message)
    raise ValueError(message)


def default_drs(drivers: tuple[str, ...], race: Race) -> str:
    """The DRS driver the game gives a team with none set: its highest-priced driver, as `Team` does."""
    return max(drivers, key=lambda d: race.drivers[d].price)


def manual_pick(drivers: tuple[str, ...], constructors: tuple[str, ...], drs: str, held: tuple[str, ...],
                race: Race, budget: float) -> Pick:
    """A pick typed in, costed at the race's prices against the budget.

    Args:
        drivers: The drivers, sorted.
        constructors: The constructors, sorted.
        drs: The DRS driver.
        held: The drivers and constructors held, from which moves are counted.
        race: The race picked for.
        budget: The team held's value plus its unused budget, or Limitless's cap.
    """
    cost = sum(race.drivers[d].price for d in drivers) + sum(race.constructors[c].price for c in constructors)
    moves = sum(1 for asset in drivers + constructors if asset not in held)
    return Pick(drivers=drivers, constructors=constructors, drs_driver=drs, moves_used=moves, cost=cost,
                unused_budget=budget - cost)


def format_table(held: Pick | None, options: list[tuple[str, Pick]], race: Race, race_prev: Race) -> list[str]:
    """The team held and each option side by side: assets with prices, then DRS, moves, cost and unused budget.

    The held team's DRS driver and moves are shown as "-": it was not picked for this race.
    With no team held, as at race 1, only the options are shown.
    """
    def asset_cell(asset: str) -> str:
        return f"{asset:<8}{asset_price(asset, race, race_prev):>6.1f}"

    columns = []
    shown = ([] if held is None else [("Held", held)]) + list(options)
    for i, (title, pick) in enumerate(shown):
        is_held = held is not None and i == 0
        columns.append([title]
                       + [asset_cell(d) for d in pick.drivers]
                       + [asset_cell(c) for c in pick.constructors]
                       + (["-", "-"] if is_held else [pick.drs_driver, str(pick.moves_used)])
                       + [f"{pick.cost:.1f}", f"{pick.unused_budget:.1f}"])
    labels = [""] + ["Driver"] * NUM_DRIVERS + ["Constructor"] * NUM_CONSTRUCTORS + ["DRS", "Moves", "Cost", "Unused"]
    widths = [max(len(cell) for cell in column) for column in columns]
    return ["  ".join([f"{label:<{_LABEL_WIDTH}}"] + [f"{column[row]:<{width}}" for column, width in zip(columns, widths)])
            .rstrip()
            for row, label in enumerate(labels)]


def format_prices(race: Race) -> list[str]:
    """Every driver and constructor in the race with its price, most expensive first."""
    prices = {**{d: a.price for d, a in race.drivers.items()}, **{c: a.price for c, a in race.constructors.items()}}
    return [f"  {asset:<8}{price:>7.1f}" for asset, price in sorted(prices.items(), key=lambda item: (-item[1], item[0]))]
