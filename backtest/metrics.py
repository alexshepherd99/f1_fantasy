"""Pair each strategy's results with the P2PM baseline and summarise them."""

import logging
from collections.abc import Sequence

import pandas as pd

from backtest.sample import assign_bands

# A team is identified within a season by its starting line-up
_TEAM_KEY = ["season", "team"]


def pair_with_baseline(results: pd.DataFrame, baseline_label: str, band_edges: Sequence[float]) -> pd.DataFrame:
    """Pair every result with the baseline's result for the same season and team.

    Each row's band is re-derived from its `sampled_value` against the current
    edges rather than taken from the stored `band`, which records the edges the
    row was drawn under. The baseline is paired with itself, at zero delta.
    Rows with no baseline result for their team are dropped and counted in the
    log.

    Args:
        results: This run's rows from `simulate_sample`.
        baseline_label: Label of the baseline strategy.
        band_edges: Current band edges.

    Returns:
        One row per (label, season, team) with its band, `sampled_value`,
        `total_points`, `baseline_points`, `delta` and `delta_pct`.

    Raises:
        ValueError: If a value falls outside every band, or the baseline has no
            results.
    """
    bands = assign_bands(results["sampled_value"], band_edges)
    if bands.isna().any():
        outside = results.loc[bands.isna(), "sampled_value"].tolist()
        logging.error(f"Sampled values outside bands {band_edges}: {outside}")
        raise ValueError(f"{len(outside)} results fall outside every band {band_edges}")

    baseline = results.loc[results["label"] == baseline_label, _TEAM_KEY + ["total_points"]]
    if baseline.empty:
        logging.error(f"No results for baseline {baseline_label}, labels are {sorted(results['label'].unique())}")
        raise ValueError(f"No results for baseline {baseline_label}")

    paired = (
        results[["label"] + _TEAM_KEY + ["sampled_value", "total_points"]]
        .assign(band=bands)
        .merge(baseline.rename(columns={"total_points": "baseline_points"}), on=_TEAM_KEY)
    )

    dropped = len(results) - len(paired)
    if dropped:
        logging.warning(f"Dropped {dropped} results with no {baseline_label} result for their team")

    paired["delta"] = paired["total_points"] - paired["baseline_points"]
    paired["delta_pct"] = paired["delta"] / paired["baseline_points"] * 100
    return paired[["label"] + _TEAM_KEY + ["band", "sampled_value", "total_points", "baseline_points", "delta", "delta_pct"]]
