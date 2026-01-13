from linear.strategy_base import VarType
from linear.strategy_p2pm import StrategyMaxP2PM
from tests.test_strategy_base import (
    fixture_all_available_drivers,
    fixture_all_available_constructors,
    fixture_asset_prices,
    fixture_pairings,
)


def test_strat_p2pm_basic_optimization(
    fixture_all_available_drivers,
    fixture_all_available_constructors,
    fixture_asset_prices,
    fixture_pairings,
):
    """Test basic P2PM optimization with P2PM derivations provided."""
    # Create P2PM derivations - higher values indicate better P2PM
    p2pm_derivs = {
        # Drivers - VER and NOR have best P2PM
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
        # Constructors - RED and MCL have best P2PM
        "MCL": 60.0,
        "FER": 35.0,
        "RED": 55.0,
        "MER": 30.0,
        "AST": 25.0,
    }
    
    strat = StrategyMaxP2PM(
        team_drivers=["VER", "LEC", "HAM", "ALO"],
        team_constructors=["MCL", "FER"],
        all_available_drivers=fixture_all_available_drivers,
        all_available_constructors=fixture_all_available_constructors,
        all_available_driver_pairs=fixture_pairings,
        prev_available_driver_pairs=fixture_pairings,
        max_cost=100.0,
        max_moves=3,
        prices_assets=fixture_asset_prices,
        derivs_assets={"P2PM Cumulative (3)": p2pm_derivs}
    )
    problem = strat.execute()

    # Should select drivers with highest P2PM: VER (50), NOR (45), PIA (40), HAM (35)
    drivers = strat._lp_variables[VarType.TeamDrivers]
    assert drivers["VER"].value() == 1.0
    assert drivers["NOR"].value() == 1.0
    assert drivers["PIA"].value() == 1.0
    assert drivers["HAM"].value() == 1.0

    # Should select constructors with highest P2PM: MCL (60), RED (55)
    constructors = strat._lp_variables[VarType.TeamConstructors]
    assert constructors["MCL"].value() == 1.0
    assert constructors["RED"].value() == 1.0

    # Objective should be sum of selected P2PM values
    expected_p2pm = 50.0 + 45.0 + 40.0 + 35.0 + 60.0 + 55.0
    assert problem.objective.value() == expected_p2pm


def test_get_drs_driver_selects_highest_points(
    fixture_all_available_drivers,
    fixture_all_available_constructors,
    fixture_asset_prices,
    fixture_pairings,
):
    """Ensure get_drs_driver returns selected driver with highest points."""
    # Points derivations - make LEC highest among the current team
    points_derivs = {
        d: 5.0 for d in fixture_all_available_drivers + fixture_all_available_constructors
    }
    points_derivs.update({"VER": 10.0, "LEC": 50.0, "HAM": 20.0, "ALO": 5.0})

    # P2PM can be zero since we fix the team with max_moves=0
    p2pm_derivs = {d: 0.0 for d in fixture_all_available_drivers + fixture_all_available_constructors}

    strat = StrategyMaxP2PM(
        team_drivers=["VER", "LEC", "HAM", "ALO"],
        team_constructors=["MCL", "FER"],
        all_available_drivers=fixture_all_available_drivers,
        all_available_constructors=fixture_all_available_constructors,
        all_available_driver_pairs=fixture_pairings,
        prev_available_driver_pairs=fixture_pairings,
        max_cost=100.0,
        max_moves=0,  # keep team fixed so selected drivers are known
        prices_assets=fixture_asset_prices,
        derivs_assets={
            "P2PM Cumulative (3)": p2pm_derivs,
            "Points Cumulative (3)": points_derivs,
        },
    )
    strat.execute()

    # LEC has the highest points among the selected drivers
    assert strat.get_drs_driver() == "LEC"


def test_get_drs_driver_returns_empty_when_no_points(
    fixture_all_available_drivers,
    fixture_all_available_constructors,
    fixture_asset_prices,
    fixture_pairings,
):
    """If selected drivers have zero points, get_drs_driver returns empty string."""
    points_derivs = {d: 0.0 for d in fixture_all_available_drivers + fixture_all_available_constructors}
    p2pm_derivs = {d: 0.0 for d in fixture_all_available_drivers + fixture_all_available_constructors}

    strat = StrategyMaxP2PM(
        team_drivers=["VER", "LEC", "HAM", "ALO"],
        team_constructors=["MCL", "FER"],
        all_available_drivers=fixture_all_available_drivers,
        all_available_constructors=fixture_all_available_constructors,
        all_available_driver_pairs=fixture_pairings,
        prev_available_driver_pairs=fixture_pairings,
        max_cost=100.0,
        max_moves=0,
        prices_assets=fixture_asset_prices,
        derivs_assets={
            "P2PM Cumulative (3)": p2pm_derivs,
            "Points Cumulative (3)": points_derivs,
        },
    )
    strat.execute()

    # No points among selected drivers -> should return empty string
    assert strat.get_drs_driver() == ""


