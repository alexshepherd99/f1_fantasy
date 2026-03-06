from external_data.get_data import get_races_for_season, get_all_race_results, get_session_laps
from external_data.process_data import get_practice_performance, get_rolling_prev_points
from external_data.fastf1_common import setup_fastf1_cache
from common import setup_logging


if __name__ == "__main__":
    setup_logging()
    setup_fastf1_cache()

    #races = get_races_for_season(season_year=2025)
    race_results = get_all_race_results(season_year=2025)

    #for race_num in get_races_for_season(season_year=2025):
    #	for session_type in ["FP2", "FP3"]:
    #		l = get_session_laps(season_year=2025, race_num=race_num, session_type=session_type)
    #		del l
    	
    # get_session_laps(season_year=2025, race_num=1, session_type="FP2")

    df = get_rolling_prev_points(race_results, 1)
