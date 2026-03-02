import pandas as pd
import fastf1
import logging
import os
import pandas as pd

from common import setup_logging, setup_fastf1_cache

RACES_RANGE = range(2025, 2026)

def get_fp2_laps(race_num: int, season_year: int, session_type: str):
	schedule = fastf1.get_event_schedule(season_year, include_testing=False)
	event = schedule[schedule["RoundNumber"] == race_num].iloc[0]
	session = event.get_session(session_type)
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
	]
	return session_laps


def analyze_driver_performance(df, session_type: str):
	"""
	Process lap data to produce one row per driver with comprehensive performance metrics.
	
	Args:
		df: DataFrame with columns: Driver, LapTime, LapNumber, Stint, PitOutTime, 
			PitInTime, Compound, TyreLife, FreshTyre. Each row represents a lap.
		session_type: String representing the session type (e.g., "FP1", "FP2", "FP3").
			Used as a prefix for all output column names.
	
	Returns:
		DataFrame with one row per driver containing:
		- {session_type}_TotalLapCount: Total number of laps (no exclusions)
		- {session_type}_MinLapTime: Minimum lap time achieved (no exclusions)
		- {session_type}_MaxLapsInStint: Highest number of laps in a single stint (no exclusions)
		- {session_type}_FastestTimeInMaxStint: Fastest time from the stint with most laps (filtered)
		- {session_type}_MeanTimeInMaxStint: Mean time from the stint with most laps (filtered)
		- {session_type}_LapTimeDifferenceInMaxStint: Difference between fastest and slowest (filtered)
		- Plus rank columns for each of the above metrics
		
		Filtering rules for subsequent calculations:
		- Exclude laps with non-null PitOutTime or PitInTime
		- Exclude laps with time > 107% of fastest overall lap time
	"""
	# Create a copy to preserve original data
	df = df.copy()
	
	# Step 1: Calculate metrics without exclusions
	total_lap_count = df.groupby("Driver").size().reset_index(name="TotalLapCount")
	min_lap_time = df.groupby("Driver")["LapTime"].min().reset_index(name="MinLapTime")
	
	# Max laps in a single stint (no exclusions)
	max_laps_in_stint = (
		df.groupby(["Driver", "Stint"]).size()
		.reset_index(name="LapCountInStint")
		.groupby("Driver")["LapCountInStint"]
		.max()
		.reset_index(name="MaxLapsInStint")
	)
	
	# Step 2: Apply filters for subsequent calculations
	# Find the fastest overall lap time across all drivers
	fastest_overall_lap = df["LapTime"].min()
	threshold_time = fastest_overall_lap * 1.07
	
	# Filter: exclude pit laps and outliers
	df_filtered = df[
		(df["PitOutTime"].isna()) & 
		(df["PitInTime"].isna()) & 
		(df["LapTime"] <= threshold_time)
	].copy()
	
	# Step 3: For each driver, find the stint with the most laps in filtered data
	# Count laps per stint in filtered data
	stint_lap_counts = (
		df_filtered.groupby(["Driver", "Stint"]).size()
		.reset_index(name="LapCountInStint")
	)
	
	# Find the stint with max laps for each driver
	max_stint_per_driver = (
		stint_lap_counts.sort_values(["Driver", "LapCountInStint"], ascending=[True, False])
		.drop_duplicates(subset="Driver", keep="first")
	)[["Driver", "Stint"]].copy()
	max_stint_per_driver.rename(columns={"Stint": "MaxLapsStint"}, inplace=True)
	
	# Step 4: Calculate metrics from the stint with most laps
	df_filtered_with_stint = df_filtered.merge(
		max_stint_per_driver, 
		on="Driver",
		how="left"
	)
	
	# Only keep rows from the stint with max laps
	df_max_stint = df_filtered_with_stint[
		df_filtered_with_stint["Stint"] == df_filtered_with_stint["MaxLapsStint"]
	]
	
	# Calculate metrics for the max stint
	max_stint_metrics = df_max_stint.groupby("Driver").agg({
		"LapTime": ["min", "mean"]
	}).reset_index()
	max_stint_metrics.columns = ["Driver", "FastestTimeInMaxStint", "MeanTimeInMaxStint"]
	
	# Calculate lap time difference (fastest - slowest) in max stint
	def get_lap_time_range(group):
		return group["LapTime"].max() - group["LapTime"].min()
	
	lap_diff = (
		df_max_stint.groupby("Driver")
		.apply(get_lap_time_range, include_groups=False)
		.reset_index(name="LapTimeDifferenceInMaxStint")
	)
	
	# Step 5: Merge all metrics together
	result = total_lap_count.merge(min_lap_time, on="Driver")
	result = result.merge(max_laps_in_stint, on="Driver")
	result = result.merge(max_stint_metrics, on="Driver", how="left")
	result = result.merge(lap_diff, on="Driver", how="left")
	
	# Step 6: Add rank columns for each metric
	result["TotalLapCount_rank"] = result["TotalLapCount"].rank(method="min", ascending=False).astype("Int64")
	result["MinLapTime_rank"] = result["MinLapTime"].rank(method="min", ascending=True).astype("Int64")
	result["MaxLapsInStint_rank"] = result["MaxLapsInStint"].rank(method="min", ascending=False).astype("Int64")
	result["FastestTimeInMaxStint_rank"] = result["FastestTimeInMaxStint"].rank(method="min", ascending=True).astype("Int64")
	result["MeanTimeInMaxStint_rank"] = result["MeanTimeInMaxStint"].rank(method="min", ascending=True).astype("Int64")
	result["LapTimeDifferenceInMaxStint_rank"] = result["LapTimeDifferenceInMaxStint"].rank(method="min", ascending=True).astype("Int64")
	
	# Step 7: Prefix all column names (except Driver) with session_type
	columns_to_prefix = [col for col in result.columns if col != "Driver"]
	rename_mapping = {col: f"{session_type}_{col}" for col in columns_to_prefix}
	result = result.rename(columns=rename_mapping)
	
	# Sort by Driver for consistency
	result = result.sort_values("Driver").reset_index(drop=True)
	
	return result


