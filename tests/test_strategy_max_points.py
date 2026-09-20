from pulp.constants import LpStatusOptimal
import pytest

from linear.strategy_base import VarType
from linear.strategy_max_points import StrategyMaxPoints
from tests.test_strategy_base import (
    fixture_all_available_drivers,
    fixture_all_available_constructors,
    fixture_asset_prices,
    fixture_pairings,
)

DERIV_POINTS = "Points Cumulative (3)"


def factory_test_strategy(
    points_derivs: dict[str, float],
    prices: dict[str, float],
    drivers: list[str],
    constructors: list[str],
    pairings: dict[str, str],
    max_cost: float = 100.0,
    max_moves: int = 3,
    race_num: int = -1,
) -> StrategyMaxPoints:
    """Build a StrategyMaxPoints over the shared fixtures, varying only what a test cares about."""
    return StrategyMaxPoints(
        team_drivers=["VER", "LEC", "HAM", "ALO"],
        team_constructors=["MCL", "FER"],
        all_available_drivers=drivers,
        all_available_constructors=constructors,
        all_available_driver_pairs=pairings,
        prev_available_driver_pairs=pairings,
        max_cost=max_cost,
        max_moves=max_moves,
        prices_assets=prices,
        derivs_assets={DERIV_POINTS: points_derivs},
        race_num=race_num,
        season_year=-1,
    )


def test_strat_max_points_basic_optimization(
    fixture_all_available_drivers,
    fixture_all_available_constructors,
    fixture_asset_prices,
    fixture_pairings,
):
    """The objective selects the highest rolling-points assets available."""
    points_derivs = {
        # Drivers - VER, NOR, PIA and HAM lead
        "VER": 50.0,
        "LEC": 30.0,
        "HAM": 35.0,
        "ALO": 20.0,
        "HUL": 25.0,
        "MAG": 15.0,
        "BOT": 10.0,
        "NOR": 45.0,
        "PIA": 40.0,
        "TSU": 28.0,
        # Constructors - MCL and RED lead
        "MCL": 60.0,
        "FER": 35.0,
        "RED": 55.0,
        "MER": 30.0,
        "AST": 25.0,
    }

    strat = factory_test_strategy(
        points_derivs,
        fixture_asset_prices,
        fixture_all_available_drivers,
        fixture_all_available_constructors,
        fixture_pairings,
    )
    problem = strat.execute()
    assert problem.status == LpStatusOptimal

    drivers = strat._lp_variables[VarType.TeamDrivers]
    assert drivers["VER"].value() == 1.0
    assert drivers["NOR"].value() == 1.0
    assert drivers["PIA"].value() == 1.0
    assert drivers["HAM"].value() == 1.0

    constructors = strat._lp_variables[VarType.TeamConstructors]
    assert constructors["MCL"].value() == 1.0
    assert constructors["RED"].value() == 1.0

    expected_points = 50.0 + 45.0 + 40.0 + 35.0 + 60.0 + 55.0
    assert problem.objective.value() == expected_points


def test_strat_max_points_is_not_swayed_by_price(
    fixture_all_available_drivers,
    fixture_all_available_constructors,
    fixture_asset_prices,
    fixture_pairings,
):
    """Points alone decide, distinguishable from both price and points-per-price.

    The fixture is built so three objectives disagree. On points the winners are
    the mid-priced NOR/BOT/MAG/HUL; a price objective would take the expensive
    PIA/TSU/AST, which score almost nothing; and a points-per-price objective -
    what StrategyMaxP2PM optimises - would take the cheap VER, whose ratio of 20
    is the best in the field.
    """
    points_derivs = {
        # Cheap, excellent points per million, mediocre in absolute terms
        "VER": 20.0,   # price 1.0
        "LEC": 18.0,   # price 2.0
        "HAM": 16.0,   # price 3.0
        "ALO": 14.0,   # price 4.0
        # Mid-priced and the best absolute scorers
        "HUL": 75.0,   # price 6.5
        "MAG": 80.0,   # price 7.0
        "BOT": 85.0,   # price 8.0
        "NOR": 90.0,   # price 9.0
        # The most expensive drivers, scoring almost nothing
        "PIA": 5.0,    # price 10.0
        "TSU": 5.0,    # price 9.5
        "MER": 70.0,   # price 7.0
        "MCL": 30.0,   # price 4.0
        "FER": 28.0,
        "RED": 26.0,
        "AST": 5.0,    # price 12.0, the most expensive constructor
    }

    strat = factory_test_strategy(
        points_derivs,
        fixture_asset_prices,
        fixture_all_available_drivers,
        fixture_all_available_constructors,
        fixture_pairings,
        max_moves=6,  # a full rebuild of the fixture team
    )
    problem = strat.execute()
    assert problem.status == LpStatusOptimal

    drivers = strat._lp_variables[VarType.TeamDrivers]
    for best_on_points in ["NOR", "BOT", "MAG", "HUL"]:
        assert drivers[best_on_points].value() == 1.0
    # Expensive but low scoring, which a price objective would have taken
    assert drivers["PIA"].value() == 0.0
    assert drivers["TSU"].value() == 0.0
    # Best points per million in the field, which P2PM's divisor would have favoured
    assert drivers["VER"].value() == 0.0

    constructors = strat._lp_variables[VarType.TeamConstructors]
    assert constructors["MER"].value() == 1.0
    assert constructors["MCL"].value() == 1.0
    assert constructors["AST"].value() == 0.0

    expected_points = 90.0 + 85.0 + 80.0 + 75.0 + 70.0 + 30.0
    assert problem.objective.value() == expected_points


