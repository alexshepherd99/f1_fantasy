"""races.season: Race and Season containers and factories.

Provides lightweight `Race` and `Season` classes and factory helpers
to build them from PPM and pairing data.
"""

import pandas as pd

from races.asset import (
    Constructor,
    Driver,
    factory_driver,
    factory_constructor,
)


class Race:
    """Represents a single race line-up.

    Attributes:
        race: Race number within a season.
        drivers: Mapping of driver name to :class:`Driver` instance.
        constructors: Mapping of constructor name to :class:`Constructor` instance.
    """
    def __init__(self, race: int, drivers: dict[str, Driver], constructors: dict[str, Constructor]):
        self.race = race
        self.drivers = drivers
        self.constructors = constructors


class Season:
    """Container for a season's races.

    Attributes:
        season: Year of the season.
        races: Mapping from race number to :class:`Race`.
    """
    def __init__(self, season: int, races: dict[int, Race]):
        self.season = season
        self.races = races


def factory_race(
    df_driver_ppm_data: pd.DataFrame,
    df_constructor_ppm_data: pd.DataFrame,
    df_driver_pairings: pd.DataFrame,
    race: int,
) -> Race:
    """Construct a :class:`Race` for a specific race number.

    Args:
        df_driver_ppm_data: Driver PPM dataframe containing price/points/derivs.
        df_constructor_ppm_data: Constructor PPM dataframe.
        df_driver_pairings: Pairing data indicating driver->constructor per race.
        race: Race number.

    Returns:
        A :class:`Race` object populated with `Driver` and `Constructor` instances.
    """
    df_filtered_pairs = df_driver_pairings[df_driver_pairings["Race"] == race]

    # Add drivers
    drivers = {}
    for idx,row in df_filtered_pairs.iterrows():
        drivers[row["Driver"]] = factory_driver(
            df_driver_ppm_data=df_driver_ppm_data,
            driver=row["Driver"],
            constructor=row["Constructor"],
            race=race,
        )

    # Add constructors
    constructors = {}
    for constructor in df_filtered_pairs["Constructor"].unique():
        constructors[constructor] = factory_constructor(
            df_constructor_ppm_data,
            constructor=constructor,
            race=race,
        )

    return Race(race=race, drivers=drivers, constructors=constructors)


def factory_season(
    df_driver_ppm_data: pd.DataFrame,
    df_constructor_ppm_data: pd.DataFrame,
    df_driver_pairings: pd.DataFrame,
    season: int,
) -> Season:
    """Build a :class:`Season` from PPM and pairing data.

    Iterates over unique race numbers in the pairings dataframe and builds
    a `Race` for each using :func:`factory_race`.
    """
    races = {}
    for race in df_driver_pairings["Race"].unique():
        races[race] = factory_race(
            df_driver_ppm_data=df_driver_ppm_data,
            df_constructor_ppm_data=df_constructor_ppm_data,
            df_driver_pairings=df_driver_pairings,
            race=race,
        )
    return Season(season=season, races=races)
