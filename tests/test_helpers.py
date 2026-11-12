from helpers import load_with_derivations
from tests.live_archive import SEASON, write_archive


def test_loads_the_season_from_the_directory_given(tmp_path):
    write_archive(tmp_path, last_race=3, price_changes={(2, "VER"): "99.9", (2, "RED"): "88.8"})

    drivers, constructors, pairs = load_with_derivations(SEASON, str(tmp_path))

    assert drivers[(drivers["Race"] == 2) & (drivers["Driver"] == "VER@RED")]["Price"].item() == 99.9
    assert constructors[(constructors["Race"] == 2) & (constructors["Constructor"] == "RED")]["Price"].item() == 88.8
    assert sorted(pairs["Race"].unique()) == [1, 2, 3]
