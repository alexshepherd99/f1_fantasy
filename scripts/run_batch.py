import os
import pandas as pd
import logging

from common import AssetType, setup_logging
from helpers import load_with_derivations
from linear.strategy_base import VarType
from linear.strategy_budget import StrategyMaxBudget
from linear.strategy_factory import factory_strategy
from races.season import factory_season, Race
from races.team import Team, factory_team_lists

_FILE_BATCH_RESULTS = "outputs/f1_fantasy_batch_results.xlsx"


def load_batch_results(filename:str = _FILE_BATCH_RESULTS) -> pd.DataFrame:
	if not os.path.exists(filename):
		return pd.DataFrame()

	# Let pandas raise any exceptions encountered while reading a present file
	# (e.g. corrupt file). This function's contract only requires returning
	# an empty DataFrame when the file does not exist.
	return pd.read_excel(filename)


def get_row_results(team: Team, race: Race, race_prev: Race, race_num: int, race_points: int, max_moves: int, used_moves: int) -> dict:
    row = {
        "strategy": "strat_test",
        "season": 2025,
        "race": race_num,
        "drivers": sorted(team.assets[AssetType.DRIVER]),
        "constructors": sorted(team.assets[AssetType.CONSTRUCTOR]),
        "total_value": team.total_value(race, race_prev),
        "points": race_points,
        "total_points": team.total_points,
        "unused_budget": round(team.unused_budget, 1),
        "total_budget": round(float(team.total_budget(season.races[race_num], race_prev)), 1),
        "max_moves": max_moves,
        "used_moves": used_moves,
    }
    drivers = sorted(team.assets[AssetType.DRIVER])
    for i in range(0, len(drivers)):
        row[f"D{i+1}"] = drivers[i]
        row[f"D{i+1}_val"] = race.drivers[drivers[i]].price
        row[f"D{i+1}_pts"] = race.drivers[drivers[i]].points
    constructors = sorted(team.assets[AssetType.CONSTRUCTOR])
    for i in range(0, len(constructors)):
        row[f"C{i+1}"] = constructors[i]
        row[f"C{i+1}_val"] = race.constructors[constructors[i]].price
        row[f"C{i+1}_pts"] = race.constructors[constructors[i]].points
    logging.info(f"Row results: {row}")
    return row


if __name__ == "__main__":
    setup_logging()

    (df_driver_ppm, df_constructor_ppm, df_driver_pairs) = load_with_derivations(season=2025)
    
    season = factory_season(
        df_driver_ppm,
        df_constructor_ppm,
        df_driver_pairs,
        2025,
        "PPM Cumulative (3)"
    )

    race_1 = season.races[1]
	
    team_start_drivers = ["SAI", "HAD", "DOO", "BEA", "TSU"]
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

    # Number of moves used to get to this team
    used_moves = -1

    # Get sorted list of races
    races = sorted([int(r) for r in season.races.keys()])
    max_race_num = max(races)

    for race_num in races:
        # Do we have a bonus free transfer from the previous race?
        max_moves = 3 if bonus_free_transfer else 2

        race_prev = season.races[race_num] if race_num == 1 else season.races[race_num - 1]
        strat = factory_strategy(season.races[race_num], race_prev, team, StrategyMaxBudget, max_moves=max_moves)

        model = strat.execute()

        # Extract selected assets from the LP model
        model_drivers = [d for d,v in strat._lp_variables[VarType.TeamDrivers].items() if v.varValue == 1]
        model_constructors = [c for c,v in strat._lp_variables[VarType.TeamConstructors].items() if v.varValue == 1]

        # Update the unused budget based on the new team selection
        team.unused_budget = strat._lp_variables[VarType.UnusedBudget].value()

        # Set the free transfer flag if we used less than two moves
        bonus_free_transfer = strat._lp_variables[VarType.TeamMoves].value() < 2

        # Update the used moves for the next iteration
        used_moves = int(strat._lp_variables[VarType.TeamMoves].value())

        # Re-populate the team with the selected assets
        team.remove_all_assets()
        for d in model_drivers:
            team.add_asset(AssetType.DRIVER, d)
        for c in model_constructors:
            team.add_asset(AssetType.CONSTRUCTOR, c)

        # Update team points based on the last race
        race_points = team.update_points(season.races[race_num])

        # Create and append a results row for this race selection
        rows.append(get_row_results(team, season.races[race_num], race_prev, race_num, race_points, max_moves, used_moves))

    # Create a DataFrame from the results rows and save to Excel
    df_results = pd.DataFrame(rows)
    df_results.to_excel(_FILE_BATCH_RESULTS, index=False)
    logging.info(f"Saved batch results to {_FILE_BATCH_RESULTS}")