def do_all(race_num: int, season_year: int, session_type: str):
	logging.info(f"Processing {session_type} stints for season {season_year}, race {race_num}")
	try:
		fp2_laps = get_fp2_laps(race_num, season_year, session_type)
		perf = analyze_driver_performance(fp2_laps, session_type)
		perf["Season"] = season_year
		perf["Race"] = race_num
		return perf
	except Exception as e:
		logging.error(f"Error processing race {race_num} in season {season_year}: {e}")
		return pd.DataFrame(
			columns=[
				"Driver",
				"Season",
				"Race",
			]
		)


def get_races_for_season(season_year: int):
	#return [1,2,3]
	schedule = fastf1.get_event_schedule(season_year, include_testing=False)
	races = [int(r) for r in schedule["RoundNumber"].unique()]
	return races


def get_best_stint_for_all() -> pd.DataFrame:
	"""Gather best FP2 stint info for every race in the range.

	The returned dataframe mirrors the output of ``do_all``/``filter_and_enrich``
	and therefore includes the usual pacing metrics along with the tyre
	compound and ``FreshTyre`` flag that was added per the latest update.
	"""
	cache_file = "outputs/all_stint_results.parquet"
	
	# Check if cache exists
	if os.path.exists(cache_file):
		logging.info(f"Loading stint results from cache: {cache_file}")
		return pd.read_parquet(cache_file)

	df_collated = pd.DataFrame()
	for season_year in RACES_RANGE:
		for race_num in get_races_for_season(season_year):
			df_fp1 = do_all(race_num, season_year, "FP1")
			df_fp2 = do_all(race_num, season_year, "FP2")
			df_fp3 = do_all(race_num, season_year, "FP3")
			df_fpx = df_fp1.merge(df_fp2, on=["Season", "Race", "Driver"], how="outer")
			df_fpx = df_fpx.merge(df_fp3, on=["Season", "Race", "Driver"], how="outer")
			df_collated = pd.concat([df_collated, df_fpx], ignore_index=True)

	# Save to cache
	logging.info(f"Saving stint results to cache: {cache_file}")
	df_collated.to_parquet(cache_file)

	return df_collated


