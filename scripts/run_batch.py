import os
import pandas as pd

from common import setup_logging

_FILE_BATCH_RESULTS = "outputs/f1_fantasy_batch_results.xlsx"


def load_batch_results(filename:str = _FILE_BATCH_RESULTS) -> pd.DataFrame:
	if not os.path.exists(filename):
		return pd.DataFrame(
			columns=[
				"season",
                "race",
				"drivers",
				"constructors",
				"total_points",
				"unused_budget",
            ]
        )

	# Let pandas raise any exceptions encountered while reading a present file
	# (e.g. corrupt file). This function's contract only requires returning
	# an empty DataFrame when the file does not exist.
	return pd.read_excel(filename)



if __name__ == "__main__":
    setup_logging()


