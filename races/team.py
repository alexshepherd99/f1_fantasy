import pandas as pd
import numpy as np

from races.asset import AssetType
from races.season import Race


class Team:
    def __init__(self, num_drivers: int = 5, num_constructors: int = 2, unused_budget: float = 0.0):
        self.total_points: int = 0
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

    def remove_all_assets(self):
        for asset_type in self.assets.keys():
            self.assets[asset_type] = []

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

    def update_points(self, race: Race) -> int:
        self.check_asset_counts()
        max_val = 0.0
        max_val_points: int = 0
        new_points: int = 0

        for driver in self.assets[AssetType.DRIVER]:
            new_points += race.drivers[driver].points
            # x2 DRS boost for highest priced driver
            if race.drivers[driver].price_old > max_val:
                max_val = race.drivers[driver].price_old
                max_val_points = race.drivers[driver].points

        for constructor in self.assets[AssetType.CONSTRUCTOR]:
            new_points += race.constructors[constructor].points

        new_points += max_val_points
        self.total_points += new_points

        return new_points


def factory_team_row(row_assets: dict[str, float], race: Race, num_drivers: int = 5, num_constructors: int = 2, total_budget: float = 100.0) -> Team:
    t = Team(num_drivers=num_drivers, num_constructors=num_constructors)

    total_value = 0.0

    for asset in row_assets.keys():
        if not np.isnan(row_assets[asset]):
            if asset in race.drivers.keys():
                t.add_asset(asset_type=AssetType.DRIVER, asset=asset)
                total_value += row_assets[asset]
            elif asset in race.constructors.keys():
                t.add_asset(asset_type=AssetType.CONSTRUCTOR, asset=asset)
                total_value += row_assets[asset]

    if len(t.assets[AssetType.DRIVER]) != num_drivers:
        raise ValueError(f"Incorrect number of drivers in {row_assets.keys()}")
    if len(t.assets[AssetType.CONSTRUCTOR]) != num_constructors:
        raise ValueError(f"Incorrect number of constructors in {row_assets.keys()}")
    
    t.unused_budget = total_budget - total_value
    return t


def factory_team_lists(drivers: list[str], constructors: list[str], race: Race, total_budget: float) -> Team:
    team = Team(num_drivers=len(drivers), num_constructors=len(constructors))

    for d in drivers:
        team.add_asset(AssetType.DRIVER, d)
    for c in constructors:
        team.add_asset(AssetType.CONSTRUCTOR, c)

    team.unused_budget = total_budget - team.total_value_old(race)
    return team
