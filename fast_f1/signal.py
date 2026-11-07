"""fastf1_v2's signal: each driver's position and each constructor's place for one race.

The signal is the combination `indicator_analysis_v1` chose for fantasy points (see its
log's *Conclusions*), built from metrics rows alone so that a race not yet run can be
ranked. See ``docs/fastf1_v2/plan.md``, step 4.
"""
from __future__ import annotations

import functools
import logging
from pathlib import Path
from typing import Callable

import pandas as pd
from scipy.optimize import isotonic_regression

from common import AssetType
from fast_f1.indicator_analysis import (
    FIRST_RACE,
    FORMAT_NORMAL,
    FORMAT_SPRINT,
    FORMAT_SPRINT_FP1,
    add_signal_inputs,
    combination_signal,
)
from fast_f1.metrics import get_rolling_window_races
from fast_f1.output import DEFAULT_HISTORICAL_OUTPUT, load_existing_metrics
from import_data.derivations import get_race_driver_constructor_pairs
from import_data.import_history import _FILE_ARCHIVE_INPUTS, load_all_archive_data

logger = logging.getLogger(__name__)

# The seasons any table is built from. 2026 is left out, as it is the season the
# strategy is judged on (see docs/fastf1_v2/requirements.md, question 7).
TABLE_SEASONS = (2023, 2024, 2025)

# How many previous rounds a negative counts for, in the chance of going negative.
RECENT_RACES = 3

# The slots added on each weekend format. A 2023 sprint weekend, which the analysis
# left out, takes the sprint rule, as that needs no practice session.
SIGNAL_SLOTS = {
    FORMAT_NORMAL: ("driver_rolling", "constructor_rolling", "late"),
    FORMAT_SPRINT: ("driver_rolling", "constructor_rolling"),
    FORMAT_SPRINT_FP1: ("driver_rolling", "constructor_rolling"),
}

# Rounding before sorting lets a sum that differs only by floating point noise count as
# a tie, so the tie breaks on the identifier rather than the order slots were added in.
_SIGNAL_DECIMALS = 9


def driver_positions(
    metrics: pd.DataFrame, pairs: pd.DataFrame, season: int, race: int
) -> dict[str, int]:
    """Each driver's signal position in one race, 1 being best.

    Args:
        metrics: Rows in the shape of ``data/fastf1_practice_rolling_metrics.xlsx``,
            keyed on the bare driver code.
        pairs: The archive's per-race driver/constructor pairs, as the third frame
            from ``helpers.load_with_derivations``.
        season: The season to rank.
        race: The race to rank.

    Returns:
        Positions keyed by the ``DRIVERCODE@CONSTRUCTOR`` identifier. Ties break on
        that identifier. Empty when the metrics hold no rows for the race. A fantasy
        driver with no metrics row has no position.

    Raises:
        ValueError: A driver in the race matches no fantasy pair or more than one, or
            lacks a value the signal adds up.
    """
    return _ranked(_signal_rows(metrics, pairs, season, race), "signal", "Asset")


def driver_values(
    metrics: pd.DataFrame, pairs: pd.DataFrame, season: int, race: int
) -> dict[str, float]:
    """Each driver's signal value in one race, on a championship points per race scale.

    The race's best signal gets the field's highest recent championship points per race,
    its worst gets the lowest, and every other driver falls in proportion between. Per
    race is ``RollingPoints`` divided by the races its window covers. A driver with no
    ``RollingPoints`` takes no part in setting that range. See
    ``docs/fastf1_v2/requirements.md``, question 1. Arguments are as for
    ``driver_positions``.

    Returns:
        Values keyed by the ``DRIVERCODE@CONSTRUCTOR`` identifier. Empty when the
        metrics hold no rows for the race. A fantasy driver with no metrics row has no
        value.

    Raises:
        ValueError: As for ``driver_positions``; every driver's signal is equal, which
            leaves nothing to stretch; or the race is the season's first, which has no
            recent championship points to stretch onto.
    """
    if race == FIRST_RACE:
        msg = f"No recent championship points for {season} race {race} to stretch onto"
        logger.error(msg)
        raise ValueError(msg)

    rows = _signal_rows(metrics, pairs, season, race)
    spread = rows["signal"].max() - rows["signal"].min()
    if spread == 0:
        msg = f"Every signal equal for {season} race {race}, so none can be stretched"
        logger.error(msg)
        raise ValueError(msg)

    per_race = rows["RollingPoints"] / len(get_rolling_window_races(race))
    low, high = per_race.min(), per_race.max()
    share = (rows["signal"] - rows["signal"].min()) / spread
    return dict(zip(rows["Asset"], (low + share * (high - low)).astype(float)))


