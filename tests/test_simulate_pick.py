import logging

import pytest

from common import AssetType
from linear.strategy_base import COST_PROHIBITIVE
from linear.strategy_budget import StrategyMaxBudget
from races.season import Season
from simulate.pick import Pick, limitless_cap, next_free_moves, solve_race
from tests.simulate_fixtures import (
    SEASON,
    StrategyInfeasible,
    StrategyMaxScore,
    make_budget_season,
    make_race,
    make_team,
)


@pytest.fixture
def budget_season() -> Season:
    return make_budget_season()


def test_solve_race_returns_the_pick_and_leaves_the_team_unchanged(budget_season):
    team = make_team(["A@T1", "B@T1"], "T1")
    race_1, race_2 = budget_season.races[1], budget_season.races[2]

    pick = solve_race(StrategyMaxScore, team, race_2, race_1, SEASON, max_moves=2)

    # Selling A (10) for C (5) within a budget of 40, with DRS on C, the cheaper driver
    assert pick == Pick(
        drivers=("B@T1", "C@T2"),
        constructors=("T1",),
        drs_driver="C@T2",
        moves_used=1,
        cost=35.0,
        unused_budget=5.0,
    )
    assert isinstance(pick.moves_used, int)
    assert team.assets == {AssetType.DRIVER: ["A@T1", "B@T1"], AssetType.CONSTRUCTOR: ["T1"]}
    assert (team.unused_budget, team.drs_driver) == (0.0, "")


@pytest.mark.parametrize("max_moves, expected", [
    (2, (("A@T1", "D@T2"), ("T1",), 2)),
    (3, (("A@T1", "D@T2"), ("T2",), 3)),
])
def test_solve_race_keeps_to_max_moves(max_moves, expected):
    race_1 = make_race(1)
    race_2 = make_race(2, scores={"A@T1": 30.0, "D@T2": 20.0, "T2": 10.0})

    pick = solve_race(StrategyMaxScore, make_team(["B@T1", "C@T2"], "T1"), race_2, race_1, SEASON, max_moves)

    assert (pick.drivers, pick.constructors, pick.moves_used) == expected


def test_solve_race_raises_when_the_solver_is_not_optimal(budget_season, caplog):
    race_1, race_2 = budget_season.races[1], budget_season.races[2]

    with caplog.at_level(logging.ERROR), pytest.raises(RuntimeError, match="not optimal"):
        solve_race(StrategyInfeasible, make_team(["A@T1", "B@T1"], "T1"), race_2, race_1, SEASON, max_moves=2)

    assert "LP model returned" in caplog.text
    assert f"Season {SEASON} race 2" in caplog.text


@pytest.mark.parametrize("moves_used, expected", [(0, 3), (1, 3), (2, 2), (3, 2), (7, 2)])
def test_next_free_moves(moves_used, expected):
    assert next_free_moves(moves_used) == expected


@pytest.mark.parametrize("max_cost, expected", [
    ({}, ("T1", 30.0, 0.0)),
    ({"max_cost": 65.0}, ("T2", 60.0, 5.0)),
])
def test_solve_race_takes_a_cost_cap_in_place_of_the_team_budget(max_cost, expected):
    # T2 costs 40 and scores, but the team is worth 30 with nothing unused
    race_1 = make_race(1)
    race_2 = make_race(2, prices={"T2": 40.0}, scores={"T2": 10.0})

    pick = solve_race(StrategyMaxScore, make_team(["A@T1", "B@T1"], "T1"), race_2, race_1, SEASON, 2, **max_cost)

    assert (pick.constructors[0], pick.cost, pick.unused_budget) == expected


def test_limitless_cap_is_the_sum_of_every_available_price():
    race = make_race(1, prices={"A@T1": 1.5, "T2": 30.0})
    del race.drivers["D@T2"]

    # A, B, C, then T1 and T2
    assert limitless_cap(race) == 1.5 + 10.0 + 10.0 + 10.0 + 30.0


def test_limitless_cap_still_forces_out_a_driver_who_has_left_the_race():
    # StrategyBase prices a held driver who has left at COST_PROHIBITIVE so no budget
    # keeps him; StrategyMaxBudget would keep him under any cap that reached it
    race_1 = make_race(1)
    race_2 = make_race(2)
    del race_2.drivers["A@T1"]
    team = make_team(["A@T1", "B@T1"], "T1")

    pick = solve_race(StrategyMaxBudget, team, race_2, race_1, SEASON, max_moves=3, max_cost=limitless_cap(race_2))

    assert "A@T1" not in pick.drivers
    assert limitless_cap(race_2) < COST_PROHIBITIVE
