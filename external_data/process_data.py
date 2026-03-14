import pandas as pd
import logging

from external_data.get_data import get_race_results, get_session_laps


def get_practice_performance(df_session_laps: pd.DataFrame) -> pd.DataFrame:
    # Check session constants do not vary
    if len(df_session_laps["Season"].unique()) != 1:
        raise ValueError(f"Season not unique in session laps")
    if len(df_session_laps["Race"].unique()) != 1:
        raise ValueError(f"Race not unique in session laps")
    if len(df_session_laps["SessionType"].unique()) != 1:
        raise ValueError(f"SessionType not unique in session laps")

    season_year = df_session_laps["Season"].max()
    race_num = df_session_laps["Race"].max()
    session_type = df_session_laps["SessionType"].max()
	
    # Create a copy to preserve original data
    df_session_laps = df_session_laps.copy()

    # Basic metrics per driver
    total_lap_count = df_session_laps.groupby("Driver").size().reset_index(name="TotalLapCount")
    min_lap_time = df_session_laps.groupby("Driver")["LapTime"].min().reset_index(name="MinLapTime")

    # Max laps in a single stint (no exclusions)
    max_laps_in_stint = (
        df_session_laps.groupby(["Driver", "Stint"]).size()
        .reset_index(name="LapCountInStint")
        .groupby("Driver")["LapCountInStint"]
        .max()
        .reset_index(name="MaxLapsInStint")
    )

    # Merge all metrics together
    df_result = total_lap_count.merge(min_lap_time, on="Driver")
    df_result = df_result.merge(max_laps_in_stint, on="Driver")

    # Add rank columns for each metric
    df_result["TotalLapCount_rank"] = df_result["TotalLapCount"].rank(method="min", ascending=False).astype("Int64")
    df_result["MinLapTime_rank"] = df_result["MinLapTime"].rank(method="min", ascending=True).astype("Int64")
    df_result["MaxLapsInStint_rank"] = df_result["MaxLapsInStint"].rank(method="min", ascending=False).astype("Int64")

    # Prefix all column names (except Driver) with session_type
    columns_to_prefix = [col for col in df_result.columns if col != "Driver"]
    rename_mapping = {col: f"{session_type}_{col}" for col in columns_to_prefix}
    df_result = df_result.rename(columns=rename_mapping)

    # Sort by Driver for consistency
    df_result = df_result.sort_values("Driver").reset_index(drop=True)

    # Add back race identifier columns
    df_result["Season"] = season_year
    df_result["Race"] = race_num

    return df_result


def get_rolling_window_races(race_num: int, rolling_window: int=3) -> list[int]:
    races = [r for r in range(race_num - rolling_window, race_num) if r > 0]
    logging.info(f"Rolling aggregate points for race {race_num} with window {rolling_window} returns races {races}")
    return races


def get_rolling_prev_points(df_all_race_results: pd.DataFrame, season_year: int, race_num: int, rolling_window: int=3) -> pd.DataFrame:
    races = get_rolling_window_races(race_num=race_num, rolling_window=rolling_window)

    df_all_race_results = df_all_race_results[df_all_race_results["Race"].isin(races)]
    df_all_race_results["Driver"] = df_all_race_results["Abbreviation"]
    df_all_race_results["RollingPoints"] = df_all_race_results["Points"]
    df_all_race_results["RollingPoints"] = pd.to_numeric(df_all_race_results["Points"], errors="coerce") 
    df_all_race_results = df_all_race_results[["Driver", "RollingPoints"]]
    df_all_race_results = df_all_race_results.groupby("Driver").sum().reset_index(drop=False)

    # Compute RollingPointsRank per race
    df_all_race_results["RollingPointsRank"] = (
        (
            df_all_race_results["RollingPoints"] - df_all_race_results["RollingPoints"].min()
        ) /
        (
            df_all_race_results["RollingPoints"].max() - df_all_race_results["RollingPoints"].min()
        )
    )

    # annotate with the race being processed
    df_all_race_results["Season"] = season_year
    df_all_race_results["Race"] = race_num

    return df_all_race_results


def get_practice_and_rolling_metrics(
    season_year: int, race_num: int, rolling_window: int = 3
) -> pd.DataFrame:
    """Return a unified dataframe containing

    * rolling points and rank for the previous ``rolling_window`` races
      ending with ``race_num``
    * practice performance metrics for FP2 and FP3 of the supplied race

    The workflow mirrors the description in the user request:

    1. call :func:`get_rolling_window_races` to identify prior races.
    2. fetch each race's results via :func:`get_race_results` and concat them.
    3. compute rolling points using :func:`get_rolling_prev_points`.
    4. load FP2 and FP3 laps for the current race and summarize them with
       :func:`get_practice_performance`.
    5. merge all partial dataframes together on ``Driver`` and annotate the
       final frame with the input season and race.

    The returned frame will include at least the columns
    ``Driver``, ``RollingPoints``, ``RollingPointsRank`` plus prefixed
    practice columns such as ``FP2_TotalLapCount`` and ``FP3_MinLapTime``.
    """

    # collect previous race results
    races = get_rolling_window_races(race_num=race_num, rolling_window=rolling_window)
    prev_results = pd.DataFrame(columns=["Race", "Abbreviation", "Points"])
    for r in races:
        df = get_race_results(season_year=season_year, race_num=r)
        prev_results = pd.concat([prev_results, df], ignore_index=True)

    rolling_df = get_rolling_prev_points(prev_results, season_year=season_year, race_num=race_num, rolling_window=rolling_window)

    # gather practice laps for the current race
    fp2_laps = get_session_laps(season_year=season_year, race_num=race_num, session_type="FP2")
    fp3_laps = get_session_laps(season_year=season_year, race_num=race_num, session_type="FP3")

    perf2 = get_practice_performance(fp2_laps) if not fp2_laps.empty else pd.DataFrame()
    perf3 = get_practice_performance(fp3_laps) if not fp3_laps.empty else pd.DataFrame()

    # merge everything
    merged = rolling_df
    if not perf2.empty:
        merged = merged.merge(perf2, on=["Driver", "Season", "Race"], how="outer")
    if not perf3.empty:
        merged = merged.merge(perf3, on=["Driver", "Season", "Race"], how="outer")

    # annotate with the race being processed
    merged["Season"] = season_year
    merged["Race"] = race_num

    merged["AggregageRank"] = 0
    if "RollingPointsRank" in merged.columns:
        merged["RollingPointsRank"] = merged["RollingPointsRank"].fillna(0)
        merged["AggregageRank"] = merged["AggregageRank"] + merged["RollingPointsRank"]
    if "FP2_MinLapTime_rank" in merged.columns:
        merged["FP2_MinLapTime_rank"] = merged["FP2_MinLapTime_rank"].fillna(0)
        merged["AggregageRank"] = merged["AggregageRank"] + merged["FP2_MinLapTime_rank"]
    if "FP3_MinLapTime_rank" in merged.columns:
        merged["FP3_MinLapTime_rank"] = merged["FP3_MinLapTime_rank"].fillna(0)
        merged["AggregageRank"] = merged["AggregageRank"] + merged["FP3_MinLapTime_rank"]
    merged = merged.sort_values(by="AggregageRank", ascending=True)

    return merged
