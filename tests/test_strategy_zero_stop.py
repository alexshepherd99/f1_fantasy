from linear.strategy_base import VarType
from linear.strategy_zero_stop import StrategyZeroStop
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
        max_cost=100.0,
        max_moves=3,  # This should get forced back to zero by the strat
        prices_assets=fixture_asset_prices,
        derivs_assets={}
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
        max_cost=100.0,
        max_moves=3,  # This should get forced back to zero by the strat
        prices_assets=fixture_asset_prices,
        derivs_assets={}
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