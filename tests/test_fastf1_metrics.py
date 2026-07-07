from __future__ import annotations

import pandas as pd
import pytest

from fast_f1.metrics import (
    aggregate_metrics,
    calculate_constructor_rolling_points,
    calculate_practice_performance,
    calculate_rolling_points,
    get_rolling_window_races,
)


def test_get_rolling_window_races_returns_prior_races():
    assert get_rolling_window_races(1, 3) == []
    assert get_rolling_window_races(2, 3) == [1]
    assert get_rolling_window_races(4, 3) == [1, 2, 3]
    assert get_rolling_window_races(5, 4) == [1, 2, 3, 4]


def test_calculate_rolling_points_sums_and_ranks():
    df_data = pd.DataFrame({
        "Race": [1, 1, 2, 2, 3, 3],
        "Abbreviation": ["VER", "HAM", "VER", "HAM", "VER", "HAM"],
        "Points": [25, 18, 20, 15, 25, 10],
    })

    result = calculate_rolling_points(df_data, season_year=2025, race_num=3, rolling_window=3)

    assert set(result["Driver"]) == {"VER", "HAM"}
    ver = result[result["Driver"] == "VER"].iloc[0]
    ham = result[result["Driver"] == "HAM"].iloc[0]
    assert ver["RollingPoints"] == 45
    assert ham["RollingPoints"] == 33
    assert ver["RollingPointsRank"] == pytest.approx(1.0, 1e-4)
    assert ham["RollingPointsRank"] == pytest.approx(0.0, 1e-4)
    assert all(result["Season"] == 2025)
    assert all(result["Race"] == 3)


def test_calculate_rolling_points_supports_constructor_column():
    df_data = pd.DataFrame({
        "Race": [1, 1, 2, 2],
        "Constructor": ["RED", "MER", "RED", "MER"],
        "Points": [18, 25, 20, 15],
    })

    result = calculate_rolling_points(df_data, season_year=2025, race_num=3, rolling_window=3)

    assert set(result["Driver"]) == {"RED", "MER"}
    red = result[result["Driver"] == "RED"].iloc[0]
    mer = result[result["Driver"] == "MER"].iloc[0]
    assert red["RollingPoints"] == 38
    assert mer["RollingPoints"] == 40
    assert mer["RollingPointsRank"] == pytest.approx(1.0, 1e-4)
    assert red["RollingPointsRank"] == pytest.approx(0.0, 1e-4)


def test_calculate_rolling_points_returns_empty_when_no_previous_races():
    df_data = pd.DataFrame({
        "Race": [1, 1],
        "Abbreviation": ["VER", "HAM"],
        "Points": [25, 18],
    })

    result = calculate_rolling_points(df_data, season_year=2025, race_num=1, rolling_window=3)
    assert result.empty
    assert list(result.columns) == ["Driver", "RollingPoints", "RollingPointsRank", "Season", "Race"]


def test_calculate_rolling_points_handles_empty_input_frame():
    result = calculate_rolling_points(pd.DataFrame(), season_year=2025, race_num=1, rolling_window=3)
    assert result.empty
    assert list(result.columns) == ["Driver", "RollingPoints", "RollingPointsRank", "Season", "Race"]


def test_calculate_constructor_rolling_points_handles_empty_input_frame():
    result = calculate_constructor_rolling_points(pd.DataFrame(), season_year=2025, race_num=1, rolling_window=3)
    assert result.empty
    assert list(result.columns) == [
        "Constructor",
        "ConstructorRollingPoints",
        "ConstructorRollingPointsRank",
        "Season",
        "Race",
    ]


def test_calculate_practice_performance_creates_ranked_columns():
    df_session_laps = pd.DataFrame({
        "Season": [2025, 2025, 2025, 2025],
        "Race": [5, 5, 5, 5],
        "SessionType": ["FP2", "FP2", "FP2", "FP2"],
        "Driver": ["PER", "ALO", "PER", "ALO"],
        "LapTime": [80.0, 82.0, 83.0, 79.0],
        "Stint": [1, 1, 2, 2],
    })

    result = calculate_practice_performance(df_session_laps)
    assert set(result.columns) >= {
        "Driver",
        "FP2_TotalLapCount",
        "FP2_MinLapTime",
        "FP2_MaxLapsInStint",
        "FP2_MinLapTime_rank",
        "Season",
        "Race",
    }
    assert result.loc[result["Driver"] == "PER", "FP2_TotalLapCount"].iloc[0] == 2
    assert result.loc[result["Driver"] == "ALO", "FP2_TotalLapCount"].iloc[0] == 2
    assert result.loc[result["Driver"] == "ALO", "FP2_MinLapTime_rank"].iloc[0] == pytest.approx(1.0, 1e-4)
    assert result.loc[result["Driver"] == "PER", "FP2_MinLapTime_rank"].iloc[0] == pytest.approx(0.0, 1e-4)


def test_calculate_practice_performance_raises_when_multiple_session_types():
    df_session_laps = pd.DataFrame({
        "Season": [2025, 2025],
        "Race": [5, 5],
        "SessionType": ["FP2", "FP3"],
        "Driver": ["PER", "ALO"],
        "LapTime": [80.0, 81.0],
        "Stint": [1, 1],
    })

    with pytest.raises(ValueError):
        calculate_practice_performance(df_session_laps)


def test_aggregate_metrics_sums_rank_columns():
    df = pd.DataFrame({
        "Driver": ["A", "B"],
        "RollingPointsRank": [1.0, 0.0],
        "ConstructorRollingPointsRank": [0.2, 0.4],
        "FP2_MinLapTime_rank": [0.5, 1.0],
        "FP3_MinLapTime_rank": [0.5, 0.0],
    })

    result = aggregate_metrics(df)
    assert list(result["Driver"]) == ["A", "B"]
    assert result.loc[result["Driver"] == "A", "AggregateRank"].iloc[0] == pytest.approx(2.2, 1e-4)
    assert result.loc[result["Driver"] == "B", "AggregateRank"].iloc[0] == pytest.approx(1.4, 1e-4)
