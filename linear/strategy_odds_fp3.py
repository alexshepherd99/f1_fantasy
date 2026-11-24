"""odds_fp3_v1's strategy: pick a team from betting odds and FP3 alone.

See ``docs/odds_fp3_v1/requirements.md``, R2-R6.
"""
import logging
from pathlib import Path

import pandas as pd
from pulp import LpMaximize, LpProblem, lpSum

from fast_f1.metrics import FORMAT_NORMAL, add_signal_inputs
from fast_f1.output import DEFAULT_HISTORICAL_OUTPUT, load_existing_metrics
from fast_f1.signal import _race_rows
from linear.strategy_base import StrategyBase, VarType


class StrategyOddsFP3(StrategyBase):
    """Strategy that maximises a mix of betting odds and FP3 pace, for a race with no history.

    Each driver's value is ``odds_weight * OddsRank + (1 - odds_weight) * FP3_MinLapTime_rank``,
    both read from the FastF1 metrics file, and a constructor's value is the sum of its drivers'.
    A missing input counts as 0, as does a driver with no metrics row. Neither fantasy points nor
    any race history is read, and prices enter only through the budget cap. The DRS driver is
    chosen inside the LP.

    It is built for a season's first race, which starts from no team. `StrategyBase` sizes the
    team from the team it is given, so a caller passes a placeholder team and allows every move.

    Parameters
    ----------
    odds_weight : float
        The odds' share of each driver's value, from 0 (FP3 alone) to 1 (odds alone).
    fn_metrics : Path | str
        The FastF1 metrics file to read the race's rows from.

    Raises
    ------
    ValueError
        If `odds_weight` is outside 0-1, the metrics hold no rows for the race, the race is not a
        normal weekend (a sprint weekend has no FP3), or a metrics row matches no single available
        driver.
    """
    def __init__(
        self,
        *args,
        odds_weight: float = 0.5,
        fn_metrics: Path | str = DEFAULT_HISTORICAL_OUTPUT,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        if not 0.0 <= odds_weight <= 1.0:
            msg = f"odds_weight must be between 0 and 1, got {odds_weight}"
            logging.error(msg)
            raise ValueError(msg)

        rows = self._race_metrics(fn_metrics)
        driver_values = (
            odds_weight * rows["OddsRank"].fillna(0.0)
            + (1.0 - odds_weight) * rows["FP3_MinLapTime_rank"].fillna(0.0)
        )
        self._values = {d: 0.0 for d in self._all_available_drivers + self._all_available_constructors}
        self._values |= dict(zip(rows["Asset"], driver_values.astype(float)))
        for driver in self._all_available_drivers:
            self._values[self._all_available_driver_pairs[driver]] += self._values[driver]

    def _race_metrics(self, fn_metrics: Path | str) -> pd.DataFrame:
        """The race's metrics rows, each with its fantasy driver in ``Asset``.

        Raises
        ------
        ValueError
            As for the class.
        """
        metrics = load_existing_metrics(fn_metrics)
        if not metrics.empty:
            metrics = metrics[(metrics["Season"] == self._season_year) & (metrics["Race"] == self._race_num)]
        if metrics.empty:
            msg = f"No metrics rows for {self._season_year} race {self._race_num} in {fn_metrics}"
            logging.error(msg)
            raise ValueError(msg)

        # The available drivers, in the shape of the archive's per-race pairs, so fast_f1's
        # matching of bare driver codes to fantasy identifiers applies unchanged
        pairs = pd.DataFrame({
            "Season": self._season_year,
            "Race": self._race_num,
            "Driver": self._all_available_drivers,
        })
        rows = add_signal_inputs(_race_rows(metrics, pairs, self._season_year, self._race_num))

        race_format = rows["format"].iloc[0]
        if race_format != FORMAT_NORMAL:
            msg = f"{self._season_year} race {self._race_num} is a {race_format} weekend, which has no FP3"
            logging.error(msg)
            raise ValueError(msg)
        return rows

    def get_problem(self) -> LpProblem:
        """Build an LP problem whose objective is the selected assets' values, with DRS counted inside it."""
        problem = LpProblem(self.__class__.__name__, LpMaximize)

        drivers = self._lp_variables[VarType.TeamDrivers]
        constructors = self._lp_variables[VarType.TeamConstructors]
        values_drivers = [self._values[i] * drivers[i] for i in self._all_available_drivers]
        values_constructors = [self._values[i] * constructors[i] for i in self._all_available_constructors]

        # DRS x2 counts the DRS driver's value a second time, so it can decide the team
        drs_values = {i: self._values[i] for i in self._all_available_drivers}
        drs_term, drs_constraints = self.get_drs_objective_term(drs_values)
        problem.extend(drs_constraints)

        self._lp_variables[VarType.OptimiseMax] = lpSum(values_drivers + values_constructors) + drs_term
        problem += self._lp_variables[VarType.OptimiseMax]
        return problem

    def get_drs_driver(self) -> str:
        """Return the DRS driver the LP chose, from the selected team.

        Returns an empty string if the chosen driver's value is zero, as the LP's pick between
        drivers worth nothing means nothing. The default team selection then picks, taking the
        highest-priced driver.
        """
        nominee = self.get_drs_nominee()
        return nominee if self._values.get(nominee, 0.0) > 0.0 else ""
