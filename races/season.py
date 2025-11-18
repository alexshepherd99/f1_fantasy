import pandas as pd

from races.asset import (
    Constructor,
    Driver,
    factory_driver,
    factory_constructor,
)


class Race:
    def __init__(self, race: int, drivers: dict[str, Driver], constructors: dict[str, Constructor]):
        self.race = race
        self.drivers = drivers
        self.constructors = constructors


class Season:
    def __init__(self, season: int, races: dict[int, Race]):
        self.season = season
        self.races = races


def factory_race(
    df_driver_ppm_data: pd.DataFrame,
    df_constructor_ppm_data: pd.DataFrame,
    df_driver_pairings: pd.DataFrame,
    race: int,
    col_ppm: str       
) -> Race:
    df_filtered_pairs = df_driver_pairings[df_driver_pairings["Race"] == race]

    # Add drivers
    drivers = {}
    for idx,row in df_filtered_pairs.iterrows():
        drivers[row["Driver"]] = factory_driver(
            df_driver_ppm_data=df_driver_ppm_data,
            driver=row["Driver"],
            constructor=row["Constructor"],
            race=race,
            col_ppm=col_ppm
        )

    # Add constructors
    constructors = {}
    for constructor in df_filtered_pairs["Constructor"].unique():
        constructors[constructor] = factory_constructor(
            df_constructor_ppm_data,
            constructor=constructor,
            race=race,
            col_ppm=col_ppm
        )

    return Race(race=race, drivers=drivers, constructors=constructors)


def factory_season(
    df_driver_ppm_data: pd.DataFrame,
    df_constructor_ppm_data: pd.DataFrame,
    df_driver_pairings: pd.DataFrame,
    season: int,
    col_ppm: str       
) -> Season:
    races = {}
    for race in df_driver_pairings["Race"].unique():
        races[race] = factory_race(
            df_driver_ppm_data=df_driver_ppm_data,
            df_constructor_ppm_data=df_constructor_ppm_data,
            df_driver_pairings=df_driver_pairings,
            race=race,
            col_ppm=col_ppm
        )
    return Season(season=season, races=races)
