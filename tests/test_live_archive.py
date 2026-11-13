import pandas as pd
import pytest

from live.archive import SeasonOver, next_race, race_scored

NAN = float("nan")


def _drivers(rows: list[tuple[int, int, float]]) -> pd.DataFrame:
    """Two drivers per (season, race, points); the second scores nothing when the race is unscored."""
    lines = []
    for season, race, points in rows:
        lines.append({"Season": season, "Race": race, "Constructor": "RED", "Driver": "VER", "Points": points,
                      "Price": 30.0})
        lines.append({"Season": season, "Race": race, "Constructor": "RED", "Driver": "HAD",
                      "Points": NAN if pd.isna(points) else 0.0, "Price": 10.0})
    return pd.DataFrame(lines)


def test_the_next_race_is_the_latest_seasons_first_without_points():
    drivers = _drivers([(2025, 1, 10.0), (2025, 2, NAN), (2026, 1, 10.0), (2026, 2, 5.0), (2026, 3, NAN)])

    assert next_race(drivers) == (2026, 3)


def test_a_season_with_every_race_scored_is_over():
    drivers = _drivers([(2025, 1, NAN), (2026, 1, 10.0), (2026, 2, 5.0)])

    with pytest.raises(SeasonOver, match="2026") as over:
        next_race(drivers)
    assert over.value.season == 2026


def test_a_race_with_points_is_scored():
    drivers = _drivers([(2026, 1, 10.0), (2026, 2, NAN)])

    assert race_scored(drivers, 2026, 1)
    assert not race_scored(drivers, 2026, 2)


def test_a_race_scoring_zero_is_scored():
    drivers = _drivers([(2026, 1, 0.0)])

    assert race_scored(drivers, 2026, 1)
