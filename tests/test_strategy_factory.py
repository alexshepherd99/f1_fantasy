import pytest

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
    )

    race = season.races[1]
    race_prev = season.races[13]

    team = Team(num_drivers=5, num_constructors=2, unused_budget=5.1)
    team.add_asset(AssetType.DRIVER, "SAR")  # 4.0
    team.add_asset(AssetType.DRIVER, "HUL")  # 4.3
    team.add_asset(AssetType.DRIVER, "DEV")  # 5.0
    team.add_asset(AssetType.DRIVER, "TSU")  # 4.8
    team.add_asset(AssetType.DRIVER, "ZHO")  # 4.9
    team.add_asset(AssetType.CONSTRUCTOR, "MCL")  # 9.1
    team.add_asset(AssetType.CONSTRUCTOR, "FER")  # 22.1

    total_budget = 4.0 + 4.3 + 5.0 + 4.8 + 4.9 + 9.1 + 22.1 + 5.1  # 59.3

    strat_budget = factory_strategy(race, race_prev, team, StrategyMaxBudget, max_moves=2)

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

    # Check previous race is used when there is no price for driver in current race
    team_prev_check = Team(num_drivers=1, num_constructors=0, unused_budget=0.0)
    team_prev_check.add_asset(AssetType.DRIVER, "LAW")  # 4.5, from previous race
    strat_prev_check = factory_strategy(race, race_prev, team_prev_check, StrategyMaxBudget, max_moves=2)
    assert strat_prev_check._max_cost == 4.5

    with pytest.raises(KeyError, match="LAW"):
        factory_strategy(race, race, team_prev_check, StrategyMaxBudget, max_moves=2)


def test_strategy_factory_derivs():
    (df_driver_ppm, df_constructor_ppm, df_driver_pairs) = load_with_derivations(season=2023)
    
    season = factory_season(
        df_driver_ppm,
        df_constructor_ppm,
        df_driver_pairs,
        2023,
    )

    race = season.races[2]
    race_prev = season.races[13]

    team = Team(num_drivers=5, num_constructors=2, unused_budget=5.1)
    team.add_asset(AssetType.DRIVER, "SAR")
    team.add_asset(AssetType.DRIVER, "HUL")
    team.add_asset(AssetType.DRIVER, "DEV")
    team.add_asset(AssetType.DRIVER, "TSU")
    team.add_asset(AssetType.DRIVER, "LAW")  # Not in available drivers
    team.add_asset(AssetType.CONSTRUCTOR, "MCL")
    team.add_asset(AssetType.CONSTRUCTOR, "FER")
 
    strat_budget = factory_strategy(race, race_prev, team, StrategyMaxBudget, max_moves=2)

    assert len(strat_budget._derivs_assets.keys()) == 4
    assert "P2PM Cumulative (3)" in strat_budget._derivs_assets.keys()
    assert "PPM Cumulative (3)" in strat_budget._derivs_assets.keys()
    assert "Price Cumulative (3)" in strat_budget._derivs_assets.keys()
    assert "Points Cumulative (3)" in strat_budget._derivs_assets.keys()

    assert len(strat_budget._derivs_assets["P2PM Cumulative (3)"]) == 30
    assert len(strat_budget._derivs_assets["PPM Cumulative (3)"]) == 30
    assert len(strat_budget._derivs_assets["Price Cumulative (3)"]) == 30
    assert len(strat_budget._derivs_assets["Points Cumulative (3)"]) == 30

    assert strat_budget._derivs_assets["P2PM Cumulative (3)"]["SAR"] == 30.25  # Driver in team and available
    assert strat_budget._derivs_assets["PPM Cumulative (3)"]["HAM"] == pytest.approx(0.8016, abs=1e-4)  # Driver not in team and available
    assert strat_budget._derivs_assets["Points Cumulative (3)"].get("LAW") is None  # Driver in team and not available
