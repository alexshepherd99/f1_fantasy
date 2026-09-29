import pytest

from linear.strategy_p2pm import StrategyMaxP2PM
from linear.strategy_p2pm_no_reset import StrategyMaxP2PMNoReset
from tests.test_strategy_base import (
    fixture_all_available_drivers,
    fixture_all_available_constructors,
    fixture_asset_prices,
    fixture_pairings,
)


def factory_test_strategy(
    strategy: type[StrategyMaxP2PM],
    drivers: list[str],
    constructors: list[str],
    prices: dict[str, float],
    pairings: dict[str, str],
    race_num: int,
    max_moves: int = 2,
) -> StrategyMaxP2PM:
    """Build a P2PM strategy over the shared fixtures, varying only the class and race."""
    p2pm_derivs = {d: 1.0 for d in drivers + constructors}
    return strategy(
        team_drivers=["VER", "LEC", "HAM", "ALO"],
        team_constructors=["MCL", "FER"],
        all_available_drivers=drivers,
        all_available_constructors=constructors,
        all_available_driver_pairs=pairings,
        prev_available_driver_pairs=pairings,
        max_cost=100.0,
        max_moves=max_moves,
        prices_assets=prices,
        derivs_assets={"P2PM Cumulative (3)": p2pm_derivs},
        race_num=race_num,
        season_year=-1,
    )


def test_strat_p2pm_no_reset_keeps_max_moves_at_race_four(
    fixture_all_available_drivers,
    fixture_all_available_constructors,
    fixture_asset_prices,
    fixture_pairings,
):
    """Race 4 keeps the moves it was given, where the parent allows a full rebuild."""
    strat = factory_test_strategy(
        StrategyMaxP2PMNoReset,
        fixture_all_available_drivers,
        fixture_all_available_constructors,
        fixture_asset_prices,
        fixture_pairings,
        race_num=4,
        max_moves=3,
    )

    assert strat._max_moves == 3


@pytest.mark.parametrize("race_num", [3, 4, 5])
def test_strat_p2pm_no_reset_leaves_the_parent_unchanged(
    fixture_all_available_drivers,
    fixture_all_available_constructors,
    fixture_asset_prices,
    fixture_pairings,
    race_num,
):
    """Subclassing does not switch the chip off in StrategyMaxP2PM itself."""
    strat = factory_test_strategy(
        StrategyMaxP2PM,
        fixture_all_available_drivers,
        fixture_all_available_constructors,
        fixture_asset_prices,
        fixture_pairings,
        race_num=race_num,
    )

    assert strat._max_moves == (6 if race_num == 4 else 2)


@pytest.mark.parametrize("race_num", [3, 5])
def test_strat_p2pm_no_reset_matches_the_parent_away_from_race_four(
    fixture_all_available_drivers,
    fixture_all_available_constructors,
    fixture_asset_prices,
    fixture_pairings,
    race_num,
):
    """Every race but the fourth is left exactly as the parent sets it."""
    args = (
        fixture_all_available_drivers,
        fixture_all_available_constructors,
        fixture_asset_prices,
        fixture_pairings,
    )
    parent = factory_test_strategy(StrategyMaxP2PM, *args, race_num=race_num)
    child = factory_test_strategy(StrategyMaxP2PMNoReset, *args, race_num=race_num)

    assert child._max_moves == parent._max_moves == 2
