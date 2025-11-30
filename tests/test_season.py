import pytest
import pandas as pd
import numpy as np

from common import AssetType
from import_data.derivations import (
    derivation_cum_tot_constructor,
    derivation_cum_tot_driver,
    get_race_driver_constructor_pairs,
)
from import_data.import_history import load_archive_data_season
from races.season import factory_race, factory_season


def test_factory_race():
    race_1 = factory_race(
        pd.DataFrame(
            columns=["Driver", "Race", "col", "Price", "Points"],
            data=[["VER", 1, 3.3, 33.33, 13], ["VER", 2, 4.4, 44.44, 14], ["VER", 3, np.nan, 55.55, 15]]
        ),
        pd.DataFrame(
            columns=["Constructor", "Race", "col", "Price", "Points"],
            data=[["RED", 1, 6.6, 66.66, 16], ["RED", 2, 7.7, 77.77, 17], ["RED", 3, np.nan, 88.88, 18]]
        ),
        pd.DataFrame(
            columns=["Race", "Constructor", "Driver"],
            data=[[1, "RED", "VER"], [2, "RED", "VER"]]
        ),
        1,
        "col"
    )
    assert race_1.race == 1
    assert len(race_1.drivers) == 1
    assert len(race_1.constructors) == 1
    assert race_1.drivers["VER"].constructor == "RED"
    assert race_1.drivers["VER"].driver == "VER"
    assert race_1.drivers["VER"].ppm == 3.3
    assert race_1.drivers["VER"].price == 44.44
    assert race_1.drivers["VER"].points == 13
    assert race_1.constructors["RED"].constructor == "RED"
    assert race_1.constructors["RED"].ppm == 6.6
    assert race_1.constructors["RED"].price == 77.77
    assert race_1.constructors["RED"].points == 16


def test_factory_race_real_data():
    df_driver_2023 = load_archive_data_season(AssetType.DRIVER, 2023)
    df_constructor_2023 = load_archive_data_season(AssetType.CONSTRUCTOR, 2023)
    df_driver_pairs_2023 = get_race_driver_constructor_pairs(df_driver_2023)
    df_driver_ppm_2023 = derivation_cum_tot_driver(df_driver_2023, rolling_window=3)
    df_constructor_ppm_2023 = derivation_cum_tot_constructor(df_constructor_2023, rolling_window=3)

    race_1 = factory_race(
        df_driver_ppm_2023,
        df_constructor_ppm_2023,
        df_driver_pairs_2023,
        1,
        "PPM Cumulative (3)"
    )

    assert list(race_1.drivers.keys()) == [
        "VER",
        "PER",
        "HAM",
        "NOR",
        "ALO",
        "SAI",
        "RUS",
        "LEC",
        "PIA",
        "STR",
        "GAS",
        "TSU",
        "ZHO",
        "ALB",
        "OCO",
        "MAG",
        "HUL",
        "DEV",
        "BOT",
        "SAR",
    ]

    assert race_1.drivers["PIA"].constructor == "MCL"
    assert race_1.drivers["PIA"].driver == "PIA"
    assert race_1.drivers["PIA"].ppm == pytest.approx(-2.2857, 0.0001)
    assert race_1.drivers["PIA"].price == 6.9

    act = list(race_1.constructors.keys())
    exp = [
        "RED",
        "MER",
        "FER",
        "MCL",
        "AST",
        "ALP",
        "ALT",
        "ALF",
        "HAA",
        "WIL",
    ]
    act.sort()
    exp.sort()
    assert act == exp

    assert race_1.constructors["MCL"].constructor == "MCL"
    assert race_1.constructors["MCL"].ppm == pytest.approx(-1.7582, 0.0001)
    assert race_1.constructors["MCL"].price == 9.0

    race_12 = factory_race(
        df_driver_ppm_2023,
        df_constructor_ppm_2023,
        df_driver_pairs_2023,
        12,
        "PPM Cumulative (3)"
    )

    assert list(race_12.drivers.keys()) == [
        "VER",
        "PER",
        "HAM",
        "NOR",
        "ALO",
        "SAI",
        "RUS",
        "LEC",
        "PIA",
        "STR",
        "GAS",
        "TSU",
        "RIC",  # in for DEV
        "ZHO",
        "ALB",
        "OCO",
        "MAG",
        "HUL",
        "BOT",
        "SAR",
    ]

    act = list(race_12.constructors.keys())
    act.sort()
    assert act == exp  # exp already defined above, expected list of constructors sorted


def test_factory_season_real_data():
    df_driver_2023 = load_archive_data_season(AssetType.DRIVER, 2023)
    df_constructor_2023 = load_archive_data_season(AssetType.CONSTRUCTOR, 2023)
    df_driver_pairs_2023 = get_race_driver_constructor_pairs(df_driver_2023)
    df_driver_ppm_2023 = derivation_cum_tot_driver(df_driver_2023, rolling_window=3)
    df_constructor_ppm_2023 = derivation_cum_tot_constructor(df_constructor_2023, rolling_window=3)

    season = factory_season(
        df_driver_ppm_2023,
        df_constructor_ppm_2023,
        df_driver_pairs_2023,
        2023,
        "PPM Cumulative (3)"
    )
    assert len(season.races) == 22

    race_12 = season.races[12]
    assert list(race_12.drivers.keys()) == [
        "VER",
        "PER",
        "HAM",
        "NOR",
        "ALO",
        "SAI",
        "RUS",
        "LEC",
        "PIA",
        "STR",
        "GAS",
        "TSU",
        "RIC",  # in for DEV
        "ZHO",
        "ALB",
        "OCO",
        "MAG",
        "HUL",
        "BOT",
        "SAR",
    ]

    cons_mcl = race_12.constructors["MCL"]
    assert cons_mcl.price == 11.8
