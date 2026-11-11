"""One race's pick: solving a strategy for a team, and the free-move rule."""

import logging
from dataclasses import dataclass

from pulp.constants import LpStatusOptimal

from linear.strategy_base import StrategyBase, VarType
from linear.strategy_factory import factory_strategy
from races.season import Race
from races.team import Team


@dataclass(frozen=True)
class Pick:
    """The team a strategy picked for one race.

    Attributes:
        drivers: The drivers picked, sorted.
        constructors: The constructors picked, sorted.
        drs_driver: The strategy's DRS driver, or "" to leave it to the default.
        moves_used: Moves from the team held into the pick.
        cost: The pick's cost at the race's prices.
        unused_budget: The budget left after the pick, as the solver returned it.
    """
    drivers: tuple[str, ...]
    constructors: tuple[str, ...]
    drs_driver: str
    moves_used: int
    cost: float
    unused_budget: float


def solve_race(strategy: type[StrategyBase], team: Team, race: Race, race_prev: Race, season_year: int,
               max_moves: int, max_cost: float | None = None) -> Pick:
    """Solve `strategy` for `team` at `race` and return its pick, leaving `team` unchanged.

    Args:
        strategy: The strategy class to solve.
        team: The team held going into the race, with its unused budget.
        race: The race to pick for.
        race_prev: The race before, for the price of a held driver no longer in `race`.
        season_year: The season, passed to the strategy.
        max_moves: The moves allowed.
        max_cost: The most the pick may cost, in place of the team's value plus its unused budget,
            as for Limitless (`limitless_cap`). None keeps the team's budget.

    Returns:
        The pick.

    Raises:
        RuntimeError: If the solver does not return an optimal solution.
    """
    strat = factory_strategy(race, race_prev, team, strategy, max_moves=max_moves, season_year=season_year,
                             max_cost=max_cost)

    model = strat.execute()

    # It should never be impossible to solve
    if model.status != LpStatusOptimal:
        logging.error(f"LP model returned {model.status}")
        logging.error(f"Team: {str(team)}")
        logging.error(f"Season {season_year} race {race.race}")
        logging.error([[d,v.varValue] for d,v in strat._lp_variables[VarType.TeamDrivers].items()])
        logging.error([[d,v.varValue] for d,v in strat._lp_variables[VarType.TeamConstructors].items()])
        raise RuntimeError(f"LP model for season {season_year} race {race.race} is not optimal: {model.status}")

    return Pick(
        drivers=tuple(sorted(d for d,v in strat._lp_variables[VarType.TeamDrivers].items() if v.varValue == 1)),
        constructors=tuple(sorted(c for c,v in strat._lp_variables[VarType.TeamConstructors].items() if v.varValue == 1)),
        drs_driver=strat.get_drs_driver(),
        moves_used=int(strat._lp_variables[VarType.TeamMoves].value()),
        cost=strat._lp_variables[VarType.TotalCost].value(),
        unused_budget=strat._lp_variables[VarType.UnusedBudget].value(),
    )


def limitless_cap(race: Race) -> float:
    """Return the cost cap for a Limitless race: the sum of every driver's and constructor's price in it.

    Any team of the race fits under it, and it stays far below `COST_PROHIBITIVE`, the price
    `StrategyBase` gives a held driver no longer in the race, so such a driver is still forced out.
    """
    return sum(d.price for d in race.drivers.values()) + sum(c.price for c in race.constructors.values())


def next_free_moves(moves_used: int) -> int:
    """Return the free moves for the next race, given the moves used in this one.

    Fewer than 2 moves carries one over, giving 3; otherwise 2. Chips are not handled here.
    """
    return 3 if moves_used < 2 else 2
