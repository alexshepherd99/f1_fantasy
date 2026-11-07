"""fastf1_v2's strategy: maximise the FastF1 signal's values.

See ``docs/fastf1_v2/plan.md``, steps 6 and 13.
"""
import logging
from pathlib import Path

from pulp import LpMaximize, LpProblem, lpSum

from fast_f1.output import DEFAULT_HISTORICAL_OUTPUT
from fast_f1.signal import load_signal_tables
from linear.strategy_base import StrategyBase, VarType


class StrategyFastF1(StrategyBase):
    """Strategy that maximises the selected assets' signal values, in championship points per race.

    Unlike `StrategyMaxP2PM`, it does not play the race-4 unlimited-moves chip.

    Parameters
    ----------
    fn_metrics : Path | str
        The FastF1 metrics file the signal is built from, read once per process by
        `load_signal_tables`.
    drs_coefficient : float
        Scales the DRS term in the objective, the DRS driver's value counted a second
        time. At zero the term is left out.
    budget_reward : float
        Value added to the objective per 1m of the team's total cost. Zero adds nothing.
    negative_penalty : float
        Value taken from the objective per unit of each selected asset's chance of going
        negative. The DRS driver's chance is not doubled. At zero the chances are not read.

    Raises
    ------
    ValueError
        If the values or chances name an asset the race does not have, as identifiers
        that disagree would otherwise score every asset zero and still solve, or an
        available asset has no chance of going negative.
    """
    def __init__(
        self,
        *args,
        fn_metrics: Path | str = DEFAULT_HISTORICAL_OUTPUT,
        drs_coefficient: float = 1.0,
        budget_reward: float = 0.0,
        negative_penalty: float = 0.0,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._drs_coefficient = drs_coefficient
        self._budget_reward = budget_reward
        self._negative_penalty = negative_penalty
        tables = load_signal_tables(fn_metrics)
        self._values = tables.values(self._season_year, self._race_num)
        # An asset with no value is left out, so only unknown assets are checked
        self._check_assets(self._values, "Values", every_asset=False)

        # Read only when they count, as a penalty of zero leaves them out of the objective
        self._negative_chance = {}
        if self._negative_penalty != 0.0:
            self._negative_chance = tables.negative_chance(self._season_year, self._race_num)
            # Every priced asset has a chance, so one missing is a defect
            self._check_assets(self._negative_chance, "Negative chance", every_asset=True)

    def _check_assets(self, values: dict[str, float], what: str, every_asset: bool) -> None:
        """Raise if `values` names an asset the race does not have or, with `every_asset`, misses one."""
        available = set(self._all_available_drivers) | set(self._all_available_constructors)
        problems = {"names assets not in the race": sorted(set(values) - available)}
        if every_asset:
            problems["has no value for available assets"] = sorted(available - set(values))

        for problem, assets in problems.items():
            if assets:
                msg = f"{what} for {self._season_year} race {self._race_num} {problem}: {assets}"
                logging.error(msg)
                raise ValueError(msg)

    def get_problem(self) -> LpProblem:
        """Build an LP problem whose objective is the values of the selected assets.

        An available asset with no value scores zero.
        """
        problem = LpProblem(self.__class__.__name__, LpMaximize)

        drivers = self._lp_variables[VarType.TeamDrivers]
        constructors = self._lp_variables[VarType.TeamConstructors]
        values_drivers = [self._values.get(i, 0.0) * drivers[i] for i in self._all_available_drivers]
        values_constructors = [
            self._values.get(i, 0.0) * constructors[i] for i in self._all_available_constructors
        ]

        # Value per 1m spent, so budget left unspent counts against a team
        objective = lpSum(values_drivers + values_constructors) + self._budget_reward * self._lp_variables[VarType.TotalCost]

        # DRS x2 counts the DRS driver's value a second time, so it can decide the team
        if self._drs_coefficient != 0.0:
            drs_values = {i: self._values.get(i, 0.0) for i in self._all_available_drivers}
            drs_term, drs_constraints = self.get_drs_objective_term(drs_values)
            problem.extend(drs_constraints)
            objective += self._drs_coefficient * drs_term

        if self._negative_penalty != 0.0:
            chance_drivers = [self._negative_chance[i] * drivers[i] for i in self._all_available_drivers]
            chance_constructors = [
                self._negative_chance[i] * constructors[i] for i in self._all_available_constructors
            ]
            objective -= self._negative_penalty * lpSum(chance_drivers + chance_constructors)

        self._lp_variables[VarType.OptimiseMax] = objective
        problem += self._lp_variables[VarType.OptimiseMax]
        return problem

    def get_drs_driver(self) -> str:
        """Return the selected driver with the best value, the same rule at any coefficient.

        A tie goes to the first identifier, so runs repeat. Returns an empty string if no selected
        driver has a value above zero, so the default team selection picks, taking the
        highest-priced driver.
        """
        drivers = self._lp_variables[VarType.TeamDrivers]
        best_driver, best_value = "", 0.0
        for d in sorted(self._all_available_drivers):
            # Called after the strategy has run, so the binaries hold the selected team
            value = self._values.get(d, 0.0)
            if drivers[d].value() > 0.5 and value > best_value:
                best_driver, best_value = d, value
        return best_driver