def test_strat_p2pm_with_cost_constraint(
    fixture_all_available_drivers,
    fixture_all_available_constructors,
    fixture_asset_prices,
    fixture_pairings,
):
    """Test P2PM optimization with tight budget constraint."""
    p2pm_derivs = {
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
        "MCL": 60.0,
        "FER": 35.0,
        "RED": 55.0,
        "MER": 30.0,
        "AST": 25.0,
    }
    
    # Limited budget should force selection of lower-cost, high-P2PM assets
    strat = StrategyMaxP2PM(
        team_drivers=["VER", "LEC", "HAM", "ALO"],
        team_constructors=["MCL", "FER"],
        all_available_drivers=fixture_all_available_drivers,
        all_available_constructors=fixture_all_available_constructors,
        all_available_driver_pairs=fixture_pairings,
        prev_available_driver_pairs=fixture_pairings,
        max_cost=30.0,  # Very tight budget
        max_moves=3,
        prices_assets=fixture_asset_prices,
        derivs_assets={"P2PM Cumulative (3)": p2pm_derivs}
    )
    problem = strat.execute()

    # Verify total cost is within budget
    drivers = strat._lp_variables[VarType.TeamDrivers]
    constructors = strat._lp_variables[VarType.TeamConstructors]
    
    total_cost = sum(
        fixture_asset_prices[d] * drivers[d].value()
        for d in fixture_all_available_drivers
    ) + sum(
        fixture_asset_prices[c] * constructors[c].value()
        for c in fixture_all_available_constructors
    )
    
    assert total_cost <= 30.0
    assert problem.objective.value() > 0  # Should still get some P2PM


def test_strat_p2pm_with_varying_derivations(
    fixture_all_available_drivers,
    fixture_all_available_constructors,
    fixture_asset_prices,
    fixture_pairings,
):
    """Test P2PM optimization with varying P2PM values (some zero, some high)."""
    # P2PM derivations with varying values
    p2pm_derivs = {
        "VER": 50.0,
        "LEC": 5.0,
        "HAM": 35.0,
        "ALO": 0.0,
        "HUL": 25.0,
        "MAG": 2.0,
        "BOT": 0.0,
        "NOR": 45.0,
        "PIA": 40.0,
        "TSU": 0.0,
        "MCL": 60.0,
        "FER": 15.0,
        "RED": 55.0,
        "MER": 10.0,
        "AST": 0.0,
    }
    
    strat = StrategyMaxP2PM(
        team_drivers=["VER", "LEC", "HAM", "ALO"],
        team_constructors=["MCL", "FER"],
        all_available_drivers=fixture_all_available_drivers,
        all_available_constructors=fixture_all_available_constructors,
        all_available_driver_pairs=fixture_pairings,
        prev_available_driver_pairs=fixture_pairings,
        max_cost=100.0,
        max_moves=3,
        prices_assets=fixture_asset_prices,
        derivs_assets={"P2PM Cumulative (3)": p2pm_derivs}
    )
    problem = strat.execute()

    drivers = strat._lp_variables[VarType.TeamDrivers]
    constructors = strat._lp_variables[VarType.TeamConstructors]
    
    # Should select high P2PM drivers
    assert drivers["VER"].value() == 1.0
    assert drivers["NOR"].value() == 1.0
    assert drivers["PIA"].value() == 1.0
    assert drivers["HAM"].value() == 1.0
    
    # Should select high P2PM constructors
    assert constructors["MCL"].value() == 1.0
    assert constructors["RED"].value() == 1.0

    # Objective should be sum of selected P2PM values
    expected_p2pm = 50.0 + 45.0 + 40.0 + 35.0 + 60.0 + 55.0
    assert problem.objective.value() == expected_p2pm


