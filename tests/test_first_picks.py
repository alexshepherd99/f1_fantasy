
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

	# Selections are held as int8 to keep a season's combinations small
	expected_df = pd.DataFrame(expected_rows, columns=[f"c{i+1}" for i in range(4)], dtype=np.int8)
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


def _patch_tiny_season(monkeypatch, driver_prices, constructor_prices, drivers_per_team=2, constructors_per_team=1):
	"""Stand up a two-constructor season so combinations stay enumerable by hand."""
	import races.first_picks as fp

	class DummyAsset:
		def __init__(self, price):
			self.price = price

	class DummyRace:
		def __init__(self):
			self.drivers = {name: DummyAsset(price) for name, price in driver_prices.items()}
			self.constructors = {name: DummyAsset(price) for name, price in constructor_prices.items()}

	monkeypatch.setattr(fp, "F1_SEASON_CONSTRUCTORS", {2023: len(constructor_prices)})
	monkeypatch.setattr(fp, "DRIVERS_PER_CONSTRUCTOR", len(driver_prices) // len(constructor_prices))
	monkeypatch.setattr(fp, "DRIVERS_PER_TEAM", drivers_per_team)
	monkeypatch.setattr(fp, "CONSTRUCTORS_PER_TEAM", constructors_per_team)
	monkeypatch.setattr(fp, "load_with_derivations", lambda season: (None, None, None))
	monkeypatch.setattr(fp, "factory_race", lambda *args: DummyRace())


def test_get_starting_combinations_replaces_prices_and_filters(monkeypatch):
	# Four drivers priced 10/5/4/3 and two constructors priced 8/2, picking two
	# drivers and one constructor, gives twelve teams valued 9 to 23
	_patch_tiny_season(
		monkeypatch,
		{"D1": 10.0, "D2": 5.0, "D3": 4.0, "D4": 3.0},
		{"C1": 8.0, "C2": 2.0},
	)

	out = get_starting_combinations(2023, 1, 15.0, 21.0)

	# Selected assets carry their price, everything else is NaN
	assert out.loc[1, "D1"] == 10.0
	assert out.loc[1, "D2"] == 5.0
	assert out.loc[1, "C2"] == 2.0
	assert np.isnan(out.loc[1, "D3"])
	assert np.isnan(out.loc[1, "C1"])

	# D1+D2+C2 = 17, D1+D3+C2 = 16, D1+D4+C1 = 21, D2+D3+C1 = 17, D2+D4+C1 = 16.
	# The two teams worth exactly 15 are excluded by the exclusive lower bound,
	# and the team worth exactly 21 is kept by the inclusive upper bound
	assert sorted(out["total_value"]) == [16.0, 16.0, 17.0, 17.0, 21.0]
	assert list(out.index) == [1, 3, 4, 6, 8]


def test_get_starting_combinations_keeps_teams_exactly_on_the_budget(monkeypatch):
	"""A team worth exactly the budget is affordable, whatever float noise says.

	0.1 + 0.2 + 0.3 sums to 0.6000000000000001 in floating point, so without
	rounding this team is priced out of a 0.6 budget it can afford.
	"""
	_patch_tiny_season(
		monkeypatch,
		{"D1": 0.1, "D2": 0.2, "D3": 0.4, "D4": 0.7},
		{"C1": 0.3, "C2": 0.9},
	)

	out = get_starting_combinations(2023, 1, 0.0, 0.6)

	assert out.loc[0, "D1"] == 0.1
	assert out.loc[0, "D2"] == 0.2
	assert out.loc[0, "C1"] == 0.3
	assert out.loc[0, "total_value"] == 0.6


def test_get_starting_combinations_standalone():
	# Just making sure the entire unpatched function gets called by a unit test
	df_combinations = get_starting_combinations(2023, 1, 99.0)
	# 8143 verified against exact integer arithmetic on the 2023 price list;
	# 823 teams are worth exactly 99.0 and 826 exactly 100.0, so the bounds
	# have to fall the right side of both
	assert df_combinations.shape == (8143, 31)
