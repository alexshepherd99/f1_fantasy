import json
import logging

import pytest
from pulp import LpMaximize, LpProblem, lpSum

from common import AssetType
from helpers import load_with_derivations
from linear.strategy_base import StrategyBase, VarType
from linear.strategy_budget import StrategyMaxBudget
from linear.strategy_fastf1 import StrategyFastF1RuleRise
from linear.strategy_p2pm import StrategyMaxP2PM
from races.asset import Constructor, Driver
from races.season import Race, Season, factory_season
from races.team import Team, factory_team_lists
from simulate.season import get_row_intermediate_results, get_strat_display_name, run_for_team

# Every per-race row of a 2025 season for two strategies, recorded from the code
# before live_picks_v1 moved run_for_team (its D3): the back-test must not change
_FILE_PINNED_ROWS = "data/test_run_for_team_2025.json"

# Hand-built seasons: four drivers in two constructors, teams of two drivers and one constructor
_PAIRS = {"A@T1": "T1", "B@T1": "T1", "C@T2": "T2", "D@T2": "T2"}
_ASSETS = [*_PAIRS, "T1", "T2"]
_SEASON = 2099


class _StrategyMaxScore(StrategyBase):
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


class _StrategyInfeasible(_StrategyMaxScore):
    """No team can cost less than nothing, so the solver never returns optimal."""

    def get_problem(self) -> LpProblem:
        problem = super().get_problem()
        problem += self._lp_variables[VarType.TotalCost] <= -1.0
        return problem


def _race(race: int, prices: dict[str, float] | None = None, scores: dict[str, float] | None = None,
          points: dict[str, int] | None = None) -> Race:
    """A race of the hand-built world; prices default to 10, scores and points to 0."""
    prices = {asset: 10.0 for asset in _ASSETS} | (prices or {})
    scores = scores or {}
    points = points or {}

    def _args(asset):
        return {"price": prices[asset], "points": points.get(asset, 0), "derivs": {"score": scores.get(asset, 0.0)}}

    drivers = {d: Driver(driver=d, constructor=c, **_args(d)) for d, c in _PAIRS.items()}
    constructors = {c: Constructor(constructor=c, **_args(c)) for c in ["T1", "T2"]}
    return Race(race=race, drivers=drivers, constructors=constructors)


def _team(drivers: list[str], constructor: str, unused_budget: float = 0.0) -> Team:
    team = Team(num_drivers=2, num_constructors=1, unused_budget=unused_budget)
    for d in drivers:
        team.add_asset(AssetType.DRIVER, d)
    team.add_asset(AssetType.CONSTRUCTOR, constructor)
    return team


def _held(row: dict) -> tuple[str, str, str]:
    return row["D1"], row["D2"], row["C1"]


@pytest.fixture
def budget_season() -> Season:
    """Race 2 sells A for the cheaper C; race 3 buys A back, affordable only with race 2's unused budget."""
    cheap_c_d = {"C@T2": 5.0, "D@T2": 5.0, "T1": 20.0, "T2": 20.0}
    return Season(season=_SEASON, races={
        1: _race(1, prices=cheap_c_d),
        2: _race(2, prices=cheap_c_d, scores={"C@T2": 50.0, "B@T1": 2.0, "A@T1": 1.0, "T1": 1.0},
                 points={"C@T2": 10, "B@T1": 3}),
        3: _race(3, prices=cheap_c_d | {"B@T1": 9.0}, scores={"A@T1": 50.0, "B@T1": 2.0, "T1": 1.0},
                 points={"A@T1": 7, "B@T1": 4}),
    })


@pytest.fixture(scope="module")
def season_2025():
    return factory_season(*load_with_derivations(season=2025), 2025)


@pytest.mark.parametrize("strategy", [StrategyMaxP2PM, StrategyFastF1RuleRise])
def test_run_for_team_matches_the_pinned_rows(season_2025, strategy):
    with open(_FILE_PINNED_ROWS) as f:
        pinned = json.load(f)[strategy.__name__]
    team = factory_team_lists(
        drivers=["TSU@VRB", "SAI@WIL", "BEA@HAA", "HAD@VRB", "DOO@ALP"],
        constructors=["MCL", "FER"],
        race=season_2025.races[1],
    )

    rows = run_for_team(strategy, team, season_2025, 2025, 1)

    assert len(rows) == 24
    for row, pinned_row in zip(rows, pinned):
        assert row == pinned_row, f"race {pinned_row['race']}"


