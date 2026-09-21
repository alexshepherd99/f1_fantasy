import pytest

from backtest.per_race import concentration, race_driver_pairs
from helpers import load_with_derivations
from races.season import factory_season

_SEASON = 2023

# One constructor's two drivers, a second constructor's two, and a lone third
_PAIRS = {
    "VER@RED": "RED",
    "PER@RED": "RED",
    "HAM@MER": "MER",
    "RUS@MER": "MER",
    "NOR@MCL": "MCL",
}


def test_a_team_sharing_no_constructor_is_unconcentrated():
    assert concentration(["VER@RED", "HAM@MER", "NOR@MCL"], ["FER"], _PAIRS) == 0


def test_two_drivers_from_one_constructor_count_once():
    assert concentration(["VER@RED", "PER@RED", "NOR@MCL"], ["FER"], _PAIRS) == 1


def test_a_driver_held_with_their_own_constructor_counts_once():
    assert concentration(["VER@RED", "HAM@MER"], ["RED"], _PAIRS) == 1


def test_a_constructor_pairs_with_each_of_its_held_drivers():
    # One driver-driver pair, plus a driver-constructor pair for each of the two
    assert concentration(["VER@RED", "PER@RED"], ["RED"], _PAIRS) == 3


def test_a_constructor_with_none_of_its_drivers_is_unconcentrated():
    assert concentration(["HAM@MER"], ["RED"], _PAIRS) == 0


def test_drivers_from_one_constructor_count_every_pair_between_them():
    # Three is impossible in F1, but it fixes the metric as pair-counting rather
    # than counting the constructors that are doubled up on
    pairs = _PAIRS | {"LAW@RED": "RED"}
    assert concentration(["VER@RED", "PER@RED", "LAW@RED"], [], pairs) == 3


def test_a_driver_missing_from_the_pairings_raises():
    with pytest.raises(ValueError, match="SAI@FER"):
        concentration(["VER@RED", "SAI@FER"], [], _PAIRS)


def test_race_driver_pairs_covers_every_driver_in_the_race():
    season = factory_season(*load_with_derivations(season=_SEASON), _SEASON)
    race = season.races[1]

    pairs = race_driver_pairs(race)

    assert set(pairs) == set(race.drivers)
    assert pairs["VER@RED"] == "RED"
