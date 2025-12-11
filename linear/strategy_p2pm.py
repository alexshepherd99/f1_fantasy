from pulp import LpProblem, LpMaximize, lpSum

from helpers import safe_to_float
from import_data.derivations import DerivationType, get_derivation_name
from linear.strategy_base import StrategyBase, VarType


class StrategyMaxP2PM(StrategyBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_problem(self) -> LpProblem:
        problem = LpProblem(self.__class__.__name__, LpMaximize)

        deriv_name = get_derivation_name(DerivationType.P2PM_CUMULATIVE, 3)

        # Ensure anything without the P2PM value defaults to zero, i.e. it's worth nothing
        for d in self._all_available_drivers + self._all_available_constructors:
            if self._derivs_assets[deriv_name].get(d) is None:
                self._derivs_assets[deriv_name][d] = 0.0
            else:
                self._derivs_assets[deriv_name][d] = safe_to_float(self._derivs_assets[deriv_name][d])

        # P2PM values as based on the team selection, using the LP variables already provided by the base class
        p2pm_drivers = [self._derivs_assets[deriv_name][i] * self._lp_variables[VarType.TeamDrivers][i] for i in self._all_available_drivers]
        p2pm_constructors = [self._derivs_assets[deriv_name][i] * self._lp_variables[VarType.TeamConstructors][i] for i in self._all_available_constructors]

        # Variable for total P2PM
        self._lp_variables[VarType.OptimiseMax] = lpSum(p2pm_drivers + p2pm_constructors)

        # Optimise for this
        problem += self._lp_variables[VarType.OptimiseMax]
        return problem