def test_run_for_team_carries_a_free_move_after_fewer_than_two_moves():
    # Each race's scores favour a line-up: 1 move at race 2 gives 3 at race 3, where
    # the favoured line-up needs all 3; 2 moves at race 4 give only 2 at race 5
    season = Season(season=_SEASON, races={
        1: _race(1),
        2: _race(2, scores={"C@T2": 50.0, "B@T1": 2.0, "A@T1": 1.0, "T1": 1.0}),
        3: _race(3, scores={"A@T1": 30.0, "D@T2": 20.0, "T2": 10.0}),
        4: _race(4, scores={"B@T1": 30.0, "C@T2": 20.0, "T1": 10.0}),
        5: _race(5, scores={"B@T1": 1.0, "C@T2": 1.0, "T2": 1.0}),
    })

    rows = run_for_team(_StrategyMaxScore, _team(["A@T1", "B@T1"], "T1"), season, _SEASON, 1)

    assert [row["max_moves"] for row in rows] == [2, 2, 3, 2, 2]
    assert [row["used_moves"] for row in rows] == [-1, 1, 3, 2, 0]
    assert [_held(row) for row in rows] == [
        ("A@T1", "B@T1", "T1"),
        ("B@T1", "C@T2", "T1"),
        ("A@T1", "D@T2", "T2"),
        ("B@T1", "C@T2", "T2"),
        ("B@T1", "C@T2", "T2"),
    ]


def test_run_for_team_carries_unused_budget_and_scores_the_chosen_drs_driver(budget_season):
    rows = run_for_team(_StrategyMaxScore, _team(["A@T1", "B@T1"], "T1"), budget_season, _SEASON, 1)

    race_1, race_2, race_3 = rows
    assert (race_1["drs_driver"], race_1["points"]) == ("", 0)
    # Selling A (10) for C (5) leaves 5 unused, and DRS on C (10 points) beats the default, B (3)
    assert _held(race_2) == ("B@T1", "C@T2", "T1")
    assert (race_2["unused_budget"], race_2["total_budget"]) == (5.0, 40.0)
    assert (race_2["drs_driver"], race_2["points"]) == ("C@T2", 10 + 3 + 10)
    # A (10) back for C (5) needs the 5 carried: B is now 9, so the team is worth 34
    assert _held(race_3) == ("A@T1", "B@T1", "T1")
    assert (race_3["unused_budget"], race_3["total_budget"]) == (0.0, 39.0)
    # DRS on B, the cheaper, rather than the default, A
    assert (race_3["drs_driver"], race_3["points"]) == ("B@T1", 7 + 4 + 4)
    assert race_3["total_points"] == 23 + 15


def test_run_for_team_starts_after_race_1_from_the_team_given(budget_season):
    rows = run_for_team(_StrategyMaxScore, _team(["A@T1", "B@T1"], "T1"), budget_season, _SEASON, 2)

    assert [row["race"] for row in rows] == [2, 3]
    # The start race keeps the team given, though race 2's scores favour C
    assert _held(rows[0]) == ("A@T1", "B@T1", "T1")
    assert (rows[0]["used_moves"], rows[0]["max_moves"]) == (-1, 2)
    assert (rows[0]["starting_value"], rows[1]["starting_value"]) == (40.0, 40.0)
    assert (rows[1]["used_moves"], _held(rows[1])) == (0, ("A@T1", "B@T1", "T1"))


def test_run_for_team_raises_when_the_solver_is_not_optimal(budget_season, caplog):
    team = _team(["A@T1", "B@T1"], "T1")

    with caplog.at_level(logging.ERROR), pytest.raises(RuntimeError):
        run_for_team(_StrategyInfeasible, team, budget_season, _SEASON, 1)

    assert "LP model returned" in caplog.text
    assert f"Season {_SEASON} race 2" in caplog.text


def test_get_row_intermediate_results_columns(budget_season):
    team = _team(["B@T1", "A@T1"], "T1", unused_budget=0.26)
    race_1, race_2 = budget_season.races[1], budget_season.races[2]

    row = get_row_intermediate_results(
        "Label", team, budget_season, _SEASON, race_2, race_1, 2, 13, 3, 1, 41.0, 21.0, 20.0,
    )

    assert row == {
        "strategy": "Label",
        "season": _SEASON,
        "race": 2,
        "total_value": 40.0,
        "starting_value": 41.0,
        "starting_value_d": 21.0,
        "starting_value_c": 20.0,
        "points": 13,
        "total_points": 0,
        "unused_budget": 0.3,
        "total_budget": 40.3,
        "max_moves": 3,
        "used_moves": 1,
        "drs_driver": "",
        "D1": "A@T1",
        "D1_val": 10.0,
        "D1_pts": 0,
        "D2": "B@T1",
        "D2_val": 10.0,
        "D2_pts": 3,
        "C1": "T1",
        "C1_val": 20.0,
        "C1_pts": 0,
    }
    # Column order too, as the back-test stores and spreadsheets follow it
    assert list(row) == ["strategy", "season", "race", "total_value", "starting_value", "starting_value_d",
                         "starting_value_c", "points", "total_points", "unused_budget", "total_budget",
                         "max_moves", "used_moves", "drs_driver", "D1", "D1_val", "D1_pts", "D2", "D2_val",
                         "D2_pts", "C1", "C1_val", "C1_pts"]


def test_get_strat_display_name():
    assert get_strat_display_name(StrategyMaxBudget) == "StrategyMaxBudget"
    assert get_strat_display_name(StrategyMaxBudget, "x") == "StrategyMaxBudget:x"
