"""Simulate one team race by race through a season, one result row per race."""

from common import AssetType
from linear.strategy_base import StrategyBase
from races.season import Season, Race
from races.team import Team
from simulate.pick import next_free_moves, solve_race


def get_row_intermediate_results(
        strat_name: str,
        team: Team,
        season: Season,
        season_year: int,
        race: Race,
        race_prev: Race,
        race_num: int,
        race_points: int,
        max_moves: int,
        used_moves: int,
        starting_value: float,
        starting_value_d: float,
        starting_value_c: float,
    ) -> dict:
    row = {
        "strategy": strat_name,
        "season": season_year,
        "race": race_num,
        "total_value": team.total_value(race, race_prev),
        "starting_value": starting_value,
        "starting_value_d": starting_value_d,
        "starting_value_c": starting_value_c,
        "points": race_points,
        "total_points": team.total_points,
        "unused_budget": round(team.unused_budget, 1),
        "total_budget": round(float(team.total_budget(season.races[race_num], race_prev)), 1),
        "max_moves": max_moves,
        "used_moves": used_moves,
        "drs_driver": team.drs_driver,
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


def get_strat_display_name(strategy: type[StrategyBase], sub_strat: str = ""):
    if len(sub_strat) > 0:
        return f"{strategy.__name__}:{sub_strat}"
    else:
        return f"{strategy.__name__}"


def run_for_team(strategy: type[StrategyBase], team: Team, season: Season, season_year: int, race_num_start: int, sub_strat: str = "") -> list:
    # Strategy name we'll use for the results data set
    strat_name = get_strat_display_name(strategy, sub_strat)

    # Collection to put all the results rows into
    rows = []

    # Free moves for the next race picked
    max_moves = 2

    # Number of moves used to get to this team
    used_moves = -1

    # Get sorted list of races
    races = sorted([int(r) for r in season.races.keys() if r >= race_num_start])

    # Get starting value, which we record against every row for this season
    starting_value = team.total_value(season.races[race_num_start], season.races[race_num_start])
    starting_value_d = team.total_value_drivers(season.races[race_num_start], season.races[race_num_start])
    starting_value_c = team.total_value_constructors(season.races[race_num_start])

    for race_num in races:
        # Needed for a fallback price when driver is no longer available for selection
        race_prev = season.races[race_num] if race_num == 1 else season.races[race_num - 1]

        # Row values for this race; the start race keeps the team given
        race_max_moves = max_moves
        if race_num > race_num_start:
            pick = solve_race(strategy, team, season.races[race_num], race_prev, season_year, max_moves)

            # Re-populate the team with the pick
            team.unused_budget = pick.unused_budget
            team.remove_all_assets()
            for d in pick.drivers:
                team.add_asset(AssetType.DRIVER, d)
            for c in pick.constructors:
                team.add_asset(AssetType.CONSTRUCTOR, c)
            team.drs_driver = pick.drs_driver

            used_moves = pick.moves_used
            max_moves = next_free_moves(pick.moves_used)

        # Update team points based on the last race
        race_points = team.update_points(season.races[race_num])

        # Create and append a results row for this race selection
        rows.append(
            get_row_intermediate_results(
                strat_name,
                team,
                season,
                season_year,
                season.races[race_num],
                race_prev,
                race_num,
                race_points,
                race_max_moves,
                used_moves,
                starting_value,
                starting_value_d,
                starting_value_c,
            )
        )

    return rows
