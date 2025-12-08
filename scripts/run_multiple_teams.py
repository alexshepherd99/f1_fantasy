import os
import pandas as pd
import logging

from common import setup_logging
from helpers import load_with_derivations
from linear.strategy_budget import StrategyMaxBudget
from races.first_picks import get_starting_combinations
from races.season import factory_race, factory_season
from races.team import Team, factory_team_row
from scripts.run_single_team import run_for_team

_SEASON = 2025
_FILE_BATCH_RESULTS = "outputs/f1_fantasy_results_batch.xlsx"
_STRATEGY = StrategyMaxBudget


def get_starting_key(strat_name: str, season: int, team: Team) -> str:
    return f"({strat_name})({season}){team}"


def open_batch_results_file(fn: str) -> pd.DataFrame:
    if not os.path.exists(fn):
        return pd.DataFrame(columns=["sim_key"])
    
    return pd.read_excel(fn)


if __name__ == "__main__":
    setup_logging()

    # TODO asset data points like PPM should be added as dict of dicts, with derivations class providing the key

    (df_driver_ppm, df_constructor_ppm, df_driver_pairs) = load_with_derivations(season=_SEASON)
    
    _season = factory_season(
        df_driver_ppm,
        df_constructor_ppm,
        df_driver_pairs,
        _SEASON,
    )
    
    _race_first = factory_race(
        df_driver_ppm,
        df_constructor_ppm,
        df_driver_pairs,
        1,
    )

    _df_batch_results = open_batch_results_file(_FILE_BATCH_RESULTS)
    _df_combinations = get_starting_combinations(_SEASON, 1, 99.5)

    counter = 0
    skipped = 0
    _rows_append = []

    for _idx, _row in _df_combinations.iterrows():
        _team = factory_team_row(_row.to_dict(), _race_first)
        _sim_key = get_starting_key(_STRATEGY.__name__, _SEASON, _team)

        if _sim_key in _df_batch_results["sim_key"].unique():
            logging.info(f"Skipping batch for {_sim_key}")
            skipped += 1

        else:
            _rows_intermediate = run_for_team(_STRATEGY, _team, _season, _SEASON, 1)
            _row_final = _rows_intermediate[-1]
            _row_final["sim_key"] = _sim_key
            _rows_append.append(_row_final)

            counter += 1
            if counter % 100 == 0:
                logging.info(f"Batch {counter} of {len(_df_combinations.index)-skipped}, writing to disk...")
                _df_tmp = pd.DataFrame(_rows_append)
                _df_batch_results = pd.concat([_df_batch_results, _df_tmp])
                _df_batch_results.to_excel(_FILE_BATCH_RESULTS, index=False)
                _rows_append = []
