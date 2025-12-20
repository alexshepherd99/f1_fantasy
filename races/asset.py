"""races.asset: Asset classes and factory functions.

Contains the base Asset class and concrete Driver and Constructor
classes, plus helpers to build assets from PPM dataframes.
"""

import pandas as pd
import numpy as np

from common import AssetType


class Asset:
    """Base class for a fantasy asset.

    Attributes:
        constructor: The constructor/team name.
        price: Price of the asset.
        points: Points scored in the race.
        derivs: Derivative metrics from PPM data (e.g., expected points).
    """
    def __init__(self, constructor: str, price: float, points: int, derivs: dict[str, float]):
        self.constructor = constructor
        self.price: float = float(price)
        self.points:int = int(points)
        self.derivs = derivs


class Driver(Asset):
    """Driver asset.

    Inherits from :class:`Asset` and adds the driver's name.
    """
    def __init__(self, driver: str, constructor: str, price: float, points: int, derivs: dict[str, float]):
        super().__init__(constructor, price, points, derivs)
        self.driver = driver


class Constructor(Asset):
    """Constructor/team asset.

    Same fields as :class:`Asset`, representing a constructor.
    """
    def __init__(self, constructor: str, price: float, points: int, derivs: dict[str, float]):
        super().__init__(constructor, price, points, derivs)   


def factory_asset(
    df_ppm_data: pd.DataFrame,
    asset_type: AssetType,
    asset_name: str,
    race: int,
) -> tuple[dict[str, float], float, int]:
    """Build asset data from a PPM DataFrame for a given race.

    Args:
        df_ppm_data: PPM dataframe containing Price, Points and derivative cols.
        asset_type: Enum specifying whether DRIVER or CONSTRUCTOR.
        asset_name: Name of the asset to find.
        race: Race number to filter on.

    Returns:
        A tuple (derivs, price, points) where `derivs` is a dict of derivative
        metrics, `price` is float, and `points` is int.

    Raises:
        ValueError: If asset not found or multiple entries exist for the asset.
    """

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
    """Create a :class:`Driver` from driver PPM data for a race.

    Args:
        df_driver_ppm_data: PPM dataframe filtered to drivers.
        driver: Driver name.
        constructor: Constructor/team name for the driver.
        race: Race number.

    Returns:
        A `Driver` instance populated with price, points and derivative metrics.
    """
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
    """Create a :class:`Constructor` from constructor PPM data for a race.

    Args:
        df_constructor_ppm_data: PPM dataframe filtered to constructors.
        constructor: Constructor/team name.
        race: Race number.

    Returns:
        A `Constructor` instance populated with price, points and derivative metrics.
    """
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
