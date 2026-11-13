import pytest

from live.display import asset_price, default_drs, format_prices, format_table, manual_pick, parse_team
from simulate.pick import Pick
from tests.live_fixtures import CONSTRUCTORS, PAIRS, make_race

PRICES = {"VER@RED": 28.4, "LEC@FER": 22.0, "HAM@FER": 21.5, "RED": 30.1, "FER": 25.0}
RACE = make_race(10, prices=PRICES, drop=("PER@CAD",))
RACE_PREV = make_race(9, prices={"PER@CAD": 7.3})

DRIVERS = ("HUL@AUD", "LAW@VRB", "LEC@FER", "PER@CAD", "VER@RED")


def test_a_price_is_the_races():
    assert asset_price("VER@RED", RACE, RACE_PREV) == 28.4
    assert asset_price("RED", RACE, RACE_PREV) == 30.1


def test_a_driver_who_has_left_is_priced_at_the_race_before():
    assert asset_price("PER@CAD", RACE, RACE_PREV) == 7.3


def test_reads_a_typed_team_sorted():
    team = parse_team(" VER@RED,LEC@FER , HUL@AUD,LAW@VRB,PER@CAD", "RED, FER", set(PAIRS), set(CONSTRUCTORS))

    assert team == (DRIVERS, ("FER", "RED"))


@pytest.mark.parametrize("drivers, constructors, match", [
    ("VER@RED,LEC@FER,HUL@AUD,LAW@VRB", "RED,FER", "five"),
    ("VER@RED,LEC@FER,HUL@AUD,LAW@VRB,LAW@VRB", "RED,FER", "five"),
    ("VER@RED,LEC@FER,HUL@AUD,LAW@VRB,VER", "RED,FER", "VER"),
    ("VER@RED,LEC@FER,HUL@AUD,LAW@VRB,PER@CAD", "RED", "two"),
    ("VER@RED,LEC@FER,HUL@AUD,LAW@VRB,PER@CAD", "RED,XXX", "XXX"),
])
def test_refuses_a_typed_team_that_does_not_fit(drivers, constructors, match):
    with pytest.raises(ValueError, match=match):
        parse_team(drivers, constructors, set(PAIRS), set(CONSTRUCTORS))


def test_the_default_drs_driver_is_the_most_expensive():
    assert default_drs(("HUL@AUD", "LEC@FER", "VER@RED"), RACE) == "VER@RED"


def test_a_manual_pick_is_costed_against_the_budget():
    held = ("HUL@AUD", "LAW@VRB", "LEC@FER", "PER@CAD", "VER@RED", "FER", "RED")
    drivers = ("HAM@FER", "HUL@AUD", "LAW@VRB", "LEC@FER", "VER@RED")

    pick = manual_pick(drivers, ("FER", "MER"), "HAM@FER", held, RACE, budget=150.0)

    cost = 21.5 + 10 + 10 + 22.0 + 28.4 + 25.0 + 10
    assert pick == Pick(drivers=drivers, constructors=("FER", "MER"), drs_driver="HAM@FER", moves_used=2,
                        cost=pytest.approx(cost), unused_budget=pytest.approx(150.0 - cost))


def test_the_table_puts_picks_side_by_side_with_prices():
    held = Pick(drivers=DRIVERS, constructors=("FER", "RED"), drs_driver="", moves_used=0, cost=103.6,
                unused_budget=1.0)
    pick = Pick(drivers=("HAM@FER", "HUL@AUD", "LAW@VRB", "LEC@FER", "VER@RED"), constructors=("FER", "MER"),
                drs_driver="VER@RED", moves_used=2, cost=99.9, unused_budget=4.7)

    lines = format_table(held, [("1 StrategyMaxP2PM", pick)], RACE, RACE_PREV)

    assert lines == [
        "             Held            1 StrategyMaxP2PM",
        "Driver       HUL@AUD   10.0  HAM@FER   21.5",
        "Driver       LAW@VRB   10.0  HUL@AUD   10.0",
        "Driver       LEC@FER   22.0  LAW@VRB   10.0",
        "Driver       PER@CAD    7.3  LEC@FER   22.0",
        "Driver       VER@RED   28.4  VER@RED   28.4",
        "Constructor  FER       25.0  FER       25.0",
        "Constructor  RED       30.1  MER       10.0",
        "DRS          -               VER@RED",
        "Moves        -               2",
        "Cost         103.6           99.9",
        "Unused       1.0             4.7",
    ]


def test_the_table_without_a_team_held_shows_only_the_picks():
    pick = Pick(drivers=("HAM@FER", "HUL@AUD", "LAW@VRB", "LEC@FER", "VER@RED"), constructors=("FER", "MER"),
                drs_driver="VER@RED", moves_used=7, cost=99.9, unused_budget=0.1)

    lines = format_table(None, [("1 StrategyBettingOdds:999.9", pick)], RACE, RACE)

    assert lines[0] == "             1 StrategyBettingOdds:999.9"
    assert lines[1] == "Driver       HAM@FER   21.5"
    assert lines[-3:] == ["Moves        7", "Cost         99.9", "Unused       0.1"]


def test_the_price_list_runs_most_expensive_first():
    lines = format_prices(RACE)

    assert lines[:3] == ["  RED        30.1", "  VER@RED    28.4", "  FER        25.0"]
    assert len(lines) == len(RACE.drivers) + len(RACE.constructors)
