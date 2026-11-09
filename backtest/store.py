"""Keys and loading for back-test results stores."""

import logging
import os

import pandas as pd

from races.team import Team


def get_starting_key(strat_name: str, season: int, team: Team) -> str:
    return f"({strat_name})({season}){team}"


def open_batch_results_file(fn: str) -> pd.DataFrame:
    if not os.path.exists(fn):
        return pd.DataFrame(columns=["sim_key"])

    df = pd.read_parquet(fn)
    logging.debug(f"Opened {fn} with shape {df.shape}")
    return df
