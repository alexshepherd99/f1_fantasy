"""Find which combination of FastF1 indicators best predicts a race.

See ``docs/indicator_analysis_v1/requirements.md`` for the rules this applies.
"""
import logging

import pandas as pd

logger = logging.getLogger(__name__)

NEVER_RACED_STATUSES = ("Did not start", "Withdrew")
FINISHED_STATUSES = ("Finished", "Lapped")

FORMAT_NORMAL = "normal"
FORMAT_SPRINT = "sprint"
FORMAT_SPRINT_FP1 = "sprint_fp1"

# Which session fills the early and late slots on each weekend format.
_FORMAT_SESSIONS = {
    FORMAT_NORMAL: ("FP2", "FP3"),
    FORMAT_SPRINT: ("FP1", "SQ"),
    FORMAT_SPRINT_FP1: ("FP1", None),
}

# Sorts a pit-lane start, which FastF1 records as grid 0, behind any real grid slot.
_PIT_LANE_GRID = 99.0


def _fantasy_points(archive: pd.DataFrame) -> pd.DataFrame:
    """Reduce the archive to one fantasy points row per season, race and driver.

    The archive identifies a driver as ``CODE@CONSTRUCTOR`` and leaves points null
    for a constructor the driver was not with at that race.
    """
    fantasy = archive.dropna(subset=["Points"])
    return pd.DataFrame({
        "Season": fantasy["Season"],
        "Race": fantasy["Race"],
        "Driver": fantasy["Driver"].str.split("@").str[0],
        "target_fantasy": fantasy["Points"],
    })


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


def _slot_values(frame: pd.DataFrame, slot_index: int, suffix: str) -> pd.Series:
    """Pick one session column per row: slot 0 is early, slot 1 is late."""
    values = pd.Series(float("nan"), index=frame.index, dtype=float)
    for race_format, sessions in _FORMAT_SESSIONS.items():
        session = sessions[slot_index]
        if session is not None:
            mask = frame["format"] == race_format
            values[mask] = pd.to_numeric(frame.loc[mask, f"{session}_{suffix}"])
    return values


def build_analysis_frame(metrics: pd.DataFrame, archive: pd.DataFrame) -> pd.DataFrame:
    """Join fantasy points onto the metrics and line indicators up into slots.

    Race 1 and drivers who never raced are dropped. Returns one row per driver per
    race, with both targets, the five indicator slots, the standalone lap count and
    stint screens, and the flags the sensitivities need. Higher is better for every
    target and signal.

    Raises:
        ValueError: A remaining driver has no fantasy points, or a race has no
            practice sessions.
    """
    kept = metrics[
        (metrics["Race"] > 1) & ~metrics["Status"].isin(NEVER_RACED_STATUSES)
    ].copy()
    frame = kept.merge(
        _fantasy_points(archive), on=["Season", "Race", "Driver"], how="left", validate="1:1"
    ).set_axis(kept.index)

    unmatched = frame[frame["target_fantasy"].isna()]
    if not unmatched.empty:
        names = ", ".join(
            f"{row.Season} race {row.Race} {row.Driver}" for row in unmatched.itertuples()
        )
        msg = f"No fantasy points for: {names}"
        logger.error(msg)
        raise ValueError(msg)

    frame["format"] = _weekend_formats(frame)
    frame["target_finish"] = -frame["Position"]
    frame["finished"] = frame["Status"].isin(FINISHED_STATUSES)
    frame["grid"] = -frame["GridPosition"].replace(0.0, _PIT_LANE_GRID)
    frame["driver_rolling"] = frame["RollingPointsRank"]
    frame["constructor_rolling"] = frame["ConstructorRollingPointsRank"]
    frame["odds"] = frame["OddsRank"]

    frame["early"] = _slot_values(frame, 0, "MinLapTime_rank")
    frame["late"] = _slot_values(frame, 1, "MinLapTime_rank")
    frame["early_laps"] = _slot_values(frame, 0, "TotalLapCount")
    frame["late_laps"] = _slot_values(frame, 1, "TotalLapCount")
    frame["early_stint"] = _slot_values(frame, 0, "MaxLapsInStint")
    frame["late_stint"] = _slot_values(frame, 1, "MaxLapsInStint")

    early_time = _slot_values(frame, 0, "MinLapTime")
    late_time = _slot_values(frame, 1, "MinLapTime")
    frame["no_time"] = early_time.isna() | (
        late_time.isna() & (frame["format"] != FORMAT_SPRINT_FP1)
    )
    return frame.reset_index(drop=True)
