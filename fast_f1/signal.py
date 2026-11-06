"""fastf1_v2's signal: each driver's position for one race.

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
    rows = add_signal_inputs(
        metrics[(metrics["Season"] == season) & (metrics["Race"] == race)]
    )
    rows["signal"] = pd.Series(float("nan"), index=rows.index, dtype=float)
    for race_format, slots in SIGNAL_SLOTS.items():
        mask = rows["format"] == race_format
        rows.loc[mask, "signal"] = combination_signal(rows[mask], slots)

    race_pairs = pairs[(pairs["Season"] == season) & (pairs["Race"] == race)]
    ids = pd.DataFrame({
        "Driver": race_pairs["Driver"].str.split("@").str[0],
        "Asset": race_pairs["Driver"],
    })
    rows = rows.merge(ids, on="Driver")

    rows["signal"] = rows["signal"].round(_SIGNAL_DECIMALS)
    ordered = rows.sort_values(["signal", "Asset"], ascending=[False, True])
    return {asset: position for position, asset in enumerate(ordered["Asset"], start=1)}
