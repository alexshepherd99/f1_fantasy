"""fastf1_v2's signal: each driver's position and each constructor's place for one race.

The signal is the combination `indicator_analysis_v1` chose for fantasy points (see its
log's *Conclusions*), built from metrics rows alone so that a race not yet run can be
ranked. See ``docs/fastf1_v2/plan.md``, step 4.
"""
import pandas as pd

from fast_f1.indicator_analysis import (
    FORMAT_NORMAL,
    FORMAT_SPRINT,
    FORMAT_SPRINT_FP1,
    add_signal_inputs,
    combination_signal,
)

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
        that identifier.
    """
    rows = add_signal_inputs(_race_rows(metrics, pairs, season, race))
    rows["signal"] = pd.Series(float("nan"), index=rows.index, dtype=float)
    for race_format, slots in SIGNAL_SLOTS.items():
        mask = rows["format"] == race_format
        rows.loc[mask, "signal"] = combination_signal(rows[mask], slots)

    rows["signal"] = rows["signal"].round(_SIGNAL_DECIMALS)
    return _ranked(rows, "signal", "Asset")


def constructor_places(
    metrics: pd.DataFrame, pairs: pd.DataFrame, season: int, race: int
) -> dict[str, int]:
    """Each constructor's place in one race on its rolling points, 1 being best.

    A constructor is reached through its drivers and the archive's per-race pairs, so
    FastF1's team name plays no part. Arguments are as for ``driver_positions``.

    Returns:
        Places keyed by the archive's constructor code. Ties break on that code.
    """
    rows = _race_rows(metrics, pairs, season, race)
    constructors = rows.drop_duplicates("AssetConstructor")
    return _ranked(constructors, "ConstructorRollingPoints", "AssetConstructor")


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
    return rows.merge(ids, on="Driver")


def _ranked(rows: pd.DataFrame, value: str, key: str) -> dict[str, int]:
    """Number rows from 1 by ``value``, highest first, breaking ties on ``key``."""
    ordered = rows.sort_values([value, key], ascending=[False, True])
    return {asset: place for place, asset in enumerate(ordered[key], start=1)}
