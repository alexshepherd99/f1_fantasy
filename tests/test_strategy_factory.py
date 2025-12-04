from common import AssetType
from helpers import load_with_derivations
from linear.strategy_budget import StrategyMaxBudget
from linear.strategy_factory import factory_strategy
from races.season import factory_season
from races.team import Team


def test_strategy_factory():
    (df_driver_ppm, df_constructor_ppm, df_driver_pairs) = load_with_derivations(season=2023)
    
    season = factory_season(
        df_driver_ppm,
        df_constructor_ppm,
        df_driver_pairs,
        2023,
        "PPM Cumulative (3)"
    )

    race = season.races[1]

    team = Team(num_drivers=5, num_constructors=2, unused_budget=5.1)
    team.add_asset(AssetType.DRIVER, "SAR")  # 4.0
    team.add_asset(AssetType.DRIVER, "HUL")  # 4.3
    team.add_asset(AssetType.DRIVER, "DEV")  # 5.0
    team.add_asset(AssetType.DRIVER, "TSU")  # 4.8
    team.add_asset(AssetType.DRIVER, "ZHO")  # 4.9
    team.add_asset(AssetType.CONSTRUCTOR, "MCL")  # 9.1
    team.add_asset(AssetType.CONSTRUCTOR, "FER")  # 22.1

    total_budget = 4.0 + 4.3 + 5.0 + 4.8 + 4.9 + 9.1 + 22.1 + 5.1  # 59.3

    strat_budget = factory_strategy(race, team, StrategyMaxBudget, max_moves=2)

    assert strat_budget._max_cost == total_budget
    assert strat_budget._team_drivers == ["SAR", "HUL", "DEV", "TSU", "ZHO"]
    assert strat_budget._team_constructors == ["MCL", "FER"]
    assert strat_budget._max_moves == 2
    assert strat_budget._all_available_drivers == list(race.drivers.keys())
    assert strat_budget._all_available_constructors == list(race.constructors.keys())
    assert strat_budget._all_available_driver_pairs == {driver: race.drivers[driver].constructor for driver in race.drivers}

    prices_assets = {}
    for d,v in race.drivers.items():
        prices_assets[d] = v.price
    for c,v in race.constructors.items():
        prices_assets[c] = v.price
    assert strat_budget._prices_assets == prices_assets
