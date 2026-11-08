from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable

import pandas as pd

from fast_f1.api import (
    get_event_for_race,
    get_race_numbers_for_season,
    get_race_results,
    get_session_drivers,
    get_session_laps,
    select_practice_sessions_from_event,
)
from fast_f1.metrics import (
    aggregate_metrics,
    calculate_constructor_rolling_points,
    calculate_odds_rank,
    calculate_practice_performance,
    calculate_rolling_points,
    get_rolling_window_races,
    link_renamed_constructors,
)

from common import AssetType
from import_data.odds import _FILE_BETTING_ODDS, load_odds

logger = logging.getLogger(__name__)

# Read when `build_race_metrics` runs rather than bound as its default, so tests
# can point every call at a fixture file.
ODDS_FILE: Path | str = _FILE_BETTING_ODDS
DEFAULT_HISTORICAL_OUTPUT = Path("data/fastf1_practice_rolling_metrics.csv")
DEFAULT_OUTPUT_DIRECTORY = Path("outputs")


class HistoricalRunIncomplete(Exception):
    """Raised at the end of a historical run in which some races failed.

    Every race that succeeded has already been saved; ``failed_races`` holds
    the (season, race) pairs that did not, which the next run retries.
    """

    def __init__(self, failed_races: list[tuple[int, int]]):
        self.failed_races = failed_races
        races = ", ".join(f"season {season} race {race}" for season, race in failed_races)
        super().__init__(f"Historical run incomplete; failed to compute {races}")


def _ensure_parent_directory(output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)


def _load_driver_odds(season_year: int, race_num: int, odds_file: Path | str) -> dict[str, float]:
    """Implied probabilities keyed by driver code, empty when unavailable.

    Odds cover only part of the archive, so a race without them is normal
    rather than exceptional. Any failure to read them degrades the odds
    indicator to zero for the whole race instead of aborting a historical run
    that is otherwise computable.
    """
    try:
        return load_odds(
            AssetType.DRIVER,
            season_year,
            race_num,
            fn=odds_file,
            qualify_driver_with_constructor=False,
        )
    except Exception as exc:
        # Deliberately broad: a damaged file fails in types that share no useful
        # base class - a missing file gives OSError, a bad price ValueError and a
        # lost column KeyError, which derives from neither. Odds are an optional
        # signal, so no failure to read them justifies losing an otherwise
        # computable race.
        logger.warning(
            "Could not load betting odds for season %s race %s (%s: %s); "
            "scoring the odds indicator as zero for every driver",
            season_year,
            race_num,
            type(exc).__name__,
            exc,
        )
        return {}


def _practice_teams(season_year: int, race_num: int, session_codes: Iterable[str]) -> pd.Series:
    """Each driver's team for the weekend, keyed by driver, from the practice driver lists.

    Before a race has results these are the only source of a driver's current
    team. Where sessions disagree, the latest one listing the driver wins.
    """
    session_drivers = [get_session_drivers(season_year, race_num, code) for code in session_codes]
    teams = pd.concat(session_drivers, ignore_index=True).dropna(subset=["Abbreviation", "TeamName"])
    return teams.drop_duplicates(subset=["Abbreviation"], keep="last").set_index("Abbreviation")["TeamName"]


