from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable

import pandas as pd

from fast_f1.api import (
    get_event_for_race,
    get_race_results,
    get_session_laps,
    select_practice_sessions_from_event,
)
from fast_f1.metrics import (
    aggregate_metrics,
    calculate_constructor_rolling_points,
    calculate_practice_performance,
    calculate_rolling_points,
)

logger = logging.getLogger(__name__)

DEFAULT_HISTORICAL_OUTPUT = Path("data/fastf1_practice_rolling_metrics.xlsx")
DEFAULT_OUTPUT_DIRECTORY = Path("outputs")
_DEFAULT_SHEET_NAME = "PracticeRollingMetrics"


def _ensure_parent_directory(output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)


def build_race_metrics(
    season_year: int,
    race_num: int,
    rolling_window: int = 3,
) -> pd.DataFrame:
    """Build the full metric set for a single race using FastF1 inputs."""
    event = get_event_for_race(season_year, race_num)
    practice_session_codes = select_practice_sessions_from_event(event)

    practice_dfs: list[pd.DataFrame] = []
    for session_code in practice_session_codes:
        session_laps = get_session_laps(season_year, race_num, session_code)
        if session_laps.empty:
            msg = (
                f"Required practice session data missing for season {season_year} "
                f"race {race_num}: {session_code}"
            )
            logger.error(msg)
            raise RuntimeError(msg)
        practice_dfs.append(calculate_practice_performance(session_laps))

    previous_race_numbers = [r for r in range(race_num - rolling_window, race_num) if r > 0]
    if not previous_race_numbers:
        msg = f"No prior races available to compute rolling points for season {season_year} race {race_num}"
        logger.error(msg)
        raise RuntimeError(msg)

    previous_results = pd.DataFrame()
    for prior_race in previous_race_numbers:
        prior_results = get_race_results(season_year, prior_race)
        previous_results = pd.concat([previous_results, prior_results], ignore_index=True, sort=False)

    if previous_results.empty:
        msg = (
            f"Failed to collect prior race results for season {season_year} "
            f"race {race_num}. Cannot compute rolling points."
        )
        logger.error(msg)
        raise RuntimeError(msg)

    if "Constructor" not in previous_results.columns:
        msg = "Constructor names are required in prior results to compute constructor rolling points."
        logger.error(msg)
        raise RuntimeError(msg)

    driver_rolling = calculate_rolling_points(
        previous_results,
        season_year=season_year,
        race_num=race_num,
        rolling_window=rolling_window,
    )
    constructor_rolling = calculate_constructor_rolling_points(
        previous_results,
        season_year=season_year,
        race_num=race_num,
        rolling_window=rolling_window,
    )

    current_results = get_race_results(season_year, race_num)

    # If official race results are not yet available, derive a minimal
    # current_results dataframe from available practice session data or
    # the rolling results. This allows metrics to be computed before the
    # Race session is published.
    if current_results.empty:
        driver_list: list[str] = []
        for df in practice_dfs:
            if "Driver" in df.columns:
                driver_list.extend(df["Driver"].tolist())

        if not driver_list and not driver_rolling.empty:
            driver_list = driver_rolling["Driver"].tolist()

        driver_list = sorted(set(driver_list))
        if not driver_list:
            msg = (
                f"Current race results unavailable and no drivers could be derived for season {season_year} "
                f"race {race_num}."
            )
            logger.error(msg)
            raise RuntimeError(msg)

        current_results = pd.DataFrame({"Abbreviation": driver_list})
        current_results["Season"] = season_year
        current_results["Race"] = race_num

        # Attempt to infer constructors from previous results if present.
        if "Abbreviation" in previous_results.columns and "Constructor" in previous_results.columns:
            mapping = (
                previous_results.dropna(subset=["Abbreviation", "Constructor"]).
                drop_duplicates(subset=["Abbreviation"]).
                set_index("Abbreviation")["Constructor"]
            )
            current_results["Constructor"] = current_results["Abbreviation"].map(mapping)
        else:
            current_results["Constructor"] = None

    if "Constructor" not in current_results.columns:
        current_results["Constructor"] = current_results.get("TeamName")

    current_results = current_results.copy()
    current_results["Driver"] = current_results["Abbreviation"]

    merged = current_results.merge(
        driver_rolling,
        on=["Driver", "Season", "Race"],
        how="left",
    )
    merged = merged.merge(
        constructor_rolling,
        on=["Constructor", "Season", "Race"],
        how="left",
    )

    for required in [
        "RollingPoints",
        "RollingPointsRank",
        "ConstructorRollingPoints",
        "ConstructorRollingPointsRank",
    ]:
        if required not in merged.columns:
            merged[required] = 0.0

    for perf_df in practice_dfs:
        merged = merged.merge(
            perf_df,
            on=["Driver", "Season", "Race"],
            how="left",
        )

    merged = aggregate_metrics(merged)
    merged = merged.sort_values(by="AggregateRank", ascending=False).reset_index(drop=True)
    return merged


def save_metrics(dataframe: pd.DataFrame, output_path: Path | str) -> None:
    path = Path(output_path)
    _ensure_parent_directory(path)
    dataframe = dataframe.sort_values(
        by=["Season", "Race", "AggregateRank"],
        ascending=[True, True, False],
    ).reset_index(drop=True)

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        dataframe.to_excel(writer, sheet_name=_DEFAULT_SHEET_NAME, index=False)


def load_existing_metrics(output_path: Path | str) -> pd.DataFrame:
    path = Path(output_path)
    if not path.exists():
        return pd.DataFrame()

    try:
        return pd.read_excel(path, sheet_name=_DEFAULT_SHEET_NAME, engine="openpyxl")
    except ValueError:
        return pd.read_excel(path, engine="openpyxl")


def generate_single_race_prediction(
    season_year: int,
    race_num: int,
    output_path: Path | str | None = None,
) -> tuple[Path, pd.DataFrame]:
    dataframe = build_race_metrics(season_year, race_num)
    path = (
        Path(output_path)
        if output_path is not None
        else DEFAULT_OUTPUT_DIRECTORY / f"fastf1_race_{season_year}_{race_num}.xlsx"
    )
    _ensure_parent_directory(path)
    save_metrics(dataframe, path)
    logger.info("Saved single-race metrics to %s", path)
    return path, dataframe


def generate_historical_metrics(
    season_years: Iterable[int],
    race_numbers: Iterable[int],
    output_path: Path | str = DEFAULT_HISTORICAL_OUTPUT,
) -> pd.DataFrame:
    path = Path(output_path)
    existing_metrics = load_existing_metrics(path)
    existing_keys = set()
    if not existing_metrics.empty:
        existing_keys = set(zip(existing_metrics["Season"], existing_metrics["Race"]))

    updated = existing_metrics.copy()

    for season_year in season_years:
        for race_num in race_numbers:
            if (season_year, race_num) in existing_keys:
                logger.info("Skipping existing metrics for season %s race %s", season_year, race_num)
                continue

            logger.info("Computing metrics for season %s race %s", season_year, race_num)
            try:
                race_metrics = build_race_metrics(season_year, race_num)
            except RuntimeError as exc:
                logger.warning(
                    "Skipping season %s race %s due to missing data: %s",
                    season_year,
                    race_num,
                    exc,
                )
                continue

            updated = pd.concat([updated, race_metrics], ignore_index=True, sort=False)
            save_metrics(updated, path)
            existing_keys.add((season_year, race_num))
            logger.info("Saved updated metrics to %s", path)

    return updated
