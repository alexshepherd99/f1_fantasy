import pytest
import numpy as np
from pulp import LpProblem, lpSum, LpMaximize
from copy import deepcopy

from linear.strategy_base import StrategyBase, COST_PROHIBITIVE, VarType


@pytest.fixture
def fixture_asset_prices() -> dict[str, float]:
    return {
        # Drivers
        "VER": 1.0,
        "LEC": 2.0,
        "HAM": 3.0,
        "ALO": 4.0,
        "HUL": 6.5,
        "MAG": 7.0,
        "BOT": 8.0,
        "NOR": 9.0,
        "PIA": 10.0,
        "TSU": 9.5,
        # Constructors
        "MCL": 4.0,
        "FER": 6.0,
        "RED": 5.0,
        "MER": 7.0,
        "AST": 12.0,
    }


@pytest.fixture
def fixture_all_available_drivers() -> list[str]:
    return ["VER", "LEC", "HAM", "ALO", "HUL", "MAG", "BOT", "NOR", "PIA", "TSU"]


@pytest.fixture
def fixture_all_available_constructors() -> list[str]:
    return ["MCL", "FER", "RED", "MER", "AST"]


@pytest.fixture
def fixture_pairings() -> dict[str, str]:
    return {
        "VER": "RED",
        "LEC": "FER",
        "HAM": "FER",
        "ALO": "AST",
        "HUL": "AST",
        "MAG": "MER",
        "BOT": "MER",
        "NOR": "MCL",
        "PIA": "MCL",
        "TSU": "RED",
    }


class StrategyDummy(StrategyBase):
    def get_problem(self) -> LpProblem:
        return LpProblem()

    
