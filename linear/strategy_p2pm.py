from pulp import LpProblem, LpMaximize

from linear.strategy_base import StrategyBase, VarType


class StrategyMaxP2PM(StrategyBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_problem(self) -> LpProblem:
        problem = LpProblem(self.__class__.__name__, LpMaximize)

        # Ensure anything without the P2PM value defaults to zero, i.e. it's worth nothing

        # Costs as based on the team selection in the above LP variables
        #cost_drivers = [self._prices_assets[i] * self._lp_variables[VarType.TeamDrivers][i] for i in driver_list]
        #cost_constructors = [self._prices_assets[i] * self._lp_variables[VarType.TeamConstructors][i] for i in constructor_list]

        # Variable and constraint for total cost
        #self._lp_variables[VarType.TotalCost] = lpSum(cost_drivers + cost_constructors)

        # Optimise for this
        #OptimiseMax

        return problem
