import pandas as pd


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
        raise ValueError(f"Driver {driver} not found for the given season {season} and race {race}")
    
    if df_ppm_filtered.shape[0] > 1:
        raise ValueError(f"Multiple entries found for driver {driver} in season {season} and race {race}")

    ser_ppm_filtered = df_ppm_filtered.iloc[0]
    ppm = ser_ppm_filtered[col_ppm]

    driver_obj = Driver(
        driver=driver,
        constructor="",
        ppm=ppm,
        price=0.0,
    )

    return driver_obj
