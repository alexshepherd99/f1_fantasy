"""races.team: Team representation and factory helpers.

Defines a Team container that holds driver and constructor selections,
methods to compute value and points, and helper factories to construct
teams from rows or lists.
"""

import pandas as pd
import numpy as np

from races.asset import AssetType
from races.season import Race


class Team:
    """Represents a fantasy team consisting of drivers and constructors.

    Attributes:
        total_points: Cumulative points scored by the team.
        unused_budget: Remaining budget after selecting assets.
        drs_driver: Name of the driver set for DRS boost (if any).
        assets: Mapping from :class:`AssetType` to list of selected names.
        asset_count: Expected counts per asset type.
    """
    def __init__(self, num_drivers: int = 5, num_constructors: int = 2, unused_budget: float = 0.0):
        self.total_points: int = 0
        self.unused_budget = unused_budget
        self.drs_driver = ""
        self.assets: dict[AssetType, list[str]] = {
            AssetType.DRIVER: [],
            AssetType.CONSTRUCTOR: [],
        }
        self.asset_count: dict[AssetType, int] = {
            AssetType.DRIVER: num_drivers,
            AssetType.CONSTRUCTOR: num_constructors,
        }

    def __str__(self) -> str:
        drivers = ",".join(sorted(self.assets[AssetType.DRIVER]))
        constructors = ",".join(sorted(self.assets[AssetType.CONSTRUCTOR]))
        return f"({drivers})({constructors})"

    def add_asset(self, asset_type: AssetType, asset: str):
        """Add an asset (driver or constructor) to the team.

        Raises a ValueError if the asset is already present or the limit is reached.
        """
        if asset in self.assets[asset_type]:
            raise ValueError(f"Asset {asset} of type {asset_type} already present")
        if len(self.assets[asset_type]) >= self.asset_count[asset_type]:
            raise ValueError(f"Unable to add asset {asset} of type {asset_type} as limit already reached")
        self.assets[asset_type].append(asset)

    def remove_asset(self, asset_type: AssetType, asset: str):
        """Remove an asset from the team.

        Raises a ValueError if the asset is not present.
        """
        if asset not in self.assets[asset_type]:
            raise ValueError(f"Unable to remove asset {asset} of type {asset_type} as asset is not present")
        self.assets[asset_type].remove(asset)

    def remove_all_assets(self):
        for asset_type in self.assets.keys():
            self.assets[asset_type] = []

    def check_asset_counts(self):
        """Validate that the team has the expected number of assets for each type.

        Raises ValueError if any count is incorrect.
        """
        for asset_type in self.assets.keys():
            if len(self.assets[asset_type]) != self.asset_count[asset_type]:
                raise ValueError(f"Team has incorrect number of assets of type {asset_type.value}, {len(self.assets[asset_type])} vs {self.asset_count[asset_type]}")
            
    def total_value(self, race: Race, race_prev: Race) -> float:
        """Return the total value of assets for budget calculations.

        Uses previous race prices for drivers not present in the current race.
        """
        self.check_asset_counts()
        return self.total_value_drivers(race, race_prev) + self.total_value_constructors(race)

    def total_value_drivers(self, race: Race, race_prev: Race) -> float:
        tot_val = 0.0
        for driver in self.assets[AssetType.DRIVER]:
            # If driver is not in current race, use previous race price
            if driver not in race.drivers:
                tot_val = tot_val + race_prev.drivers[driver].price
            else:
                tot_val = tot_val + race.drivers[driver].price
        return tot_val
    
    def total_value_constructors(self, race: Race) -> float:
        tot_val = 0.0
        for constructor in self.assets[AssetType.CONSTRUCTOR]:
            tot_val = tot_val + race.constructors[constructor].price
        return tot_val

    def total_budget(self, race: Race, race_prev: Race) -> float:
        return self.total_value(race, race_prev) + self.unused_budget

    def update_points(self, race: Race) -> int:
        """Compute and add points scored in a race to the team's total.

        Returns the number of newly added points.
        """
        self.check_asset_counts()
        new_points: int = 0

        for driver in self.assets[AssetType.DRIVER]:
            new_points += race.drivers[driver].points

        for constructor in self.assets[AssetType.CONSTRUCTOR]:
            new_points += race.constructors[constructor].points

        new_points += self.get_drs_points(race)
        self.total_points += new_points

        return new_points
    
    def get_drs_points(self, race: Race) -> int:
        """Return the points awarded for the DRS-boosted driver.

        If an explicit `drs_driver` is set and present in the race, their points
        are used; otherwise the highest-priced driver in the team is used.
        """
        if self.drs_driver in race.drivers:
            return race.drivers[self.drs_driver].points
        
        else:
            max_val = 0.0
            max_val_points: int = 0

            for driver in self.assets[AssetType.DRIVER]:
                # x2 DRS boost for highest priced driver
                if race.drivers[driver].price > max_val:
                    max_val = race.drivers[driver].price
                    max_val_points = race.drivers[driver].points

            return max_val_points


def factory_team_row(row_assets: dict[str, float], race: Race, num_drivers: int = 5, num_constructors: int = 2, total_budget: float = 100.0) -> Team:
    """Create a Team from a row-like mapping of asset prices.

    `row_assets` is typically a dict from `DataFrame.iloc[row].to_dict()` where
    assets not selected are NaN. The function populates drivers and constructors
    into a `Team`, validates counts, and sets the unused budget.
    """
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
    """Create a Team from explicit driver and constructor name lists.

    The `total_budget` is used to compute `unused_budget` after calculating
    the team's total value for the provided `race`.
    """
    team = Team(num_drivers=len(drivers), num_constructors=len(constructors))

    for d in drivers:
        team.add_asset(AssetType.DRIVER, d)
    for c in constructors:
        team.add_asset(AssetType.CONSTRUCTOR, c)

    team.unused_budget = total_budget - team.total_value(race, race)  # Previous race should not be required here
    return team