def constructor_places(
    metrics: pd.DataFrame, pairs: pd.DataFrame, season: int, race: int
) -> dict[str, int]:
    """Each constructor's place in one race on its rolling points, 1 being best.

    A constructor is reached through its drivers and the archive's per-race pairs, so
    FastF1's team name plays no part. Arguments are as for ``driver_positions``.

    Returns:
        Places keyed by the archive's constructor code. Ties break on that code.

    Raises:
        ValueError: As for ``driver_positions``, or a constructor's drivers disagree on
            its rolling points.
    """
    rows = _race_rows(metrics, pairs, season, race)
    values_per_constructor = rows.groupby("AssetConstructor")["ConstructorRollingPoints"].nunique(
        dropna=False
    )
    _raise_for(
        values_per_constructor[values_per_constructor > 1].index.to_series(),
        "Drivers disagree on constructor rolling points",
        season,
        race,
    )
    constructors = rows.drop_duplicates("AssetConstructor")
    return _ranked(constructors, "ConstructorRollingPoints", "AssetConstructor")


@functools.cache
def load_signal_tables(
    fn_metrics: Path | str = DEFAULT_HISTORICAL_OUTPUT, fn_archive: str = _FILE_ARCHIVE_INPUTS
) -> SignalTables:
    """The ``SignalTables`` for a metrics file and the archive, read once per process.

    A strategy is built per team per race, so its tables must not be rebuilt each time.
    A file changed while the process runs is not read again.

    Raises:
        FileNotFoundError: The metrics file is missing or holds no rows.
    """
    metrics = load_existing_metrics(fn_metrics)
    if metrics.empty:
        msg = f"No metrics rows in {fn_metrics}"
        logger.error(msg)
        raise FileNotFoundError(msg)
    return SignalTables(
        metrics,
        load_all_archive_data(AssetType.DRIVER, fn=fn_archive),
        load_all_archive_data(AssetType.CONSTRUCTOR, fn=fn_archive),
    )


