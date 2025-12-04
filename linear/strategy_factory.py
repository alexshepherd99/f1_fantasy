from common import AssetType
from linear.strategy_base import StrategyBase
from races.season import Race
from races.team import Team


def factory_strategy(race: Race, race_prev: Race, team: Team, strategy: type[StrategyBase], max_moves) -> StrategyBase:
    team_drivers = team.assets[AssetType.DRIVER]
    team_constructors = team.assets[AssetType.CONSTRUCTOR]
    all_available_drivers = list(race.drivers.keys())
    all_available_constructors = list(race.constructors.keys())
    all_available_driver_pairs = {driver: race.drivers[driver].constructor for driver in race.drivers}
    max_cost = team.total_budget(race, race_prev)  # Previous race, in case current race has no driver valuation
    prices_assets = {}
    for driver in race.drivers.values():
        prices_assets[driver.driver] = driver.price
    for constructor in race.constructors.values():
        prices_assets[constructor.constructor] = constructor.price

    return strategy(
        team_drivers=team_drivers,
        team_constructors=team_constructors,
        all_available_drivers=all_available_drivers,
        all_available_constructors=all_available_constructors,
        all_available_driver_pairs=all_available_driver_pairs,
        max_cost=max_cost,
        max_moves=max_moves,
        prices_assets=prices_assets
    )
