from pulp import LpProblem, LpMaximize

from linear.strategy_base import StrategyBase, VarType


class StrategyZeroStop(StrategyBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # We'll only allow a change if there are unavailable drivers, as we dont't currently handle the points penalty
        num_unavailable_drivers = 0
        for d in self._team_drivers:
            if d not in self._all_available_drivers:
                num_unavailable_drivers += 1

        # Usually, this will be zero
        self._max_moves = num_unavailable_drivers

    def get_problem(self) -> LpProblem:
        # Otherwise we'll do same as max budget strategy, to ensure all the variables behave as expected
        problem = LpProblem(self.__class__.__name__, LpMaximize)
        problem += self._lp_variables[VarType.TotalCost]
        return problem
