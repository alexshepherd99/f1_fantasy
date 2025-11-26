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
        max_cost=100.0,
        max_moves=3,
        prices_assets=fixture_asset_prices,
    )
    problem = strat.execute("max_budget_strat_3")

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
