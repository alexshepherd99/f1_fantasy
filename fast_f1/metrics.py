from __future__ import annotations

import logging
from typing import Iterable, Literal

import numpy as np
import pandas as pd


logger = logging.getLogger(__name__)

# Relative contribution of each indicator to AggregateRank. Indicators not
# listed here carry a weight of 1.0.
METRIC_WEIGHTS: dict[str, float] = {
    "OddsRank": 2.0,
}


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


def _calculate_rolling_points(
    df_all_race_results: pd.DataFrame,
    asset_col: str,
    season_year: int,
    race_num: int,
    rolling_window: int = 3,
    output_name_prefix: str = "",
    output_asset_name: str | None = None,
) -> pd.DataFrame:
    """Calculate rolling points for a generic asset column and normalize the result."""
    if output_asset_name is None:
        output_asset_name = asset_col

    races = get_rolling_window_races(race_num=race_num, rolling_window=rolling_window)
    if not races:
        return pd.DataFrame(
            columns=[output_asset_name, f"{output_name_prefix}RollingPoints", f"{output_name_prefix}RollingPointsRank", "Season", "Race"]
        )

    df_prev_results = df_all_race_results[df_all_race_results["Race"].isin(races)].copy()
    if df_prev_results.empty:
        return pd.DataFrame(
            columns=[output_asset_name, f"{output_name_prefix}RollingPoints", f"{output_name_prefix}RollingPointsRank", "Season", "Race"]
        )

    df_prev_results = df_prev_results.copy()
    df_prev_results["RollingPoints"] = pd.to_numeric(
        df_prev_results["Points"], errors="coerce"
    )
    df_result = (
        df_prev_results.groupby(asset_col, as_index=False)["RollingPoints"].sum()
    )

    output_points = f"{output_name_prefix}RollingPoints"
    output_rank = f"{output_name_prefix}RollingPointsRank"
    df_result = df_result.rename(columns={asset_col: output_asset_name})
    df_result = df_result.rename(columns={"RollingPoints": output_points})

    min_points = df_result[output_points].min()
    max_points = df_result[output_points].max()
    if min_points == max_points:
        df_result[output_rank] = 0.0
    else:
        df_result[output_rank] = (
            df_result[output_points] - min_points
        ) / (max_points - min_points)

    df_result["Season"] = season_year
    df_result["Race"] = race_num
    df_result = df_result.sort_values(output_asset_name).reset_index(drop=True)
    return df_result


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
    if df_all_race_results.empty:
        return pd.DataFrame(
            columns=["Driver", "RollingPoints", "RollingPointsRank", "Season", "Race"]
        )

    asset_col = _get_asset_column(df_all_race_results)
    return _calculate_rolling_points(
        df_all_race_results,
        asset_col=asset_col,
        season_year=season_year,
        race_num=race_num,
        rolling_window=rolling_window,
        output_name_prefix="",
        output_asset_name="Driver",
    )


def calculate_constructor_rolling_points(
    df_all_race_results: pd.DataFrame,
    season_year: int,
    race_num: int,
    rolling_window: int = 3,
) -> pd.DataFrame:
    """Calculate rolling constructor points and normalized rank over prior races."""
    if df_all_race_results.empty:
        return pd.DataFrame(
            columns=["Constructor", "ConstructorRollingPoints", "ConstructorRollingPointsRank", "Season", "Race"]
        )

    return _calculate_rolling_points(
        df_all_race_results,
        asset_col="Constructor",
        season_year=season_year,
        race_num=race_num,
        rolling_window=rolling_window,
        output_name_prefix="Constructor",
    )


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


def calculate_odds_rank(
    driver_odds: dict[str, float],
    drivers: Iterable[str],
    season_year: int,
    race_num: int,
) -> pd.DataFrame:
    """Normalise betting odds into a 0-1 indicator for each driver.

    ``driver_odds`` maps driver code to implied probability. Normalisation is
    min-max over ``log`` of that probability rather than over the probability
    itself: race-winner odds are so skewed that a linear scale collapses most of
    the field onto zero, whereas a log scale keeps the midfield separable while
    preserving the ordering.

    Drivers absent from ``driver_odds`` score 0.0, as does every driver when no
    odds are available for the race or when every price is identical.

    The result is one row per distinct driver, in first-seen order. Callers merge
    it on ``Driver``, so a repeated driver would fan that merge out into a
    cartesian product rather than annotating the rows already there.
    """
    drivers = list(dict.fromkeys(drivers))
    df_result = pd.DataFrame({"Driver": drivers})
    df_result["OddsImpliedProbability"] = (
        df_result["Driver"].map(driver_odds).fillna(0.0).astype(float)
    )
    df_result["OddsRank"] = 0.0

    priced = df_result["OddsImpliedProbability"] > 0.0
    if priced.any():
        log_probability = np.log(df_result.loc[priced, "OddsImpliedProbability"])
        span = log_probability.max() - log_probability.min()
        if span > 0:
            df_result.loc[priced, "OddsRank"] = (
                log_probability - log_probability.min()
            ) / span
        else:
            logger.info(
                "All betting odds identical for season %s race %s; odds indicator contributes nothing",
                season_year,
                race_num,
            )
    else:
        logger.info(
            "No betting odds available for season %s race %s; odds indicator contributes nothing",
            season_year,
            race_num,
        )

    df_result["Season"] = season_year
    df_result["Race"] = race_num
    return df_result


def aggregate_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Combine independent indicators into an aggregate ranking.

    Each indicator contributes its normalised 0-1 value scaled by its weight in
    ``METRIC_WEIGHTS``, defaulting to 1.0.
    """
    if df.empty:
        return df.copy()

    df = df.copy()
    # Include both PascalCase `...Rank` and snake_case `..._rank` suffixes
    rank_columns = [
        col for col in df.columns
        if col != "AggregateRank" and (
            col.endswith("Rank") or col.endswith("_rank")
        )
    ]
    df["AggregateRank"] = 0.0
    for col in rank_columns:
        df[col] = df[col].fillna(0.0)
        df["AggregateRank"] += METRIC_WEIGHTS.get(col, 1.0) * df[col]

    df = df.sort_values(by="AggregateRank", ascending=False).reset_index(drop=True)
    return df
