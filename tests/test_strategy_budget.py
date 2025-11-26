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
    problem = strat.execute("Maximize Budget Strategy - 3 swaps")
    assert problem.objective.value() == 100.0
    
