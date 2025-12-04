import pandas as pd
import logging

from common import AssetType, setup_logging
from helpers import load_with_derivations
from linear.strategy_base import VarType
from linear.strategy_budget import StrategyMaxBudget
from linear.strategy_factory import factory_strategy
from races.season import Season, factory_season, Race
from races.team import Team, factory_team_lists

_FILE_BATCH_RESULTS = "outputs/f1_fantasy_results_single.xlsx"

_SEASON = 2025
_TEAM_START_DRIVERS = ["SAI", "HAD", "DOO", "BEA", "TSU"]
_TEAM_START_CONSTRUCTORS = ["MCL", "FER"]
_STARTING_RACE = 1


def get_row_intermediate_results(team: Team, season: Season, race: Race, race_prev: Race, race_num: int, race_points: int, max_moves: int, used_moves: int) -> dict:
    row = {
        "strategy": "strat_test",
        "season": _SEASON,
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
    #logging.info(f"Row results: {row}")
    return row


def run_for_team(team: Team, season: Season, race_num_start: int) -> list:
    # Collection to put all the results rows into
    rows = []

    # Flag to indicate if the next round should have a bonus free transfer
    bonus_free_transfer = False

    # Number of moves used to get to this team
    used_moves = -1

    # Get sorted list of races
    races = sorted([int(r) for r in season.races.keys() if r >= race_num_start])

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
        rows.append(get_row_intermediate_results(team, season, season.races[race_num], race_prev, race_num, race_points, max_moves, used_moves))

    return rows


if __name__ == "__main__":
    setup_logging()

    (df_driver_ppm, df_constructor_ppm, df_driver_pairs) = load_with_derivations(season=_SEASON)
    
    _season = factory_season(
        df_driver_ppm,
        df_constructor_ppm,
        df_driver_pairs,
        _SEASON,
        "PPM Cumulative (3)"
    )

    # This will calculate the unused budget based on starting prices
    _team = factory_team_lists(
        drivers=_TEAM_START_DRIVERS,
        constructors=_TEAM_START_CONSTRUCTORS,
        race=_season.races[_STARTING_RACE],
        total_budget=100.0  # Starting budget
    )
    
    _rows = run_for_team(_team, _season, _STARTING_RACE)

    # Create a DataFrame from the results rows and save to Excel
    df_results = pd.DataFrame(_rows)
    df_results.to_excel(_FILE_BATCH_RESULTS, index=False)
    logging.info(f"Saved batch results to {_FILE_BATCH_RESULTS}")
