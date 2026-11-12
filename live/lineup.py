"""The strategies a live run offers for a race, and their picks (D16, D20, D22)."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from linear.strategy_base import StrategyBase
from linear.strategy_p2pm import StrategyMaxP2PM
from linear.strategy_p2pm_no_reset import StrategyMaxP2PMNoReset
from live.team_file import LIMITLESS, NUM_CONSTRUCTORS, NUM_DRIVERS, WILDCARD
from races.season import Race
from races.team import Team
from simulate.pick import Pick, limitless_cap, solve_race

logger = logging.getLogger(__name__)

# The race at which StrategyMaxP2PM plays the Wildcard itself
P2PM_WILDCARD_RACE = 4


@dataclass(frozen=True)
class Option:
    """One pick on offer, and the strategies that gave it, in line-up order."""
    strategies: tuple[str, ...]
    pick: Pick


def strategies_for(race: int, wildcard_used: bool) -> list[type[StrategyBase]]:
    """The strategies to run for a race after race 1.

    `StrategyMaxP2PM` plays the Wildcard at race 4, so while the Wildcard is unused that race
    also offers `StrategyMaxP2PMNoReset`, listed first so that a pick both give records as
    the one spending no chip; once the Wildcard is used, only `StrategyMaxP2PMNoReset`.

    Raises:
        ValueError: For race 1, which race-1 mode picks.
    """
    if race == 1:
        message = "The strategy line-up is for races after race 1; race 1 is race-1 mode's"
        logger.error(message)
        raise ValueError(message)
    if race != P2PM_WILDCARD_RACE:
        return [StrategyMaxP2PM]
    return [StrategyMaxP2PMNoReset] if wildcard_used else [StrategyMaxP2PMNoReset, StrategyMaxP2PM]


def implied_chip(strategy: str, race: int) -> str:
    """The chip a strategy's pick plays by itself: the Wildcard for `StrategyMaxP2PM` at race 4, else none."""
    return WILDCARD if strategy == StrategyMaxP2PM.__name__ and race == P2PM_WILDCARD_RACE else ""


def run_lineup(strategies: list[type[StrategyBase]], team: Team, race: Race, race_prev: Race, season_year: int,
               free_moves: int, chip: str = "") -> list[Option]:
    """Solve each strategy for `team` at `race`, merging those that pick the same team and DRS driver.

    Args:
        strategies: The strategies, in line-up order.
        team: The team held, with its unused budget.
        race: The race to pick for.
        race_prev: The race before.
        season_year: The season.
        free_moves: The free moves for the race.
        chip: `WILDCARD` or `LIMITLESS` to give every strategy unlimited moves, and for
            Limitless a budget of every asset's price (D20); otherwise "".

    Returns:
        One option per distinct pick, in the order first given.
    """
    unlimited = chip in (WILDCARD, LIMITLESS)
    max_moves = NUM_DRIVERS + NUM_CONSTRUCTORS if unlimited else free_moves
    max_cost = limitless_cap(race) if chip == LIMITLESS else None

    options: list[Option] = []
    for strategy in strategies:
        pick = solve_race(strategy, team, race, race_prev, season_year, max_moves, max_cost)
        same = next((i for i, o in enumerate(options)
                     if (o.pick.drivers, o.pick.constructors, o.pick.drs_driver)
                     == (pick.drivers, pick.constructors, pick.drs_driver)), None)
        if same is None:
            options.append(Option(strategies=(strategy.__name__,), pick=pick))
        else:
            options[same] = Option(strategies=options[same].strategies + (strategy.__name__,),
                                   pick=options[same].pick)
    return options
