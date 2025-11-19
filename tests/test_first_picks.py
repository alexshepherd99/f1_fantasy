
import pandas as pd
import itertools

from races.first_picks import get_all_combinations


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
