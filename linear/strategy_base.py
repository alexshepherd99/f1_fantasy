from abc import ABC, abstractmethod
from pulp import LpAffineExpression, LpProblem, LpVariable, lpSum, PULP_CBC_CMD
from enum import Enum, auto


COST_PROHIBITIVE = 999999.99  # A really big float number that we can never afford


class VarType(Enum):
    TeamDrivers = auto()
    TeamConstructors = auto()
    TeamMoves = auto()
    TotalCost = auto()
    UnusedBudget = auto()


class StrategyBase(ABC):
    def __init__(
        self,
        team_drivers: list[str],
        team_constructors: list[str],
        all_available_drivers: list[str],
        all_available_constructors: list[str],
        all_available_driver_pairs: dict[str, str],
        max_cost: float,
        max_moves: int,
        prices_assets: dict[str, float],
    ) -> None:
        # Check team constructors are available in list of all constructors
        for i in team_constructors:
            if i not in all_available_constructors:
                raise ValueError(f"Cannot find team constructor {i} in all available constructors")
            
        # Check not too many team drivers
        if len(team_drivers) > len(all_available_drivers):
            raise ValueError(f"Team count of {len(team_drivers)} is greater than {len(all_available_drivers)} available drivers")
        
        # Check not too many team constructors
        if len(team_constructors) > len(all_available_constructors):
            raise ValueError(f"Team count of {len(team_constructors)} is greater than {len(all_available_constructors)} available constructors")

        # Checks on price, helper method so we can re-use it
        self.verify_data_available(
            all_available_drivers,
            all_available_constructors,
            prices_assets,
            "price"
        )

        # Check drivers and constructors from pairing are in all lists
        for k,v in all_available_driver_pairs.items():
            if k not in all_available_drivers:
                raise ValueError(f"Driver from pairing {k}/{v} is not available in all drivers")
            if v not in all_available_constructors:
                raise ValueError(f"Constructor from pairing {k}/{v} is not available in all constructors")
            
        # Check all drivers are present in pairings
        for i in all_available_drivers:
            if i not in all_available_driver_pairs.keys():
                raise ValueError(f"Driver {i} is not available in driver/constructor pairs")
            
        # Take a copy of the prices
        self._prices_assets = prices_assets.copy()
        # Any drivers in the team which are no longer available, have a prohibitive price
        for x in team_drivers:
            if x not in self._prices_assets.keys():
                self._prices_assets[x] = COST_PROHIBITIVE

        # Set all parameters
        self._team_drivers = team_drivers
        self._team_constructors = team_constructors
        self._all_available_drivers = all_available_drivers
        self._all_available_constructors = all_available_constructors
        self._all_available_driver_pairs = all_available_driver_pairs
        self._max_cost = max_cost
        self._max_moves = max_moves

        # Collections to support constraints and variables
        self._lp_variables = {}
        self._lp_constraints = {}

    @classmethod
    def verify_data_available(
        cls,
        all_available_drivers: list[str],
        all_available_constructors: list[str],
        data_assets: dict[str, float],
        data_type: str,
    ):
        # All available drivers have a price
        for i in all_available_drivers:
            if i not in data_assets.keys():
                raise ValueError(f"Driver {i} does not have a {data_type}")
            
        # All available constructors have a price
        for i in all_available_constructors:
            if i not in data_assets.keys():
                raise ValueError(f"Constructor {i} does not have a {data_type}")
            
        # Everything with a price is available in either drivers or constructors
        for i in data_assets.keys():
            if (i not in all_available_drivers) and (i not in all_available_constructors):
                raise ValueError(f"Asset {i} has a {data_type} but is not in available drivers or constructors")

    @classmethod
    def get_team_selection_dict(cls, list_assets_available: list[str], list_assets_team: list[str]) -> dict[str, int]:
        all_assets = set(list_assets_available).union(set(list_assets_team))
        selection_dict = dict()
        for i in all_assets:
            if i in list_assets_team:
                selection_dict[i] = 1
            else:
                selection_dict[i] = 0
        return selection_dict

    def initialise(self):
        # Driver and constructor lists need to include available assets, in addition to driver assets which are
        # currently in the team (even if no longer available)
        driver_team = self.get_team_selection_dict(self._all_available_drivers, self._team_drivers)
        constructor_team = self.get_team_selection_dict(self._all_available_constructors, self._team_constructors)
        driver_list = list(driver_team.keys())
        constructor_list = list(constructor_team.keys())

        # Infer team sizes from the team which is passed in
        team_size_drivers = len(self._team_drivers)
        team_size_constructors = (len(self._team_constructors))
        team_size_total = team_size_drivers + team_size_constructors

        # LP variables for resulting team selection, separate for drivers and constructors
        self._lp_variables[VarType.TeamDrivers] = LpVariable.dicts('driver', driver_list, cat="Binary")
        self._lp_variables[VarType.TeamConstructors] = LpVariable.dicts('constructor', constructor_list, cat="Binary")

        # Costs as based on the team selection in the above LP variables
        cost_drivers = [self._prices_assets[i] * self._lp_variables[VarType.TeamDrivers][i] for i in driver_list]
        cost_constructors = [self._prices_assets[i] * self._lp_variables[VarType.TeamConstructors][i] for i in constructor_list]

        # Variable and constraint for total cost
        self._lp_variables[VarType.TotalCost] = lpSum(cost_drivers + cost_constructors)
        self._lp_constraints[VarType.TotalCost] = self._lp_variables[VarType.TotalCost] <= self._max_cost

        # Convenience variable for unused budget, we don't need a constraint for this
        self._lp_variables[VarType.UnusedBudget] = self._max_cost - self._lp_variables[VarType.TotalCost]

        # Constraints for team sizes
        self._lp_constraints[VarType.TeamDrivers] = lpSum([self._lp_variables[VarType.TeamDrivers][i] for i in driver_list]) == team_size_drivers
        self._lp_constraints[VarType.TeamConstructors] = lpSum([self._lp_variables[VarType.TeamConstructors][i] for i in constructor_list]) == team_size_constructors

        # Calculate number of driver and constructor moves, as a list of 0s / 1s initially
        driver_moves = [driver_team[i] * self._lp_variables[VarType.TeamDrivers][i] for i in driver_list]
        constructor_moves = [constructor_team[i] * self._lp_variables[VarType.TeamConstructors][i] for i in constructor_list]

        # Variable and constraint for total team moves
        self._lp_variables[VarType.TeamMoves] = team_size_total - lpSum(driver_moves + constructor_moves)
        self._lp_constraints[VarType.TeamMoves] = self._lp_variables[VarType.TeamMoves] <= self._max_moves

    def execute(self) -> LpProblem:
        # Base initialisation and constraints
        self.initialise()

        # Create the model, add the objective and constraints
        model = self.get_problem()
        # Make sure objective is added
        if model.objective is None:
            raise ValueError("Objective function not set in the problem")
        
        # Add the constraints
        for constraint in self._lp_constraints.values():
            model += constraint

        # Solve and return the model
        PULP_CBC_CMD(msg=0).solve(model)
        return model

    @abstractmethod
    def get_problem(self) -> LpProblem:
        pass
