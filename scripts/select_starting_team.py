from common import setup_logging
from helpers import load_with_derivations
from races.first_picks import get_starting_combinations
from races.season import factory_race
from races.team import factory_team_row
from scripts.run_multiple_teams import _FILE_BATCH_RESULTS_PARQET, ALL_STRATEGIES, get_starting_key, open_batch_results_file
import logging

_SEASON_YEAR = 2026
_MIN_BUDGET = 99.9


if __name__ == "__main__":
    setup_logging()

    (df_driver_ppm, df_constructor_ppm, df_driver_pairs) = load_with_derivations(season=_SEASON_YEAR)
    
    _race_first = factory_race(
        df_driver_ppm,
        df_constructor_ppm,
        df_driver_pairs,
        1,
    )

    _df_combinations = get_starting_combinations(_SEASON_YEAR, 1, _MIN_BUDGET)
    _df_batch_results = open_batch_results_file(_FILE_BATCH_RESULTS_PARQET)

    _min_starting_ratio = 999.99

    for _idx, _row in _df_combinations.iterrows():
        _team = factory_team_row(_row.to_dict(), _race_first)

        _starting_value_d = _team.total_value_drivers(_race_first, _race_first)
        _starting_value_c = _team.total_value_constructors(_race_first)
        _starting_value_tot = _team.total_value(_race_first, _race_first)
        _starting_ratio = _starting_value_d / _starting_value_c

        if _starting_ratio < _min_starting_ratio:
            _min_starting_ratio = _starting_ratio
            logging.info(f"New lowest ratio {_min_starting_ratio:.4f} {_team} Total cost:{_starting_value_tot:.1f}")

            for _strat in ALL_STRATEGIES:
                _sim_key = get_starting_key(_strat.__name__, _SEASON_YEAR, _team)
                _df_filtered = _df_batch_results[_df_batch_results["sim_key"] == _sim_key]
                if len(_df_filtered.index) > 0:
                    _batch_row = _df_filtered.iloc[0]
                    logging.info(f"{_strat.__name__} : {_batch_row['total_points']}")

