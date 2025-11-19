import pandas as pd

from races.asset import AssetType
from races.season import Race


class Team:
    def __init__(self, num_drivers: int = 5, num_constructors: int = 2):
        self.total_points = 0
        self.assets: dict[AssetType, list[str]] = {
            AssetType.DRIVER: [],
            AssetType.CONSTRUCTOR: [],
        }
        self.asset_count: dict[AssetType, int] = {
            AssetType.DRIVER: num_drivers,
            AssetType.CONSTRUCTOR: num_constructors,
        }

    def add_asset(self, asset_type: AssetType, asset: str):
        if asset in self.assets[asset_type]:
            raise ValueError(f"Asset {asset} of type {asset_type} already present")
        if len(self.assets[asset_type]) >= self.asset_count[asset_type]:
            raise ValueError(f"Unable to add asset {asset} of type {asset_type} as limit already reached")
        self.assets[asset_type].append(asset)

    def remove_asset(self, asset_type: AssetType, asset: str):
        if asset not in self.assets[asset_type]:
            raise ValueError(f"Unable to remove asset {asset} of type {asset_type} as asset is not present")
        self.assets[asset_type].remove(asset)

    def total_value(self, race: Race) -> float:
        tot_val = 0.0
        for driver in self.assets[AssetType.DRIVER]:
            tot_val = tot_val + race.drivers[driver].price
        for constructor in self.assets[AssetType.CONSTRUCTOR]:
            tot_val = tot_val + race.constructors[constructor].price
        return tot_val

    def total_value_old(self, race: Race) -> float:
        tot_val = 0.0
        for driver in self.assets[AssetType.DRIVER]:
            tot_val = tot_val + race.drivers[driver].price_old
        for constructor in self.assets[AssetType.CONSTRUCTOR]:
            tot_val = tot_val + race.constructors[constructor].price_old
        return tot_val
