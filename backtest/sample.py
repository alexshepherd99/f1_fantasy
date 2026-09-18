"""Draw a seeded sample of starting teams per season and value band."""

import logging
from collections.abc import Sequence

import pandas as pd

from races.first_picks import get_starting_combinations

# Starting teams are drawn as they stand before the first race
STARTING_RACE = 1

DEFAULT_BAND_EDGES = (90.0, 95.0, 99.5, 100.0)


def band_labels(band_edges: Sequence[float]) -> list[str]:
    """Return a `(min, max]` label for each band between consecutive edges."""
    return [f"({low:g}, {high:g}]" for low, high in zip(band_edges, band_edges[1:])]


def validate_band_edges(band_edges: Sequence[float]) -> None:
    """Raise `ValueError` unless the edges are at least two, strictly increasing."""
    if len(band_edges) < 2 or any(low >= high for low, high in zip(band_edges, band_edges[1:])):
        logging.error(f"Invalid band edges {band_edges}")
        raise ValueError(f"Band edges must be at least two strictly increasing values, got {band_edges}")


def assign_bands(values: pd.Series, band_edges: Sequence[float]) -> pd.Series:
    """Label each value with its `(min, max]` band, or NaN if it is in none."""
    return pd.cut(values, list(band_edges), labels=band_labels(band_edges)).astype(object)


def sample_starting_teams(
    season: int,
    n: int,
    seed: int,
    band_edges: Sequence[float] = DEFAULT_BAND_EDGES,
) -> pd.DataFrame:
    """Draw up to `n` starting teams from each value band of a season.

    Each band is a `(min, max]` window between consecutive edges, matching the
    exclusive-minimum, inclusive-maximum bounds of `get_starting_combinations`.
    The season is enumerated once across all the bands and then cut into them.

    Args:
        season: Season year.
        n: Teams to draw per band; a band with no more than `n` teams is taken whole.
        seed: Random seed, so the same seed and archive data give the same teams.
        band_edges: Strictly increasing band edges.

    Returns:
        The sampled priced combinations with an added `band` label column,
        indexed by each team's position in the full set of combinations.

    Raises:
        ValueError: If the edges are fewer than two or not strictly increasing.
    """
    validate_band_edges(band_edges)

    combinations = get_starting_combinations(season, STARTING_RACE, band_edges[0], band_edges[-1])
    combinations["band"] = assign_bands(combinations["total_value"], band_edges)

    samples = []
    for label in band_labels(band_edges):
        band = combinations[combinations["band"] == label]
        samples.append(band if len(band) <= n else band.sample(n, random_state=seed))

    return pd.concat(samples)
