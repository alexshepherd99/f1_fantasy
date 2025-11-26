from pulp import LpProblem, LpMaximize, LpAffineExpression

from linear.strategy_base import StrategyBase, VarType


class StrategyMaxBudget(StrategyBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_objective(self) -> LpAffineExpression:
        return self._lp_variables[VarType.TotalCost]
    
    def get_problem(self, strategy_name: str) -> LpProblem:
        return LpProblem(strategy_name, LpMaximize)

    def additional_constraints(self):
        pass
