"""Find which combination of FastF1 indicators best predicts a race.

See ``docs/indicator_analysis_v1/requirements.md`` for the rules this applies.
"""
from dataclasses import dataclass
import logging
from typing import Iterable, Literal

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

logger = logging.getLogger(__name__)

RACE_KEYS = ["Season", "Race"]

BOOTSTRAP_RESAMPLES = 10_000
BOOTSTRAP_SEED = 20261031

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


def combination_signal(
    frame: pd.DataFrame,
    slots: tuple[str, ...],
    scale: Literal["stored", "rank"] = "stored",
) -> pd.Series:
    """Add the given slots with equal weight.

    ``scale="stored"`` uses the values as held. ``scale="rank"`` first converts each
    slot to its within-race percentile rank. A missing slot value makes the sum
    missing rather than counting as zero.
    """
    values = frame[list(slots)]
    if scale == "rank":
        values = values.groupby([frame[key] for key in RACE_KEYS]).rank(pct=True)
    return values.sum(axis=1, skipna=False)


def _top_k_overlap(race: pd.DataFrame, k: int) -> float:
    """Share of the actual top k that the signal also placed in its top k."""
    def _top(column: str) -> set[str]:
        # Ties resolve on driver code, so that a score is repeatable.
        ordered = race.sort_values([column, "Driver"], ascending=[False, True])
        return set(ordered["Driver"].head(k))

    return len(_top("_signal") & _top("_target")) / k


def race_scores(frame: pd.DataFrame, signal: pd.Series, target: str) -> pd.DataFrame:
    """Score a signal against a target, one row per race.

    Returns ``Season``, ``Race``, ``spearman``, ``top3`` and ``top5``.

    Raises:
        ValueError: A race's signal has missing values or does not vary, either of
            which would otherwise drop out of an average unnoticed.
    """
    working = frame[[*RACE_KEYS, "Driver"]].assign(_signal=signal, _target=frame[target])
    rows = []
    for (season, race_num), race in working.groupby(RACE_KEYS):
        if race["_signal"].isna().any() or race["_signal"].nunique() < 2:
            msg = f"Signal is missing or constant in {season} race {race_num}"
            logger.error(msg)
            raise ValueError(msg)
        rows.append({
            "Season": season,
            "Race": race_num,
            "spearman": spearmanr(race["_signal"], race["_target"]).statistic,
            "top3": _top_k_overlap(race, 3),
            "top5": _top_k_overlap(race, 5),
        })
    return pd.DataFrame(rows)


def bootstrap_interval(
    values: Iterable[float],
    resamples: int = BOOTSTRAP_RESAMPLES,
    seed: int = BOOTSTRAP_SEED,
) -> tuple[float, float]:
    """95% percentile bootstrap interval on the mean of ``values``."""
    data = np.asarray(list(values), dtype=float)
    picks = np.random.default_rng(seed).integers(0, len(data), (resamples, len(data)))
    means = data[picks].mean(axis=1)
    low, high = np.percentile(means, [2.5, 97.5])
    return float(low), float(high)


@dataclass(frozen=True)
class Comparison:
    """The per-race Spearman gain of one signal over another, and its verdict."""

    races: int
    mean_gain: float
    low: float
    high: float
    season_gains: dict[int, float]
    wins: bool


def compare_scores(candidate: pd.DataFrame, baseline: pd.DataFrame) -> Comparison:
    """Apply the bar for a win to two sets of per-race scores.

    A win needs the 95% interval on the mean gain to exclude zero on the positive
    side, and the mean gain to be positive in every season.

    Raises:
        ValueError: The two sets do not cover the same races.
    """
    paired = candidate[[*RACE_KEYS, "spearman"]].merge(
        baseline[[*RACE_KEYS, "spearman"]],
        on=RACE_KEYS,
        how="outer",
        suffixes=("_candidate", "_baseline"),
    )
    if paired.isna().any().any():
        msg = "Comparison scores must cover the same races"
        logger.error(msg)
        raise ValueError(msg)

    gains = paired["spearman_candidate"] - paired["spearman_baseline"]
    low, high = bootstrap_interval(gains)
    season_gains = gains.groupby(paired["Season"]).mean().to_dict()
    return Comparison(
        races=len(gains),
        mean_gain=float(gains.mean()),
        low=low,
        high=high,
        season_gains=season_gains,
        wins=low > 0 and all(gain > 0 for gain in season_gains.values()),
    )
