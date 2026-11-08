import pytest

from boxbox.mapping import TEAM_CODES, constructor_code, driver_code, results_by_driver_code, round_for_race
from boxbox.source import BoxBoxDataError, parse_files
from tests.boxbox_fixtures import driver_history, modified, raw_files


def test_constructor_code_maps_every_2026_slug():
    assert {slug: constructor_code(slug) for slug in TEAM_CODES} == {
        "mercedes": "MER", "ferrari": "FER", "red_bull": "RED", "racing_bulls": "VRB", "haas": "HAA",
        "alpine": "ALP", "williams": "WIL", "mclaren": "MCL", "audi": "AUD", "cadillac": "CAD",
        "aston_martin": "AST",
    }


def test_constructor_code_rejects_an_unknown_slug():
    with pytest.raises(BoxBoxDataError, match="andretti"):
        constructor_code("andretti")


@pytest.mark.parametrize("key, code", [("VER", "VER"), ("HIR_HAAS", "HIR")])
def test_driver_code_takes_the_part_before_any_suffix(key, code):
    assert driver_code(key) == code


@pytest.mark.parametrize("key", ["", "ver", "VERS", "V1R", "_HAAS"])
def test_driver_code_rejects_a_key_that_is_not_a_driver_code(key):
    with pytest.raises(BoxBoxDataError):
        driver_code(key)


def test_round_for_race_skips_cancelled_rounds():
    data = parse_files(raw_files())

    assert [round_for_race(data, race) for race in [1, 2, 3, 4]] == [1, 2, 4, 5]


@pytest.mark.parametrize("race", [0, 5])
def test_round_for_race_rejects_a_race_beyond_the_calendar(race):
    data = parse_files(raw_files())

    with pytest.raises(BoxBoxDataError, match=f"race {race}"):
        round_for_race(data, race)


def test_results_by_driver_code_strips_suffixes():
    history = modified(driver_history(), lambda h: h["drivers"].update(HAD_RED=h["drivers"].pop("HAD")))
    data = parse_files(raw_files(history=history))

    results = results_by_driver_code(data)

    assert sorted(results) == ["ANT", "HAD", "RUS", "VER"]
    assert results["HAD"] == {1: 5.0, 2: -3.0, 4: 7.5}


def test_results_by_driver_code_rejects_two_keys_for_one_code():
    history = modified(driver_history(), lambda h: h["drivers"].update(VER_HAAS={"rounds": []}))
    data = parse_files(raw_files(history=history))

    with pytest.raises(BoxBoxDataError, match="VER"):
        results_by_driver_code(data)
