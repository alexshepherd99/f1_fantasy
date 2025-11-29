import pandas as pd
import numpy as np

from races.asset import AssetType
from races.season import Race


class Team:
    def __init__(self, num_drivers: int = 5, num_constructors: int = 2, unused_budget: float = 0.0):
        self.total_points = 0
        self.unused_budget = unused_budget
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

    def check_asset_counts(self):
        for asset_type in self.assets.keys():
            if len(self.assets[asset_type]) != self.asset_count[asset_type]:
                raise ValueError(f"Team has incorrect number of assets of type {asset_type.value}, {len(self.assets[asset_type])} vs {self.asset_count[asset_type]}")
            
    def total_value(self, race: Race) -> float:
        self.check_asset_counts()
        tot_val = 0.0
        for driver in self.assets[AssetType.DRIVER]:
            tot_val = tot_val + race.drivers[driver].price
        for constructor in self.assets[AssetType.CONSTRUCTOR]:
            tot_val = tot_val + race.constructors[constructor].price
        return tot_val

    def total_value_old(self, race: Race) -> float:
        self.check_asset_counts()
        tot_val = 0.0
        for driver in self.assets[AssetType.DRIVER]:
            tot_val = tot_val + race.drivers[driver].price_old
        for constructor in self.assets[AssetType.CONSTRUCTOR]:
            tot_val = tot_val + race.constructors[constructor].price_old
        return tot_val

    def total_budget(self, race: Race) -> float:
        return self.total_value(race) + self.unused_budget

    def total_budget_old(self, race: Race) -> float:
        return self.total_value_old(race) + self.unused_budget


def factory_team_row(row_assets: dict[str, float], race: Race, num_drivers: int = 5, num_constructors: int = 2) -> Team:
    t = Team(num_drivers=num_drivers, num_constructors=num_constructors)
    for asset in row_assets.keys():
        if not np.isnan(row_assets[asset]):
            if asset in race.drivers.keys():
                t.add_asset(asset_type=AssetType.DRIVER, asset=asset)
            elif asset in race.constructors.keys():
                t.add_asset(asset_type=AssetType.CONSTRUCTOR, asset=asset)

    if len(t.assets[AssetType.DRIVER]) != num_drivers:
        raise ValueError(f"Incorrect number of drivers in {row_assets.keys()}")
    if len(t.assets[AssetType.CONSTRUCTOR]) != num_constructors:
        raise ValueError(f"Incorrect number of constructors in {row_assets.keys()}")
    
    return t
