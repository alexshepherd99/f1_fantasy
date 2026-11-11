"""Simulate a single team across races using various strategies and save per-race results to an Excel file."""

import pandas as pd
import logging

from common import setup_logging
from helpers import load_with_derivations
from linear.strategy_budget import StrategyMaxBudget
from linear.strategy_p2pm import StrategyMaxP2PM
from linear.strategy_zero_stop import StrategyZeroStop
from linear.strategy_odds import StrategyBettingOdds
from races.season import factory_season
from races.team import factory_team_lists
from simulate.season import run_for_team

_FILE_BATCH_RESULTS = "outputs/f1_fantasy_results_single.xlsx"

# Config items to run a single team prediction for all strategies.  This will start at the specified race
# within that season, then run to the last race with available data.
#SEASON = 2025
#TEAM_START_DRIVERS = ["LEC", "SAI", "VER", "HAD", "ALO"]
#TEAM_START_CONSTRUCTORS = ["MER", "HAA"]
#STARTING_RACE = 23  # The team above is for race 23, therefore we start predicting from race 24
#STARTING_UNUSED_BUDGET = 0.5  # This will only be used if starting after the first race of the season

# My starting team from 2025
#SEASON = 2025
#TEAM_START_DRIVERS = ["TSU@VRB", "SAI@WIL", "BEA@HAA", "HAD@VRB", "DOO@ALP"]
#TEAM_START_CONSTRUCTORS = ["MCL", "FER"]
#STARTING_RACE = 1
#STARTING_UNUSED_BUDGET = 0.1  # Not used here, if we are starting in the first race of the season

# 2026 team - primary
SEASON = 2026
#TEAM_START_DRIVERS = ["RUS@MER", "LIN@VRB", "COL@ALP", "BOR@AUD", "HAD@RED"]  # Starting line-up
#TEAM_START_CONSTRUCTORS = ["HAA", "MER"]  # Starting line-up
TEAM_START_DRIVERS = ["VER@RED", "LEC@FER", "PER@CAD", "BOR@AUD", "LAW@VRB"]
TEAM_START_CONSTRUCTORS = ["RED", "FER"]
STARTING_RACE = 21
STARTING_UNUSED_BUDGET = 1.0


if __name__ == "__main__":
    setup_logging()

    (df_driver_ppm, df_constructor_ppm, df_driver_pairs) = load_with_derivations(season=SEASON)

    _season = factory_season(
        df_driver_ppm,
        df_constructor_ppm,
        df_driver_pairs,
        SEASON,
    )

    _rows = []

    #for strat in StrategyMaxBudget, StrategyMaxP2PM, StrategyZeroStop:
    for strat in [StrategyMaxP2PM]:

        # This will calculate the unused budget based on starting prices
        _team = factory_team_lists(
            drivers=TEAM_START_DRIVERS,
            constructors=TEAM_START_CONSTRUCTORS,
            race=_season.races[STARTING_RACE],
        )

        # If we're starting mid-season, use the specified unused budget
        if STARTING_RACE > 1:
            _team.unused_budget = STARTING_UNUSED_BUDGET

        _rows = _rows + run_for_team(strat, _team, _season, SEASON, STARTING_RACE)

    # Create a DataFrame from the results rows and save to Excel
    pd.DataFrame(_rows).to_excel(_FILE_BATCH_RESULTS, index=False)
    logging.info(f"Saved batch results to {_FILE_BATCH_RESULTS} with {len(_rows)} rows")
