"""Pair each strategy's results with the P2PM baseline and summarise them."""

import logging
from collections.abc import Sequence

import pandas as pd

from backtest.sample import assign_bands, band_labels

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


def _p10(values: pd.Series) -> float:
    return values.quantile(0.1)


def _win_rate(deltas: pd.Series) -> float:
    # A tie does not beat the baseline
    return (deltas > 0).mean()


_SUMMARY_METRICS = {
    "teams": ("team", "count"),
    "mean_points": ("total_points", "mean"),
    "median_points": ("total_points", "median"),
    "p10_points": ("total_points", _p10),
    "max_points": ("total_points", "max"),
    "mean_delta": ("delta", "mean"),
    "mean_delta_pct": ("delta_pct", "mean"),
    "median_delta": ("delta", "median"),
    "p10_delta": ("delta", _p10),
    "win_rate": ("delta", _win_rate),
}

POOLED_BAND = "pooled"


def season_summary(paired: pd.DataFrame, band_edges: Sequence[float]) -> pd.DataFrame:
    """Summarise paired results per label, season and band, plus pooled per season.

    The pooled row pools every paired team of the season, so it is a mean over
    the sampled bands, equally sampled but unequally populated, and not over all
    the teams that exist. It is computed from the per-team rows rather than by
    averaging band means, which diverge once pairing leaves bands unequal.

    Args:
        paired: Output of `pair_with_baseline`.
        band_edges: Current band edges, which order the bands.

    Returns:
        One row per (label, season, band) with a populated band, and one per
        (label, season) with band `pooled`, ordered by season, label, band edge
        and then the pooled row.
    """
    by_band = paired.groupby(["label", "season", "band"], as_index=False).agg(**_SUMMARY_METRICS)
    pooled = paired.groupby(["label", "season"], as_index=False).agg(**_SUMMARY_METRICS).assign(band=POOLED_BAND)

    summary = pd.concat([by_band, pooled], ignore_index=True)
    band_order = pd.Categorical(summary["band"], categories=band_labels(band_edges) + [POOLED_BAND], ordered=True)
    summary = summary.assign(_band_order=band_order).sort_values(["season", "label", "_band_order"])
    return summary[["label", "season", "band"] + list(_SUMMARY_METRICS)].reset_index(drop=True)