def test_construct_strategy(
        fixture_all_available_drivers,
        fixture_all_available_constructors,
        fixture_asset_prices,
        fixture_pairings,
    ):
    # Team constructors all present in all available constructors
    with pytest.raises(ValueError) as excinfo:
        StrategyDummy(
            team_drivers=[],
            team_constructors=["???"],
            all_available_drivers=[],
            all_available_constructors=fixture_all_available_constructors,
            all_available_driver_pairs=fixture_pairings,
            max_cost=0.0,
            max_moves=2,
            prices_assets={},
            derivs_assets={}
        );
    assert str(excinfo.value) == "Cannot find team constructor ??? in all available constructors"

    # Team count drivers greater than count of available drivers
    with pytest.raises(ValueError) as excinfo:
        StrategyDummy(
            team_drivers=["A", "A", "A", "A", "A", "A", "A", "A", "A", "A", "A",],
            team_constructors=[],
            all_available_drivers=fixture_all_available_drivers,
            all_available_constructors=[],
            all_available_driver_pairs=fixture_pairings,
            max_cost=0.0,
            max_moves=2,
            prices_assets={},
            derivs_assets={}
        )
    assert str(excinfo.value) == "Team count of 11 is greater than 10 available drivers"

    # Team count constructors greater than count of available constructors
    with pytest.raises(ValueError) as excinfo:
        StrategyDummy(
            team_drivers=[],
            team_constructors=["MCL", "MCL", "MCL", "MCL", "MCL", "MCL",],
            all_available_drivers=[],
            all_available_constructors=fixture_all_available_constructors,
            all_available_driver_pairs=fixture_pairings,
            max_cost=0.0,
            max_moves=2,
            prices_assets={},
            derivs_assets={}
        )
    assert str(excinfo.value) == "Team count of 6 is greater than 5 available constructors"

    # All available drivers have a price
    with pytest.raises(ValueError) as excinfo:
        StrategyDummy(
            team_drivers=[],
            team_constructors=[],
            all_available_drivers=fixture_all_available_drivers + ["XXX"],
            all_available_constructors=[],
            all_available_driver_pairs=fixture_pairings,
            max_cost=0.0,
            max_moves=2,
            prices_assets=fixture_asset_prices,
            derivs_assets={}
        )
    assert str(excinfo.value) == "Driver XXX does not have a price"

    # All available constructors have a price
    with pytest.raises(ValueError) as excinfo:
        StrategyDummy(
            team_drivers=[],
            team_constructors=[],
            all_available_drivers=[],
            all_available_constructors=fixture_all_available_constructors + ["XXX"],
            all_available_driver_pairs=fixture_pairings,
            max_cost=0.0,
            max_moves=2,
            prices_assets=fixture_asset_prices,
            derivs_assets={}
        )
    assert str(excinfo.value) == "Constructor XXX does not have a price"

    # Team drivers not available in all available drivers have a high price
    sb = StrategyDummy(
        team_drivers=["VER", "RUS"],
        team_constructors=["MCL"],
        all_available_drivers=fixture_all_available_drivers,
        all_available_constructors=fixture_all_available_constructors,
        all_available_driver_pairs=fixture_pairings,
        max_cost=0.0,
        max_moves=2,
        prices_assets=fixture_asset_prices,
        derivs_assets={}
    )
    assert len(sb._prices_assets) == len(fixture_asset_prices) + 1
    assert sb._prices_assets["RUS"] == COST_PROHIBITIVE

    # Everything in price assets is available in either all drivers or all constructors (check both)
    fap2 = fixture_asset_prices.copy()
    fap2["???"] = 99.99
    with pytest.raises(ValueError) as excinfo:
        StrategyDummy(
            team_drivers=[],
            team_constructors=[],
            all_available_drivers=fixture_all_available_drivers,
            all_available_constructors=fixture_all_available_constructors,
            all_available_driver_pairs=fixture_pairings,
            max_cost=0.0,
            max_moves=2,
            prices_assets=fap2,
            derivs_assets={}
        )
    assert str(excinfo.value) == "Asset ??? has a price but is not in available drivers or constructors"

    # All driver pairs keys are in all available drivers
    with pytest.raises(ValueError) as excinfo:
        dp = fixture_pairings.copy()
        dp["XXX"] = "MCL"
        StrategyDummy(
            team_drivers=[],
            team_constructors=[],
            all_available_drivers=fixture_all_available_drivers,
            all_available_constructors=fixture_all_available_constructors,
            all_available_driver_pairs=dp,
            max_cost=0.0,
            max_moves=2,
            prices_assets=fixture_asset_prices,
            derivs_assets={}
        )
    assert str(excinfo.value) == "Driver from pairing XXX/MCL is not available in all drivers"

    # All driver pairs values are in all available constructors
    with pytest.raises(ValueError) as excinfo:
        dp = fixture_pairings.copy()
        dp["NOR"] = "XXX"
        StrategyDummy(
            team_drivers=[],
            team_constructors=[],
            all_available_drivers=fixture_all_available_drivers,
            all_available_constructors=fixture_all_available_constructors,
            all_available_driver_pairs=dp,
            max_cost=0.0,
            max_moves=2,
            prices_assets=fixture_asset_prices,
            derivs_assets={}
        )
    assert str(excinfo.value) == "Constructor from pairing NOR/XXX is not available in all constructors"

    # All drivers have a matching item in the pairs
    with pytest.raises(ValueError) as excinfo:
        fap2 = fixture_asset_prices.copy()
        fap2["XXX"] = 99.99
        StrategyDummy(
            team_drivers=[],
            team_constructors=[],
            all_available_drivers=fixture_all_available_drivers + ["XXX"],
            all_available_constructors=fixture_all_available_constructors,
            all_available_driver_pairs=fixture_pairings,
            max_cost=0.0,
            max_moves=2,
            prices_assets=fap2,
            derivs_assets={}
        )
    assert str(excinfo.value) == "Driver XXX is not available in driver/constructor pairs"

    # Pairings valid, no exception raised
    sb = StrategyDummy(
        team_drivers=[],
        team_constructors=[],
        all_available_drivers=fixture_all_available_drivers,
        all_available_constructors=fixture_all_available_constructors,
        all_available_driver_pairs=fixture_pairings,
        max_cost=0.0,
        max_moves=2,
        prices_assets=fixture_asset_prices,
        derivs_assets={}
    )


def test_get_team_selection_dict():
    list_available = ["A", "C", "B", "D"]  # intentional unsorted
    list_team = ["B", "E"]
    dict_expected = {
        "A": 0,
        "B": 1,
        "C": 0,
        "D": 0,
        "E": 1,
    }
    dict_result = StrategyBase.get_team_selection_dict(
        list_available,
        list_team
    )
    assert dict_result == dict_expected


