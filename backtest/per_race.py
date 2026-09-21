"""Re-simulate sampled teams keeping every race, and measure team concentration."""

import logging
from collections.abc import Mapping, Sequence
from itertools import combinations

from races.season import Race


def race_driver_pairs(race: Race) -> dict[str, str]:
    """Return each driver's constructor for one race.

    The `DRIVER@CONSTRUCTOR` identifier carries the same information, but the
    race's own pairing is the authoritative one and needs no parsing.

    Args:
        race: Race whose drivers to map.

    Returns:
        Each driver in the race, mapped to their constructor.
    """
    return {name: driver.constructor for name, driver in race.drivers.items()}


def concentration(
    drivers: Sequence[str],
    constructors: Sequence[str],
    driver_pairs: Mapping[str, str],
) -> int:
    """Count the same-constructor pairings within a team.

    One for each pair of held drivers sharing a constructor, plus one for each
    held driver whose constructor is also held. Zero is a team with no exposure
    doubled up, and a constructor held with both its drivers scores three.

    This is the measure `StrategyBettingOdds` constrains on
    (`linear/strategy_odds.py`), so what is measured here and what would
    eventually be limited are the same quantity.

    Args:
        drivers: Drivers held, by their `DRIVER@CONSTRUCTOR` identifiers.
        constructors: Constructors held.
        driver_pairs: Driver to constructor, for the race in question.

    Returns:
        The number of same-constructor pairings.

    Raises:
        ValueError: If a held driver has no entry in `driver_pairs`.
    """
    missing = [driver for driver in drivers if driver not in driver_pairs]
    if missing:
        logging.error(f"Drivers {missing} are not in the pairings {sorted(driver_pairs)}")
        raise ValueError(f"No constructor pairing for held drivers {missing}")

    held = [driver_pairs[driver] for driver in drivers]
    shared = sum(1 for first, second in combinations(held, 2) if first == second)
    owned = sum(1 for constructor in held if constructor in constructors)
    return shared + owned
