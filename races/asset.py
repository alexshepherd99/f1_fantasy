import pandas as pd
import numpy as np

from common import AssetType


class Asset:
    def __init__(self, constructor: str, ppm: float, price: float, points: int):
        self.constructor = constructor
        self.ppm: float = float(ppm)
        self.price: float = float(price)
        self.points:int = int(points)


class Driver(Asset):
    def __init__(self, driver: str, constructor: str, ppm: float, price: float, points: int):
        super().__init__(constructor, ppm, price, points)
        self.driver = driver


class Constructor(Asset):
    def __init__(self, constructor: str, ppm: float, price: float, points: int):
        super().__init__(constructor, ppm, price, points)   


def factory_asset(
    df_ppm_data: pd.DataFrame,
    asset_type: AssetType,
    asset_name: str,
    race: int,
    col_ppm: str,    
) -> tuple[float, float, int]:

    df_ppm_filtered = df_ppm_data[
        (df_ppm_data[asset_type.value] == asset_name) &
        (df_ppm_data["Race"] == race)
    ]

    if df_ppm_filtered.empty:
        raise ValueError(f"{asset_type.value} {asset_name} not found for race {race}")
    
    if df_ppm_filtered.shape[0] > 1:
        raise ValueError(f"Multiple entries found for {asset_type.value} {asset_name} in race {race}")

    ppm = df_ppm_filtered.iloc[0][col_ppm]
    price = df_ppm_filtered.iloc[0]["Price"]    
    points = df_ppm_filtered.iloc[0]["Points"]

    return (ppm, price, points)


def factory_driver(
    df_driver_ppm_data: pd.DataFrame,
    driver: str,
    constructor: str,
    race: int,
    col_ppm: str
) -> Driver:
    (ppm, price, points) = factory_asset(
        df_ppm_data=df_driver_ppm_data,
        asset_type=AssetType.DRIVER,
        asset_name=driver,
        race=race,
        col_ppm=col_ppm
    )

    return Driver(
        driver=driver,
        constructor=constructor,
        ppm=ppm,
        price=price,
        points=points
    )


def factory_constructor(
    df_constructor_ppm_data: pd.DataFrame,
    constructor: str,
    race: int,
    col_ppm: str
) -> Constructor:
    (ppm, price, points) = factory_asset(
        df_ppm_data=df_constructor_ppm_data,
        asset_type=AssetType.CONSTRUCTOR,
        asset_name=constructor,
        race=race,
        col_ppm=col_ppm
    )

    return Constructor(
        constructor=constructor,
        ppm=ppm,
        price=price,
        points=points
    )
