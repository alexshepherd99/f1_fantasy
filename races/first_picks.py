import pandas as pd
from itertools import combinations
import logging
import numpy as np

from common import setup_logging
from races.season import Race, factory_race
from races.team import factory_team_row
from helpers import load_with_derivations


def get_all_combinations(
    num_total: int,
    num_allowed: int,
    col_prefix: str
) -> pd.DataFrame:
    rows = []
    for comb in combinations(range(num_total), num_allowed):
        row = [0] * num_total
        for i in comb:
            row[i] = 1
        rows.append(row)

    cols = [f"{col_prefix}{i+1}" for i in range(num_total)]
    return pd.DataFrame(rows, columns=cols)


def get_all_team_combinations(
    num_drivers_total: int=20,
    num_drivers_team: int=5,
    num_constructors_total: int=10,
    num_constructors_team: int=2
) -> pd.DataFrame:
    df_drivers = get_all_combinations(num_drivers_total, num_drivers_team, "D")
    df_constructors = get_all_combinations(num_constructors_total, num_constructors_team, "C")
    return df_drivers.merge(df_constructors, how="cross")


def set_combination_assets(df_combinations: pd.DataFrame, race: Race) -> pd.DataFrame:
    drivers = list(race.drivers.keys())
    constructors = list(race.constructors.keys())

    if len(drivers) + len(constructors) != len (df_combinations.columns):
        raise ValueError("Combinations shape did not match race line-up")
    
    df_combinations.columns = drivers + constructors
    return df_combinations


def get_starting_combinations(season: int, race_num: int, min_total_value: float, max_total_value: float=100.0) -> pd.DataFrame:
    (df_driver_ppm, df_constructor_ppm, df_driver_pairs) = load_with_derivations(season)

    race = factory_race(
        df_driver_ppm,
        df_constructor_ppm,
        df_driver_pairs,
        race_num,
        "PPM Cumulative (3)"
    )

    df_combinations = set_combination_assets(get_all_team_combinations(), race)

    for driver in race.drivers.keys():
        price_old = race.drivers[driver].price_old
        df_combinations[driver] = df_combinations[driver].replace(1, price_old)
        df_combinations[driver] = df_combinations[driver].replace(0, np.nan)

    for constructor in race.constructors.keys():
        price_old = race.constructors[constructor].price_old
        df_combinations[constructor] = df_combinations[constructor].replace(1, price_old)
        df_combinations[constructor] = df_combinations[constructor].replace(0, np.nan)

    df_combinations["total_value"] = df_combinations.sum(axis=1)

    df_combinations = df_combinations[
        (df_combinations["total_value"] <= max_total_value) &
        (df_combinations["total_value"] > min_total_value)
    ]

    return df_combinations


if __name__ == "__main__":
    setup_logging()

    df_combinations = get_starting_combinations(2023, 1, 98.0)
    logging.info(df_combinations.shape)
    logging.info(df_combinations.sample(2))

    (df_driver_ppm, df_constructor_ppm, df_driver_pairs) = load_with_derivations(2023)

    race = factory_race(
        df_driver_ppm,
        df_constructor_ppm,
        df_driver_pairs,
        1,
        "PPM Cumulative (3)"
    )
    
    team = factory_team_row(df_combinations.iloc[0].to_dict(), race)
