from external_data.get_data import get_races_for_season, get_all_race_results, get_session_laps
from common import setup_logging


if __name__ == "__main__":
	setup_logging()
	#races = get_races_for_season(2025)
	#race_results = get_all_race_results(2025)

	for race_num in get_races_for_season(2025):
		for session_type in ["FP2", "FP3"]:
			get_session_laps(race_num, 2025, session_type)
