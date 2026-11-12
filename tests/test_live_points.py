from dataclasses import replace

import pytest

from live.points import predict_points
from live.team_file import TeamRow
from tests.live_fixtures import make_race

ROW = TeamRow(season=2026, race=20, strategy="StrategyMaxP2PM", chip="",
              drivers=("HUL@AUD", "LAW@VRB", "LEC@FER", "PER@CAD", "VER@RED"), constructors=("FER", "RED"),
              drs="VER@RED", free_moves=2, moves_used=1, team_value=135.3, unused_budget=1.0,
              points_predicted=None, points=None)

# Team total without DRS: 1 + 2 + 13 - 6 + 10 + 20 + 30 = 70; LEC scores most of the drivers
POINTS = {"HUL@AUD": 1, "LAW@VRB": 2, "LEC@FER": 13, "PER@CAD": -6, "VER@RED": 10, "FER": 20, "RED": 30,
          "HAM@FER": 25}
RACE = make_race(20, points=POINTS)


def test_the_drs_driver_scores_twice():
    assert predict_points(ROW, RACE) == 70 + 10


def test_extra_drs_scores_the_drs_driver_three_times():
    assert predict_points(replace(ROW, chip="Extra DRS"), RACE) == 70 + 2 * 10


def test_autopilot_gives_drs_to_the_highest_scoring_driver():
    assert predict_points(replace(ROW, chip="Autopilot"), RACE) == 70 + 13


def test_no_negative_is_left_out():
    assert predict_points(replace(ROW, chip="No Negative"), RACE) == 70 + 10


def test_final_fix_scores_the_driver_swapped_in():
    row = replace(ROW, chip="Final Fix")

    assert predict_points(row, RACE, final_fix=("PER@CAD", "HAM@FER")) == 70 + 6 + 25 + 10


def test_final_fix_of_the_drs_driver_gives_drs_to_the_one_swapped_in():
    row = replace(ROW, chip="Final Fix")

    assert predict_points(row, RACE, final_fix=("VER@RED", "HAM@FER")) == 70 - 10 + 25 + 25


@pytest.mark.parametrize("chip, final_fix, match", [
    ("", ("PER@CAD", "HAM@FER"), "Final Fix"),
    ("Final Fix", None, "Final Fix"),
    ("Final Fix", ("BOR@AUD", "HAM@FER"), "BOR@AUD"),
    ("Final Fix", ("PER@CAD", "LEC@FER"), "LEC@FER"),
    ("Final Fix", ("PER@CAD", "XXX@YYY"), "XXX@YYY"),
])
def test_refuses_a_final_fix_that_does_not_fit(chip, final_fix, match):
    with pytest.raises(ValueError, match=match):
        predict_points(replace(ROW, chip=chip), RACE, final_fix=final_fix)
