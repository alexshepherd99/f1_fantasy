from common import setup_logging
from helpers import load_with_derivations
from races.first_picks import get_starting_combinations
from races.season import factory_race
from races.team import Team, factory_team_row
import logging

_SEASON_YEAR = 2026
_MIN_BUDGET = 99.8


def select_starting_team(season_year=_SEASON_YEAR, min_budget=_MIN_BUDGET) -> Team:
    (df_driver_ppm, df_constructor_ppm, df_driver_pairs) = load_with_derivations(season=season_year)
    
    _race_first = factory_race(
        df_driver_ppm,
        df_constructor_ppm,
        df_driver_pairs,
        1,
    )

    _df_combinations = get_starting_combinations(season_year, 1, min_budget)

    _min_starting_ratio = 999.99
    final_team = None

    for _idx, _row in _df_combinations.iterrows():
        _team = factory_team_row(_row.to_dict(), _race_first)

        _starting_value_d = _team.total_value_drivers(_race_first, _race_first)
        _starting_value_c = _team.total_value_constructors(_race_first)
        _starting_value_tot = _team.total_value(_race_first, _race_first)
        _starting_ratio = _starting_value_d / _starting_value_c

        if _starting_ratio < _min_starting_ratio:
            _min_starting_ratio = _starting_ratio
            logging.info(f"New lowest ratio {_min_starting_ratio:.4f} {_team} Total cost:{_starting_value_tot:.1f}")
            final_team = _team

    return final_team


if __name__ == "__main__":
    setup_logging()
    select_starting_team()
