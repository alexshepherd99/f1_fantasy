
import pandas as pd
import itertools

from races.first_picks import get_all_combinations
from races.first_picks import set_combination_assets, get_starting_combinations
import numpy as np


def test_get_all_combinations_shape_and_columns():
	df = get_all_combinations(10, 3, "col")
	# 10 choose 3 = 120 rows, 10 columns
	assert df.shape == (120, 10)
	assert list(df.columns) == [f"col{i+1}" for i in range(10)]
	# each row should have exactly 3 ones
	assert all(df.sum(axis=1) == 3)


def test_get_all_combinations_small():
	df = get_all_combinations(4, 2, "c")
	# 4 choose 2 = 6 rows
	assert df.shape == (6, 4)

	expected_rows = []
	for comb in itertools.combinations(range(4), 2):
		row = [0] * 4
		for i in comb:
			row[i] = 1
		expected_rows.append(row)

	expected_df = pd.DataFrame(expected_rows, columns=[f"c{i+1}" for i in range(4)])
	pd.testing.assert_frame_equal(df.reset_index(drop=True), expected_df)


def test_set_combination_assets_renames_and_raises():
	# create a simple 3-column combinations DataFrame
	df = pd.DataFrame([[1, 0, 1], [0, 1, 0]], columns=["a", "b", "c"])

	class DummyAsset:
		def __init__(self, price_old):
			self.price_old = price_old

	# race with 2 drivers and 1 constructor
	class DummyRace:
		def __init__(self):
			self.drivers = {}
			self.constructors = {}

	race = DummyRace()
	race.drivers = {"D1": DummyAsset(10), "D2": DummyAsset(20)}
	race.constructors = {"C1": DummyAsset(30)}

	# should rename columns to drivers + constructors
	out = set_combination_assets(df.copy(), race)
	assert list(out.columns) == ["D1", "D2", "C1"]

	# if shape mismatch -> ValueError
	df2 = pd.DataFrame([[1, 0]], columns=["a", "b"])  # 2 columns, race needs 3
	try:
		set_combination_assets(df2, race)
		assert False, "expected ValueError for shape mismatch"
	except ValueError:
		pass


def test_get_starting_combinations_replaces_prices_and_filters(monkeypatch):
	# Prepare a small combinations DataFrame (3 assets: two drivers, one constructor)
		df_combs = pd.DataFrame([
			[1, 0, 0],  # D1 only
			[0, 1, 0],  # D2 only
			[1, 1, 1],  # D1 + D2 + C1
		], columns=["x", "y", "z"])

		# monkeypatch get_all_team_combinations to return our small frame
		import races.first_picks as fp

		monkeypatch.setattr(fp, "get_all_team_combinations", lambda: df_combs.copy())

		# stub load_with_derivations (not used, but function expects it)
		monkeypatch.setattr(fp, "load_with_derivations", lambda season: (None, None, None))

		# create dummy race object with price_old values
		class DummyAsset:
			def __init__(self, price):
				self.price = price

		class DummyRace:
			def __init__(self):
				self.drivers = {}
				self.constructors = {}

		race = DummyRace()
		race.drivers = {"D1": DummyAsset(10), "D2": DummyAsset(5)}
		race.constructors = {"C1": DummyAsset(8)}

		# monkeypatch factory_race to return our dummy race
		monkeypatch.setattr(fp, "factory_race", lambda a, b, c, race_num, s: race)

		# run function with min_total_value = 5, max_total_value = 20
		out = get_starting_combinations(2023, 1, 5.0, 20.0)

		# verify values replaced correctly
		# rows are converted: 1 -> price_old, 0 -> NaN
		# Use reset_index for stable indexing
		outr = out.reset_index(drop=True)

		# Row 0: D1 selected -> total 10 (allowed, >5)
		assert outr.loc[0, "D1"] == 10
		assert np.isnan(outr.loc[0, "D2"])
		# Row 1: D2 selected -> total 5 (should be excluded because >min_total_value required)
		assert outr.shape[0] == 1


def test_get_starting_combinations_standalone():
	df_combinations = get_starting_combinations(2023, 1, 99.0)
    #assert df_combinations.shape == (15283, 2)
	assert False

