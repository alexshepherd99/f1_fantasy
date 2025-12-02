import os
import pandas as pd
import logging

from common import AssetType, setup_logging
from helpers import load_with_derivations
from linear.strategy_base import VarType
from linear.strategy_budget import StrategyMaxBudget
from linear.strategy_factory import factory_strategy
from races.season import factory_season
from races.team import Team, factory_team_lists

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


def get_row_results(team: Team, race_num: int, race_points: int, total_budget: float, max_moves: int) -> dict:
    row = {
        "strategy": "strat_test",
        "season": 2023,
        "race": race_num,
        "drivers": team.assets[AssetType.DRIVER],
        "constructors": team.assets[AssetType.CONSTRUCTOR],
        "points": race_points,
        "total_points": team.total_points,
        "unused_budget": team.unused_budget,
        "total_budget": float(total_budget),
        "max_moves": max_moves,
    }
    logging.info(f"Row results: {row}")
    return row


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

    # This will calculate the unused budget based on starting prices
    team = factory_team_lists(
        drivers=team_start_drivers,
        constructors=team_start_constructors,
        race=race_1,
        total_budget=100.0  # Starting budget
    )
    
    # Collection to put all the results rows into
    rows = []

    # Flag to indicate if the next round should have a bonus free transfer
    bonus_free_transfer = False

    # Get sorted list of races
    races = sorted([int(r) for r in season.races.keys()])
    max_race_num = max(races)

    for race_num in races:
        # Update team points based on the last race
        race_points = team.update_points(season.races[race_num])

        # Do we have a bonus free transfer from the previous race?
        max_moves = 3 if bonus_free_transfer else 2

        # Create and append a results row for this race selection
        rows.append(get_row_results(team, race_num, race_points, team.total_budget(season.races[race_num]), max_moves))

        # We don't need to do a strategy for the last race
        if race_num < max_race_num:
            # In the first iteration, we are now looking at the data from race 1, to make an estimate of the team
            # we need for race 2.
            # The prices used to assess the max available budget will be based on the unused budget from the previous
            # run, with the team prices from the next run
            strat = factory_strategy(season.races[race_num], team, StrategyMaxBudget, max_moves=max_moves)

            model = strat.execute()

            # Extract selected assets from the LP model
            model_drivers = [d for d,v in strat._lp_variables[VarType.TeamDrivers].items() if v.varValue == 1]
            model_constructors = [c for c,v in strat._lp_variables[VarType.TeamConstructors].items() if v.varValue == 1]

            # Update the unused budget based on the new team selection
            team.unused_budget = strat._lp_variables[VarType.UnusedBudget].value()

            # Set the free transfer flag if we used less than two moves
            bonus_free_transfer = strat._lp_variables[VarType.TeamMoves].value() < 2

            # Re-populate the team with the selected assets
            team.remove_all_assets()
            for d in model_drivers:
                team.add_asset(AssetType.DRIVER, d)
            for c in model_constructors:
                team.add_asset(AssetType.CONSTRUCTOR, c)

    # Create a DataFrame from the results rows and save to Excel
    df_results = pd.DataFrame(rows)
    df_results.to_excel(_FILE_BATCH_RESULTS, index=False)
    logging.info(f"Saved batch results to {_FILE_BATCH_RESULTS}")
