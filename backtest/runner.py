"""Simulate sampled starting teams and store one result row per team."""

import logging

import pandas as pd


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
