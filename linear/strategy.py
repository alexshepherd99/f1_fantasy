COST_PROHIBITIVE = 999999.99  # A really big float number that we can never afford


class StrategyBase:
    def __init__(
        self,
        team_drivers: list[str],
        team_constructors: list[str],
        all_available_drivers: list[str],
        all_available_constructors: list[str],
        all_available_driver_pairs: dict[str, str],
        max_cost: float,
        max_moves: int,
        prices_assets: dict[str, float],
    ) -> None:
        # Check team constructors are available in list of all constructors
        for i in team_constructors:
            if i not in all_available_constructors:
                raise ValueError(f"Cannot find team constructor {i} in all available constructors")
            
        # Check not too many team drivers
        if len(team_drivers) > len(all_available_drivers):
            raise ValueError(f"Team count of {len(team_drivers)} is greater than {len(all_available_drivers)} available drivers")
        
        # Check not too many team constructors
        if len(team_constructors) > len(all_available_constructors):
            raise ValueError(f"Team count of {len(team_constructors)} is greater than {len(all_available_constructors)} available constructors")

        # All available drivers have a price
        for i in all_available_drivers:
            if i not in prices_assets.keys():
                raise ValueError(f"Driver {i} does not have a price")
            
        # All available constructors have a price
        for i in all_available_constructors:
            if i not in prices_assets.keys():
                raise ValueError(f"Constructor {i} does not have a price")

        # Take a copy of the prices
        self._prices_assets = prices_assets.copy()
        # Any drivers in the team which are no longer available, have a prohibitive price
        for x in team_drivers:
            if x not in self._prices_assets.keys():
                self._prices_assets[x] = COST_PROHIBITIVE
