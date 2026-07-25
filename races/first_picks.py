"""Utilities to generate initial team combinations for a race.

Provides functions to enumerate driver/constructor combinations and
convert those 0/1 selections into price-based teams that satisfy a
budget constraint.
"""

import pandas as pd
from itertools import combinations
import logging
import numpy as np

from common import CONSTRUCTORS_PER_TEAM, DEFAULT_STARTING_BUDGET, DRIVERS_PER_CONSTRUCTOR, DRIVERS_PER_TEAM, F1_SEASON_CONSTRUCTORS, setup_logging
from races.season import Race, factory_race
from races.team import factory_team_row
from helpers import load_with_derivations


# Team values are compared against budget thresholds that hundreds of teams hit
# exactly, so round away float summation noise before comparing
_VALUE_PRECISION = 6


def get_combination_matrix(num_total: int, num_allowed: int) -> np.ndarray:
    """Return all combinations as a 0/1 matrix, one row per combination.

    Held as `int8`: a season's driver combinations alone run to tens of
    thousands of rows, and the wider the row the more a season costs.

    Args:
        num_total: Total number of items (columns).
        num_allowed: Number of items selected (1s per row).
    """
    picks = np.fromiter(
        (i for comb in combinations(range(num_total), num_allowed) for i in comb),
        dtype=np.int64,
    ).reshape(-1, num_allowed)

    matrix = np.zeros((picks.shape[0], num_total), dtype=np.int8)
    np.put_along_axis(matrix, picks, 1, axis=1)
    return matrix


def get_all_combinations(
    num_total: int,
    num_allowed: int,
    col_prefix: str
) -> pd.DataFrame:
    """Return all combinations as a 0/1 DataFrame.

    Args:
        num_total: Total number of items (columns).
        num_allowed: Number of items selected (1s per row).
        col_prefix: Column name prefix for generated columns.

    Returns:
        DataFrame where each row is a 0/1 vector indicating a valid
        selection of `num_allowed` items out of `num_total`.
    """
    cols = [f"{col_prefix}{i+1}" for i in range(num_total)]
    return pd.DataFrame(get_combination_matrix(num_total, num_allowed), columns=cols)


def set_combination_assets(df_combinations: pd.DataFrame, race: Race) -> pd.DataFrame:
    """Assign driver and constructor column names to a combinations frame.

    Validates that the number of columns matches the race line-up and
    replaces generic column names with driver and constructor names.
    """
    drivers = list(race.drivers.keys())
    constructors = list(race.constructors.keys())

    if len(drivers) + len(constructors) != len (df_combinations.columns):
        raise ValueError("Combinations shape did not match race line-up")
    
    df_combinations.columns = drivers + constructors
    return df_combinations


def get_starting_combinations(season: int, race_num: int, min_total_value: float, max_total_value: float=DEFAULT_STARTING_BUDGET) -> pd.DataFrame:
    """Generate price-based team combinations that satisfy a budget window.

    This loads PPM derivations for a season, builds a `Race` object for the
    requested race, converts 0/1 combinations into price lists and filters
    teams by total value between `min_total_value` (exclusive) and
    `max_total_value` (inclusive).

    A team's value is its driver combination plus its constructor combination,
    so the budget filter is applied to the sum of the two sides and only the
    teams that survive it are ever priced up. Building every combination first
    costs hundreds of megabytes for a handful of thousands of valid teams.

    Args:
        season: Season year used to load PPM derivations.
        race_num: Race number within the season.
        min_total_value: Exclusive lower bound on team total value.
        max_total_value: Inclusive upper bound on team total value (default 100).

    Returns:
        DataFrame of valid, priced team combinations for the given race,
        indexed by each team's position in the full set of combinations.
    """
    (df_driver_ppm, df_constructor_ppm, df_driver_pairs) = load_with_derivations(season)

    race = factory_race(
        df_driver_ppm,
        df_constructor_ppm,
        df_driver_pairs,
        race_num,
    )

    num_constructors_total = F1_SEASON_CONSTRUCTORS[season]  # Intentionally throw if we can't find the season
    num_drivers_total = num_constructors_total * DRIVERS_PER_CONSTRUCTOR
    driver_combinations = get_combination_matrix(num_drivers_total, DRIVERS_PER_TEAM)
    constructor_combinations = get_combination_matrix(num_constructors_total, CONSTRUCTORS_PER_TEAM)

    driver_prices = np.array([driver.price for driver in race.drivers.values()], dtype=float)
    constructor_prices = np.array([constructor.price for constructor in race.constructors.values()], dtype=float)
    if len(driver_prices) != num_drivers_total or len(constructor_prices) != num_constructors_total:
        raise ValueError("Combinations shape did not match race line-up")

    driver_values = driver_combinations @ driver_prices
    constructor_values = constructor_combinations @ constructor_prices
    total_values = np.round(driver_values[:, None] + constructor_values[None, :], _VALUE_PRECISION)

    within_budget = (total_values <= max_total_value) & (total_values > min_total_value)
    driver_rows, constructor_rows = np.nonzero(within_budget)

    selections = np.hstack([driver_combinations[driver_rows], constructor_combinations[constructor_rows]])
    prices = np.concatenate([driver_prices, constructor_prices])

    df_combinations = pd.DataFrame(
        np.where(selections == 1, prices, np.nan),
        columns=[f"D{i+1}" for i in range(num_drivers_total)] + [f"C{i+1}" for i in range(num_constructors_total)],
        index=driver_rows * len(constructor_combinations) + constructor_rows,
    )
    df_combinations = set_combination_assets(df_combinations, race)
    df_combinations["total_value"] = total_values[driver_rows, constructor_rows]

    return df_combinations


if __name__ == "__main__":
    setup_logging()

    df_combinations = get_starting_combinations(2026, 1, 99.0)
    logging.info(df_combinations.shape)
    logging.info(df_combinations.sample(2))

    (df_driver_ppm, df_constructor_ppm, df_driver_pairs) = load_with_derivations(2026)
    race = factory_race(
        df_driver_ppm,
        df_constructor_ppm,
        df_driver_pairs,
        1,
    )
    
    team = factory_team_row(df_combinations.iloc[0].to_dict(), race)
