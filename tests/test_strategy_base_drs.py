import pytest
from pulp import LpProblem, LpMaximize, lpSum, LpConstraintEQ

from linear.strategy_base import StrategyBase, VarType


# The worked example from docs/max_points_v1/proposal.md: pick 2 drivers from 4 on a budget of 40.  DRS-blind, the
# two mid drivers win 130 to 125; counting the DRS driver twice, STAR + CHEAP win 225 to 195.
_WORKED_VALUES = {"STAR": 100.0, "MID_A": 65.0, "MID_B": 65.0, "CHEAP": 25.0}
_WORKED_PRICES = {"STAR": 30.0, "MID_A": 20.0, "MID_B": 20.0, "CHEAP": 10.0, "CON": 0.0}


class StrategyDrsProbe(StrategyBase):
    """Maximises the passed driver values, optionally with the DRS term and optionally without its constraints."""
    def __init__(self, *args, driver_values: dict[str, float], use_drs: bool = True, add_constraints: bool = True,
                 **kwargs):
        super().__init__(*args, **kwargs)
        self.driver_values = driver_values
        self.use_drs = use_drs
        self.add_constraints = add_constraints
        self.drs_constraints = None

    def get_problem(self) -> LpProblem:
        problem = LpProblem("drs_probe", LpMaximize)
        drivers = self._lp_variables[VarType.TeamDrivers]
        objective = lpSum([self.driver_values.get(d, 0.0) * drivers[d] for d in drivers])
        if self.use_drs:
            drs_term, self.drs_constraints = self.get_drs_objective_term(self.driver_values)
            if self.add_constraints:
                problem.extend(self.drs_constraints)
            objective = objective + drs_term
        problem += objective
        return problem


def make_probe(
        driver_values: dict[str, float] = _WORKED_VALUES,
        prices: dict[str, float] = _WORKED_PRICES,
        team_drivers: list[str] = ["MID_A", "CHEAP"],
        max_cost: float = 40.0,
        **kwargs,
    ) -> StrategyDrsProbe:
    available = [d for d in prices if d != "CON"]
    return StrategyDrsProbe(
        team_drivers=team_drivers,
        team_constructors=[],
        all_available_drivers=available,
        all_available_constructors=["CON"],
        all_available_driver_pairs={d: "CON" for d in available},
        prev_available_driver_pairs={d: "CON" for d in available},
        max_cost=max_cost,
        max_moves=2,
        prices_assets=prices,
        derivs_assets={},
        race_num=5,
        season_year=2025,
        driver_values=driver_values,
        **kwargs,
    )


def selected_drivers(strat: StrategyBase) -> set[str]:
    return {d for d, v in strat._lp_variables[VarType.TeamDrivers].items() if v.value() > 0.5}


def test_drs_term_is_blind_without_the_helper():
    strat = make_probe(use_drs=False)
    strat.execute()
    assert selected_drivers(strat) == {"MID_A", "MID_B"}
    assert VarType.DrsDriver not in strat._lp_variables


def test_drs_term_changes_the_team_not_just_the_nominee():
    strat = make_probe()
    strat.execute()
    assert selected_drivers(strat) == {"STAR", "CHEAP"}
    assert strat.get_drs_nominee() == "STAR"


def test_drs_constraints_one_per_driver_plus_an_exact_sum():
    strat = make_probe()
    strat.execute()
    constraints = strat.drs_constraints
    assert len(constraints) == len(_WORKED_VALUES) + 1
    assert set(constraints) == {"drs_one"} | {f"drs_owned_{d}" for d in _WORKED_VALUES}
    # Exactly one DRS driver, never "at most one"
    assert constraints["drs_one"].sense == LpConstraintEQ
    assert constraints["drs_one"].constant == -1


def test_drs_variables_cover_owned_but_unavailable_drivers():
    # GONE is on the team but no longer available, so it is priced out rather than listed.  The DRS binaries must still
    # index it, matching the team-driver binaries they are paired with.
    strat = make_probe(team_drivers=["GONE", "CHEAP"])
    strat.execute()
    assert set(strat._lp_variables[VarType.DrsDriver]) == set(strat._lp_variables[VarType.TeamDrivers])
    assert "drs_owned_GONE" in strat.drs_constraints
    assert "GONE" not in selected_drivers(strat)


def test_drs_driver_missing_from_values_counts_as_zero():
    values = {"STAR": 100.0, "MID_A": 65.0, "MID_B": 65.0}  # No CHEAP
    strat = make_probe(driver_values=values)
    strat.execute()
    # CHEAP worth nothing: STAR + CHEAP scores 200, the mids 195, so STAR + CHEAP still wins but only just
    assert selected_drivers(strat) == {"STAR", "CHEAP"}
    assert strat.get_drs_nominee() == "STAR"


def test_drs_nominee_is_on_the_team_when_the_best_driver_is_unaffordable():
    values = {"STAR": 1000.0, "MID_A": 65.0, "MID_B": 65.0, "CHEAP": 25.0}
    prices = {"STAR": 50.0, "MID_A": 20.0, "MID_B": 20.0, "CHEAP": 10.0, "CON": 0.0}
    strat = make_probe(driver_values=values, prices=prices)
    strat.execute()
    assert selected_drivers(strat) == {"MID_A", "MID_B"}
    assert strat.get_drs_nominee() in selected_drivers(strat)


def test_drs_nominee_raises_when_constraints_were_not_added():
    # Without the constraints the solver parks DRS on the unaffordable STAR, who is not on the team
    values = {"STAR": 1000.0, "MID_A": 65.0, "MID_B": 65.0, "CHEAP": 25.0}
    prices = {"STAR": 50.0, "MID_A": 20.0, "MID_B": 20.0, "CHEAP": 10.0, "CON": 0.0}
    strat = make_probe(driver_values=values, prices=prices, add_constraints=False)
    strat.execute()
    with pytest.raises(ValueError, match="were the DRS constraints added"):
        strat.get_drs_nominee()


def test_drs_nominee_raises_when_helper_was_not_called():
    strat = make_probe(use_drs=False)
    strat.execute()
    with pytest.raises(ValueError, match="get_drs_objective_term"):
        strat.get_drs_nominee()
