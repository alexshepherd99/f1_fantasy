import os
import pandas as pd
import logging

from common import AssetType, setup_logging
from helpers import load_with_derivations
from linear.strategy_base import VarType
from linear.strategy_budget import StrategyMaxBudget
from linear.strategy_factory import factory_strategy
from races.season import factory_season
from races.team import factory_team_lists

_FILE_BATCH_RESULTS = "outputs/f1_fantasy_batch_results.xlsx"


def load_batch_results(filename:str = _FILE_BATCH_RESULTS) -> pd.DataFrame:
	if not os.path.exists(filename):
		return pd.DataFrame(
			columns=[
				"strategy",
				"season",
                "race",
				"drivers",
				"constructors",
				"points",
				"total_points",
				"unused_budget",
            ]
        )

	# Let pandas raise any exceptions encountered while reading a present file
	# (e.g. corrupt file). This function's contract only requires returning
	# an empty DataFrame when the file does not exist.
	return pd.read_excel(filename)



if __name__ == "__main__":
    setup_logging()

    (df_driver_ppm, df_constructor_ppm, df_driver_pairs) = load_with_derivations(season=2023)
    
    season = factory_season(
        df_driver_ppm,
        df_constructor_ppm,
        df_driver_pairs,
        2023,
        "PPM Cumulative (3)"
    )

    race_1 = season.races[1]
	
    team_start_drivers = ["SAR", "HUL", "DEV", "TSU", "ZHO"]
    team_start_constructors = ["MCL", "FER"]

    team = factory_team_lists(
        drivers=team_start_drivers,
        constructors=team_start_constructors,
        race=race_1,
        total_budget=100.0
    )
    race_1_points = team.update_points(race_1)

    rows = []
    row = {
            "strategy": "strat_test",
            "season": 2023,
            "race": 1,
            "drivers": team.assets[AssetType.DRIVER],
            "constructors": team.assets[AssetType.CONSTRUCTOR],
            "points": race_1_points,
            "total_points": team.total_points,  # Same as race 1 this time around
            "unused_budget": team.unused_budget,
            "total_budget": 100.0
        }
    rows.append(row)
    logging.info(row)

    for race_num in season.races.keys():
        strat = factory_strategy(season.races[race_num], team, StrategyMaxBudget, max_moves=2)

        # Update the max available budget to reflect prices from next race
        strat._max_cost = team.total_budget(season.races[race_num])
        max_budget = strat._max_cost

        model = strat.execute()

        # Extract selected assets from the LP model
        model_drivers = [d for d,v in strat._lp_variables[VarType.TeamDrivers].items() if v.varValue == 1]
        model_constructors = [c for c,v in strat._lp_variables[VarType.TeamConstructors].items() if v.varValue == 1]

        # Create new team based on selected assets
        team = factory_team_lists(
            drivers=model_drivers,
            constructors=model_constructors,
            race=season.races[race_num],
            total_budget=max_budget
        )
