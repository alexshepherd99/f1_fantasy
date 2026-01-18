from pulp.constants import LpStatusOptimal

from linear.strategy_base import VarType
from tests.test_strategy_base import (
    fixture_all_available_drivers,
    fixture_all_available_constructors,
    fixture_asset_prices,
    fixture_pairings,
)
from linear.strategy_budget import StrategyMaxBudget


def test_strat_budget_three_swaps(
    fixture_all_available_drivers,
    fixture_all_available_constructors,
    fixture_asset_prices,
    fixture_pairings,
):
    strat = StrategyMaxBudget(
        team_drivers=["VER", "LEC", "HAM", "ALO"],
        team_constructors=["MCL", "FER"],
        all_available_drivers=fixture_all_available_drivers,
        all_available_constructors=fixture_all_available_constructors,
        all_available_driver_pairs=fixture_pairings,
        prev_available_driver_pairs=fixture_pairings,
        max_cost=100.0,
        max_moves=3,
        prices_assets=fixture_asset_prices,
        derivs_assets={},
        race_num=-1,
    )
    problem = strat.execute()

    drivers = strat._lp_variables[VarType.TeamDrivers]
    assert drivers["VER"].value() == 0.0
    assert drivers["LEC"].value() == 0.0
    assert drivers["HAM"].value() == 1.0
    assert drivers["ALO"].value() == 1.0
    assert drivers["HUL"].value() == 0.0
    assert drivers["MAG"].value() == 0.0
    assert drivers["BOT"].value() == 0.0
    assert drivers["NOR"].value() == 0.0
    assert drivers["PIA"].value() == 1.0
    assert drivers["TSU"].value() == 1.0

    constructors = strat._lp_variables[VarType.TeamConstructors]
    assert constructors["MCL"].value() == 0.0
    assert constructors["FER"].value() == 1.0
    assert constructors["RED"].value() == 0.0
    assert constructors["MER"].value() == 0.0
    assert constructors["AST"].value() == 1.0

    assert problem.objective.value() == 44.5
    assert strat._lp_variables[VarType.UnusedBudget].value() == 55.5


def test_strat_budget_limited_cost(
    fixture_all_available_drivers,
    fixture_all_available_constructors,
    fixture_asset_prices,
    fixture_pairings,
):
    strat = StrategyMaxBudget(
        team_drivers=["VER", "LEC", "HAM", "ALO"],
        team_constructors=["MCL", "FER"],
        all_available_drivers=fixture_all_available_drivers,
        all_available_constructors=fixture_all_available_constructors,
        all_available_driver_pairs=fixture_pairings,
        prev_available_driver_pairs=fixture_pairings,
        max_cost=40.0,
        max_moves=3,
        prices_assets=fixture_asset_prices,
        derivs_assets={},
        race_num=-1,
    )
    problem = strat.execute()
    assert problem.status == LpStatusOptimal

    # Unbeknown to me at the time of writing this test, there are actually two different solutions to this strategy / team
    # combination, and when I ran it for the first time on an ARM-based CPU, the alternative solution was found.  Instead of
    # testing each driver and constructor individually, just check the aggregate solution.

    drivers = strat._lp_variables[VarType.TeamDrivers]
    constructors = strat._lp_variables[VarType.TeamConstructors]

    total_value = 0.0
    driver_count = 0
    constructor_count = 0

    for d in drivers.keys():
        if drivers[d].value() > 0.5:  # Catch any odd large numbers
            driver_count += 1
            total_value += fixture_asset_prices[d]

    for c in constructors.keys():
        if constructors[c].value() > 0.5:  # Catch any odd large numbers
            constructor_count += 1
            total_value += fixture_asset_prices[c]

    assert driver_count == 4
    assert constructor_count == 2
    assert total_value == 40.0

    assert problem.objective.value() == 40.0
    assert strat._lp_variables[VarType.UnusedBudget].value() == 0.0


def test_strat_budget_no_moves(
    fixture_all_available_drivers,
    fixture_all_available_constructors,
    fixture_asset_prices,
    fixture_pairings,
):
    strat = StrategyMaxBudget(
        team_drivers=["VER", "LEC", "HAM", "ALO"],
        team_constructors=["MCL", "FER"],
        all_available_drivers=fixture_all_available_drivers,
        all_available_constructors=fixture_all_available_constructors,
        all_available_driver_pairs=fixture_pairings,
        prev_available_driver_pairs=fixture_pairings,
        max_cost=100.0,
        max_moves=0,
        prices_assets=fixture_asset_prices,
        derivs_assets={},
        race_num=-1,
    )
    problem = strat.execute()

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

    constructors = strat._lp_variables[VarType.TeamConstructors]
    assert constructors["MCL"].value() == 1.0
    assert constructors["FER"].value() == 1.0
    assert constructors["RED"].value() == 0.0
    assert constructors["MER"].value() == 0.0
    assert constructors["AST"].value() == 0.0

    assert problem.objective.value() == 20.0
    assert strat._lp_variables[VarType.UnusedBudget].value() == 80.0


def test_strat_budget_driver_unavailable(
    fixture_all_available_drivers,
    fixture_all_available_constructors,
    fixture_asset_prices,
    fixture_pairings,
):
    strat = StrategyMaxBudget(
        team_drivers=["RUS", "LEC", "HAM", "ALO"],  # RUS is unavailable
        team_constructors=["MCL", "FER"],
        all_available_drivers=fixture_all_available_drivers,
        all_available_constructors=fixture_all_available_constructors,
        all_available_driver_pairs=fixture_pairings,
        prev_available_driver_pairs=fixture_pairings,
        max_cost=100.0,
        max_moves=1,
        prices_assets=fixture_asset_prices,
        derivs_assets={},
        race_num=-1,
    )
    problem = strat.execute()

    drivers = strat._lp_variables[VarType.TeamDrivers]
    assert drivers["RUS"].value() == 0.0
    assert drivers["VER"].value() == 0.0
    assert drivers["LEC"].value() == 1.0
    assert drivers["HAM"].value() == 1.0
    assert drivers["ALO"].value() == 1.0
    assert drivers["HUL"].value() == 0.0
    assert drivers["MAG"].value() == 0.0
    assert drivers["BOT"].value() == 0.0
    assert drivers["NOR"].value() == 0.0
    assert drivers["PIA"].value() == 1.0
    assert drivers["TSU"].value() == 0.0

    constructors = strat._lp_variables[VarType.TeamConstructors]
    assert constructors["MCL"].value() == 1.0
    assert constructors["FER"].value() == 1.0
    assert constructors["RED"].value() == 0.0
    assert constructors["MER"].value() == 0.0
    assert constructors["AST"].value() == 0.0

    assert problem.objective.value() == 29.0
    assert strat._lp_variables[VarType.UnusedBudget].value() == 71.0
