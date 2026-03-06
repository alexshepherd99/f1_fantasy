from external_data.process_data import get_rolling_window_races


def test_get_rolling_window_races():
    assert get_rolling_window_races(1, 3) == []
    assert get_rolling_window_races(2, 3) == [1]
    assert get_rolling_window_races(3, 3) == [1, 2]
    assert get_rolling_window_races(4, 3) == [1, 2, 3]
    assert get_rolling_window_races(5, 3) == [2, 3, 4]
    assert get_rolling_window_races(5, 4) == [1, 2, 3, 4]