def test_strat_p2pm_no_moves_constraint(
    fixture_all_available_drivers,
    fixture_all_available_constructors,
    fixture_asset_prices,
    fixture_pairings,
):
    """Test P2PM optimization with no moves allowed (team must stay same)."""
    p2pm_derivs = {
        "VER": 50.0,
        "LEC": 80.0,  # Very high, but can't be selected due to moves constraint
        "HAM": 35.0,
        "ALO": 20.0,
        "HUL": 25.0,
        "MAG": 15.0,
        "BOT": 10.0,
        "NOR": 45.0,  # Would prefer this but can't due to moves constraint
        "PIA": 40.0,
        "TSU": 28.0,
        "MCL": 60.0,
        "FER": 100.0,  # Very high, but must keep
        "RED": 55.0,
        "MER": 30.0,
        "AST": 25.0,
    }
    
    strat = StrategyMaxP2PM(
        team_drivers=["VER", "LEC", "HAM", "ALO"],
        team_constructors=["MCL", "FER"],
        all_available_drivers=fixture_all_available_drivers,
        all_available_constructors=fixture_all_available_constructors,
        all_available_driver_pairs=fixture_pairings,
        prev_available_driver_pairs=fixture_pairings,
        max_cost=100.0,
        max_moves=0,  # No moves allowed
        prices_assets=fixture_asset_prices,
        derivs_assets={"P2PM Cumulative (3)": p2pm_derivs}
    )
    problem = strat.execute()

    drivers = strat._lp_variables[VarType.TeamDrivers]
    constructors = strat._lp_variables[VarType.TeamConstructors]
    
    # Team must remain unchanged
    assert drivers["VER"].value() == 1.0
    assert drivers["LEC"].value() == 1.0
    assert drivers["HAM"].value() == 1.0
    assert drivers["ALO"].value() == 1.0

    assert constructors["MCL"].value() == 1.0
    assert constructors["FER"].value() == 1.0

    # Objective should be sum of current team's P2PM values
    expected_p2pm = 50.0 + 80.0 + 35.0 + 20.0 + 60.0 + 100.0
    assert problem.objective.value() == expected_p2pm


def test_strat_p2pm_zero_p2pm_values(
    fixture_all_available_drivers,
    fixture_all_available_constructors,
    fixture_asset_prices,
    fixture_pairings,
):
    """Test P2PM optimization where all P2PM values are zero."""
    p2pm_derivs = {
        d: 0.0 for d in fixture_all_available_drivers + fixture_all_available_constructors
    }
    
    strat = StrategyMaxP2PM(
        team_drivers=["VER", "LEC", "HAM", "ALO"],
        team_constructors=["MCL", "FER"],
        all_available_drivers=fixture_all_available_drivers,
        all_available_constructors=fixture_all_available_constructors,
        all_available_driver_pairs=fixture_pairings,
        prev_available_driver_pairs=fixture_pairings,
        max_cost=100.0,
        max_moves=3,
        prices_assets=fixture_asset_prices,
        derivs_assets={"P2PM Cumulative (3)": p2pm_derivs}
    )
    problem = strat.execute()

    # All assets have P2PM value of 0.0, so objective is None or 0 depending on solver
    # When all coefficients are zero, the solver may return None for the objective value
    assert problem.objective.value() is None or problem.objective.value() == 0.0


def test_strat_p2pm_negative_p2pm_values(
    fixture_all_available_drivers,
    fixture_all_available_constructors,
    fixture_asset_prices,
    fixture_pairings,
):
    """Test P2PM optimization with negative P2PM values."""
    p2pm_derivs = {
        "VER": 50.0,
        "LEC": -10.0,
        "HAM": 35.0,
        "ALO": -20.0,
        "HUL": 25.0,
        "MAG": -5.0,
        "BOT": 10.0,
        "NOR": 45.0,
        "PIA": 40.0,
        "TSU": -15.0,
        "MCL": 60.0,
        "FER": -25.0,
        "RED": 55.0,
        "MER": 30.0,
        "AST": 25.0,
    }
    
    strat = StrategyMaxP2PM(
        team_drivers=["VER", "LEC", "HAM", "ALO"],
        team_constructors=["MCL", "FER"],
        all_available_drivers=fixture_all_available_drivers,
        all_available_constructors=fixture_all_available_constructors,
        all_available_driver_pairs=fixture_pairings,
        prev_available_driver_pairs=fixture_pairings,
        max_cost=100.0,
        max_moves=3,
        prices_assets=fixture_asset_prices,
        derivs_assets={"P2PM Cumulative (3)": p2pm_derivs}
    )
    problem = strat.execute()

    drivers = strat._lp_variables[VarType.TeamDrivers]
    constructors = strat._lp_variables[VarType.TeamConstructors]
    
    # Should select drivers with positive or highest P2PM
    assert drivers["VER"].value() == 1.0
    assert drivers["NOR"].value() == 1.0
    assert drivers["PIA"].value() == 1.0
    assert drivers["HAM"].value() == 1.0
    # Should avoid negative P2PM drivers like TSU, ALO
    assert drivers["TSU"].value() == 0.0
    assert drivers["ALO"].value() == 0.0

    # Should select positive P2PM constructors
    assert constructors["MCL"].value() == 1.0
    assert constructors["RED"].value() == 1.0
    # Should avoid negative P2PM constructors
    assert constructors["FER"].value() == 0.0


