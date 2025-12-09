from pulp import LpProblem, LpMaximize

from linear.strategy_base import StrategyBase, VarType


class StrategyMaxP2PM(StrategyBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_problem(self) -> LpProblem:
        problem = LpProblem(self.__class__.__name__, LpMaximize)


        
        return problem
