from pulp import LpProblem, LpMaximize, lpSum

from helpers import safe_to_float
from import_data.derivations import DerivationType, get_derivation_name
from linear.strategy_base import StrategyBase, VarType


class StrategyMaxPoints(StrategyBase):
    """Strategy that maximises the rolling points total over available assets.

    Where `StrategyMaxP2PM` divides by cumulative price, this optimises the points
    themselves. The budget cap in `StrategyBase` already rations expensive assets,
    so the divisor penalises them a second time; whether that helps or hurts is
    what back-testing this against P2PM measures.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # If we are at race 4, play the "unlimited moves" chip. After 3 races, we have our cumulative average stats fully
        # populated, so this is a chance to recover from any unfortunate initial picks now that we have a picture of how
        # well each asset is performing.  Total number of allowed moves is total size of team, we can swap out whole if
        # we want to.  Copied from StrategyMaxP2PM deliberately: it is the back-test baseline, and leaving the chip out
        # would make the comparison measure the chip as well as the objective.
        if self._race_num == 4:
            team_size_drivers = len(self._team_drivers)
            team_size_constructors = (len(self._team_constructors))
            self._max_moves = team_size_drivers + team_size_constructors

    def get_problem(self) -> LpProblem:
        """Build an LP problem whose objective is the cumulative points over selected assets."""
        problem = LpProblem(self.__class__.__name__, LpMaximize)

        deriv_name = get_derivation_name(DerivationType.POINTS_CUMULATIVE, 3)

        # Ensure anything without the points value defaults to zero, i.e. it's worth nothing
        for d in self._all_available_drivers + self._all_available_constructors:
            if self._derivs_assets[deriv_name].get(d) is None:
                self._derivs_assets[deriv_name][d] = 0.0
            else:
                self._derivs_assets[deriv_name][d] = safe_to_float(self._derivs_assets[deriv_name][d])

        # Points values as based on the team selection, using the LP variables already provided by the base class
        points_drivers = [self._derivs_assets[deriv_name][i] * self._lp_variables[VarType.TeamDrivers][i] for i in self._all_available_drivers]
        points_constructors = [self._derivs_assets[deriv_name][i] * self._lp_variables[VarType.TeamConstructors][i] for i in self._all_available_constructors]

        # Variable for total points
        self._lp_variables[VarType.OptimiseMax] = lpSum(points_drivers + points_constructors)

        # Optimise for this
        problem += self._lp_variables[VarType.OptimiseMax]
        return problem