def test_strat_p2pm_limited_moves(
    fixture_all_available_drivers,
    fixture_all_available_constructors,
    fixture_asset_prices,
    fixture_pairings,
):
    """Test P2PM optimization with limited moves constraint."""
    p2pm_derivs = {
        "VER": 10.0,
        "LEC": 20.0,
        "HAM": 30.0,
        "ALO": 40.0,
        "HUL": 25.0,
        "MAG": 15.0,
        "BOT": 10.0,
        "NOR": 45.0,
        "PIA": 40.0,
        "TSU": 28.0,
        "MCL": 60.0,
        "FER": 35.0,
        "RED": 55.0,  # Slightly lower than FER to prevent constructor swap with driver change
        "MER": 30.0,
        "AST": 25.0,
    }
    
    # Limited to 1 move - can only swap 1 player
    strat = StrategyMaxP2PM(
        team_drivers=["VER", "LEC", "HAM", "ALO"],
        team_constructors=["MCL", "FER"],
        all_available_drivers=fixture_all_available_drivers,
        all_available_constructors=fixture_all_available_constructors,
        all_available_driver_pairs=fixture_pairings,
        prev_available_driver_pairs=fixture_pairings,
        max_cost=100.0,
        max_moves=1,  # Only 1 move allowed
        prices_assets=fixture_asset_prices,
        derivs_assets={"P2PM Cumulative (3)": p2pm_derivs}
    )
    problem = strat.execute()

    drivers = strat._lp_variables[VarType.TeamDrivers]
    constructors = strat._lp_variables[VarType.TeamConstructors]
    
    # Should bring in highest P2PM available driver with 1 move if it's beneficial
    # NOR (45.0) is best available driver, so should replace lowest current (VER at 10.0)
    assert drivers["NOR"].value() == 1.0
    # Keep three of the four initial drivers
    current_drivers_count = sum(
        drivers[d].value() for d in ["VER", "LEC", "HAM", "ALO"]
    )
    assert current_drivers_count == 3  # Exactly 3 of 4 initial drivers should remain
    
    # Should still optimize P2PM within the moves constraint
    objective_val = problem.objective.value()
    assert objective_val is None or objective_val >= 0


def test_strat_p2pm_with_some_zero_derivations(
    fixture_all_available_drivers,
    fixture_all_available_constructors,
    fixture_asset_prices,
    fixture_pairings,
):
    """Test P2PM optimization with some zero P2PM values."""
    # Complete P2PM derivations with some zero values
    p2pm_derivs = {
        "VER": 50.0,
        "LEC": 0.0,
        "HAM": 35.0,
        "ALO": 0.0,
        "HUL": 25.0,
        "MAG": 0.0,
        "BOT": 0.0,
        "NOR": 45.0,
        "PIA": 40.0,
        "TSU": 0.0,
        "MCL": 60.0,
        "FER": 0.0,
        "RED": 55.0,
        "MER": 30.0,
        "AST": 0.0,
    }
    
    strat = StrategyMaxP2PM(
        team_drivers=["VER", "LEC", "HAM", "ALO"],
        team_constructors=["MCL", "FER"],
        all_available_drivers=fixture_all_available_drivers,
        all_available_constructors=fixture_all_available_constructors,
        all_available_driver_pairs=fixture_pairings,
        prev_available_driver_pairs=fixture_pairings,
        max_cost=100.0,
        max_moves=3,
        prices_assets=fixture_asset_prices,
        derivs_assets={"P2PM Cumulative (3)": p2pm_derivs}
    )
    problem = strat.execute()

    drivers = strat._lp_variables[VarType.TeamDrivers]
    constructors = strat._lp_variables[VarType.TeamConstructors]
    
    # Should select drivers with non-zero P2PM
    assert drivers["VER"].value() == 1.0
    assert drivers["NOR"].value() == 1.0
    assert drivers["PIA"].value() == 1.0
    assert drivers["HAM"].value() == 1.0
    
    # Should select constructors with non-zero P2PM
    assert constructors["MCL"].value() == 1.0
    assert constructors["RED"].value() == 1.0
    
    expected_p2pm = 50.0 + 45.0 + 40.0 + 35.0 + 60.0 + 55.0
    assert problem.objective.value() == expected_p2pm