def test_strat_max_points_treats_a_none_derivation_as_zero(
    fixture_all_available_drivers,
    fixture_all_available_constructors,
    fixture_asset_prices,
    fixture_pairings,
):
    """An available asset whose derivation is None scores zero rather than raising.

    Derivations skip StrategyBase's float check (`check_type=False`), so a None
    value reaches the objective and has to be filled.
    """
    points_derivs = {
        "VER": 50.0,
        "LEC": 30.0,
        "HAM": 35.0,
        "ALO": 20.0,
        "HUL": 25.0,
        "MAG": 15.0,
        "BOT": None,  # no rolling points for this asset
        "NOR": 45.0,
        "PIA": 40.0,
        "TSU": 28.0,
        "MCL": 60.0,
        "FER": 35.0,
        "RED": 55.0,
        "MER": 30.0,
        "AST": None,  # nor this one
    }

    strat = factory_test_strategy(
        points_derivs,
        fixture_asset_prices,
        fixture_all_available_drivers,
        fixture_all_available_constructors,
        fixture_pairings,
    )
    problem = strat.execute()
    assert problem.status == LpStatusOptimal

    # The None assets are worth nothing, so they are not selected
    assert strat._lp_variables[VarType.TeamDrivers]["BOT"].value() == 0.0
    assert strat._lp_variables[VarType.TeamConstructors]["AST"].value() == 0.0

    expected_points = 50.0 + 45.0 + 40.0 + 35.0 + 60.0 + 55.0
    assert problem.objective.value() == expected_points


def test_strat_max_points_respects_the_budget_cap(
    fixture_all_available_drivers,
    fixture_all_available_constructors,
    fixture_asset_prices,
    fixture_pairings,
):
    """A tight budget binds, and points decide within it.

    The best scorers here are also the cheapest, so the points-optimal team costs
    19.0 and leaves 6.0 unspent. That distinguishes the objective from one that
    merely fills the budget, which would spend close to the 25.0 cap.
    """
    points_derivs = {
        "VER": 50.0,   # price 1.0
        "LEC": 40.0,   # price 2.0
        "HAM": 30.0,   # price 3.0
        "ALO": 20.0,   # price 4.0
        "HUL": 5.0,
        "MAG": 5.0,
        "BOT": 5.0,
        "NOR": 5.0,
        "PIA": 5.0,
        "TSU": 5.0,
        "MCL": 50.0,   # price 4.0
        "RED": 40.0,   # price 5.0
        "FER": 5.0,
        "MER": 5.0,
        "AST": 5.0,
    }

    # The cheapest feasible team costs 19.0, so 25.0 is feasible but tight
    strat = factory_test_strategy(
        points_derivs,
        fixture_asset_prices,
        fixture_all_available_drivers,
        fixture_all_available_constructors,
        fixture_pairings,
        max_cost=25.0,
        max_moves=6,
    )
    problem = strat.execute()
    assert problem.status == LpStatusOptimal

    drivers = strat._lp_variables[VarType.TeamDrivers]
    for cheap_and_best in ["VER", "LEC", "HAM", "ALO"]:
        assert drivers[cheap_and_best].value() == 1.0

    constructors = strat._lp_variables[VarType.TeamConstructors]
    assert constructors["MCL"].value() == 1.0
    assert constructors["RED"].value() == 1.0

    total_cost = strat._lp_variables[VarType.TotalCost].value()
    assert total_cost == pytest.approx(19.0, abs=1e-3)
    assert strat._lp_variables[VarType.UnusedBudget].value() == pytest.approx(6.0, abs=1e-3)

    expected_points = 50.0 + 40.0 + 30.0 + 20.0 + 50.0 + 40.0
    assert problem.objective.value() == expected_points


def test_strat_max_points_respects_max_moves(
    fixture_all_available_drivers,
    fixture_all_available_constructors,
    fixture_asset_prices,
    fixture_pairings,
):
    """With no moves allowed the team is held, however good the alternatives are."""
    points_derivs = {
        "VER": 10.0,
        "LEC": 10.0,
        "HAM": 10.0,
        "ALO": 10.0,
        "HUL": 25.0,
        "MAG": 15.0,
        "BOT": 90.0,  # far better, but unreachable
        "NOR": 95.0,  # likewise
        "PIA": 99.0,
        "TSU": 28.0,
        "MCL": 10.0,
        "FER": 10.0,
        "RED": 99.0,  # likewise
        "MER": 30.0,
        "AST": 25.0,
    }

    strat = factory_test_strategy(
        points_derivs,
        fixture_asset_prices,
        fixture_all_available_drivers,
        fixture_all_available_constructors,
        fixture_pairings,
        max_moves=0,
    )
    problem = strat.execute()
    assert problem.status == LpStatusOptimal

    drivers = strat._lp_variables[VarType.TeamDrivers]
    for held in ["VER", "LEC", "HAM", "ALO"]:
        assert drivers[held].value() == 1.0

    constructors = strat._lp_variables[VarType.TeamConstructors]
    assert constructors["MCL"].value() == 1.0
    assert constructors["FER"].value() == 1.0

    expected_points = 10.0 + 10.0 + 10.0 + 10.0 + 10.0 + 10.0
    assert problem.objective.value() == expected_points


