from __future__ import annotations

import pandas as pd


def get_rolling_window_races(race_num: int, rolling_window: int = 3) -> list[int]:
    """Return the list of prior race numbers included in a rolling window."""
    return [r for r in range(race_num - rolling_window, race_num) if r > 0]


def calculate_rolling_points(df_all_race_results: pd.DataFrame, season_year: int, race_num: int, rolling_window: int = 3) -> pd.DataFrame:
    """Calculate driver rolling points and ranking over prior races."""
    raise NotImplementedError("calculate_rolling_points is not implemented yet")


def calculate_practice_performance(df_session_laps: pd.DataFrame) -> pd.DataFrame:
    """Summarize practice session performance metrics for a single race session."""
    raise NotImplementedError("calculate_practice_performance is not implemented yet")


def aggregate_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Combine independent indicators into an aggregate ranking."""
    raise NotImplementedError("aggregate_metrics is not implemented yet")
