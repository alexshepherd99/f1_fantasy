import pandas as pd
import numpy as np

class Asset:
    def __init__(self, constructor: str, ppm: float, price: float):
        self.constructor = constructor
        self.ppm = ppm
        self.price = price


class Driver(Asset):
    def __init__(self, driver: str, constructor: str, ppm: float, price: float):
        super().__init__(constructor, ppm, price)
        self.driver = driver


class Constructor(Asset):
    def __init__(self, constructor: str, ppm: float, price: float):
        super().__init__(constructor, ppm, price)   
        pass


class RaceLineUp:
    def __init__(self, season: int, race: int):
        self.season = season
        self.race = race

    def validate(self):
        pass


def factory_driver(
    df_driver_ppm_data: pd.DataFrame,
    df_driver_constructor_pairs: pd.DataFrame,
    driver: str,
    season: int,
    race: int,
    col_ppm: str,    
) -> Driver:

    df_ppm_filtered = df_driver_ppm_data[
        (df_driver_ppm_data["Driver"] == driver) &
        (df_driver_ppm_data["Season"] == season) & 
        (df_driver_ppm_data["Race"] == race)
    ]

    if df_ppm_filtered.empty:
        raise ValueError(f"Driver {driver} not found for season {season} and race {race}")
    
    if df_ppm_filtered.shape[0] > 1:
        raise ValueError(f"Multiple entries found for driver {driver} in season {season} and race {race}")

    ppm = df_ppm_filtered.iloc[0][col_ppm]

    price = np.nan
    df_price = df_driver_ppm_data[
        (df_driver_ppm_data["Driver"] == driver) &
        (df_driver_ppm_data["Season"] == season) & 
        (df_driver_ppm_data["Race"] == (race+1))  # Current price is from next race
    ]

    if df_price.shape[0] > 1:
        raise ValueError(f"Multiple price entries found for driver {driver} in season {season} and race {race+1}")
    
    if not df_price.empty:
        price = df_price.iloc[0]["Price"]

    df_pairs_filtered = df_driver_constructor_pairs[
        (df_driver_constructor_pairs["Driver"] == driver) &
        (df_driver_constructor_pairs["Season"] == season) & 
        (df_driver_constructor_pairs["Race"] == race)
    ]

    if df_pairs_filtered.empty:
        raise ValueError(f"Driver pairing for {driver} not found for season {season} and race {race}")
    
    if df_pairs_filtered.shape[0] > 1:
        raise ValueError(f"Multiple entries found for driver pairing {driver} in season {season} and race {race}")
    
    constructor = df_pairs_filtered.iloc[0]["Constructor"]

    return Driver(
        driver=driver,
        constructor=constructor,
        ppm=ppm,
        price=price,
    )