class SignalTables:
    """Expected fantasy points for any race's assets, from their signal positions.

    A season's tables come from the ``TABLE_SEASONS`` other than itself, races 2
    onwards, so a season never sees its own results and 2026 never enters a table. A
    table holds the mean points at each position, forced to fall by position, and a
    position past its end takes the last value. Each table is built once per instance.

    Args:
        metrics: Rows in the shape of ``data/fastf1_practice_rolling_metrics.xlsx``.
        driver_archive: ``load_all_archive_data(AssetType.DRIVER)``, which also gives
            the per-race driver/constructor pairs.
        constructor_archive: ``load_all_archive_data(AssetType.CONSTRUCTOR)``.
    """

    def __init__(
        self,
        metrics: pd.DataFrame,
        driver_archive: pd.DataFrame,
        constructor_archive: pd.DataFrame,
    ):
        self._metrics = metrics
        self._pairs = get_race_driver_constructor_pairs(driver_archive)
        self._archive = {
            AssetType.DRIVER: driver_archive,
            AssetType.CONSTRUCTOR: constructor_archive,
        }
        self._history: pd.DataFrame | None = None
        self._negatives: pd.DataFrame | None = None
        self._tables: dict[tuple[str, int, AssetType], pd.Series] = {}
        self._race_values: dict[tuple[str, int, int], dict[str, float]] = {}

    def expected_points(self, season: int, race: int) -> dict[str, float]:
        """Each ranked asset's expected fantasy points in one race.

        Returns:
            Points keyed by driver identifier and constructor code. Empty when the race
            has no signal, and an asset with no position or place is left out.

        Raises:
            ValueError: A ranked asset in a table season has no fantasy points, a table
                has no history to draw on, or as for ``driver_positions``.
        """
        return self._per_race("points", season, race, self._expected_points)

    def _expected_points(self, season: int, race: int) -> dict[str, float]:
        expected = {}
        for asset_type, ranking in _RANKINGS.items():
            places = ranking(self._metrics, self._pairs, season, race)
            if places:
                table = self._table("points", season, asset_type)
                expected |= {asset: _look_up(table, place) for asset, place in places.items()}
        return expected

    def negative_chance(self, season: int, race: int) -> dict[str, float]:
        """Each priced asset's chance of going negative in one race.

        Looked up by asset type and by whether the asset went negative in any of the
        previous three rounds of the season. A driver carries their negatives to a new
        team, and a round an asset was not in counts for nothing. Reads no result from
        the race itself.

        Returns:
            Chances keyed by driver identifier and constructor code, for every asset
            priced in the race.

        Raises:
            ValueError: A table has no history to draw on.
        """
        return self._per_race("negatives", season, race, self._negative_chance)

    def _negative_chance(self, season: int, race: int) -> dict[str, float]:
        chances = {}
        for asset_type, archive in self._archive.items():
            priced = archive[(archive["Season"] == season) & (archive["Race"] == race)
                             & archive["Price"].notna()]
            if priced.empty:
                continue
            table = self._table("negatives", season, asset_type)
            recent = _any_recent_negative(archive, asset_type, season, race, priced)
            chances |= {
                asset: _look_up(table, flag)
                for asset, flag in zip(priced[asset_type.value], recent)
            }
        return chances

    def _per_race(
        self, name: str, season: int, race: int, compute: Callable[[int, int], dict[str, float]]
    ) -> dict[str, float]:
        """A race's values, computed once, as a copy the caller may change."""
        key = (name, season, race)
        if key not in self._race_values:
            self._race_values[key] = compute(season, race)
        return dict(self._race_values[key])

    def _table(self, name: str, season: int, asset_type: AssetType) -> pd.Series:
        """A season's table, built from the other table seasons on first use."""
        key = (name, season, asset_type)
        if key not in self._tables:
            history, summarise = {
                "points": (self._ranked_history, _falling_means),
                "negatives": (self._negative_history, _negative_shares),
            }[name]
            rows = history()
            self._tables[key] = summarise(
                rows[(rows["Season"] != season) & (rows["AssetType"] == asset_type)]
            )
        table = self._tables[key]
        if table.empty:
            msg = f"No 2023-25 history for {season}'s {asset_type.value} {name} table"
            logger.error(msg)
            raise ValueError(msg)
        return table

    def _negative_history(self) -> pd.DataFrame:
        """Every table season's assets from race 2 on: whether they had a recent negative,
        and whether they then went negative."""
        if self._negatives is not None:
            return self._negatives
        frames = [pd.DataFrame(columns=["AssetType", "Season", "Race", "RecentNegative", "Negative"])]
        for asset_type, archive in self._archive.items():
            scored = archive[archive["Season"].isin(TABLE_SEASONS) & archive["Points"].notna()
                             & (archive["Race"] > FIRST_RACE)]
            for (season, race), raced in scored.groupby(["Season", "Race"]):
                frames.append(pd.DataFrame({
                    "AssetType": asset_type,
                    "Season": season,
                    "Race": race,
                    "RecentNegative": _any_recent_negative(
                        archive, asset_type, season, race, raced
                    ).to_numpy(),
                    "Negative": (raced["Points"] < 0).to_numpy(),
                }))
        self._negatives = pd.concat(frames, ignore_index=True).astype(
            {"RecentNegative": int, "Negative": bool}
        )
        return self._negatives

    def _ranked_history(self) -> pd.DataFrame:
        """Every table season's ranked assets from race 2 on, with their fantasy points."""
        if self._history is not None:
            return self._history
        rows = []
        for season in TABLE_SEASONS:
            in_season = self._metrics[self._metrics["Season"] == season]
            for race in sorted(in_season.loc[in_season["Race"] > FIRST_RACE, "Race"].unique()):
                for asset_type, ranking in _RANKINGS.items():
                    for asset, place in ranking(self._metrics, self._pairs, season, race).items():
                        rows.append({"AssetType": asset_type, "Season": season, "Race": race,
                                     "Asset": asset, "Place": place})
        history = pd.DataFrame(rows, columns=["AssetType", "Season", "Race", "Asset", "Place"])

        # Driver identifiers hold an "@" and constructor codes do not, so one join serves both.
        points = pd.concat(
            archive[["Season", "Race", asset_type.value, "Points"]].rename(
                columns={asset_type.value: "Asset"}
            )
            for asset_type, archive in self._archive.items()
        )
        history = history.merge(points, on=["Season", "Race", "Asset"], how="left", validate="m:1")

        missing = history[history["Points"].isna()]
        if not missing.empty:
            names = ", ".join(f"{r.Season} race {r.Race}: {r.Asset}" for r in missing.itertuples())
            msg = f"No fantasy points for ranked assets in {names}"
            logger.error(msg)
            raise ValueError(msg)
        self._history = history
        return history


