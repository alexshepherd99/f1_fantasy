from pulp import LpProblem, LpMaximize, LpAffineExpression

from linear.strategy_base import StrategyBase, VarType


class StrategyMaxBudget(StrategyBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_problem(self) -> LpProblem:
        problem = LpProblem("StrategyMaxBudget", LpMaximize)
        problem += self._lp_variables[VarType.TotalCost]
        return problem