def test_initialise_sets_up_lp_variables_and_constraints(
        fixture_all_available_drivers,
        fixture_all_available_constructors,
        fixture_asset_prices,
        fixture_pairings,
    ):
    # Create a strategy with one driver that is no longer available to ensure it's included
    team_drivers = [fixture_all_available_drivers[0], "RUS"]
    team_constructors = [fixture_all_available_constructors[0]]

    sb = StrategyDummy(
        team_drivers=team_drivers,
        team_constructors=team_constructors,
        all_available_drivers=fixture_all_available_drivers,
        all_available_constructors=fixture_all_available_constructors,
        all_available_driver_pairs=fixture_pairings,
        max_cost=1000.0,
        max_moves=2,
        prices_assets=fixture_asset_prices,
        derivs_assets={}
    )

    # Call initialise which should populate _lp_variables and _lp_constraints
    sb.initialise()

    # Verify expected VarType keys present
    assert VarType.TeamDrivers in sb._lp_variables
    assert VarType.TeamConstructors in sb._lp_variables
    assert VarType.TotalCost in sb._lp_variables
    assert VarType.TeamMoves in sb._lp_variables

    # TeamDrivers and TeamConstructors variables should be dict-like and include team items
    drivers_vars = sb._lp_variables[VarType.TeamDrivers]
    constructors_vars = sb._lp_variables[VarType.TeamConstructors]

    # All available drivers plus the unavailable team driver should be present
    for d in fixture_all_available_drivers:
        assert d in drivers_vars
    # 'RUS' came from the team but was not in available drivers — it must still be present
    assert "RUS" in drivers_vars

    # All available constructors present
    for c in fixture_all_available_constructors:
        assert c in constructors_vars

    # TotalCost and TeamMoves should be LpAffineExpressions (lpSum returns that)
    from pulp import LpAffineExpression

    assert isinstance(sb._lp_variables[VarType.TotalCost], LpAffineExpression)
    assert isinstance(sb._lp_variables[VarType.TeamMoves], LpAffineExpression)

    # Constraints for sizes and cost/moves should be present
    assert VarType.TotalCost in sb._lp_constraints
    assert VarType.TeamDrivers in sb._lp_constraints
    assert VarType.TeamConstructors in sb._lp_constraints
    assert VarType.TeamMoves in sb._lp_constraints

    # The team drivers constraint should enforce exactly the team driver count
    constraint_drivers = sb._lp_constraints[VarType.TeamDrivers]
    # The right-hand side of the equality is stored as a negative constant on the
    # constraint expression (sum(vars) - RHS == 0), so check for -team_size
    assert constraint_drivers.constant == -len(team_drivers)

    # Execute on this dummy will throw an exception as no objective is set
    with pytest.raises(ValueError) as excinfo:
        sb.execute()
    assert str(excinfo.value) == "Objective function not set in the problem"


class ExecStrategyDummy(StrategyBase):
    def __init__(self, *args, scores=None, **kwargs):
        super().__init__(*args, **kwargs)
        # simple map used by the objective to prefer one driver over another
        self.scores = scores or {}

    def get_problem(self) -> LpProblem:
        # Create a maximisation problem so the solver will pick the highest-score
        # legal team according to the constraints created in initialise()
        problem = LpProblem("ExecStrategyDummy", LpMaximize)

        # Objective uses the already-created LP variables (initialise is called
        # prior to get_objective in execute()). Aim to maximise the total score.
        drivers = self._lp_variables[VarType.TeamDrivers]
        constructors = self._lp_variables[VarType.TeamConstructors]

        terms = []
        for d, var in drivers.items():
            terms.append(self.scores.get(d, 0.0) * var)
        for c, var in constructors.items():
            terms.append(self.scores.get(c, 0.0) * var)

        objective = lpSum(terms)

        problem += objective
        return problem

def test_execute_picks_best_scoring_team():
    # Two drivers available, must pick exactly 1 driver and 1 constructor
    drivers = ["A", "B"]
    constructors = ["C1"]
    pairings = {"A": "C1", "B": "C1"}

    # Prices must be present for all assets (values not important here other
    # than satisfying verify_data_available)
    prices = {"A": 1.0, "B": 1.0, "C1": 1.0}

    # We'll require a team of one driver and one constructor
    team_drivers = ["A"]
    team_constructors = ["C1"]

    # Give B a much higher score so the solver prefers B over initial team-member A
    scores = {"A": 1.0, "B": 10.0, "C1": 0.0}

    s = ExecStrategyDummy(
        team_drivers=team_drivers,
        team_constructors=team_constructors,
        all_available_drivers=drivers,
        all_available_constructors=constructors,
        all_available_driver_pairs=pairings,
        max_cost=1000.0,
        max_moves=2,
        prices_assets=prices,
        derivs_assets={},
        scores=scores,
    )

    # Execute should initialise, add the objective, add constraints and then solve
    model = s.execute()

    # result should be an LpProblem
    assert isinstance(model, LpProblem)

    # After solving, the variables in our bookkeeping should have values. The
    # high-scoring driver 'B' should be chosen (=1) and 'A' should not (=0).
    drivers_vars = s._lp_variables[VarType.TeamDrivers]
    assert float(drivers_vars["B"].value()) == 1.0
    assert float(drivers_vars["A"].value()) == 0.0