def get_race_results(race_num: int, season_year: int):
	logging.info(f"Processing race results for season {season_year}, race {race_num}")
	schedule = fastf1.get_event_schedule(season_year, include_testing=False)
	event = schedule[schedule["RoundNumber"] == race_num].iloc[0]
	race = event.get_session("R")
	race.load()
	results = race.results
	results = results[["Abbreviation", "Status", "Position", "ClassifiedPosition", "GridPosition", "Points"]].copy()
	results["Season"] = season_year
	results["Race"] = race_num
	return results


def get_all_race_results() -> pd.DataFrame:
	cache_file = "outputs/all_race_results.parquet"
	
	# Check if cache exists
	if os.path.exists(cache_file):
		logging.info(f"Loading race results from cache: {cache_file}")
		return pd.read_parquet(cache_file)
	
	logging.info("Cache not found, computing race results...")
	df_collated = pd.DataFrame()
	for season_year in RACES_RANGE:
		for race_num in get_races_for_season(season_year):
			df = get_race_results(race_num, season_year)
			df_collated = pd.concat([df_collated, df], ignore_index=True)
	
	# Save to cache
	logging.info(f"Saving race results to cache: {cache_file}")
	df_collated.to_parquet(cache_file)
	
	return df_collated


def get_and_merge():
	r = get_all_race_results()
	r = calculate_reliability_ratio(r)
	r = compute_aggregate_points(r)
	s = get_best_stint_for_all()
	j = r.merge(
		s,
		how="left",
		left_on=["Season", "Race", "Abbreviation"],
		right_on=["Season", "Race", "Driver"]
	)
	j = calc_final_score(j)
	return j


def calc_final_score(df):
	df = df.copy()
	df["FinalTotal"] = None

	df.loc[df["FP3_MinLapTime_rank"].notna(), "FinalTotal"] = (
		df["FP1_MinLapTime_rank"].fillna(0) +
		df["FP2_MinLapTime_rank"].fillna(0) +
		df["FP3_MinLapTime_rank"].fillna(0) +
		df["AggregatePointsRank"].fillna(0)
	)

	df.loc[df["FP3_MinLapTime_rank"].isna(), "FinalTotal"] = (
		df["FP1_MinLapTime_rank"].fillna(0) +
		df["AggregatePointsRank"].fillna(0)
	)

	return df


def calculate_reliability_ratio(df):
	"""
	Add ReliabilityRatio and ReliabilityRatioRank columns to a race results dataframe.
	
	Args:
		df: DataFrame with columns: Season, Race, Abbreviation, Status, Position, 
			ClassifiedPosition, GridPosition
	
	Returns:
		DataFrame with two additional columns:
		- ReliabilityRatio: Decimal 0-1 representing the ratio of completed races to total races
		  for that driver up to that point in the season. 1.0 for the first race.
		- ReliabilityRatioRank: Rank of the ReliabilityRatio within each race (1 is best)
	
	A completed race is one where Status is "Finished" or contains "Lap".
	"""
	df = df.copy()
	
	# Sort by Season, Race to ensure chronological ordering
	df = df.sort_values(["Season", "Race"]).reset_index(drop=True)
	
	# Initialize the ReliabilityRatio column
	df["ReliabilityRatio"] = 0.0
	
	# For each unique (Season, Abbreviation) combination, calculate reliability ratio
	for (season, abbreviation), group_indices in df.groupby(["Season", "Abbreviation"]).groups.items():
		# Get the races for this driver/season in chronological order
		group_df = df.loc[group_indices].sort_values("Race")
		races = group_df["Race"].values
		
		for i, race in enumerate(races):
			if i == 0:
				# First race gets 1.0
				df.loc[group_indices[i], "ReliabilityRatio"] = 1.0
			else:
				# For subsequent races, calculate ratio based on previous races
				previous_races = group_df.iloc[:i]
				
				# A race is completed if Status is "Finished" or contains "Lap"
				completed = previous_races["Status"].apply(
					lambda x: x == "Finished" or "Lap" in str(x)
				).sum()
				
				total = len(previous_races)
				ratio = completed / total if total > 0 else 0.0
				
				# Find the actual index in the original df for this row
				mask = (df["Season"] == season) & (df["Abbreviation"] == abbreviation) & (df["Race"] == race)
				df.loc[mask, "ReliabilityRatio"] = ratio
	
	# Add ranking: rank within each race (higher ratio = lower rank number = better)
	df["ReliabilityRatioRank"] = df.groupby(["Season", "Race"])["ReliabilityRatio"].rank(
		method="min", ascending=False
	).astype("Int64")
	
	return df.sort_values(["Season", "Race"]).reset_index(drop=True)


