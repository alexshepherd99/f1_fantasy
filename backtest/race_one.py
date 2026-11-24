"""odds_fp3_v1's single-race back-test: each weekend scored as if it were a season's first race.

See ``docs/odds_fp3_v1/requirements.md``, R7-R9.
"""
import argparse
import logging
import math
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path

import numpy as np
import pandas as pd

from backtest.variants import make_variant
from common import DEFAULT_STARTING_BUDGET, AssetType, setup_logging
from fast_f1.output import DEFAULT_HISTORICAL_OUTPUT, load_existing_metrics
from helpers import load_with_derivations
from import_data.odds import _FILE_BETTING_ODDS, load_odds
from linear.strategy_budget import StrategyMaxBudget
from linear.strategy_odds import StrategyBettingOdds
from linear.strategy_odds_fp3 import StrategyOddsFP3
from races.season import Race, Season, factory_season
from races.team import Team
from simulate.pick import limitless_cap, solve_race

# The one season with odds (R7)
DEFAULT_SEASON = 2026
DEFAULT_OUTPUT = "outputs/odds_fp3_v1_races.csv"

NUM_DRIVERS = 5
NUM_CONSTRUCTORS = 2

# R9's mixes: the odds' share of each driver's value, from FP3 alone to odds alone
MIXES = (0.0, 0.25, 0.5, 0.75, 1.0)

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


def mix_label(odds_weight: float) -> str:
    """The results label for a mix, such as ``OddsFP3_w0p25`` for an odds weight of 0.25."""
    return f"OddsFP3_w{odds_weight:g}".replace(".", "p")


def run_race(season_year: int, race: Race, first_race: Race, fn_metrics: Path | str, fn_odds: str) -> list[dict]:
    """Pick and score a team from scratch at `race` for each mix and control (R9).

    Each strategy picks from the placeholder team with every move allowed, under `race_cap`, and
    its team is scored with its own DRS driver, or the dearest when it names none.

    Args:
        season_year: The season.
        race: The race to pick and score at.
        first_race: The season's race 1, which the cap is scaled from.
        fn_metrics: The FastF1 metrics file the mixes read.
        fn_odds: The odds file `StrategyBettingOdds` reads.

    Returns:
        One row per mix, then max budget, betting odds and the random teams, each with ``season``,
        ``race``, ``label``, ``cap``, ``cost``, ``drivers``, ``constructors`` (comma-separated, sorted),
        ``drs_driver`` (empty for the dearest) and ``points``. The random row's points are the mean,
        and its team columns are empty.
    """
    cap = race_cap(race, first_race)
    placeholder = placeholder_team(race)
    strategies = [make_variant(StrategyOddsFP3, mix_label(w), odds_weight=w, fn_metrics=fn_metrics) for w in MIXES]
    strategies += [make_variant(StrategyMaxBudget, "MaxBudget"), make_variant(StrategyBettingOdds, "BettingOdds", fn_odds=fn_odds)]

    rows = []
    for strategy in strategies:
        pick = solve_race(strategy, placeholder, race, race, season_year, NUM_DRIVERS + NUM_CONSTRUCTORS, cap)
        rows.append({
            "season": season_year,
            "race": race.race,
            "label": strategy.__name__,
            "cap": cap,
            "cost": pick.cost,
            "drivers": ",".join(pick.drivers),
            "constructors": ",".join(pick.constructors),
            "drs_driver": pick.drs_driver,
            "points": score_team(pick.drivers, pick.constructors, pick.drs_driver, race),
        })
    rows.append({
        "season": season_year,
        "race": race.race,
        "label": "RandomTeams",
        "cap": cap,
        "cost": math.nan,
        "drivers": "",
        "constructors": "",
        "drs_driver": "",
        "points": random_teams_points(race, cap),
    })
    return rows