def test_verify_data_available():
    with pytest.raises(ValueError, match="Asset LAW has invalid DT of nan"):
        StrategyBase.verify_data_available(
            all_available_drivers = ["LAW"],
            all_available_constructors = ["MCL"],
            data_assets = {"LAW": np.nan, "MCL": 1.0},
            data_type = "DT"
        )

    with pytest.raises(ValueError, match="Asset MCL has invalid DT of bad"):
        StrategyBase.verify_data_available(
            all_available_drivers = ["LAW"],
            all_available_constructors = ["MCL"],
            data_assets = {"LAW": 1.0, "MCL": "bad"},
            data_type = "DT"
        )

    with pytest.raises(ValueError, match="Asset LAW has invalid DT of None"):
        StrategyBase.verify_data_available(
            all_available_drivers = ["LAW"],
            all_available_constructors = ["MCL"],
            data_assets = {"LAW": None, "MCL": 1.0},
            data_type = "DT"
        )


def test_strategy_derivs(
    fixture_all_available_drivers,
    fixture_all_available_constructors,
    fixture_asset_prices,
    fixture_pairings,
):
    derivs_assets = {
        "Deriv1": {
            "VER": 0.1,
            "LEC": 0.2,
            "HAM": 0.3,
            "ALO": 0.4,
            "HUL": 0.5,
            "MAG": 0.6,
            "BOT": 0.7,
            "NOR": 0.8,
            "PIA": 0.9,
            "TSU": 1.0,
            "MCL": 1.1,
            "FER": 1.2,
            "RED": 1.3,
            "MER": 1.4,
            "AST": 1.5,
        },
        "Deriv2": {
            "VER": 0.11,
            "LEC": 0.22,
            "HAM": 0.33,
            "ALO": 0.44,
            "HUL": 0.55,
            "MAG": 0.66,
            "BOT": 0.77,
            "NOR": 0.88,
            "PIA": 0.99,
            "TSU": 1.01,
            "MCL": 1.11,
            "FER": 1.22,
            "RED": 1.33,
            "MER": 1.44,
            "AST": 1.55,
        },
    }

    derivs_assets_missing_driver = deepcopy(derivs_assets)
    derivs_assets_missing_driver["Deriv1"].pop("VER")
    with pytest.raises(ValueError, match="Driver VER does not have a Deriv1"):
        StrategyDummy(
            team_drivers=[],
            team_constructors=[],
            all_available_drivers=fixture_all_available_drivers,
            all_available_constructors=fixture_all_available_constructors,
            all_available_driver_pairs=fixture_pairings,
            max_cost=0.0,
            max_moves=2,
            prices_assets=fixture_asset_prices,
            derivs_assets=derivs_assets_missing_driver
        )

    derivs_assets_missing_constructor = deepcopy(derivs_assets)
    derivs_assets_missing_constructor["Deriv2"].pop("RED")
    with pytest.raises(ValueError, match="Constructor RED does not have a Deriv2"):
        StrategyDummy(
            team_drivers=[],
            team_constructors=[],
            all_available_drivers=fixture_all_available_drivers,
            all_available_constructors=fixture_all_available_constructors,
            all_available_driver_pairs=fixture_pairings,
            max_cost=0.0,
            max_moves=2,
            prices_assets=fixture_asset_prices,
            derivs_assets=derivs_assets_missing_constructor
        )

    sb=StrategyDummy(
        team_drivers=["???"],  # Team driver not available
        team_constructors=[],
        all_available_drivers=fixture_all_available_drivers,
        all_available_constructors=fixture_all_available_constructors,
        all_available_driver_pairs=fixture_pairings,
        max_cost=0.0,
        max_moves=2,
        prices_assets=fixture_asset_prices,
        derivs_assets=derivs_assets
    )
    assert len(sb._derivs_assets.keys()) == 2
    assert len(sb._derivs_assets["Deriv1"].keys()) == 15  # Added for available drivers only
    assert sb._derivs_assets["Deriv2"]["AST"] == 1.55
