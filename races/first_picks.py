import pandas as pd
from itertools import combinations
import logging

from common import setup_logging
from races.season import Race, factory_race
from scripts.helper import load_with_derivations


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


if __name__ == "__main__":
    setup_logging()

    (df_driver_ppm, df_constructor_ppm, df_driver_pairs) = load_with_derivations(2023)

    race_1 = factory_race(
        df_driver_ppm,
        df_constructor_ppm,
        df_driver_pairs,
        1,
        "PPM Cumulative (3)"
    )

    df_combinations = set_combination_assets(get_all_team_combinations(), race_1)
    logging.info(df_combinations.sample(2))

    for driver in race_1.drivers.keys():
        price_old = race_1.drivers[driver].price_old
        df_combinations[driver] = df_combinations[driver].replace(1, price_old)

    for constructor in race_1.constructors.keys():
        price_old = race_1.constructors[constructor].price_old
        df_combinations[constructor] = df_combinations[constructor].replace(1, price_old)

    logging.info(df_combinations.sample(2))

    df_combinations["total_value"] = df_combinations.sum(axis=1)
    logging.info(df_combinations.sample(2))

    df_combinations_limit = df_combinations[
        (df_combinations["total_value"] <= 100.0) &
        (df_combinations["total_value"] > 90)
    ]
    logging.info(df_combinations_limit.shape)
    logging.info(df_combinations_limit.sample(2))

