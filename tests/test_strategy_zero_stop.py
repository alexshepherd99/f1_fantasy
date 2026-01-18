from pulp.constants import LpStatusOptimal

from common import AssetType
from helpers import load_with_derivations
from linear.strategy_base import VarType
from linear.strategy_factory import factory_strategy
from linear.strategy_zero_stop import StrategyZeroStop
from races.season import factory_season
from races.team import Team
from tests.test_strategy_base import (
    fixture_all_available_drivers,
    fixture_all_available_constructors,
    fixture_asset_prices,
    fixture_pairings,
)


def test_strat_zero_stop_no_moves(
    fixture_all_available_drivers,
    fixture_all_available_constructors,
    fixture_asset_prices,
    fixture_pairings,
):
    strat = StrategyZeroStop(
        team_drivers=["VER", "LEC", "HAM", "ALO"],
        team_constructors=["MCL", "FER"],
        all_available_drivers=fixture_all_available_drivers,
        all_available_constructors=fixture_all_available_constructors,
        all_available_driver_pairs=fixture_pairings,
        prev_available_driver_pairs=fixture_pairings,
        max_cost=100.0,
        max_moves=3,  # This should get forced back to zero by the strat
        prices_assets=fixture_asset_prices,
        derivs_assets={},
        race_num=-1,
    )
    assert strat._max_moves == 0

    problem = strat.execute()

    # Drivers unchanged
    drivers = strat._lp_variables[VarType.TeamDrivers]
    assert drivers["VER"].value() == 1.0
    assert drivers["LEC"].value() == 1.0
    assert drivers["HAM"].value() == 1.0
    assert drivers["ALO"].value() == 1.0
    assert drivers["HUL"].value() == 0.0
    assert drivers["MAG"].value() == 0.0
    assert drivers["BOT"].value() == 0.0
    assert drivers["NOR"].value() == 0.0
    assert drivers["PIA"].value() == 0.0
    assert drivers["TSU"].value() == 0.0

    # Constructors unchanged
    constructors = strat._lp_variables[VarType.TeamConstructors]
    assert constructors["MCL"].value() == 1.0
    assert constructors["FER"].value() == 1.0
    assert constructors["RED"].value() == 0.0
    assert constructors["MER"].value() == 0.0
    assert constructors["AST"].value() == 0.0

    # Plenty of spare budget left
    assert problem.objective.value() == 20.0
    assert strat._lp_variables[VarType.UnusedBudget].value() == 80.0


def test_strat_zero_stop_unavailable_driver(
    fixture_all_available_drivers,
    fixture_all_available_constructors,
    fixture_asset_prices,
    fixture_pairings,
):
    strat = StrategyZeroStop(
        team_drivers=["VER", "LEC", "HAM", "XXX"],
        team_constructors=["MCL", "FER"],
        all_available_drivers=fixture_all_available_drivers,
        all_available_constructors=fixture_all_available_constructors,
        all_available_driver_pairs=fixture_pairings,
        prev_available_driver_pairs=fixture_pairings,
        max_cost=100.0,
        max_moves=3,  # This should get forced back to zero by the strat
        prices_assets=fixture_asset_prices,
        derivs_assets={},
        race_num=-1,
    )
    # One driver forced to change
    assert strat._max_moves == 1

    problem = strat.execute()

    # Drivers changed
    drivers = strat._lp_variables[VarType.TeamDrivers]
    assert drivers["VER"].value() == 1.0
    assert drivers["LEC"].value() == 1.0
    assert drivers["HAM"].value() == 1.0
    assert drivers["ALO"].value() == 0.0
    assert drivers["HUL"].value() == 0.0
    assert drivers["MAG"].value() == 0.0
    assert drivers["BOT"].value() == 0.0
    assert drivers["NOR"].value() == 0.0
    assert drivers["PIA"].value() == 1.0  # One move was allowed, brought in highest driver
    assert drivers["TSU"].value() == 0.0

    # Constructors unchanged
    constructors = strat._lp_variables[VarType.TeamConstructors]
    assert constructors["MCL"].value() == 1.0
    assert constructors["FER"].value() == 1.0
    assert constructors["RED"].value() == 0.0
    assert constructors["MER"].value() == 0.0
    assert constructors["AST"].value() == 0.0

    # Plenty of spare budget left
    assert problem.objective.value() == 26.0
    assert strat._lp_variables[VarType.UnusedBudget].value() == 74.0


def test_strategy_zero_stop_change_real_data():
    (df_driver_ppm, df_constructor_ppm, df_driver_pairs) = load_with_derivations(season=2025)
    
    season = factory_season(
        df_driver_ppm,
        df_constructor_ppm,
        df_driver_pairs,
        2025,
    )

    # LAW moved from RED to VRB, between races 2 and 3
    race_2 = season.races[2]
    race_3 = season.races[3]

    team = Team(num_drivers=2, num_constructors=1, unused_budget=50.0)
    team.add_asset(AssetType.DRIVER, "LAW@RED")
    team.add_asset(AssetType.DRIVER, "VER@RED")
    team.add_asset(AssetType.CONSTRUCTOR, "MCL")

    strat = factory_strategy(race_3, race_2, team, StrategyZeroStop, max_moves=2)
    assert strat._max_moves == 1

    model = strat.execute()
    assert model.status == LpStatusOptimal

    # Drivers changed
    drivers = strat._lp_variables[VarType.TeamDrivers]
    assert drivers["LAW@RED"].value() == 0.0  # not selected
    assert drivers["LAW@VRB"].value() == 0.0  # not selected
    assert drivers["VER@RED"].value() == 1.0
    assert drivers["NOR@MCL"].value() == 1.0  # change to this driver with our only allowed move

    # Constructors unchanged
    constructors = strat._lp_variables[VarType.TeamConstructors]
    assert constructors["MCL"].value() == 1.0
