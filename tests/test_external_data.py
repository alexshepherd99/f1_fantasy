import pandas as pd
import pytest
from external_data.process_data import get_rolling_window_races, get_rolling_prev_points, get_practice_and_rolling_metrics
from external_data.fastf1_common import get_cache_filename


def test_get_cache_filename():
    def dummy_func():
        pass
    
    assert get_cache_filename(
        dummy_func,
        (),
        {}
    ) == "cache_dummy_func.pkl"

    assert get_cache_filename(
        dummy_func,
        (100,),
        {}
    ) == "cache_dummy_func_100.pkl"

    assert get_cache_filename(
        dummy_func,
        (100, 200),
        {}
    ) == "cache_dummy_func_100_200.pkl"

    assert get_cache_filename(
        dummy_func,
        (),
        {"a": 99}
    ) == "cache_dummy_func_a-99.pkl"

    assert get_cache_filename(
        dummy_func,
        (),
        {"a": 99, "b": 88}
    ) == "cache_dummy_func_a-99_b-88.pkl"

    assert get_cache_filename(
        dummy_func,
        (100, 200),
        {"a": 99, "b": 88}
    ) == "cache_dummy_func_100_200_a-99_b-88.pkl"


def test_get_rolling_window_races():
    assert get_rolling_window_races(1, 3) == []
    assert get_rolling_window_races(2, 3) == [1]
    assert get_rolling_window_races(3, 3) == [1, 2]
    assert get_rolling_window_races(4, 3) == [1, 2, 3]
    assert get_rolling_window_races(5, 3) == [2, 3, 4]
    assert get_rolling_window_races(5, 4) == [1, 2, 3, 4]


def test_get_rolling_prev_points():
    # Create sample race results data
    df_data = pd.DataFrame({
        "Race": [1, 1, 2, 2, 3, 3],
        "Abbreviation": ["VER", "HAM", "VER", "HAM", "VER", "HAM"],
        "Points": [25, 18, 20, 15, 25, 10]
    })

    # Test 1: Rolling window of 3 for race 3 (includes races 1, 2)
    result = get_rolling_prev_points(df_data, season_year=1999, race_num=3, rolling_window=3)
    
    # Check that both drivers are in the result
    assert len(result) == 2
    assert set(result["Driver"]) == {"VER", "HAM"}
    
    # Check rolling points are summed correctly
    # VER: 25 (race 1) + 20 (race 2) = 45
    # HAM: 18 (race 1) + 15 (race 2) = 33
    ver_row = result[result["Driver"] == "VER"].iloc[0]
    ham_row = result[result["Driver"] == "HAM"].iloc[0]
    assert ver_row["RollingPoints"] == 45
    assert ham_row["RollingPoints"] == 33
    
    # Check rankings (VER should be rank 1, HAM should be rank 2)
    assert ver_row["RollingPointsRank"] == pytest.approx(1.0, 0.0001)
    assert ham_row["RollingPointsRank"] == pytest.approx(0.0, 0.0001)


def test_get_rolling_prev_points_with_nan():
    # Test handling of NaN/coerced values
    df_data = pd.DataFrame({
        "Race": [1, 1, 2, 2],
        "Abbreviation": ["VER", "HAM", "VER", "HAM"],
        "Points": [25, "18", 20, None]  # Mixed valid and invalid values
    })

    result = get_rolling_prev_points(df_data, season_year=1999, race_num=3, rolling_window=3)
    
    # get_rolling_window_races(3, 3) returns [1, 2]
    # VER: 25 (race 1) + 20 (race 2) = 45
    # HAM: 18 (race 1) + NaN (race 2) = 18 (NaN is coerced to NaN, then sums to 18)
    ver_row = result[result["Driver"] == "VER"].iloc[0]
    ham_row = result[result["Driver"] == "HAM"].iloc[0]
    assert ver_row["RollingPoints"] == 45
    assert ham_row["RollingPoints"] == 18.0


def test_get_rolling_prev_points_single_race():
    # Test edge case where race_num=1 (no previous races)
    df_data = pd.DataFrame({
        "Race": [1, 1],
        "Abbreviation": ["VER", "HAM"],
        "Points": [25, 18]
    })

    result = get_rolling_prev_points(df_data, season_year=1999, race_num=1, rolling_window=3)
    
    # Should return empty dataframe since there are no races in rolling window
    assert len(result) == 0