def eligible_races(season: Season, fn_metrics: Path | str, fn_odds: str) -> list[int]:
    """The season's races a race-1 pick can be back-tested on (R7), found afresh on each run.

    A race qualifies when it has been run (some asset scored points, as the archive loads a race
    not yet run with every point 0), its metrics have FP3 and odds, so it was a normal weekend,
    and the odds file prices it. A race whose odds file has odds but whose metrics scored them all
    zero had its metrics built before the odds were added: it is left out with a warning to
    rebuild them.
    """
    metrics = load_existing_metrics(fn_metrics)
    if metrics.empty:
        return []
    metrics = metrics[metrics["Season"] == season.season]

    eligible = []
    for race_num, race in sorted(season.races.items()):
        rows = metrics[metrics["Race"] == race_num]
        if rows.empty or not _has_been_run(race):
            continue
        # Only a normal weekend runs FP3, so this also leaves out every sprint weekend
        if rows["FP3_MinLapTime_rank"].isna().all():
            continue
        has_odds = any(odds > 0.0 for odds in load_odds(AssetType.DRIVER, season.season, race_num, fn=fn_odds).values())
        if not has_odds:
            continue
        if not (rows["OddsRank"] > 0.0).any():
            logging.warning(
                f"{season.season} race {race_num} has odds, but its metrics scored them all zero: "
                "rebuild its metrics to include it"
            )
            continue
        eligible.append(int(race_num))
    return eligible


class NoEligibleRaces(ValueError):
    """No race of the season can be back-tested."""


def run_season(season_year: int, fn_metrics: Path | str, fn_odds: str) -> pd.DataFrame:
    """`run_race`'s rows for every eligible race of the season, in race order.

    Raises:
        NoEligibleRaces: No race is eligible.
    """
    season = factory_season(*load_with_derivations(season=season_year), season_year)
    races = eligible_races(season, fn_metrics, fn_odds)
    if not races:
        msg = f"No {season_year} race has been run with FP3 and odds to back-test on"
        logging.error(msg)
        raise NoEligibleRaces(msg)

    logging.info(f"Back-testing {season_year} races {races}")
    rows = []
    for race_num in races:
        logging.info(f"Race {race_num}")
        rows += run_race(season_year, season.races[race_num], season.races[1], fn_metrics, fn_odds)
    return pd.DataFrame(rows)


def parse_arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse the command line."""
    parser = argparse.ArgumentParser(
        description="Pick and score a team from scratch at each eligible race, for odds_fp3_v1's mixes and controls",
    )
    parser.add_argument("--season", type=int, default=DEFAULT_SEASON, help=f"season to run (default: {DEFAULT_SEASON})")
    parser.add_argument("--metrics", default=str(DEFAULT_HISTORICAL_OUTPUT), help="FastF1 metrics file the mixes read")
    parser.add_argument("--odds", default=_FILE_BETTING_ODDS, help="odds file the betting-odds control reads")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="per-race results CSV, overwritten")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the back-test and write its per-race results.

    Returns:
        0 on success, 1 if no race is eligible, when nothing is written.
    """
    args = parse_arguments(argv)
    try:
        results = run_season(args.season, args.metrics, args.odds)
    except NoEligibleRaces:
        return 1
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(args.output, index=False)
    logging.info(f"Wrote {len(results)} rows to {args.output}")
    return 0


def _has_been_run(race: Race) -> bool:
    """Whether any asset scored points at `race`; the archive loads a race not yet run with every point 0."""
    return any(a.points != 0 for a in list(race.drivers.values()) + list(race.constructors.values()))


def random_teams_points(race: Race, cap: float, count: int = RANDOM_TEAMS, seed: int = RANDOM_SEED) -> float:
    """The mean points of `draw_random_teams`' teams at `race`, DRS on each team's dearest driver."""
    teams = draw_random_teams(race, cap, count, seed)
    return sum(score_team(drivers, constructors, "", race) for drivers, constructors in teams) / len(teams)


if __name__ == "__main__":
    setup_logging()
    sys.exit(main())
