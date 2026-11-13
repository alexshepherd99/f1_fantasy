"""The strategies a live run offers for a race, and their picks (D16, D20, D22, D29)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace

from backtest.variants import make_variant
from common import AssetType
from fast_f1.output import load_existing_metrics
from linear.strategy_base import StrategyBase
from linear.strategy_fastf1 import StrategyFastF1RuleRise
from linear.strategy_odds import StrategyBettingOdds
from linear.strategy_p2pm import StrategyMaxP2PM
from linear.strategy_p2pm_no_reset import StrategyMaxP2PMNoReset
from live.display import default_drs
from live.team_file import LIMITLESS, NUM_CONSTRUCTORS, NUM_DRIVERS, WILDCARD
from races.season import Race
from races.team import Team
from simulate.pick import Pick, limitless_cap, solve_race

logger = logging.getLogger(__name__)

# The race at which StrategyMaxP2PM plays the Wildcard itself
P2PM_WILDCARD_RACE = 4
# Race 1's concentration limits, loosest first (D29), and its budget
CONCENTRATION_LIMITS = (999.9, 4.0, 3.0, 2.0, 1.0, 0.0)
RACE_1_BUDGET = 100.0


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
    options: list[Option] = []
    for strategy in strategies:
        options = add_to_lineup(options, strategy, team, race, race_prev, season_year, free_moves, chip)
    return options


def add_to_lineup(options: list[Option], strategy: type[StrategyBase], team: Team, race: Race, race_prev: Race,
                  season_year: int, free_moves: int, chip: str = "") -> list[Option]:
    """Solve one more strategy, merging its pick into an option with the same team and DRS driver.

    Arguments are as for `run_lineup`, with `options` the line-up so far, left unchanged.

    Returns:
        The line-up with the strategy's pick added.

    Raises:
        RuntimeError: As for `solve_race`, and whatever the strategy raises.
    """
    unlimited = chip in (WILDCARD, LIMITLESS)
    max_moves = NUM_DRIVERS + NUM_CONSTRUCTORS if unlimited else free_moves
    max_cost = limitless_cap(race) if chip == LIMITLESS else None

    pick = solve_race(strategy, team, race, race_prev, season_year, max_moves, max_cost)
    return _merge(options, strategy.__name__, pick, race)


def _merge(options: list[Option], label: str, pick: Pick, race: Race) -> list[Option]:
    """`options` with `pick` added under `label`, or `label` added to an option with the same team and DRS driver.

    A pick leaving DRS to the default is given it first, so that it merges with one naming that driver.
    """
    pick = replace(pick, drs_driver=pick.drs_driver or default_drs(pick.drivers, race))
    added = list(options)
    same = next((i for i, o in enumerate(added)
                 if (o.pick.drivers, o.pick.constructors, o.pick.drs_driver)
                 == (pick.drivers, pick.constructors, pick.drs_driver)), None)
    if same is None:
        added.append(Option(strategies=(label,), pick=pick))
    else:
        added[same] = Option(strategies=added[same].strategies + (label,), pick=added[same].pick)
    return added


def run_race1_lineup(race: Race, season_year: int, odds_file: str) -> list[Option]:
    """Race 1's picks: `StrategyBettingOdds` at each of `CONCENTRATION_LIMITS` (D29).

    Each has a budget of `RACE_1_BUDGET` and the whole team to pick. Identical picks merge, and
    each is labelled `StrategyBettingOdds:<limit>`, as the team file records it.

    Args:
        race: Race 1.
        season_year: The season.
        odds_file: The odds file the strategy reads.

    Returns:
        One option per distinct pick, loosest limit first, each with every asset as a move.

    Raises:
        RuntimeError: As for `solve_race`, when no team meets a limit.
    """
    # The strategy needs a team held to count moves from; with every move free and the
    # budget given, which team it is cannot change the pick
    placeholder = Team(unused_budget=0.0)
    for driver in sorted(race.drivers, key=lambda d: (race.drivers[d].price, d))[:NUM_DRIVERS]:
        placeholder.add_asset(AssetType.DRIVER, driver)
    for constructor in sorted(race.constructors, key=lambda c: (race.constructors[c].price, c))[:NUM_CONSTRUCTORS]:
        placeholder.add_asset(AssetType.CONSTRUCTOR, constructor)

    options: list[Option] = []
    for limit in CONCENTRATION_LIMITS:
        pick = solve_race(_odds_strategy(limit, odds_file), placeholder, race, race, season_year,
                          NUM_DRIVERS + NUM_CONSTRUCTORS, RACE_1_BUDGET)
        pick = replace(pick, moves_used=NUM_DRIVERS + NUM_CONSTRUCTORS)
        options = _merge(options, f"{StrategyBettingOdds.__name__}:{limit:g}", pick, race)
    return options


def _odds_strategy(limit: float, odds_file: str) -> type[StrategyBase]:
    """`StrategyBettingOdds` reading `odds_file`, held to a concentration limit.

    The limit is an attribute the strategy sets in its constructor, not an argument, so
    `make_variant` cannot pass it; this subclass sets it after, as
    `scripts/select_odds_start.py` does.
    """
    def __init__(self, *args, **kwargs):
        StrategyBettingOdds.__init__(self, *args, fn_odds=odds_file, **kwargs)
        self.max_concentration = limit

    return type(StrategyBettingOdds.__name__, (StrategyBettingOdds,), {"__init__": __init__})


def fastf1_strategy(metrics_file: str) -> type[StrategyBase]:
    """`StrategyFastF1RuleRise`, under its own name, reading its signal from `metrics_file`.

    `factory_strategy` cannot pass the strategy a metrics file, so the file is bound in a
    subclass, as the back-test binds its variants' settings.
    """
    return make_variant(StrategyFastF1RuleRise, StrategyFastF1RuleRise.__name__, fn_metrics=metrics_file)


def has_signal(metrics_file: str, season: int, race: int) -> bool:
    """Whether the metrics file holds rows for the race.

    Without them the FastF1 strategy would score every asset zero and still pick, so a
    live run does not offer it (D18).
    """
    metrics = load_existing_metrics(metrics_file)
    return not metrics.empty and bool(((metrics["Season"] == season) & (metrics["Race"] == race)).any())
