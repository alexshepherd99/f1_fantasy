import pandas as pd
import numpy as np

from common import AssetType


class Asset:
    def __init__(self, constructor: str, price: float, points: int, derivs: dict[str, float]):
        self.constructor = constructor
        self.price: float = float(price)
        self.points:int = int(points)
        self.derivs = derivs


class Driver(Asset):
    def __init__(self, driver: str, constructor: str, price: float, points: int, derivs: dict[str, float]):
        super().__init__(constructor, price, points, derivs)
        self.driver = driver


class Constructor(Asset):
    def __init__(self, constructor: str, price: float, points: int, derivs: dict[str, float]):
        super().__init__(constructor, price, points, derivs)   


def factory_asset(
    df_ppm_data: pd.DataFrame,
    asset_type: AssetType,
    asset_name: str,
    race: int,
) -> tuple[dict[str, float], float, int]:

    df_ppm_filtered = df_ppm_data[
        (df_ppm_data[asset_type.value] == asset_name) &
        (df_ppm_data["Race"] == race)
    ]

    if df_ppm_filtered.empty:
        raise ValueError(f"{asset_type.value} {asset_name} not found for race {race}")
    
    if df_ppm_filtered.shape[0] > 1:
        raise ValueError(f"Multiple entries found for {asset_type.value} {asset_name} in race {race}")

    price = df_ppm_filtered.iloc[0]["Price"]    
    points = df_ppm_filtered.iloc[0]["Points"]

    derivs = {}
    for c in df_ppm_filtered.columns:
        if c not in ["Season", "Driver", "Constructor", "Race", "Price", "Points"]:
            derivs[c] = float(df_ppm_filtered.iloc[0][c])

    return (derivs, price, points)


def factory_driver(
    df_driver_ppm_data: pd.DataFrame,
    driver: str,
    constructor: str,
    race: int,
) -> Driver:
    (derivs, price, points) = factory_asset(
        df_ppm_data=df_driver_ppm_data,
        asset_type=AssetType.DRIVER,
        asset_name=driver,
        race=race,
    )

    return Driver(
        driver=driver,
        constructor=constructor,
        price=price,
        points=points,
        derivs=derivs
    )


def factory_constructor(
    df_constructor_ppm_data: pd.DataFrame,
    constructor: str,
    race: int,
) -> Constructor:
    (derivs, price, points) = factory_asset(
        df_ppm_data=df_constructor_ppm_data,
        asset_type=AssetType.CONSTRUCTOR,
        asset_name=constructor,
        race=race,
    )

    return Constructor(
        constructor=constructor,
        price=price,
        points=points,
        derivs=derivs
    )
