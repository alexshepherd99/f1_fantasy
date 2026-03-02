import pandas as pd


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