def test_strat_max_points_resets_moves_at_race_four(
    fixture_all_available_drivers,
    fixture_all_available_constructors,
    fixture_asset_prices,
    fixture_pairings,
):
    """Race 4 plays the unlimited-moves chip, allowing a full team rebuild.

    Copied from StrategyMaxP2PM so the paired back-test measures the change of
    objective alone, rather than that plus whether the chip was played.
    """
    points_derivs = {
        d: 1.0
        for d in fixture_all_available_drivers + fixture_all_available_constructors
    }

    strat = factory_test_strategy(
        points_derivs,
        fixture_asset_prices,
        fixture_all_available_drivers,
        fixture_all_available_constructors,
        fixture_pairings,
        max_moves=2,
        race_num=4,
    )

    # Four drivers plus two constructors in the fixture team
    assert strat._max_moves == 6


def test_strat_max_points_does_not_reset_moves_before_race_four(
    fixture_all_available_drivers,
    fixture_all_available_constructors,
    fixture_asset_prices,
    fixture_pairings,
):
    """Race 3 is left alone: the rolling window is not yet fully populated."""
    points_derivs = {
        d: 1.0
        for d in fixture_all_available_drivers + fixture_all_available_constructors
    }

    strat = factory_test_strategy(
        points_derivs,
        fixture_asset_prices,
        fixture_all_available_drivers,
        fixture_all_available_constructors,
        fixture_pairings,
        max_moves=2,
        race_num=3,
    )

    assert strat._max_moves == 2


def test_strat_max_points_nominates_the_highest_rolling_points_driver(
    fixture_all_available_drivers,
    fixture_all_available_constructors,
    fixture_asset_prices,
    fixture_pairings,
):
    """DRS goes to the selected driver with the most rolling points, as StrategyMaxP2PM does.

    The rule is matched to P2PM's deliberately, so that a back-test between the two
    compares their objectives and nothing else. Without it the strategy nominates
    nobody and Team falls back to the highest-priced driver, which is a second
    difference and would confound the comparison.
    """
    points_derivs = {
        d: 5.0 for d in fixture_all_available_drivers + fixture_all_available_constructors
    }
    # LEC leads among the current team, which max_moves=0 holds in place
    points_derivs.update({"VER": 10.0, "LEC": 50.0, "HAM": 20.0, "ALO": 5.0})

    strat = factory_test_strategy(
        points_derivs,
        fixture_asset_prices,
        fixture_all_available_drivers,
        fixture_all_available_constructors,
        fixture_pairings,
        max_moves=0,
    )
    strat.execute()

    assert strat.get_drs_driver() == "LEC"


def test_strat_max_points_nominates_only_a_driver_it_owns(
    fixture_all_available_drivers,
    fixture_all_available_constructors,
    fixture_asset_prices,
    fixture_pairings,
):
    """The best driver in the field is not nominated unless the team holds them.

    Team.get_drs_points() checks the nominee is in the race, not that the team owns
    them, so an unowned nominee's points would be added silently.
    """
    points_derivs = {
        d: 5.0 for d in fixture_all_available_drivers + fixture_all_available_constructors
    }
    points_derivs.update({"VER": 10.0, "LEC": 50.0, "HAM": 20.0, "ALO": 5.0})
    # Far and away the best in the field, and deliberately not on the team
    points_derivs["PIA"] = 999.0

    strat = factory_test_strategy(
        points_derivs,
        fixture_asset_prices,
        fixture_all_available_drivers,
        fixture_all_available_constructors,
        fixture_pairings,
        max_moves=0,
    )
    strat.execute()

    assert strat._lp_variables[VarType.TeamDrivers]["PIA"].value() == 0.0
    assert strat.get_drs_driver() == "LEC"


def test_strat_max_points_nominates_nobody_when_no_driver_has_points(
    fixture_all_available_drivers,
    fixture_all_available_constructors,
    fixture_asset_prices,
    fixture_pairings,
):
    """With no points to go on, the choice is left to Team, which picks on price."""
    points_derivs = {
        d: 0.0 for d in fixture_all_available_drivers + fixture_all_available_constructors
    }

    strat = factory_test_strategy(
        points_derivs,
        fixture_asset_prices,
        fixture_all_available_drivers,
        fixture_all_available_constructors,
        fixture_pairings,
        max_moves=0,
    )
    strat.execute()

    assert strat.get_drs_driver() == ""
