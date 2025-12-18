import os
import pandas as pd
import logging

from common import F1_SEASON_CONSTRUCTORS, setup_logging
from helpers import load_with_derivations
from linear.strategy_base import StrategyBase
from linear.strategy_budget import StrategyMaxBudget
from linear.strategy_p2pm import StrategyMaxP2PM
from linear.strategy_zero_stop import StrategyZeroStop
from races.first_picks import get_starting_combinations
from races.season import factory_race, factory_season
from races.team import Team, factory_team_row
from scripts.run_single_team import get_strat_display_name, run_for_team

_SEASONS = F1_SEASON_CONSTRUCTORS.keys()
_FILE_BATCH_RESULTS_PARQET = "outputs/f1_fantasy_results_batch.parquet"
_FILE_BATCH_RESULTS_EXCEL = "outputs/f1_fantasy_results_batch.csv"
_STRATEGIES = [StrategyMaxBudget, StrategyZeroStop, StrategyMaxP2PM]
_SUB_STRAT = ""


def get_starting_key(strat_name: str, season: int, team: Team, sub_strat: str = "") -> str:
    if len(sub_strat) > 0:
        return f"({strat_name}:{sub_strat})({season}){team}"
    else:
        return f"({strat_name})({season}){team}"
    

def open_batch_results_file(fn: str) -> pd.DataFrame:
    if not os.path.exists(fn):
        return pd.DataFrame(columns=["sim_key"])
    
    df = pd.read_parquet(fn)
    logging.debug(f"Opened {fn} with shape {df.shape}")
    return df

def write_batch_results(df_batch_results: pd.DataFrame, rows_append: list) -> pd.DataFrame:
    df_tmp = pd.DataFrame(rows_append)
    df_batch_results = pd.concat([df_batch_results, df_tmp])
    logging.info(f"Writing {_FILE_BATCH_RESULTS_PARQET}, new shape {df_tmp.shape}, total shape {df_batch_results.shape}")
    df_batch_results.to_parquet(_FILE_BATCH_RESULTS_PARQET)
    return df_batch_results


def run_strategy_for_season(season_year: int, strategy: type[StrategyBase]):
    (df_driver_ppm, df_constructor_ppm, df_driver_pairs) = load_with_derivations(season=season_year)
    
    _season = factory_season(
        df_driver_ppm,
        df_constructor_ppm,
        df_driver_pairs,
        season_year,
    )
    
    _race_first = factory_race(
        df_driver_ppm,
        df_constructor_ppm,
        df_driver_pairs,
        1,
    )

    _df_batch_results = open_batch_results_file(_FILE_BATCH_RESULTS_PARQET)
    _df_combinations = get_starting_combinations(season_year, 1, 99.5)

    counter = 0
    skipped = 0
    _rows_append = []

    strat_display_name = get_strat_display_name(strategy, _SUB_STRAT)
    logging.info(f"Running simulation for season {season_year} strategy {strat_display_name}")

    for _idx, _row in _df_combinations.iterrows():
        _team = factory_team_row(_row.to_dict(), _race_first)
        _sim_key = get_starting_key(strategy.__name__, season_year, _team, _SUB_STRAT)

        if _sim_key in _df_batch_results["sim_key"].unique():
            logging.debug(f"Skipping batch for {_sim_key}")
            skipped += 1

        else:
            _rows_intermediate = run_for_team(strategy, _team, _season, season_year, 1, _SUB_STRAT)
            _row_final = _rows_intermediate[-1]
            _row_final["sim_key"] = _sim_key
            _rows_append.append(_row_final)

            counter += 1
            if counter % 100 == 0:
                logging.info(f"Batch {counter} of {len(_df_combinations.index)-skipped}, writing to disk, skipped {skipped}...")
                _df_batch_results = write_batch_results(_df_batch_results, _rows_append)
                _rows_append = []

    # Write any remaining results
    logging.info(f"Writing remaining {len(_rows_append)} batches to disk, skipped {skipped}...")
    _df_batch_results = write_batch_results(_df_batch_results, _rows_append)
    _rows_append = []


if __name__ == "__main__":
    setup_logging()

    for _season_year in _SEASONS:
        for _strategy in _STRATEGIES:
            run_strategy_for_season(_season_year, _strategy)