def build_race_metrics(
    season_year: int,
    race_num: int,
    rolling_window: int = 3,
    odds_file: Path | str | None = None,
) -> pd.DataFrame:
    """Build the full metric set for a single race using FastF1 inputs.

    ``odds_file`` is the betting odds file to read, ``ODDS_FILE`` when omitted.
    """
    if odds_file is None:
        odds_file = ODDS_FILE
    event = get_event_for_race(season_year, race_num)
    practice_session_codes = select_practice_sessions_from_event(event)

    practice_dfs: list[pd.DataFrame] = []
    for session_code in practice_session_codes:
        session_laps = get_session_laps(season_year, race_num, session_code)
        # A session stopped before anyone set a time still returns lap rows, so
        # emptiness alone does not cover it - and every rank here is derived
        # from a lap time.
        if session_laps.empty or not session_laps["LapTime"].notna().any():
            msg = (
                f"Required practice session data missing for season {season_year} "
                f"race {race_num}: {session_code}"
            )
            logger.error(msg)
            raise RuntimeError(msg)
        practice_dfs.append(calculate_practice_performance(session_laps))

    previous_race_numbers = get_rolling_window_races(race_num, rolling_window)
    previous_results = pd.DataFrame()
    if not previous_race_numbers:
        if race_num == 1:
            msg = (
                f"No prior races available to compute rolling points for season {season_year} "
                f"race {race_num}. Assuming zero historical points for drivers and constructors."
            )
            logger.info(msg)
        else:
            msg = f"No prior races available to compute rolling points for season {season_year} race {race_num}"
            logger.error(msg)
            raise RuntimeError(msg)
    else:
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

    if not previous_results.empty and "Constructor" not in previous_results.columns:
        msg = "Constructor names are required in prior results to compute constructor rolling points."
        logger.error(msg)
        raise RuntimeError(msg)

    driver_rolling = calculate_rolling_points(
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

        team_by_driver = _practice_teams(season_year, race_num, practice_session_codes)
        unplaced = sorted(set(driver_list) - set(team_by_driver.index))
        if unplaced:
            msg = (
                f"No practice session names a team for {', '.join(unplaced)} in season {season_year} "
                f"race {race_num}, so their constructor points cannot be found."
            )
            logger.error(msg)
            raise RuntimeError(msg)
        current_results["Constructor"] = current_results["Abbreviation"].map(team_by_driver)

    if "Constructor" not in current_results.columns:
        current_results["Constructor"] = current_results.get("TeamName")

    current_results = current_results.copy()
    current_results["Driver"] = current_results["Abbreviation"]

    # Linked against the current race's names, so a team FastF1 has renamed
    # still finds its points in the merge below.
    constructor_rolling = calculate_constructor_rolling_points(
        link_renamed_constructors(previous_results, current_results),
        season_year=season_year,
        race_num=race_num,
        rolling_window=rolling_window,
    )

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

    odds_rank = calculate_odds_rank(
        _load_driver_odds(season_year, race_num, odds_file),
        drivers=merged["Driver"],
        season_year=season_year,
        race_num=race_num,
    )
    merged = merged.merge(odds_rank, on=["Driver", "Season", "Race"], how="left")

    # aggregate_metrics returns the frame sorted by AggregateRank descending,
    # which is also what `method="first"` needs to break ties in that order.
    merged = aggregate_metrics(merged)
    merged["RankPosition"] = merged["AggregateRank"].rank(method="first", ascending=False).astype(int)
    return merged


def _durations_in_days(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Turn FastF1's lap-time durations into days, the unit the stored rows hold.

    The metrics file was an Excel workbook until 2026-11, and Excel stores a
    duration in days. A historical run appends new races' durations to stored
    rows already in days, so a column can hold both.
    """
    day = pd.Timedelta(days=1)

    def in_days(value: object) -> object:
        if isinstance(value, pd.Timedelta):
            return value / day
        return float("nan") if value is pd.NaT else value

    converted = dataframe.copy()
    for column in converted.columns:
        values = converted[column]
        if pd.api.types.is_timedelta64_dtype(values) or values.map(lambda value: isinstance(value, pd.Timedelta)).any():
            converted[column] = values.map(in_days).astype(float)
    return converted


def save_metrics(dataframe: pd.DataFrame, output_path: Path | str) -> None:
    path = Path(output_path)
    _ensure_parent_directory(path)
    dataframe = _durations_in_days(dataframe).sort_values(
        by=["Season", "Race", "AggregateRank"],
        ascending=[True, True, False],
    ).reset_index(drop=True)

    dataframe.to_csv(path, index=False)


def load_existing_metrics(output_path: Path | str) -> pd.DataFrame:
    path = Path(output_path)
    if not path.exists():
        return pd.DataFrame()

    # pandas' default parser can read a float back one step out in its last
    # digit; round_trip reads back exactly what to_csv wrote.
    return pd.read_csv(path, float_precision="round_trip")


def generate_single_race_prediction(
    season_year: int,
    race_num: int,
    output_path: Path | str | None = None,
) -> tuple[Path, pd.DataFrame]:
    dataframe = build_race_metrics(season_year, race_num)
    path = (
        Path(output_path)
        if output_path is not None
        else DEFAULT_OUTPUT_DIRECTORY / f"fastf1_race_{season_year}_{race_num}.csv"
    )
    _ensure_parent_directory(path)
    save_metrics(dataframe, path)
    logger.info("Saved single-race metrics to %s", path)
    return path, dataframe


def generate_historical_metrics(
    season_years: Iterable[int],
    output_path: Path | str = DEFAULT_HISTORICAL_OUTPUT,
) -> pd.DataFrame:
    """Build metrics for every scheduled race of each season, resuming where left off.

    Each season is walked over the rounds it actually scheduled, so seasons of
    differing length are all covered in full.

    A race whose sessions do not exist is skipped with a warning. A race that
    fails for any other reason - a refused download, a bug - is logged as an
    error and stepped over so it cannot block the races after it; once every
    race has been tried, ``HistoricalRunIncomplete`` is raised naming them.
    """
    path = Path(output_path)
    existing_metrics = load_existing_metrics(path)
    existing_keys = set()
    if not existing_metrics.empty:
        existing_keys = set(zip(existing_metrics["Season"], existing_metrics["Race"]))

    updated = existing_metrics.copy()
    failed_races: list[tuple[int, int]] = []

    for season_year in season_years:
        for race_num in get_race_numbers_for_season(season_year):
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
            except Exception:
                # Deliberately broad: classifying every way a fetch can fail is
                # not possible, and nothing is saved for this race, so the next
                # run retries it. The run still ends in HistoricalRunIncomplete.
                logger.exception("Failed to compute metrics for season %s race %s", season_year, race_num)
                failed_races.append((season_year, race_num))
                continue

            updated = pd.concat([updated, race_metrics], ignore_index=True, sort=False)
            save_metrics(updated, path)
            existing_keys.add((season_year, race_num))
            logger.info("Saved updated metrics to %s", path)

    if failed_races:
        raise HistoricalRunIncomplete(failed_races)

    return updated
