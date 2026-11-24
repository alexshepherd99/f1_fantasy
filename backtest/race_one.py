"""odds_fp3_v1's single-race back-test: each weekend scored as if it were a season's first race.

See ``docs/odds_fp3_v1/requirements.md``, R7-R9.
"""
import logging
from collections.abc import Iterable

import numpy as np

from common import DEFAULT_STARTING_BUDGET, AssetType
from races.season import Race
from races.team import Team
from simulate.pick import limitless_cap

NUM_DRIVERS = 5
NUM_CONSTRUCTORS = 2

# R9's random control: how many teams, and the seed
RANDOM_TEAMS = 1000
RANDOM_SEED = 1
# Draws allowed per team wanted before giving up. In 2026 most random teams fit the cap, so this
# is only reached when almost none do
MAX_DRAWS_PER_TEAM = 1000

# The same allowance `StrategyBase.initialise()` gives its budget constraint, so a random team
# fits the cap exactly when a strategy's pick could
COST_EPSILON = 0.0000001


def race_cap(race: Race, first_race: Race) -> float:
    """The budget cap for a team picked from scratch at `race` (R8).

    The starting budget scaled by the whole grid's price at `race` against `first_race`, so a
    later race buys the same share of the field as race 1 does.
    """
    return DEFAULT_STARTING_BUDGET * limitless_cap(race) / limitless_cap(first_race)


def placeholder_team(race: Race) -> Team:
    """The race's cheapest drivers and constructors, ties by name, as a team to pick from.

    `StrategyBase` sizes the team from the team it is given, so a pick from scratch needs a
    team held. With every move allowed and the cap given, which team it is cannot change the
    pick. The same rule as `live.lineup`'s race-1 options.
    """
    team = Team(num_drivers=NUM_DRIVERS, num_constructors=NUM_CONSTRUCTORS, unused_budget=0.0)
    for driver in sorted(race.drivers, key=lambda d: (race.drivers[d].price, d))[:NUM_DRIVERS]:
        team.add_asset(AssetType.DRIVER, driver)
    for constructor in sorted(race.constructors, key=lambda c: (race.constructors[c].price, c))[:NUM_CONSTRUCTORS]:
        team.add_asset(AssetType.CONSTRUCTOR, constructor)
    return team


def score_team(drivers: Iterable[str], constructors: Iterable[str], drs_driver: str, race: Race) -> int:
    """The team's fantasy points at `race`, with the DRS driver counted twice.

    An empty `drs_driver` leaves DRS to the game's default, the dearest driver, as `Team` applies it.

    Raises:
        ValueError: The team is not 5 drivers and 2 constructors.
    """
    team = Team(num_drivers=NUM_DRIVERS, num_constructors=NUM_CONSTRUCTORS)
    for driver in drivers:
        team.add_asset(AssetType.DRIVER, driver)
    for constructor in constructors:
        team.add_asset(AssetType.CONSTRUCTOR, constructor)
    team.drs_driver = drs_driver
    return team.update_points(race)


def draw_random_teams(
    race: Race,
    cap: float,
    count: int = RANDOM_TEAMS,
    seed: int = RANDOM_SEED,
    max_draws_per_team: int = MAX_DRAWS_PER_TEAM,
) -> list[tuple[tuple[str, ...], tuple[str, ...]]]:
    """Draw `count` teams at random, every team within `cap` equally likely (R9's random control).

    Each draw takes 5 drivers and 2 constructors at random and keeps them only if they fit the cap,
    so every team that fits is as likely as any other. The generator is seeded by `seed` and the
    race number together, so each race's draw stays the same however many races are run.

    Returns:
        Each team as its sorted drivers and sorted constructors.

    Raises:
        ValueError: Not even the cheapest team fits the cap.
        RuntimeError: `count` teams took more than `count * max_draws_per_team` draws, as so few
            teams fit that drawing on would take too long.
    """
    drivers = sorted(race.drivers)
    constructors = sorted(race.constructors)
    driver_prices = np.array([race.drivers[d].price for d in drivers])
    constructor_prices = np.array([race.constructors[c].price for c in constructors])

    cheapest = np.sort(driver_prices)[:NUM_DRIVERS].sum() + np.sort(constructor_prices)[:NUM_CONSTRUCTORS].sum()
    if cheapest > cap + COST_EPSILON:
        msg = f"No team fits a cap of {cap} at race {race.race}: the cheapest costs {cheapest}"
        logging.error(msg)
        raise ValueError(msg)

    rng = np.random.default_rng([seed, race.race])
    teams = []
    max_draws = count * max_draws_per_team
    draws = 0
    while len(teams) < count:
        if draws == max_draws:
            msg = f"Only {len(teams)} of {count} teams fit a cap of {cap} at race {race.race} in {max_draws} draws"
            logging.error(msg)
            raise RuntimeError(msg)
        draws += 1
        team_drivers = rng.choice(len(drivers), NUM_DRIVERS, replace=False)
        team_constructors = rng.choice(len(constructors), NUM_CONSTRUCTORS, replace=False)
        cost = driver_prices[team_drivers].sum() + constructor_prices[team_constructors].sum()
        if cost <= cap + COST_EPSILON:
            teams.append((
                tuple(sorted(drivers[i] for i in team_drivers)),
                tuple(sorted(constructors[i] for i in team_constructors)),
            ))
    return teams


def random_teams_points(race: Race, cap: float, count: int = RANDOM_TEAMS, seed: int = RANDOM_SEED) -> float:
    """The mean points of `draw_random_teams`' teams at `race`, DRS on each team's dearest driver."""
    teams = draw_random_teams(race, cap, count, seed)
    return sum(score_team(drivers, constructors, "", race) for drivers, constructors in teams) / len(teams)
