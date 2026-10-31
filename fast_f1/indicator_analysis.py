"""Find which combination of FastF1 indicators best predicts a race.

See ``docs/indicator_analysis_v1/requirements.md`` for the rules this applies.
"""
from dataclasses import dataclass
from itertools import combinations
import logging
from typing import Iterable, Literal

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from common import AssetType, setup_logging
from fast_f1.output import DEFAULT_HISTORICAL_OUTPUT, DEFAULT_OUTPUT_DIRECTORY
from import_data.import_history import load_all_archive_data
from import_data.odds import _FILE_BETTING_ODDS

logger = logging.getLogger(__name__)

RACE_KEYS = ["Season", "Race"]

BOOTSTRAP_RESAMPLES = 10_000
BOOTSTRAP_SEED = 20261031

TARGETS = ("target_fantasy", "target_finish")
HOLDOUT_SEASON = 2026

COMBINATION_SLOTS = ("driver_rolling", "constructor_rolling", "early", "late")
BASELINE_SLOTS = ("driver_rolling",)
AGGREGATE_SLOTS = ("driver_rolling", "early", "late")
LAP_SCREEN_SIGNALS = ("early_laps", "late_laps", "early_stint", "late_stint")
STANDALONE_SIGNALS = (*COMBINATION_SLOTS, "odds", *LAP_SCREEN_SIGNALS)

COMPARED_FORMATS = ("normal", "sprint")

ODDS_LEAK_SNAPSHOT = "Odds_Post_Quali"
ODDS_PRE_WEEKEND_SNAPSHOT = "Odds_Pre_Weekend"

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
    columns = list(slots)
    values = _within_race_ranks(frame, columns) if scale == "rank" else frame[columns]
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


def all_combinations(slots: tuple[str, ...] = COMBINATION_SLOTS) -> list[tuple[str, ...]]:
    """Every non-empty subset of the slots."""
    return [
        combo
        for size in range(1, len(slots) + 1)
        for combo in combinations(slots, size)
    ]


def rank_combinations(
    frame: pd.DataFrame,
    target: str,
    slots: tuple[str, ...] = COMBINATION_SLOTS,
) -> pd.DataFrame:
    """Score every equal-weight combination, best mean Spearman first.

    Exact ties go to the smaller combination, since it is the simpler answer.
    """
    rows = []
    for order, combo in enumerate(all_combinations(slots)):
        scores = race_scores(frame, combination_signal(frame, combo), target)
        rows.append({
            "combination": combo,
            "spearman": scores["spearman"].mean(),
            "top3": scores["top3"].mean(),
            "top5": scores["top5"].mean(),
            "_order": order,
        })
    ranked = pd.DataFrame(rows).sort_values(
        ["spearman", "_order"], ascending=[False, True]
    )
    return ranked.drop(columns="_order").reset_index(drop=True)


def leave_one_season_out_selection(
    frame: pd.DataFrame,
    target: str,
    slots: tuple[str, ...] = COMBINATION_SLOTS,
) -> tuple[pd.DataFrame, dict[int, tuple[str, ...]]]:
    """Score each season on the combination chosen from the other seasons.

    Returns the per-race scores and the combination chosen for each held-out season.
    """
    chosen: dict[int, tuple[str, ...]] = {}
    held_out_scores = []
    for season, held_out in frame.groupby("Season"):
        train = frame[frame["Season"] != season]
        chosen[season] = rank_combinations(train, target, slots)["combination"].iloc[0]
        held_out_scores.append(
            race_scores(held_out, combination_signal(held_out, chosen[season]), target)
        )
    return pd.concat(held_out_scores, ignore_index=True), chosen


