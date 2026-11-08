"""fastf1_v2's signal: each driver's and constructor's value for one race, with the
chance of going negative and the expected price rise.

The signal is the combination `indicator_analysis_v1` chose for fantasy points (see its
log's *Conclusions*), built from metrics rows alone so that a race not yet run can be
valued. See ``docs/fastf1_v2/plan.md``, steps 4, 11, 12 and 20.
"""
from __future__ import annotations

import dataclasses
import functools
import logging
from pathlib import Path
from typing import Callable

import pandas as pd

from common import AssetType
from fast_f1.indicator_analysis import combination_signal
from fast_f1.metrics import (
    FIRST_RACE,
    SIGNAL_SLOTS,
    add_signal_inputs,
    get_rolling_window_races,
)
from fast_f1.output import DEFAULT_HISTORICAL_OUTPUT, load_existing_metrics
from import_data.derivations import get_race_driver_constructor_pairs
from import_data.import_history import _DIR_ARCHIVE_INPUTS, load_all_archive_data

logger = logging.getLogger(__name__)

# The seasons any table is built from. 2026 is left out, as it is the season the
# strategy is judged on (see docs/fastf1_v2/requirements.md, question 7).
TABLE_SEASONS = (2023, 2024, 2025)

# Rounding lets signals that differ only by floating point noise count as equal, so a
# race whose signals are all equal is caught rather than stretched on that noise.
_SIGNAL_DECIMALS = 9


@dataclasses.dataclass(frozen=True)
class PriceRules:
    """One season's figures for the game's three-race price model, in 1m.

    Attributes:
        split: An asset priced at or above it takes the smaller, upper-tier steps.
        floor: A fall stops here.
        cap: A rise stops here, or None for no cap.
    """
    split: float
    floor: float
    cap: float | None


# The game's price rules from 2025, as checked against the archive (docs/fastf1_v2/log.md,
# *The 2025 model against the archive*). 2023-24 ran a different model, and a season after
# the last here takes its figures.
PRICE_RULES = {
    2025: PriceRules(split=18.5, floor=4.5, cap=None),
    2026: PriceRules(split=18.5, floor=3.0, cap=34.0),
}

# Fantasy points for a race from an asset's value, as (intercept, slope), fitted on 2023-24
# (docs/fastf1_v2/log.md, *Step 19: the conversion for estimate (a)*).
POINTS_FROM_VALUE = {
    AssetType.DRIVER: (1.538, 1.469),
    AssetType.CONSTRUCTOR: (5.948, 1.687),
}

# Each rating band's step, as (at or above the split, below it).
_BAND_STEPS = {
    "Great": (0.3, 0.6),
    "Good": (0.1, 0.2),
    "Poor": (-0.1, -0.2),
    "Terrible": (-0.3, -0.6),
}


def rule_price_move(rating: float, price: float, season: int) -> float:
    """An asset's next price move under the game's three-race model, in 1m.

    Args:
        rating: The asset's mean points per 1m over the three races that set the move.
        price: The asset's price now.
        season: The season, whose ``PRICE_RULES`` apply.

    Returns:
        The move, rounded to 0.1. A floor or cap stops a move, but never pushes an asset
        already beyond it back inside.

    Raises:
        ValueError: The season is before the first in ``PRICE_RULES``.
    """
    if season < min(PRICE_RULES):
        msg = f"No price rules for {season}, which priced under a different model"
        logger.error(msg)
        raise ValueError(msg)
    rules = PRICE_RULES[max(s for s in PRICE_RULES if s <= season)]

    upper, lower = _BAND_STEPS[_rating_band(rating)]
    moved = price + (upper if price >= rules.split else lower)
    if rules.cap is not None:
        moved = min(moved, max(price, rules.cap))
    moved = max(moved, min(price, rules.floor))
    return round(moved - price, 1)


def _rating_band(rating: float) -> str:
    """The band of a rating: above 1.2, from 0.9, from 0.6, and below 0.6."""
    if rating > 1.2:
        return "Great"
    if rating >= 0.9:
        return "Good"
    if rating >= 0.6:
        return "Poor"
    return "Terrible"


