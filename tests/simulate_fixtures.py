"""A hand-built world for the simulate tests.

Four drivers in two constructors, and teams of two drivers and one constructor.
Each asset carries one deriv, `score`, which `StrategyMaxScore` maximises, so a
test chooses the line-up a race favours by its scores.
"""

from pulp import LpMaximize, LpProblem, lpSum

from common import AssetType
from linear.strategy_base import StrategyBase, VarType
from races.asset import Constructor, Driver
from races.season import Race, Season
from races.team import Team

PAIRS = {"A@T1": "T1", "B@T1": "T1", "C@T2": "T2", "D@T2": "T2"}
ASSETS = [*PAIRS, "T1", "T2"]
SEASON = 2099


class StrategyMaxScore(StrategyBase):
    """Maximises each asset's `score` deriv, and nominates the cheapest selected driver for DRS.

    The default DRS driver is the most expensive, so a nomination shows in the points.
    """

    def get_problem(self) -> LpProblem:
        problem = LpProblem(self.__class__.__name__, LpMaximize)
        scores = self._derivs_assets["score"]
        selections = {**self._lp_variables[VarType.TeamDrivers], **self._lp_variables[VarType.TeamConstructors]}
        problem += lpSum([scores.get(asset, 0.0) * selected for asset, selected in selections.items()])
        return problem

    def get_drs_driver(self) -> str:
        selected = [d for d, v in self._lp_variables[VarType.TeamDrivers].items() if v.varValue == 1]
        return min(selected, key=lambda d: (self._prices_assets[d], d))


class StrategyInfeasible(StrategyMaxScore):
    """No team can cost less than nothing, so the solver never returns optimal."""

    def get_problem(self) -> LpProblem:
        problem = super().get_problem()
        problem += self._lp_variables[VarType.TotalCost] <= -1.0
        return problem


def make_race(race: int, prices: dict[str, float] | None = None, scores: dict[str, float] | None = None,
              points: dict[str, int] | None = None) -> Race:
    """A race of the hand-built world; prices default to 10, scores and points to 0."""
    prices = {asset: 10.0 for asset in ASSETS} | (prices or {})
    scores = scores or {}
    points = points or {}

    def _args(asset):
        return {"price": prices[asset], "points": points.get(asset, 0), "derivs": {"score": scores.get(asset, 0.0)}}

    drivers = {d: Driver(driver=d, constructor=c, **_args(d)) for d, c in PAIRS.items()}
    constructors = {c: Constructor(constructor=c, **_args(c)) for c in ["T1", "T2"]}
    return Race(race=race, drivers=drivers, constructors=constructors)


def make_team(drivers: list[str], constructor: str, unused_budget: float = 0.0) -> Team:
    """A team of the hand-built world's size."""
    team = Team(num_drivers=2, num_constructors=1, unused_budget=unused_budget)
    for d in drivers:
        team.add_asset(AssetType.DRIVER, d)
    team.add_asset(AssetType.CONSTRUCTOR, constructor)
    return team


def make_budget_season() -> Season:
    """Race 2 sells A for the cheaper C; race 3 buys A back, affordable only with race 2's unused budget."""
    cheap_c_d = {"C@T2": 5.0, "D@T2": 5.0, "T1": 20.0, "T2": 20.0}
    return Season(season=SEASON, races={
        1: make_race(1, prices=cheap_c_d),
        2: make_race(2, prices=cheap_c_d, scores={"C@T2": 50.0, "B@T1": 2.0, "A@T1": 1.0, "T1": 1.0},
                     points={"C@T2": 10, "B@T1": 3}),
        3: make_race(3, prices=cheap_c_d | {"B@T1": 9.0}, scores={"A@T1": 50.0, "B@T1": 2.0, "T1": 1.0},
                     points={"A@T1": 7, "B@T1": 4}),
    })