def _within_race_ranks(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Each column as its within-race percentile rank."""
    return frame[columns].groupby([frame[key] for key in RACE_KEYS]).rank(pct=True)


def _centred(values: pd.DataFrame, frame: pd.DataFrame) -> pd.DataFrame:
    """Remove each race's mean, so a fit explains order within a race only."""
    keys = [frame[key] for key in RACE_KEYS]
    return values - values.groupby(keys).transform("mean")


def fit_weights(
    frame: pd.DataFrame,
    target: str,
    slots: tuple[str, ...] = COMBINATION_SLOTS,
) -> dict[str, float]:
    """Least squares weights of the slots on the target, on within-race ranks."""
    features = _centred(_within_race_ranks(frame, list(slots)), frame)
    outcome = _centred(_within_race_ranks(frame, [target]), frame)
    weights, *_ = np.linalg.lstsq(features.to_numpy(), outcome[target].to_numpy(), rcond=None)
    return dict(zip(slots, (float(weight) for weight in weights)))


def fitted_signal(frame: pd.DataFrame, weights: dict[str, float]) -> pd.Series:
    """Apply fitted weights to the slots' within-race ranks."""
    ranks = _within_race_ranks(frame, list(weights))
    return sum(ranks[slot] * weight for slot, weight in weights.items())


def leave_one_season_out_fitted(
    frame: pd.DataFrame,
    target: str,
    slots: tuple[str, ...] = COMBINATION_SLOTS,
) -> tuple[pd.DataFrame, dict[int, dict[str, float]]]:
    """Score each season on weights fitted to the other seasons.

    Returns the per-race scores and the weights used for each held-out season.
    """
    weights: dict[int, dict[str, float]] = {}
    held_out_scores = []
    for season, held_out in frame.groupby("Season"):
        weights[season] = fit_weights(frame[frame["Season"] != season], target, slots)
        held_out_scores.append(
            race_scores(held_out, fitted_signal(held_out, weights[season]), target)
        )
    return pd.concat(held_out_scores, ignore_index=True), weights


def odds_capture_points(odds: pd.DataFrame) -> dict[int, str]:
    """Work out which snapshot column each race's ``Odds`` were taken from.

    Raises:
        ValueError: No snapshot matches every driver in a race.
    """
    def _normalised(prices: pd.Series) -> pd.Series:
        return prices.astype(str).str.strip().str.replace(r"[-:]", "/", regex=True)

    captured: dict[int, str] = {}
    for race_num, race in odds.groupby("Race"):
        chosen = _normalised(race["Odds"])
        matches = [
            column for column in odds.columns
            if column.startswith("Odds_") and (_normalised(race[column]) == chosen).all()
        ]
        if not matches:
            msg = f"No odds snapshot matches every driver in race {race_num}"
            logger.error(msg)
            raise ValueError(msg)
        captured[race_num] = matches[0]
    return captured


def _scores_for(frame: pd.DataFrame, slots: tuple[str, ...], target: str) -> pd.DataFrame:
    return race_scores(frame, combination_signal(frame, slots), target)


def _comparison_row(
    labels: dict[str, str], comparison: str, scope: str, result: Comparison
) -> dict:
    return {
        **labels,
        "comparison": comparison,
        "scope": scope,
        "races": result.races,
        "mean_gain": result.mean_gain,
        "low": result.low,
        "high": result.high,
        **{f"gain_{season}": gain for season, gain in result.season_gains.items()},
        "wins": result.wins,
    }


def _usable_odds_races(frame: pd.DataFrame, capture_points: dict[int, str]) -> pd.DataFrame:
    """The held-out season's rows, less any race whose odds knew qualifying."""
    return frame[
        (frame["Season"] == HOLDOUT_SEASON)
        & (frame["Race"].map(capture_points) != ODDS_LEAK_SNAPSHOT)
    ]


def _standalone_table(
    frame: pd.DataFrame, target: str, capture_points: dict[int, str]
) -> pd.DataFrame:
    """Score every signal alone, per weekend format and per season."""
    rows = []
    for race_format, in_format in frame.groupby("format"):
        signals = [*STANDALONE_SIGNALS, "grid"]
        if race_format == FORMAT_SPRINT_FP1:
            signals = [signal for signal in signals if not signal.startswith("late")]
        for signal in signals:
            if signal == "odds":
                scoped = _usable_odds_races(in_format, capture_points)
                if scoped.empty:
                    continue
            else:
                scoped = in_format
            values = scoped[signal]
            if signal in LAP_SCREEN_SIGNALS:
                values = values.fillna(0.0)
            scores = race_scores(scoped, values, target)
            for season, group in [("all", scores), *scores.groupby("Season")]:
                rows.append({
                    "target": target,
                    "format": race_format,
                    "signal": signal,
                    "season": season,
                    "races": len(group),
                    "spearman": group["spearman"].mean(),
                    "top3": group["top3"].mean(),
                    "top5": group["top5"].mean(),
                })
    return pd.DataFrame(rows)


def _overlap_table(frame: pd.DataFrame) -> pd.DataFrame:
    """Mean within-race Spearman between each pair of slots, per weekend format."""
    rows = []
    for race_format in COMPARED_FORMATS:
        in_format = frame[frame["format"] == race_format]
        for first, second in combinations(COMBINATION_SLOTS, 2):
            scores = race_scores(in_format, in_format[first], second)
            rows.append({
                "format": race_format,
                "first": first,
                "second": second,
                "spearman": scores["spearman"].mean(),
            })
    return pd.DataFrame(rows)


def _format_comparisons(
    in_format: pd.DataFrame, target: str, race_format: str, winner: tuple[str, ...]
) -> tuple[list[dict], dict]:
    """The comparisons for one target on one weekend format, and the stability row."""
    labels = {"target": target, "format": race_format}
    rolling = _scores_for(in_format, BASELINE_SLOTS, target)
    best = _scores_for(in_format, winner, target)
    aggregate = _scores_for(in_format, AGGREGATE_SLOTS, target)
    grid = race_scores(in_format, in_format["grid"], target)
    chosen_scores, chosen = leave_one_season_out_selection(in_format, target)
    fitted_scores, weights = leave_one_season_out_fitted(in_format, target)

    def _held_out(scores: pd.DataFrame) -> pd.DataFrame:
        return scores[scores["Season"] == HOLDOUT_SEASON]

    rows = [
        _comparison_row(labels, "winner vs rolling", "all", compare_scores(best, rolling)),
        _comparison_row(
            labels, "winner vs rolling", str(HOLDOUT_SEASON),
            compare_scores(_held_out(best), _held_out(rolling)),
        ),
        _comparison_row(labels, "winner vs aggregate", "all", compare_scores(best, aggregate)),
        _comparison_row(
            labels, "winner vs aggregate", str(HOLDOUT_SEASON),
            compare_scores(_held_out(best), _held_out(aggregate)),
        ),
        _comparison_row(labels, "aggregate vs rolling", "all", compare_scores(aggregate, rolling)),
        _comparison_row(labels, "grid vs rolling", "all", compare_scores(grid, rolling)),
        _comparison_row(labels, "grid vs winner", "all", compare_scores(grid, best)),
        _comparison_row(
            labels, "unseen season choice vs rolling", "all", compare_scores(chosen_scores, rolling)
        ),
        _comparison_row(
            labels, "fitted vs unseen season choice", "all",
            compare_scores(fitted_scores, chosen_scores),
        ),
        _comparison_row(
            labels, "fitted vs rolling", "all", compare_scores(fitted_scores, rolling)
        ),
        _comparison_row(
            labels, "true ranks vs stored ranks: winner", "all",
            compare_scores(
                race_scores(in_format, combination_signal(in_format, winner, scale="rank"), target),
                best,
            ),
        ),
    ]
    for label, subset in (
        ("set a time only: winner vs rolling", in_format[~in_format["no_time"]]),
        ("finishers only: winner vs rolling", in_format[in_format["finished"]]),
    ):
        rows.append(_comparison_row(
            labels, label, "all",
            compare_scores(
                _scores_for(subset, winner, target), _scores_for(subset, BASELINE_SLOTS, target)
            ),
        ))
    stability = {
        **labels,
        "chosen_by_held_out_season": chosen,
        "fitted_weights_by_held_out_season": weights,
    }
    return rows, stability


def _odds_comparisons(
    frame: pd.DataFrame,
    target: str,
    winners: dict[str, tuple[str, ...]],
    capture_points: dict[int, str],
) -> list[dict]:
    """Compare odds with the best non-odds signal inside the held-out season."""
    races = _usable_odds_races(frame, capture_points)
    best_signal = pd.concat([
        combination_signal(races[races["format"] == race_format], winner)
        for race_format, winner in winners.items()
    ]).reindex(races.index)
    best = race_scores(races, best_signal, target)
    alone = race_scores(races, races["odds"], target)
    together = race_scores(races, best_signal + races["odds"], target)
    rolling = _scores_for(races, BASELINE_SLOTS, target)
    aggregate = _scores_for(races, (*AGGREGATE_SLOTS, "odds"), target)
    pairs = [
        ("odds vs best non-odds", alone, best),
        ("odds + best non-odds vs best non-odds", together, best),
        ("odds + best non-odds vs odds", together, alone),
        ("odds vs rolling", alone, rolling),
        ("aggregate with odds vs best non-odds", aggregate, best),
    ]
    pre_weekend = {
        race for race, column in capture_points.items() if column == ODDS_PRE_WEEKEND_SNAPSHOT
    }
    scopes = {
        str(HOLDOUT_SEASON): lambda scores: scores,
        "pre_weekend": lambda scores: scores[scores["Race"].isin(pre_weekend)],
        "during_weekend": lambda scores: scores[~scores["Race"].isin(pre_weekend)],
    }
    labels = {"target": target, "format": "odds"}
    return [
        _comparison_row(labels, name, scope, compare_scores(pick(first), pick(second)))
        for name, first, second in pairs
        for scope, pick in scopes.items()
    ]


def run_analysis(frame: pd.DataFrame, capture_points: dict[int, str]) -> dict[str, pd.DataFrame]:
    """Produce every table the effort reports, keyed by name.

    Winners are chosen on the seasons before ``HOLDOUT_SEASON``, separately for each
    target and each compared weekend format.
    """
    standalone, comparison_rows, stability_rows, winner_rows, combination_tables = [], [], [], [], []
    for target in TARGETS:
        standalone.append(_standalone_table(frame, target, capture_points))
        winners: dict[str, tuple[str, ...]] = {}
        for race_format in COMPARED_FORMATS:
            in_format = frame[frame["format"] == race_format]
            development = in_format[in_format["Season"] != HOLDOUT_SEASON]
            for split, subset in (
                ("development", development),
                (str(HOLDOUT_SEASON), in_format[in_format["Season"] == HOLDOUT_SEASON]),
                ("all", in_format),
            ):
                combination_tables.append(
                    rank_combinations(subset, target).assign(
                        target=target, format=race_format, split=split
                    )
                )
            winners[race_format] = rank_combinations(development, target)["combination"].iloc[0]
            winner_rows.append(
                {"target": target, "format": race_format, "combination": winners[race_format]}
            )
            rows, stability = _format_comparisons(
                in_format, target, race_format, winners[race_format]
            )
            comparison_rows.extend(rows)
            stability_rows.append(stability)
        comparison_rows.extend(_odds_comparisons(frame, target, winners, capture_points))
    return {
        "winners": pd.DataFrame(winner_rows),
        "standalone": pd.concat(standalone, ignore_index=True),
        "overlap": _overlap_table(frame),
        "combinations": pd.concat(combination_tables, ignore_index=True),
        "comparisons": pd.DataFrame(comparison_rows),
        "stability": pd.DataFrame(stability_rows),
    }


def main() -> None:
    """Run the analysis on the real data and write its tables to ``outputs/``."""
    setup_logging()
    try:
        metrics = pd.read_excel(DEFAULT_HISTORICAL_OUTPUT)
        odds = pd.read_excel(_FILE_BETTING_ODDS)
    except OSError:
        logger.exception("Could not read the analysis inputs")
        raise
    frame = build_analysis_frame(metrics, load_all_archive_data(AssetType.DRIVER))
    # Odds can be captured for a race before its results reach the metrics file.
    analysed_races = frame.loc[frame["Season"] == HOLDOUT_SEASON, "Race"]
    held_out_odds = odds[(odds["Season"] == HOLDOUT_SEASON) & odds["Race"].isin(analysed_races)]
    report = run_analysis(frame, odds_capture_points(held_out_odds))
    DEFAULT_OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    for name, table in report.items():
        path = DEFAULT_OUTPUT_DIRECTORY / f"indicator_analysis_v1_{name}.csv"
        table.to_csv(path, index=False)
        logger.info("Wrote %s", path)


if __name__ == "__main__":
    main()
