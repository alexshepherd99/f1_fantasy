import logging
from pulp.constants import LpStatusOptimal

from common import setup_logging
from linear.strategy_base import VarType
from races.team import factory_team_lists
from helpers import load_with_derivations
from races.season import factory_season
from linear.strategy_factory import factory_strategy
from linear.strategy_odds import StrategyBettingOdds


TEAM_START_DRIVERS = ["BOR@KCK", "BOT@CAD", "PER@CAD", "COL@ALP", "LIN@VRB"]
TEAM_START_CONSTRUCTORS = ["CAD", "KCK"]


def select_odds_start_for_season(season_year: int):
    (df_driver_ppm, df_constructor_ppm, df_driver_pairs) = load_with_derivations(season=season_year)
    
    season = factory_season(
        df_driver_ppm,
        df_constructor_ppm,
        df_driver_pairs,
        season_year,
    )
    
    team = factory_team_lists(
        drivers=TEAM_START_DRIVERS,
        constructors=TEAM_START_CONSTRUCTORS,
        race=season.races[1],
    )

    team_value = team.total_value(season.races[1], season.races[1])
    team.unused_budget = 100.0 - team_value
    logging.info(team_value)
    logging.info(team.unused_budget)

    strat = factory_strategy(
        season.races[1],
        season.races[1],
        team,
        StrategyBettingOdds,
        max_moves=10,
        season_year=season_year
    )

    model = strat.execute()

    # If model failed, we need to barf - it should never be impossible to solve
    if model.status != LpStatusOptimal:
        logging.error(f"LP model returned {model.status}")
        logging.error([[d,v.varValue] for d,v in strat._lp_variables[VarType.TeamDrivers].items()])
        logging.error([[d,v.varValue] for d,v in strat._lp_variables[VarType.TeamConstructors].items()])
        raise RuntimeError()

    # Extract selected assets from the LP model
    model_drivers = [d for d,v in strat._lp_variables[VarType.TeamDrivers].items() if v.varValue == 1]
    model_constructors = [c for c,v in strat._lp_variables[VarType.TeamConstructors].items() if v.varValue == 1]

    logging.info(model_drivers)
    logging.info(model_constructors)
    logging.info(strat._lp_variables[VarType.UnusedBudget].value())
    logging.info(strat._lp_variables[VarType.Concentration].value())


if __name__ == "__main__":
    setup_logging()

    select_odds_start_for_season(2026)
