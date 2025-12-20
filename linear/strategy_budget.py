from pulp import LpProblem, LpMaximize

from linear.strategy_base import StrategyBase, VarType


class StrategyMaxBudget(StrategyBase):
    """Strategy that maximises total budget usage (proxy for maximizing value)."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_problem(self) -> LpProblem:
        """Construct an LP problem that maximises the total cost (spend) of the selected team."""
        problem = LpProblem(self.__class__.__name__, LpMaximize)
        problem += self._lp_variables[VarType.TotalCost]
        return problem
