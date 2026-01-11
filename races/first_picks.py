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
    rows = []
    for comb in combinations(range(num_total), num_allowed):
        row = [0] * num_total
        for i in comb:
            row[i] = 1
        rows.append(row)

    cols = [f"{col_prefix}{i+1}" for i in range(num_total)]
    return pd.DataFrame(rows, columns=cols)


def get_all_team_combinations(
    season_year: int,
    num_drivers_team: int=DRIVERS_PER_TEAM,
    num_constructors_team: int=CONSTRUCTORS_PER_TEAM
) -> pd.DataFrame:
    """Return all valid driver+constructor team selection combinations.

    The returned DataFrame contains driver selection columns prefixed with
    `D` and constructor columns prefixed with `C`, with 0/1 values.
    """
    num_constructors_total = F1_SEASON_CONSTRUCTORS[season_year]  # Intentionally throw if we can't find the season
    num_drivers_total = num_constructors_total * DRIVERS_PER_CONSTRUCTOR
    df_drivers = get_all_combinations(num_drivers_total, num_drivers_team, "D")
    df_constructors = get_all_combinations(num_constructors_total, num_constructors_team, "C")
    return df_drivers.merge(df_constructors, how="cross")


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

    Args:
        season: Season year used to load PPM derivations.
        race_num: Race number within the season.
        min_total_value: Exclusive lower bound on team total value.
        max_total_value: Inclusive upper bound on team total value (default 100).

    Returns:
        DataFrame of valid, priced team combinations for the given race.
    """
    (df_driver_ppm, df_constructor_ppm, df_driver_pairs) = load_with_derivations(season)

    race = factory_race(
        df_driver_ppm,
        df_constructor_ppm,
        df_driver_pairs,
        race_num,
    )

    df_combinations = set_combination_assets(get_all_team_combinations(season), race)

    for driver in race.drivers.keys():
        price = race.drivers[driver].price
        df_combinations[driver] = df_combinations[driver].replace(1, price)
        df_combinations[driver] = df_combinations[driver].replace(0, np.nan)

    for constructor in race.constructors.keys():
        price = race.constructors[constructor].price
        df_combinations[constructor] = df_combinations[constructor].replace(1, price)
        df_combinations[constructor] = df_combinations[constructor].replace(0, np.nan)

    df_combinations["total_value"] = df_combinations.sum(axis=1)

    df_combinations = df_combinations[
        (df_combinations["total_value"] <= max_total_value) &
        (df_combinations["total_value"] > min_total_value)
    ]

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