def compute_aggregate_points(df: pd.DataFrame) -> pd.DataFrame:
		"""
		Add AggregatePoints and AggregatePointsRank columns to df.

		- AggregatePoints: sum of previous Points values for the same
			driver (`Abbreviation`) within the same `Season`. The current row's
			Points is excluded. Missing `Points` values are treated as 0 for aggregation.

		- AggregatePointsRank: dense rank of `AggregatePoints` within each
			(`Season`, `Race`) group where 1 is best (highest AggregatePoints).
			Missing AggregatePoints values rank last.
		"""
		df = df.copy()

		# Ensure chronological order so previous races are correctly accumulated
		df = df.sort_values(["Season", "Race"]).reset_index(drop=True)

		df["Points"] = pd.to_numeric(df["Points"], errors="coerce")  # Convert to numeric, coercing errors to NaN
		df["ClassifiedPosition"] = pd.to_numeric(df["ClassifiedPosition"], errors="coerce")  # Convert to numeric, coercing errors to NaN

		# Compute AggregatePosition: cumulative sum of previous ClassifiedPosition
		# Treat NaN as 20 (last place) when summing previous ClassifiedPosition values
		df["AggregatePoints"] = (
				df.groupby(["Season", "Abbreviation"])['Points']
				.transform(lambda x: x.fillna(0).cumsum() - x.fillna(0))
		)

		# Compute AggregatePointsRank per race. Fill NaN with a large value so
		# that drivers without an AggregatePoints value rank last within the race.
		df["AggregatePointsRank"] = (
				df.groupby(["Season", "Race"])["AggregatePoints"]
				.transform(lambda x: x.fillna(1e9).rank(method="dense", ascending=False))
				.astype("Int64")
		)

		return df


if __name__ == "__main__":
	setup_logging()
	setup_fastf1_cache()
	j = get_and_merge()
	j.to_csv("outputs/collated_data.csv", index=False)

	print(j.sample(2))

	#for s in RACES_RANGE:
	#	print(f"\n=== Correlations for season {s} ===")
	#	season_data = j[j["Season"] == s]
	#	print(season_data[["FinalTotal", "FP2_MinLapTime_rank", "FP3_MinLapTime_rank", "ReliabilityRatioRank", "AggregatePointsRank", "ClassifiedPosition"]].corr(method="pearson"))

	print(f"\n=== Correlations for all seasons (Total) ===")
	print(j[["FinalTotal", "FP1_MinLapTime_rank", "FP2_MinLapTime_rank", "FP3_MinLapTime_rank", "ReliabilityRatioRank", "AggregatePointsRank", "ClassifiedPosition"]].corr(method="pearson"))

	df_no_sprints = j[j["FP3_MinLapTime_rank"].notna()]
	print(f"\n=== Correlations for all seasons (No Sprints) ===")
	print(df_no_sprints[["FinalTotal", "FP1_MinLapTime_rank", "FP2_MinLapTime_rank", "FP3_MinLapTime_rank","ReliabilityRatioRank", "AggregatePointsRank", "ClassifiedPosition"]].corr(method="pearson"))	

	df_no_sprints = j[j["FP3_MinLapTime_rank"].isna()]
	print(f"\n=== Correlations for all seasons (Sprints) ===")
	print(df_no_sprints[["FinalTotal", "FP1_MinLapTime_rank", "ReliabilityRatioRank", "ClassifiedPosition"]].corr(method="pearson"))	
	