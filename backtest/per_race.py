"""Re-simulate sampled teams keeping every race, and measure team concentration."""

import logging
import re
from collections.abc import Iterable, Mapping, Sequence
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


def full_stack_count(
    drivers: Sequence[str],
    constructors: Sequence[str],
    driver_pairs: Mapping[str, str],
) -> int:
    """Count held constructors whose every driver is held too.

    This is R7's literal prediction in `docs/max_points_v1/requirements.md` —
    that a pure-points objective takes the top constructor and both its
    drivers. `concentration` scores such a team three, but three can also be
    reached without one, so it is counted in its own right.

    Args:
        drivers: Drivers held, by their `DRIVER@CONSTRUCTOR` identifiers.
        constructors: Constructors held.
        driver_pairs: Driver to constructor, for the race in question.

    Returns:
        The number of held constructors whose whole line-up is held.
    """
    held = set(drivers)
    line_ups = ([d for d, c in driver_pairs.items() if c == constructor] for constructor in constructors)
    return sum(1 for line_up in line_ups if line_up and held.issuperset(line_up))


def _pairs_by_season_race(seasons: Iterable[int]) -> dict[tuple[int, int], dict[str, str]]:
    """Return the driver-to-constructor pairings of every race of each season."""
    pairs = {}
    for season in seasons:
        season_data = factory_season(*load_with_derivations(season=int(season)), int(season))
        for number, race in season_data.races.items():
            pairs[(int(season), int(number))] = race_driver_pairs(race)
    return pairs


def add_full_stacks(per_race: pd.DataFrame) -> pd.DataFrame:
    """Return the frame with a `full_stacks` column, scored against each row's race.

    Rebuilds the pairings from the same season data `simulate_per_race` used,
    rather than parsing them out of the driver identifiers. Rows are read one
    at a time, since the whole frame is a season's teams times every race.

    Args:
        per_race: Rows from `simulate_per_race`.

    Returns:
        The frame with `full_stacks` added, everything else unchanged.
    """
    pairs = _pairs_by_season_race(per_race["season"].unique())
    counts = [
        full_stack_count(*row_assets(row._asdict()), pairs[(row.season, row.race)])
        for row in per_race.itertuples(index=False)
    ]
    return per_race.assign(full_stacks=counts)


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


# A team is identified within a season by its starting line-up, as in
# backtest.metrics; the season is part of the key because a strategy's rows
# for one season must never pair with another's
_TEAM_KEY = ["season", "team"]


def _require_full_stacks(per_race: pd.DataFrame) -> None:
    """Raise unless the rows have been through `add_full_stacks`."""
    if "full_stacks" not in per_race.columns:
        logging.error(f"Per-race rows lack a full_stacks column, have {sorted(per_race.columns)}")
        raise ValueError("Per-race rows need a full_stacks column: call add_full_stacks first")


def _share_above_zero(values: pd.Series) -> float:
    return (values > 0).mean()


def concentration_summary(per_race: pd.DataFrame) -> pd.DataFrame:
    """Summarise how concentrated each strategy's teams are, per season.

    Counts over every team-race, so a strategy that concentrates in a few races
    reads differently from one that concentrates all season.

    Args:
        per_race: Rows from `simulate_per_race`, through `add_full_stacks`.

    Returns:
        One row per (label, season), with the number of team-races, the mean
        and median concentration, the share of team-races carrying any, and the
        same for constructors held with their whole line-up.

    Raises:
        ValueError: If `full_stacks` is missing.
    """
    _require_full_stacks(per_race)
    return per_race.groupby(["season", "label"], as_index=False).agg(
        team_races=("concentration", "count"),
        mean_concentration=("concentration", "mean"),
        median_concentration=("concentration", "median"),
        share_concentrated=("concentration", _share_above_zero),
        mean_full_stacks=("full_stacks", "mean"),
        share_full_stacked=("full_stacks", _share_above_zero),
    )[["label", "season", "team_races", "mean_concentration", "median_concentration",
       "share_concentrated", "mean_full_stacks", "share_full_stacked"]]


def team_summary(per_race: pd.DataFrame, baseline_label: str) -> pd.DataFrame:
    """Summarise each team's season: how concentrated it was, and its paired delta.

    The delta is the team's final-race `total_points` less the baseline's for
    the same season and starting team — the quantity `backtest.metrics` pairs
    on — set beside the concentration it carried getting there, so the two can
    be tested against each other.

    Args:
        per_race: Rows from `simulate_per_race`, through `add_full_stacks`.
        baseline_label: Label of the strategy every team is paired against.

    Returns:
        One row per (label, season, team) with its mean concentration and full
        stacks across the season, its band, `total_points`, `baseline_points`
        and `delta`.

    Raises:
        ValueError: If `full_stacks` is missing.
    """
    _require_full_stacks(per_race)
    finals = per_race.loc[per_race.groupby("sim_key")["race"].idxmax()]
    baseline = finals.loc[finals["label"] == baseline_label, _TEAM_KEY + ["total_points"]].rename(
        columns={"total_points": "baseline_points"}
    )

    summary = per_race.groupby(["label"] + _TEAM_KEY, as_index=False).agg(
        mean_concentration=("concentration", "mean"),
        mean_full_stacks=("full_stacks", "mean"),
        share_full_stacked=("full_stacks", _share_above_zero),
    )
    summary = summary.merge(finals[["label"] + _TEAM_KEY + ["band", "total_points"]], on=["label"] + _TEAM_KEY)
    summary = summary.merge(baseline, on=_TEAM_KEY)
    summary["delta"] = summary["total_points"] - summary["baseline_points"]
    return summary


def race_summary(per_race: pd.DataFrame, baseline_label: str) -> pd.DataFrame:
    """Summarise each race of each season, to show where a gap opens.

    A steady drift against the baseline reads as a straight line in
    `mean_cumulative_delta`; a few bad weekends read as steps. `mean_race_delta`
    is that race alone, so the two separate a persistent handicap from an event.

    Args:
        per_race: Rows from `simulate_per_race`, through `add_full_stacks`.
        baseline_label: Label of the strategy every race is paired against.

    Returns:
        One row per (label, season, race) with the teams paired, the mean
        cumulative and single-race deltas, and the mean concentration and full
        stacks held at that point in the season.

    Raises:
        ValueError: If `full_stacks` is missing.
    """
    _require_full_stacks(per_race)
    baseline = per_race.loc[
        per_race["label"] == baseline_label, _TEAM_KEY + ["race", "total_points", "points"]
    ].rename(columns={"total_points": "baseline_total_points", "points": "baseline_race_points"})

    paired = per_race.merge(baseline, on=_TEAM_KEY + ["race"])
    paired["cumulative_delta"] = paired["total_points"] - paired["baseline_total_points"]
    paired["race_delta"] = paired["points"] - paired["baseline_race_points"]
    return paired.groupby(["label", "season", "race"], as_index=False).agg(
        teams=("team", "count"),
        mean_cumulative_delta=("cumulative_delta", "mean"),
        mean_race_delta=("race_delta", "mean"),
        mean_concentration=("concentration", "mean"),
        mean_full_stacks=("full_stacks", "mean"),
    )


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
