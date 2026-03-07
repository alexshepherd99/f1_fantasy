import pandas as pd
from external_data.process_data import get_rolling_window_races, get_rolling_prev_points
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
    result = get_rolling_prev_points(df_data, race_num=3, rolling_window=3)
    
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
    assert ver_row["RollingPointsRank"] == 1
    assert ham_row["RollingPointsRank"] == 2


def test_get_rolling_prev_points_with_nan():
    # Test handling of NaN/coerced values
    df_data = pd.DataFrame({
        "Race": [1, 1, 2, 2],
        "Abbreviation": ["VER", "HAM", "VER", "HAM"],
        "Points": [25, "18", 20, None]  # Mixed valid and invalid values
    })

    result = get_rolling_prev_points(df_data, race_num=3, rolling_window=3)
    
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

    result = get_rolling_prev_points(df_data, race_num=1, rolling_window=3)
    
    # Should return empty dataframe since there are no races in rolling window
    assert len(result) == 0


def test_get_rolling_prev_points_five_races_three_drivers():
    # Test with 5 races in total, 3 drivers, and rolling window of 3
    df_data = pd.DataFrame({
        "Race": [1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4, 5, 5, 5],
        "Abbreviation": ["VER", "HAM", "LEC", "VER", "HAM", "LEC", "VER", "HAM", "LEC", "VER", "HAM", "LEC", "VER", "HAM", "LEC"],
        "Points": [25, 18, 15, 20, 25, 18, 18, 20, 25, 25, 15, 20, 22, 20, 18]
    })

    # Test for race 5 with window 3 (includes races 2, 3, 4)
    result = get_rolling_prev_points(df_data, race_num=5, rolling_window=3)
    
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
    assert lec_row["RollingPoints"] == 63
    
    # Check rankings (VER and LEC tied at rank 1, HAM at rank 2)
    assert ver_row["RollingPointsRank"] == 1
    assert lec_row["RollingPointsRank"] == 1
    assert ham_row["RollingPointsRank"] == 2
