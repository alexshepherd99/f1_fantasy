from pulp import LpProblem, LpMaximize

from linear.strategy_base import StrategyBase, VarType


class StrategyMaxBudget(StrategyBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_problem(self) -> LpProblem:
        problem = LpProblem(self.__class__.__name__, LpMaximize)
        problem += self._lp_variables[VarType.TotalCost]
        return problem
