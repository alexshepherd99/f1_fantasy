from pulp import LpProblem, LpMaximize, lpSum

from helpers import safe_to_float
from import_data.derivations import DerivationType, get_derivation_name
from linear.strategy_base import StrategyBase, VarType


class StrategyMaxP2PM(StrategyBase):
    """Strategy that maximises Points-per-Million (P2PM) derived over available assets."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # If we are at race 4, play the "unlimited moves" chip. After 3 races, we have our cumulative average stats fully
        # populated, so this is a chance to recover from any unfortunate initial picks now that we have a picture of how
        # well each asset is performing.  Total number of allowed moves is total size of team, we can swap out whole if
        # we want to.
        if self._race_num == 4:
            team_size_drivers = len(self._team_drivers)
            team_size_constructors = (len(self._team_constructors))
            self._max_moves = team_size_drivers + team_size_constructors

    def get_problem(self) -> LpProblem:
        """Build an LP problem whose objective is the cumulative P2PM over selected assets."""
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


    def get_drs_driver(self) -> str:
        """Select a driver from the chosen team to assign DRS based on maximum recent points.

        Returns an empty string if no suitable driver has points data.
        """
        # Override behaviour to select driver with highest points average
        deriv_points = get_derivation_name(DerivationType.POINTS_CUMULATIVE, 3)

        max_points = 0.0
        max_driver = ""

        for d in self._all_available_drivers:
            # This will only be called after the strategy has run, so self._lp_variables[VarType.TeamDrivers] will
            # represent the selected drivers
            if self._lp_variables[VarType.TeamDrivers][d].value() > 0:
                if self._derivs_assets[deriv_points][d] > max_points:
                    max_points = self._derivs_assets[deriv_points][d]
                    max_driver = d

        # If we had no points to work with, ensure we return no driver.  This will allow the default team selection
        # to choose, which will pick driver with max current value.
        if max_points == 0.0:
            return ""
        else:
            return max_driver
