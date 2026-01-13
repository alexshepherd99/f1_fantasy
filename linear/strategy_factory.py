from common import AssetType
from linear.strategy_base import StrategyBase
from races.season import Race
from races.team import Team


def factory_strategy(race: Race, race_prev: Race, team: Team, strategy: type[StrategyBase], max_moves) -> StrategyBase:
    """Create and return a configured instance of `strategy` for a given race and team.

    Gathers current prices and derivations from the `race` object and computes the
    budget available using `team.total_budget` (using `race_prev` if needed).
    """
    team_drivers = team.assets[AssetType.DRIVER]
    team_constructors = team.assets[AssetType.CONSTRUCTOR]
    all_available_drivers = list(race.drivers.keys())
    all_available_constructors = list(race.constructors.keys())
    all_available_driver_pairs = {driver: race.drivers[driver].constructor for driver in race.drivers}
    prev_available_driver_pairs = {driver: race_prev.drivers[driver].constructor for driver in race_prev.drivers}
    max_cost = team.total_budget(race, race_prev)  # Previous race, in case current race has no driver valuation

    all_derivs = set()
    prices_assets = {}

    for driver in race.drivers.values():
        prices_assets[driver.driver] = driver.price
        all_derivs.update(driver.derivs.keys())
    for constructor in race.constructors.values():
        prices_assets[constructor.constructor] = constructor.price
        all_derivs.update(constructor.derivs.keys())

    derivs_assets = {}
    for deriv in all_derivs:
        derivs_assets[deriv] = {}
        for driver in race.drivers.values():
            derivs_assets[deriv][driver.driver] = driver.derivs[deriv]
        for constructor in race.constructors.values():
            derivs_assets[deriv][constructor.constructor] = constructor.derivs[deriv]

    return strategy(
        team_drivers=team_drivers,
        team_constructors=team_constructors,
        all_available_drivers=all_available_drivers,
        all_available_constructors=all_available_constructors,
        all_available_driver_pairs=all_available_driver_pairs,
        prev_available_driver_pairs=prev_available_driver_pairs,
        max_cost=max_cost,
        max_moves=max_moves,
        prices_assets=prices_assets,
        derivs_assets=derivs_assets
    )
