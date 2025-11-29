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

    team = Team(num_drivers=5, num_constructors=2, unused_budget=0.0)
    team.add_asset(AssetType.DRIVER, "HAM")
    team.add_asset(AssetType.DRIVER, "LEC")
    team.add_asset(AssetType.DRIVER, "NOR")
    team.add_asset(AssetType.DRIVER, "PIA")
    team.add_asset(AssetType.DRIVER, "VER")
    team.add_asset(AssetType.CONSTRUCTOR, "MCL")
    team.add_asset(AssetType.CONSTRUCTOR, "FER")

    strat_budget = factory_strategy(race, team, StrategyMaxBudget, max_moves=2)

    assert False
