from __future__ import annotations

import logging
from typing import Literal

import pandas as pd


logger = logging.getLogger(__name__)


def get_rolling_window_races(race_num: int, rolling_window: int = 3) -> list[int]:
    """Return the list of prior race numbers included in a rolling window."""
    return [r for r in range(race_num - rolling_window, race_num) if r > 0]


def _get_asset_column(df: pd.DataFrame) -> str:
    if "Driver" in df.columns:
        return "Driver"
    if "Abbreviation" in df.columns:
        return "Abbreviation"
    if "Constructor" in df.columns:
        return "Constructor"

    raise ValueError(
        "Input dataframe must contain one of 'Driver', 'Abbreviation', or 'Constructor' columns."
    )


def calculate_rolling_points(
    df_all_race_results: pd.DataFrame,
    season_year: int,
    race_num: int,
    rolling_window: int = 3,
) -> pd.DataFrame:
    """Calculate rolling points and normalized rank over prior races.

    The returned frame includes at least:
    ``Driver``, ``RollingPoints``, ``RollingPointsRank``, ``Season``, ``Race``.
    """
    races = get_rolling_window_races(race_num=race_num, rolling_window=rolling_window)
    if not races:
        return pd.DataFrame(
            columns=["Driver", "RollingPoints", "RollingPointsRank", "Season", "Race"]
        )

    df_prev_results = df_all_race_results[df_all_race_results["Race"].isin(races)].copy()
    if df_prev_results.empty:
        return pd.DataFrame(
            columns=["Driver", "RollingPoints", "RollingPointsRank", "Season", "Race"]
        )

    asset_col = _get_asset_column(df_prev_results)
    df_prev_results = df_prev_results.copy()
    df_prev_results["RollingPoints"] = pd.to_numeric(
        df_prev_results["Points"], errors="coerce"
    )
    df_result = (
        df_prev_results.groupby(asset_col, as_index=False)["RollingPoints"].sum()
    )
    df_result = df_result.rename(columns={asset_col: "Driver"})

    min_points = df_result["RollingPoints"].min()
    max_points = df_result["RollingPoints"].max()
    if min_points == max_points:
        df_result["RollingPointsRank"] = 0.0
    else:
        df_result["RollingPointsRank"] = (
            df_result["RollingPoints"] - min_points
        ) / (max_points - min_points)

    df_result["Season"] = season_year
    df_result["Race"] = race_num
    df_result = df_result.sort_values("Driver").reset_index(drop=True)
    return df_result


def calculate_practice_performance(df_session_laps: pd.DataFrame) -> pd.DataFrame:
    """Summarize practice session performance metrics for a single race session."""
    if len(df_session_laps["Season"].unique()) != 1:
        raise ValueError("Season not unique in session laps")
    if len(df_session_laps["Race"].unique()) != 1:
        raise ValueError("Race not unique in session laps")
    if len(df_session_laps["SessionType"].unique()) != 1:
        raise ValueError("SessionType not unique in session laps")

    session_type = df_session_laps["SessionType"].iloc[0]
    df_session_laps = df_session_laps.copy()

    fastest_overall_lap = df_session_laps["LapTime"].min()
    threshold_time = fastest_overall_lap * 1.07
    df_session_laps = df_session_laps[
        df_session_laps["LapTime"] <= threshold_time
    ].copy()

    total_lap_count = (
        df_session_laps.groupby("Driver")
        .size()
        .reset_index(name="TotalLapCount")
    )
    min_lap_time = (
        df_session_laps.groupby("Driver")
        ["LapTime"]
        .min()
        .reset_index(name="MinLapTime")
    )
    max_laps_in_stint = (
        df_session_laps.groupby(["Driver", "Stint"]).size()
        .reset_index(name="LapCountInStint")
        .groupby("Driver")["LapCountInStint"]
        .max()
        .reset_index(name="MaxLapsInStint")
    )

    df_result = total_lap_count.merge(min_lap_time, on="Driver")
    df_result = df_result.merge(max_laps_in_stint, on="Driver")

    if df_result["MinLapTime"].max() == df_result["MinLapTime"].min():
        df_result["MinLapTime_rank"] = 0.0
    else:
        df_result["MinLapTime_rank"] = (
            1.0 - (
                (df_result["MinLapTime"] - df_result["MinLapTime"].min()) /
                (df_result["MinLapTime"].max() - df_result["MinLapTime"].min())
            )
        )

    columns_to_prefix = [col for col in df_result.columns if col != "Driver"]
    rename_mapping = {
        col: f"{session_type}_{col}" for col in columns_to_prefix
    }
    df_result = df_result.rename(columns=rename_mapping)
    df_result = df_result.sort_values("Driver").reset_index(drop=True)

    df_result["Season"] = df_session_laps["Season"].iloc[0]
    df_result["Race"] = df_session_laps["Race"].iloc[0]
    return df_result


def aggregate_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Combine independent indicators into an aggregate ranking."""
    if df.empty:
        return df.copy()

    df = df.copy()
    rank_columns = [
        col for col in df.columns
        if col != "AggregateRank" and (
            col == "RollingPointsRank" or col.endswith("_rank")
        )
    ]
    df["AggregateRank"] = 0.0
    for col in rank_columns:
        df[col] = df[col].fillna(0.0)
        df["AggregateRank"] += df[col]

    df = df.sort_values(by="AggregateRank", ascending=False).reset_index(drop=True)
    return df