def _falling_means(history: pd.DataFrame) -> pd.Series:
    """Mean points by place, forced to fall by place and weighted by each place's count."""
    stats = history.groupby("Place")["Points"].agg(["mean", "count"])
    if stats.empty:
        return pd.Series(dtype=float)
    fitted = isotonic_regression(
        stats["mean"].to_numpy(), weights=stats["count"].to_numpy(), increasing=False
    ).x
    return pd.Series(fitted, index=stats.index)


def _negative_shares(history: pd.DataFrame) -> pd.Series:
    """The share of rows that went negative, without and with a recent negative."""
    return history.groupby("RecentNegative")["Negative"].mean()


def _any_recent_negative(
    archive: pd.DataFrame, asset_type: AssetType, season: int, race: int, rows: pd.DataFrame
) -> pd.Series:
    """1 for each row with a negative in the previous ``RECENT_RACES`` rounds of the
    season, else 0. One negative counts the same as several, as in 2023-25 several were
    no riskier than one (fastf1_v2 log, step 5)."""
    prior = archive[(archive["Season"] == season)
                    & archive["Race"].between(race - RECENT_RACES, race - 1)
                    & archive["Points"].notna()]
    went_negative = set(_carrier(prior[prior["Points"] < 0], asset_type))
    return _carrier(rows, asset_type).isin(went_negative).astype(int)


def _carrier(rows: pd.DataFrame, asset_type: AssetType) -> pd.Series:
    """Who a negative history belongs to: the driver whatever their team, or the constructor."""
    ids = rows[asset_type.value]
    return ids.str.split("@").str[0] if asset_type == AssetType.DRIVER else ids


def _look_up(table: pd.Series, key: int) -> float:
    """A key's value, a key past the table's end taking the last one."""
    return float(table[min(key, table.index.max())])


def _signal_rows(
    metrics: pd.DataFrame, pairs: pd.DataFrame, season: int, race: int
) -> pd.DataFrame:
    """One race's metrics rows, as ``_race_rows`` gives them, with each driver's ``signal``.

    Raises:
        ValueError: As for ``_race_rows``, or a driver lacks a value the signal adds up.
    """
    rows = add_signal_inputs(_race_rows(metrics, pairs, season, race))
    rows["signal"] = pd.Series(float("nan"), index=rows.index, dtype=float)
    for race_format, slots in SIGNAL_SLOTS.items():
        mask = rows["format"] == race_format
        rows.loc[mask, "signal"] = combination_signal(rows[mask], slots)

    _raise_for(rows[rows["signal"].isna()]["Driver"], "Missing signal input", season, race)
    rows["signal"] = rows["signal"].round(_SIGNAL_DECIMALS)
    return rows


def _race_rows(
    metrics: pd.DataFrame, pairs: pd.DataFrame, season: int, race: int
) -> pd.DataFrame:
    """One race's metrics rows, with each driver's fantasy ``Asset`` and ``AssetConstructor``."""
    race_pairs = pairs[(pairs["Season"] == season) & (pairs["Race"] == race)]
    ids = pd.DataFrame({
        "Driver": race_pairs["Driver"].str.split("@").str[0],
        "Asset": race_pairs["Driver"],
        "AssetConstructor": race_pairs["Constructor"],
    })
    rows = metrics[(metrics["Season"] == season) & (metrics["Race"] == race)]
    pair_counts = rows["Driver"].map(ids["Driver"].value_counts())
    _raise_for(rows[pair_counts != 1]["Driver"], "No single fantasy pair", season, race)
    return rows.merge(ids, on="Driver")


def _raise_for(names: pd.Series, problem: str, season: int, race: int) -> None:
    """Log and raise a ``ValueError`` naming each offender, if there are any."""
    if names.empty:
        return
    msg = f"{problem} for {season} race {race}: {', '.join(sorted(names))}"
    logger.error(msg)
    raise ValueError(msg)


def _ranked(rows: pd.DataFrame, value: str, key: str) -> dict[str, int]:
    """Number rows from 1 by ``value``, highest first, breaking ties on ``key``."""
    ordered = rows.sort_values([value, key], ascending=[False, True])
    return {asset: place for place, asset in enumerate(ordered[key], start=1)}


_RANKINGS = {AssetType.DRIVER: driver_positions, AssetType.CONSTRUCTOR: constructor_places}
