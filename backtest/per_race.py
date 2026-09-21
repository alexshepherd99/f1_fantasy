"""Re-simulate sampled teams keeping every race, and measure team concentration."""

import logging
import re
from collections.abc import Mapping, Sequence
from itertools import combinations

import pandas as pd

from backtest.runner import SAMPLE_COLUMNS, append_results
from backtest.sample import DEFAULT_BAND_EDGES, STARTING_RACE, sample_starting_teams
from common import setup_logging
from helpers import load_with_derivations
from linear.strategy_base import StrategyBase
from linear.strategy_max_points import StrategyMaxPoints
from linear.strategy_p2pm import StrategyMaxP2PM
from races.season import Race, factory_season
from races.team import factory_team_row
from scripts.run_multiple_teams import get_starting_key, open_batch_results_file
from scripts.run_single_team import run_for_team

# `get_row_intermediate_results` spreads the team over numbered columns, each
# with `_val` and `_pts` companions that these deliberately exclude
_DRIVER_COLUMN = re.compile(r"^D\d+$")
_CONSTRUCTOR_COLUMN = re.compile(r"^C\d+$")

# The run this module was built for: max_points_v1's per-race re-simulation.
# Same seed, edges and sample size as Verification 1, so every team's final
# race is directly comparable with outputs/max_points_v1_results.parquet
SEASONS = [2023, 2024, 2025]
SAMPLE_SIZE = 500
SEED = 1
STRATEGIES = [StrategyMaxP2PM, StrategyMaxPoints]
STORE = "outputs/max_points_v1_per_race.parquet"


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


def row_assets(row: Mapping[str, object]) -> tuple[list[str], list[str]]:
    """Return the drivers and constructors a per-race result row holds.

    `scripts.run_single_team.get_row_intermediate_results` spreads the team
    across numbered `D1..Dn` and `C1..Cn` columns, which is the only record of
    what a team held mid-season once the simulation has moved on.

    Args:
        row: One result row from `run_for_team`.

    Returns:
        The drivers held and the constructors held.
    """
    drivers = [row[key] for key in row if _DRIVER_COLUMN.match(key)]
    constructors = [row[key] for key in row if _CONSTRUCTOR_COLUMN.match(key)]
    return drivers, constructors


def simulate_per_race(
    season: int,
    sample: pd.DataFrame,
    strategies: Sequence[type[StrategyBase]],
    store_path: str,
    flush_every: int = 100,
) -> pd.DataFrame:
    """Simulate every strategy on every sampled team, keeping every race's row.

    `backtest.runner.simulate_sample` stores only `run_for_team`'s final row,
    which is an end-of-season snapshot and cannot show what a team held along
    the way. This stores them all, each carrying the same `sim_key`, `label`,
    `team`, `sampled_value` and `band`, plus the team's `concentration` for
    that race, computed while the race's pairings are to hand.

    Keys already in the store are skipped whole, so a resumed run never leaves
    a team half-simulated, and the store is written every `flush_every`
    simulations rather than every `flush_every` rows.

    Args:
        season: Season year.
        sample: Sampled starting teams from `sample_starting_teams`.
        strategies: Strategy classes to simulate, in order; each is labelled by
            its `__name__`.
        store_path: Parquet results store to resume from and write to.
        flush_every: Simulations between writes.

    Returns:
        This run's rows, every race of every (strategy, team), whether
        simulated now or found in the store. Rows the store holds for other
        teams or strategies stay on disk but are not returned.
    """
    season_data = factory_season(*load_with_derivations(season=season), season)
    starting_race = season_data.races[STARTING_RACE]
    pairs_by_race = {number: race_driver_pairs(race) for number, race in season_data.races.items()}

    store = open_batch_results_file(store_path)
    done = set(store["sim_key"])
    rows = []
    simulated = 0
    skipped = 0
    run_keys = []

    for strategy in strategies:
        label = strategy.__name__
        logging.info(f"Simulating {label} for season {season} on {len(sample)} teams, keeping every race")

        for _, sampled in sample.iterrows():
            team = factory_team_row(sampled.drop(SAMPLE_COLUMNS).to_dict(), starting_race)
            # Taken before simulating, which leaves the team as it ends the season
            starting_team = str(team)
            sim_key = get_starting_key(label, season, team)
            run_keys.append(sim_key)
            if sim_key in done:
                skipped += 1
                continue

            for row in run_for_team(strategy, team, season_data, season, STARTING_RACE):
                row.update(
                    sim_key=sim_key,
                    label=label,
                    team=starting_team,
                    sampled_value=sampled["total_value"],
                    band=sampled["band"],
                    concentration=concentration(*row_assets(row), pairs_by_race[row["race"]]),
                )
                rows.append(row)

            simulated += 1
            if simulated % flush_every == 0:
                store = append_results(store, rows, store_path)
                rows = []

    logging.info(f"Season {season}: skipped {skipped} simulations already in the store")
    store = append_results(store, rows, store_path)
    return store[store["sim_key"].isin(run_keys)].reset_index(drop=True)


def run_per_race(
    seasons: Sequence[int],
    n: int,
    seed: int,
    strategies: Sequence[type[StrategyBase]],
    band_edges: Sequence[float],
    store_path: str,
) -> pd.DataFrame:
    """Sample and simulate every season into one store, keeping every race.

    Each season is sampled and simulated in turn and its sample released before
    the next, as `run_backtest` does. Sampling with the same seed and edges as a
    paired back-test draws the same teams, so the final race of each simulation
    here is comparable with that back-test's stored row.

    Args:
        seasons: Seasons to run.
        n: Teams to sample per band.
        seed: Sampling seed.
        strategies: Strategy classes to simulate.
        band_edges: Value band edges.
        store_path: Parquet results store, resumed from and appended to.

    Returns:
        Every race of every (strategy, team) across the seasons run.
    """
    results = []
    for season in seasons:
        sample = sample_starting_teams(season, n, seed, band_edges)
        results.append(simulate_per_race(season, sample, strategies, store_path))
        del sample

    return pd.concat(results, ignore_index=True)


if __name__ == "__main__":
    setup_logging()
    run_per_race(SEASONS, SAMPLE_SIZE, SEED, STRATEGIES, DEFAULT_BAND_EDGES, STORE)
