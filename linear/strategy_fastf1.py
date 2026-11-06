"""fastf1_v2's strategy: maximise expected fantasy points from the FastF1 signal.

See ``docs/fastf1_v2/plan.md``, step 6.
"""
import logging
from pathlib import Path

from pulp import LpMaximize, LpProblem, lpSum

from fast_f1.output import DEFAULT_HISTORICAL_OUTPUT
from fast_f1.signal import load_signal_tables
from linear.strategy_base import StrategyBase, VarType


class StrategyFastF1(StrategyBase):
    """Strategy that maximises expected fantasy points, from each asset's signal position.

    Unlike `StrategyMaxP2PM`, it does not play the race-4 unlimited-moves chip.

    Parameters
    ----------
    fn_metrics : Path | str
        The FastF1 metrics file the signal is built from, read once per process by
        `load_signal_tables`.
    drs_coefficient : float
        Scales the DRS term in the objective, the DRS driver's expected points counted
        a second time. At zero the term is left out.

    Raises
    ------
    ValueError
        If the signal names an asset the race does not have, as identifiers that
        disagree would otherwise score every asset zero and still solve.
    """
    def __init__(
        self,
        *args,
        fn_metrics: Path | str = DEFAULT_HISTORICAL_OUTPUT,
        drs_coefficient: float = 1.0,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._drs_coefficient = drs_coefficient
        tables = load_signal_tables(fn_metrics)
        self._expected_points = tables.expected_points(self._season_year, self._race_num)

        available = set(self._all_available_drivers) | set(self._all_available_constructors)
        unknown = sorted(set(self._expected_points) - available)
        if unknown:
            msg = (f"Signal for {self._season_year} race {self._race_num} names assets not in the race: "
                   f"{unknown}")
            logging.error(msg)
            raise ValueError(msg)

    def get_problem(self) -> LpProblem:
        """Build an LP problem whose objective is the expected points of the selected assets.

        An available asset with no signal position scores zero.
        """
        problem = LpProblem(self.__class__.__name__, LpMaximize)

        drivers = self._lp_variables[VarType.TeamDrivers]
        constructors = self._lp_variables[VarType.TeamConstructors]
        points_drivers = [self._expected_points.get(i, 0.0) * drivers[i] for i in self._all_available_drivers]
        points_constructors = [
            self._expected_points.get(i, 0.0) * constructors[i] for i in self._all_available_constructors
        ]

        objective = lpSum(points_drivers + points_constructors)

        # DRS x2 counts the DRS driver's expected points a second time, so they can decide the team
        if self._drs_coefficient != 0.0:
            drs_values = {i: self._expected_points.get(i, 0.0) for i in self._all_available_drivers}
            drs_term, drs_constraints = self.get_drs_objective_term(drs_values)
            problem.extend(drs_constraints)
            objective += self._drs_coefficient * drs_term

        self._lp_variables[VarType.OptimiseMax] = objective
        problem += self._lp_variables[VarType.OptimiseMax]
        return problem