def driver_values(
    metrics: pd.DataFrame, pairs: pd.DataFrame, season: int, race: int
) -> dict[str, float]:
    """Each driver's signal value in one race, on a championship points per race scale.

    The race's best signal gets the field's highest recent championship points per race,
    its worst gets the lowest, and every other driver falls in proportion between. Per
    race is ``RollingPoints`` divided by the races its window covers. A driver with no
    ``RollingPoints`` takes no part in setting that range. See
    ``docs/fastf1_v2/requirements.md``, question 1.

    Args:
        metrics: Rows in the shape of ``data/fastf1_practice_rolling_metrics.csv``,
            keyed on the bare driver code.
        pairs: The archive's per-race driver/constructor pairs, as the third frame
            from ``helpers.load_with_derivations``.
        season: The season to value.
        race: The race to value.

    Returns:
        Values keyed by the ``DRIVERCODE@CONSTRUCTOR`` identifier. Empty when the
        metrics hold no rows for the race. A fantasy driver with no metrics row has no
        value.

    Raises:
        ValueError: A driver in the race matches no fantasy pair or more than one, or
            lacks a value the signal adds up; every driver's signal is equal, which
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


def constructor_values(
    metrics: pd.DataFrame, pairs: pd.DataFrame, season: int, race: int
) -> dict[str, float]:
    """Each constructor's value in one race: the sum of its drivers' ``driver_values``.

    A constructor is reached through the archive's per-race pairs, and a driver with no
    value counts as zero, as a team that lost a driver still runs one car. See
    ``docs/fastf1_v2/requirements.md``, question 2. Arguments are as for
    ``driver_values``.

    Returns:
        Values keyed by the archive's constructor code. Empty when the metrics hold no
        rows for the race.

    Raises:
        ValueError: As for ``driver_values``.
    """
    values = driver_values(metrics, pairs, season, race)
    if not values:
        return {}
    race_pairs = pairs[(pairs["Season"] == season) & (pairs["Race"] == race)]
    # The sum skips a driver with no value, which counts them as zero.
    totals = race_pairs["Driver"].map(values).groupby(race_pairs["Constructor"]).sum()
    return {constructor: float(total) for constructor, total in totals.items()}


@functools.cache
def load_signal_tables(
    fn_metrics: Path | str = DEFAULT_HISTORICAL_OUTPUT, fn_archive: str = _DIR_ARCHIVE_INPUTS
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
    """Each asset's signal value in a race, its chance of going negative, and its expected
    price move.

    The chance is looked up by asset type and price third. A season's table comes from the
    ``TABLE_SEASONS`` other than itself, races 2 onwards, so a season never sees its own
    results and 2026 never enters a table. A key past a table's end takes the last value.
    The price move follows the game's rules, in ``price_rise``. Each table is built once per
    instance, and each race's figures once.

    Args:
        metrics: Rows in the shape of ``data/fastf1_practice_rolling_metrics.csv``.
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
        self._negatives: pd.DataFrame | None = None
        self._tables: dict[tuple[int, AssetType], pd.Series] = {}
        self._race_values: dict[tuple[str, int, int], dict[str, float]] = {}

    def values(self, season: int, race: int) -> dict[str, float]:
        """Each asset's value in one race: ``driver_values`` and ``constructor_values`` together.

        Returns:
            Values keyed by driver identifier and constructor code. Empty when the race has
            no signal, and a driver with no metrics row is left out.

        Raises:
            ValueError: As for ``driver_values``.
        """
        return self._per_race("values", season, race, self._values)

    def _values(self, season: int, race: int) -> dict[str, float]:
        return (driver_values(self._metrics, self._pairs, season, race)
                | constructor_values(self._metrics, self._pairs, season, race))

    def negative_chance(self, season: int, race: int) -> dict[str, float]:
        """Each priced asset's chance of going negative in one race.

        Looked up by asset type and by the asset's price third within the race, as
        ``_thirds`` splits them. Reads no result from the race itself.

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
            priced = _priced_in(archive, season, race)
            if priced.empty:
                continue
            table = self._negative_table(season, asset_type)
            chances |= {
                asset: _look_up(table, third)
                for asset, third in zip(priced[asset_type.value], _thirds(priced["Price"]))
            }
        return chances

    def price_rise(self, season: int, race: int) -> dict[str, float]:
        """Each priced asset's expected price move from one race to the next, in 1m.

        ``rule_price_move`` on the asset's rating: its points per 1m in each of the two
        races before this one held so far, from the archive, and this race's estimate,
        averaged. The estimate is the asset's value converted to fantasy points by
        ``POINTS_FROM_VALUE``, over its price. Reads no result from the race itself.

        A driver is followed by their code across a constructor switch, and a held race
        with no priced row for the asset counts as zero points.

        Returns:
            Moves keyed by driver identifier and constructor code, for every asset priced
            in the race that has a value. Empty when the race has no signal, or the season
            is before the first in ``PRICE_RULES``.

        Raises:
            ValueError: As for ``driver_values``.
        """
        return self._per_race("rises", season, race, self._price_rise)

    def _price_rise(self, season: int, race: int) -> dict[str, float]:
        if season < min(PRICE_RULES):
            return {}
        values = self.values(season, race)
        rises = {}
        for asset_type, archive in self._archive.items():
            held = [_points_per_million(archive, asset_type, season, r)
                    for r in get_rolling_window_races(race, rolling_window=2)]
            intercept, slope = POINTS_FROM_VALUE[asset_type]
            priced = _priced_in(archive, season, race)
            for asset, price in zip(priced[asset_type.value], priced["Price"]):
                if asset not in values:
                    continue
                code = asset.split("@")[0]
                estimate = (intercept + slope * values[asset]) / price
                rating = (sum(ppm.get(code, 0.0) for ppm in held) + estimate) / (len(held) + 1)
                rises[asset] = rule_price_move(rating, price, season)
        return rises

    def _per_race(
        self, name: str, season: int, race: int, compute: Callable[[int, int], dict[str, float]]
    ) -> dict[str, float]:
        """A race's values, computed once, as a copy the caller may change."""
        key = (name, season, race)
        if key not in self._race_values:
            self._race_values[key] = compute(season, race)
        return dict(self._race_values[key])

    def _negative_table(self, season: int, asset_type: AssetType) -> pd.Series:
        """A season's negatives table, built from the other table seasons on first use."""
        key = (season, asset_type)
        if key not in self._tables:
            rows = self._negative_history()
            self._tables[key] = _negative_shares(
                rows[(rows["Season"] != season) & (rows["AssetType"] == asset_type)]
            )
        table = self._tables[key]
        if table.empty:
            msg = f"No 2023-25 history for {season}'s {asset_type.value} negatives table"
            logger.error(msg)
            raise ValueError(msg)
        return table

    def _negative_history(self) -> pd.DataFrame:
        """Every table season's priced assets from race 2 on: their price third within the
        race, and whether they went negative."""
        if self._negatives is not None:
            return self._negatives
        frames = [pd.DataFrame(columns=["AssetType", "Season", "Third", "Negative"])]
        for asset_type, archive in self._archive.items():
            scored = archive[archive["Season"].isin(TABLE_SEASONS) & archive["Points"].notna()
                             & archive["Price"].notna() & (archive["Race"] > FIRST_RACE)]
            frames.append(pd.DataFrame({
                "AssetType": asset_type,
                "Season": scored["Season"],
                "Third": scored.groupby(["Season", "Race"])["Price"].transform(_thirds),
                "Negative": scored["Points"] < 0,
            }))
        self._negatives = pd.concat(frames, ignore_index=True).astype(
            {"Third": int, "Negative": bool}
        )
        return self._negatives


