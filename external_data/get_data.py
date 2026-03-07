import fastf1
import logging
import pandas as pd

import external_data.fastf1_common
from external_data.fastf1_common import filecache


@filecache
def get_races_for_season(season_year: int) -> list[int]:
	logging.info(f"Loading races for season {season_year}")
	schedule = fastf1.get_event_schedule(season_year, include_testing=False)
	races = [int(r) for r in schedule["RoundNumber"].unique()]
	logging.info(f"Loaded races for season {season_year} : {races}")
	return races


@filecache
def get_race_results(season_year: int, race_num: int) -> pd.DataFrame:
	logging.info(f"Processing race results for season {season_year}, race {race_num}")
	schedule = fastf1.get_event_schedule(season_year, include_testing=False)
	event = schedule[schedule["RoundNumber"] == race_num].iloc[0]

	try:
		race = event.get_session("R")
		race.load()
		results = race.results
		results = results[["Abbreviation", "Status", "Position", "ClassifiedPosition", "GridPosition", "Points"]].copy()
		results["Season"] = season_year
		results["Race"] = race_num
		logging.info(f"Processed race results for season {season_year}, race {race_num}, shape {results.shape}")
		return results
	except fastf1.SessionNotAvailableError:
		logging.warning(f"Could not find race results for season {season_year}, race {race_num}")
		return pd.DataFrame(columns=["Season", "Race", "Abbreviation", "Status", "Position", "ClassifiedPosition", "GridPosition", "Points"])


def get_all_race_results(season_year: int) -> pd.DataFrame:
	df_collated = pd.DataFrame()
	for race_num in get_races_for_season(season_year=season_year):
		df = get_race_results(season_year=season_year, race_num=race_num)
		df_collated = pd.concat([df_collated, df], ignore_index=True)
	
	return df_collated


@filecache
def get_session_laps(season_year: int, race_num: int, session_type: str) -> pd.DataFrame:
	logging.info(f"Processing session laps for season {season_year}, race {race_num}, session {session_type}")
	schedule = fastf1.get_event_schedule(season_year, include_testing=False)
	event = schedule[schedule["RoundNumber"] == race_num].iloc[0]

	try:
		session = event.get_session(session_type)
	except ValueError:
		logging.warning(f"Could not find session for season {season_year}, race {race_num}, session {session_type}")
		return pd.DataFrame(columns=["Season", "Race", "SessionType"])
			
	session.load()
	session_laps = session.laps
	session_laps = session_laps[
		[
			"Driver",
			"LapTime",
			"LapNumber",
			"Stint",
			"PitOutTime",
			"PitInTime",
			"Compound",
			"TyreLife",
			"FreshTyre",
		]
	].copy()
	session_laps["Season"] = season_year
	session_laps["Race"] = race_num
	session_laps["SessionType"] = session_type
	logging.info(f"Processed session laps for season {season_year}, race {race_num}, session {session_type}, shape {session_laps.shape}")
	return session_laps
