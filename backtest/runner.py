"""Simulate sampled starting teams and store one result row per team."""

import logging
from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from backtest.metrics import POOLED_BAND, pair_with_baseline, rank_challengers, season_summary, verdict
from backtest.sample import STARTING_RACE, sample_starting_teams
from helpers import load_with_derivations
from linear.strategy_base import StrategyBase
from linear.strategy_p2pm import StrategyMaxP2PM
from races.season import factory_season
from races.team import factory_team_row
from scripts.run_multiple_teams import get_starting_key, open_batch_results_file
from scripts.run_single_team import run_for_team

# Columns the sample adds to the priced combinations, which are not assets
_SAMPLE_COLUMNS = ["total_value", "band"]

# Every challenger is paired with this strategy's result for the same team (R2)
BASELINE = StrategyMaxP2PM


def append_results(store: pd.DataFrame, rows: list[dict], path: str) -> pd.DataFrame:
    """Append result rows to the store and write the whole store to `path`.

    Stands in for `scripts.run_multiple_teams.write_batch_results`, which
    hardcodes its output path. Nothing is written when there are no rows.

    Args:
        store: Results so far, as opened by `open_batch_results_file`.
        rows: New result rows, one dict per simulated team.
        path: Parquet file to write.

    Returns:
        The store with the new rows appended.
    """
    if not rows:
        return store

    new_rows = pd.DataFrame(rows)
    # An empty store has only a sim_key column, and concatenating onto it
    # upcasts every other integer column to float
    store = new_rows if store.empty else pd.concat([store, new_rows], ignore_index=True)

    logging.info(f"Writing {path}, {len(new_rows)} new rows, {len(store)} in total")
    store.to_parquet(path)
    return store


def simulate_sample(
    season: int,
    sample: pd.DataFrame,
    strategies: list[type[StrategyBase]],
    store_path: str,
    flush_every: int = 100,
) -> pd.DataFrame:
    """Simulate every strategy on every sampled team of one season, resumably.

    Each (strategy, team) pair is simulated from the starting race by the
    unchanged `run_for_team`, on a fresh `Team` since that function mutates the
    team it is given. Its final-race row is stored with `sim_key`, `label`,
    `team`, `sampled_value` and `band` added. The engine's own `total_value` is
    the team's end-of-season valuation, so the sample's value is stored as
    `sampled_value` rather than overwriting it. Keys already in the store are
    skipped, and the store is written every `flush_every` simulations.

    Args:
        season: Season year.
        sample: Sampled starting teams from `sample_starting_teams`.
        strategies: Strategy classes to simulate, in order; each is labelled by
            its `__name__`.
        store_path: Parquet results store to resume from and write to.
        flush_every: Simulations between writes.

    Returns:
        This run's rows, one per (strategy, team), whether simulated now or
        found in the store. Rows the store holds for other teams or strategies
        stay on disk but are not returned, so they cannot leak into a summary.
    """
    season_data = factory_season(*load_with_derivations(season=season), season)
    starting_race = season_data.races[STARTING_RACE]

    store = open_batch_results_file(store_path)
    done = set(store["sim_key"])
    rows = []
    skipped = 0
    run_keys = []

    for strategy in strategies:
        label = strategy.__name__
        logging.info(f"Simulating {label} for season {season} on {len(sample)} teams")

        for _, sampled in sample.iterrows():
            team = factory_team_row(sampled.drop(_SAMPLE_COLUMNS).to_dict(), starting_race)
            # Taken before simulating, which leaves the team as it ends the season
            starting_team = str(team)
            sim_key = get_starting_key(label, season, team)
            run_keys.append(sim_key)
            if sim_key in done:
                skipped += 1
                continue

            row = run_for_team(strategy, team, season_data, season, STARTING_RACE)[-1]
            row.update(
                sim_key=sim_key,
                label=label,
                team=starting_team,
                sampled_value=sampled["total_value"],
                band=sampled["band"],
            )
            rows.append(row)

            if len(rows) == flush_every:
                store = append_results(store, rows, store_path)
                rows = []

    logging.info(f"Season {season}: skipped {skipped} simulations already in the store")
    store = append_results(store, rows, store_path)
    return store[store["sim_key"].isin(run_keys)].reset_index(drop=True)


def _with_baseline_first(strategies: Sequence[type[StrategyBase]]) -> list[type[StrategyBase]]:
    """Put the baseline first, adding it if absent, and reject duplicate labels.

    Two strategies sharing a label would share keys, so the second would
    silently reuse the first's results.
    """
    ordered = [BASELINE] + [s for s in strategies if s.__name__ != BASELINE.__name__]
    labels = [s.__name__ for s in strategies]
    duplicates = sorted({label for label in labels if labels.count(label) > 1})
    if duplicates:
        logging.error(f"Duplicate strategy labels {duplicates}")
        raise ValueError(f"Strategy labels must be unique, duplicated: {duplicates}")
    return ordered


def verdict_path(summary_path: str) -> str:
    """Return where the verdict is written: beside the summary, suffixed `_verdict`."""
    path = Path(summary_path)
    return str(path.with_name(f"{path.stem}_verdict{path.suffix}"))


def run_backtest(
    seasons: Sequence[int],
    n: int,
    seed: int,
    strategies: Sequence[type[StrategyBase]],
    band_edges: Sequence[float],
    store_path: str,
    summary_path: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Sample, simulate and summarise every strategy against the P2PM baseline.

    Each season is sampled and simulated in turn, the baseline first, and its
    sample released before the next. The combined rows are then paired with the
    baseline, summarised per season and band, ranked, and judged. The summary is
    written to `summary_path` and the verdict beside it; both are logged.

    Args:
        seasons: Seasons to run.
        n: Teams to sample per band.
        seed: Sampling seed.
        strategies: Challengers; the baseline is added, or moved, to the front.
        band_edges: Value band edges.
        store_path: Parquet results store, resumed from and appended to.
        summary_path: CSV to write the ranked summary to.

    Returns:
        The ranked summary and the verdict.

    Raises:
        ValueError: If two strategies share a label.
    """
    strategies = _with_baseline_first(strategies)
    baseline_label = BASELINE.__name__

    results = []
    for season in seasons:
        sample = sample_starting_teams(season, n, seed, band_edges)
        results.append(simulate_sample(season, sample, strategies, store_path))
        del sample

    paired = pair_with_baseline(pd.concat(results, ignore_index=True), baseline_label, band_edges)
    summary = rank_challengers(season_summary(paired, band_edges), baseline_label)
    verdicts = verdict(summary, baseline_label)

    summary.to_csv(summary_path, index=False)
    verdicts.to_csv(verdict_path(summary_path), index=False)

    logging.info(f"Summary, written to {summary_path}:\n{summary.to_string(index=False)}")
    logging.info(
        f"'{POOLED_BAND}' rows pool the equally sampled bands, so they are a mean over the sampled "
        "bands, not over every team that exists"
    )
    logging.info(f"Verdict against {baseline_label}, written to {verdict_path(summary_path)}:\n"
                 f"{verdicts.to_string(index=False)}")
    return summary, verdicts