def _negative_shares(history: pd.DataFrame) -> pd.Series:
    """The share of rows that went negative, by price third."""
    return history.groupby("Third")["Negative"].mean()


def _points_per_million(
    archive: pd.DataFrame, asset_type: AssetType, season: int, race: int
) -> dict[str, float]:
    """Each priced asset's points per 1m in one race, keyed by driver code or constructor
    code, so that a driver is followed across a constructor switch."""
    priced = _priced_in(archive, season, race)
    codes = priced[asset_type.value].str.split("@").str[0]
    return dict(zip(codes, priced["Points"] / priced["Price"]))


def _priced_in(archive: pd.DataFrame, season: int, race: int) -> pd.DataFrame:
    """One race's archive rows with a price."""
    return archive[(archive["Season"] == season) & (archive["Race"] == race)
                   & archive["Price"].notna()]


def _thirds(values: pd.Series) -> pd.Series:
    """Each value's third among ``values``, 1 holding the lowest.

    Rank r of n falls in third ``(r - 1) * 3 // n + 1``, so a remainder goes to the lower
    thirds: 20 split 7/7/6 and 10 split 4/3/3. Equal values share the third of their
    lowest rank.
    """
    ranks = values.rank(method="min")
    return ((ranks - 1) * 3 // len(values) + 1).astype(int)


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
    """One race's metrics rows, with each driver's fantasy ``Asset``."""
    race_pairs = pairs[(pairs["Season"] == season) & (pairs["Race"] == race)]
    ids = pd.DataFrame({
        "Driver": race_pairs["Driver"].str.split("@").str[0],
        "Asset": race_pairs["Driver"],
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
