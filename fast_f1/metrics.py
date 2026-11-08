from __future__ import annotations

import logging
from typing import Iterable

import numpy as np
import pandas as pd


logger = logging.getLogger(__name__)

# Relative contribution of each indicator to AggregateRank. Indicators not
# listed here carry a weight of 1.0.
#
# Constructor rolling points are still computed and reported, but contribute
# nothing to the aggregate: the indicator carries real signal on its own yet is
# almost entirely redundant with the driver indicators it sits alongside
# (correlating 0.80-0.98 per race with driver rolling points and 0.80-0.96 with
# odds over 2026). See docs/fastf1_v1/log.md for the measurements.
METRIC_WEIGHTS: dict[str, float] = {
    "ConstructorRollingPointsRank": 0.0,
}

FIRST_RACE = 1

FORMAT_NORMAL = "normal"
FORMAT_SPRINT = "sprint"
FORMAT_SPRINT_FP1 = "sprint_fp1"

# Which session fills the early and late slots on each weekend format.
_FORMAT_SESSIONS = {
    FORMAT_NORMAL: ("FP2", "FP3"),
    FORMAT_SPRINT: ("FP1", "SQ"),
    FORMAT_SPRINT_FP1: ("FP1", None),
}

# The slots added on each weekend format: the combination `indicator_analysis_v1` chose
# for fantasy points (see its log's *Conclusions*). A 2023 sprint weekend, which the
# analysis left out, takes the sprint rule, as that needs no practice session.
SIGNAL_SLOTS = {
    FORMAT_NORMAL: ("driver_rolling", "constructor_rolling", "late"),
    FORMAT_SPRINT: ("driver_rolling", "constructor_rolling"),
    FORMAT_SPRINT_FP1: ("driver_rolling", "constructor_rolling"),
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


def link_renamed_constructors(
    previous_results: pd.DataFrame,
    current_results: pd.DataFrame,
) -> pd.DataFrame:
    """Relabel prior races' constructor names to the names the current race uses.

    FastF1 can give one team two names, as in 2024 race 24, where its fallback
    source named four teams differently from the races before. A prior name
    that is also in the current race keeps its own points. A prior name missing
    from the current race is relabelled to the one current team its drivers
    now race for. That covers a name changing back and forth, while leaving a
    driver swap between two teams that both race on untouched. A missing name
    whose drivers lead to no team or to several is left as it is and logged.

    Both frames need ``Abbreviation`` and ``Constructor``. Returns a copy of
    ``previous_results``.
    """
    linked = previous_results.copy()
    if linked.empty:
        return linked

    current_names = set(current_results["Constructor"].dropna())
    current_team_by_driver = (
        current_results.dropna(subset=["Abbreviation", "Constructor"])
        .drop_duplicates(subset=["Abbreviation"])
        .set_index("Abbreviation")["Constructor"]
    )

    relabel: dict[str, str] = {}
    for old_name in sorted(set(linked["Constructor"].dropna()) - current_names):
        drivers = linked.loc[linked["Constructor"] == old_name, "Abbreviation"].unique()
        new_names = set(current_team_by_driver.reindex(drivers).dropna())
        if len(new_names) == 1:
            relabel[old_name] = new_names.pop()
        else:
            logger.warning(
                "Constructor %r is missing from the current race and its drivers %s now race for %s; "
                "its rolling points are not carried over",
                old_name,
                sorted(drivers),
                sorted(new_names) or "no team",
            )

    linked["Constructor"] = linked["Constructor"].replace(relabel)
    return linked


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


def _weekend_formats(metrics: pd.DataFrame) -> pd.Series:
    """Classify each row's weekend from the sessions any driver in the race has."""
    formats = pd.Series(index=metrics.index, dtype=object)
    for (season, race_num), race in metrics.groupby(["Season", "Race"]):
        if race["FP2_MinLapTime_rank"].notna().any():
            formats[race.index] = FORMAT_NORMAL
        elif race["SQ_MinLapTime_rank"].notna().any():
            formats[race.index] = FORMAT_SPRINT
        elif race["FP1_MinLapTime_rank"].notna().any():
            formats[race.index] = FORMAT_SPRINT_FP1
        else:
            msg = f"No practice sessions found for {season} race {race_num}"
            logger.error(msg)
            raise ValueError(msg)
    return formats


def slot_values(frame: pd.DataFrame, slot_index: int, suffix: str) -> pd.Series:
    """Pick one session column per row: slot 0 is early, slot 1 is late.

    Args:
        frame: Rows holding a ``format`` column, as ``add_signal_inputs`` adds it.
        slot_index: 0 for the early session, 1 for the late one.
        suffix: The session column's name after ``<session>_``, such as ``MinLapTime_rank``.

    Returns:
        One value per row, missing where the format has no session in that slot.
    """
    values = pd.Series(float("nan"), index=frame.index, dtype=float)
    for race_format, sessions in _FORMAT_SESSIONS.items():
        session = sessions[slot_index]
        if session is not None:
            mask = frame["format"] == race_format
            values[mask] = pd.to_numeric(frame.loc[mask, f"{session}_{suffix}"])
    return values


def add_signal_inputs(metrics: pd.DataFrame) -> pd.DataFrame:
    """Add each row's weekend format and the indicator slots, from metrics rows alone.

    Reads no race results, so it suits a race not yet run. Returns a copy holding
    ``format``, the slots ``driver_rolling``, ``constructor_rolling``, ``early`` and
    ``late``, and ``odds``. Higher is better for each.

    Raises:
        ValueError: A race has no practice sessions.
    """
    frame = metrics.copy()
    frame["format"] = _weekend_formats(frame)
    frame["driver_rolling"] = frame["RollingPointsRank"]
    frame["constructor_rolling"] = frame["ConstructorRollingPointsRank"]
    frame["odds"] = frame["OddsRank"]
    frame["early"] = slot_values(frame, 0, "MinLapTime_rank")
    frame["late"] = slot_values(frame, 1, "MinLapTime_rank")
    return frame


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