def test_get_rolling_prev_points_five_races_three_drivers():
    # Test with 5 races in total, 3 drivers, and rolling window of 3
    df_data = pd.DataFrame({
        "Race": [1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4, 5, 5, 5],
        "Abbreviation": ["VER", "HAM", "LEC", "VER", "HAM", "LEC", "VER", "HAM", "LEC", "VER", "HAM", "LEC", "VER", "HAM", "LEC"],
        "Points": [25, 18, 15, 20, 25, 18, 18, 20, 25, 25, 15, 15, 22, 20, 18]
    })

    # Test for race 5 with window 3 (includes races 2, 3, 4)
    result = get_rolling_prev_points(df_data, season_year=1999, race_num=5, rolling_window=3)
    
    # Check that all three drivers are in the result
    assert len(result) == 3
    assert set(result["Driver"]) == {"VER", "HAM", "LEC"}
    
    # Check rolling points are summed correctly for races 2, 3, 4
    # VER: 20 (race 2) + 18 (race 3) + 25 (race 4) = 63
    # HAM: 25 (race 2) + 20 (race 3) + 15 (race 4) = 60
    # LEC: 18 (race 2) + 25 (race 3) + 20 (race 4) = 63
    ver_row = result[result["Driver"] == "VER"].iloc[0]
    ham_row = result[result["Driver"] == "HAM"].iloc[0]
    lec_row = result[result["Driver"] == "LEC"].iloc[0]
    
    assert ver_row["RollingPoints"] == 63
    assert ham_row["RollingPoints"] == 60
    assert lec_row["RollingPoints"] == 58
    
    # Check rankings (VER and LEC tied at rank 1, HAM at rank 2)
    assert ver_row["RollingPointsRank"] == pytest.approx(1.0, 0.001)
    assert lec_row["RollingPointsRank"] == pytest.approx(0.0, 0.001)
    assert ham_row["RollingPointsRank"] == pytest.approx(0.4, 0.001)


def test_practice_and_rolling_metrics_end_to_end():
    # exercise the new aggregation function with real fastf1 data
    season = 2025
    race = 5

    df = get_practice_and_rolling_metrics(season, race)

    assert isinstance(df, pd.DataFrame)

    # minimum expected columns should exist
    expected = {
        "Driver",
        "RollingPoints",
        "RollingPointsRank",
        "FP2_TotalLapCount",
        "FP3_TotalLapCount",
        "FP2_TotalLapCount_rank",
        "FP3_TotalLapCount_rank",
        "FP2_MinLapTime",
        "FP3_MinLapTime",
        "FP2_MinLapTime_rank",
        "FP3_MinLapTime_rank",
        "FP2_MaxLapsInStint",
        "FP3_MaxLapsInStint",
        "FP2_MaxLapsInStint_rank",
        "FP3_MaxLapsInStint_rank",
        "Season",
        "Race",
        "AggregageRank",
    }
    assert expected.issubset(set(df.columns)), f"Missing cols: {expected - set(df.columns)}"

    # No additional columns added
    assert "Season_x" not in df.columns
    assert "Season_y" not in df.columns
    assert "Race_x" not in df.columns
    assert "Race_y" not in df.columns

    # season/race columns are consistent with the arguments
    assert df["Season"].nunique() <= 1
    assert df["Race"].nunique() <= 1
    if not df.empty:
        assert df["Season"].iloc[0] == season
        assert df["Race"].iloc[0] == race

    # there should be at least one driver with a non-null rolling points rank
    assert df["RollingPointsRank"].notna().any()

    # Run again for first race of the season
    df = get_practice_and_rolling_metrics(2025, 1)


def get_val_for_driver(df, drv, val):
    return df.loc[df["Driver"]==drv][val].values[0]


def test_practice_and_rolling_metrics_race_1():
    # Checks on the actual output data.  
    df_2026_1 = get_practice_and_rolling_metrics(2026, 1)

    # No points yet to check, for race 1.  All rank values should be identical.
    assert df_2026_1["RollingPointsRank"].min() == 0.0
    assert df_2026_1["RollingPointsRank"].max() == 0.0


def test_practice_and_rolling_metrics_race_5():
    # Checks on the actual output data.  
    df_2025_5 = get_practice_and_rolling_metrics(2025, 5)

    # Race 5 has some zero points and some null values
    assert df_2025_5["RollingPointsRank"].min() == 0.0
    assert df_2025_5["RollingPointsRank"].max() == 1.0
    assert get_val_for_driver(df_2025_5, "PIA", "RollingPointsRank") == pytest.approx(1.0, 0.0001)
    assert get_val_for_driver(df_2025_5, "NOR", "RollingPointsRank") == pytest.approx(0.7846, 0.0001)
    assert get_val_for_driver(df_2025_5, "BOR", "RollingPointsRank") == 0.0
