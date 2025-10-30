import pytest
from pandas.testing import assert_frame_equal
import pandas as pd

from import_data.import_history import convert_data_sheet


def test_convert_data_sheet_two_column():
    df_input = pd.DataFrame(
        columns=["Team", "Driver", 1, 2, 3, 4],
        data=[
            ["Team A", "Driver 1", 10, 15, 20, 25],
            ["Team B", "Driver 2", 12, 18, 22, 28],
            ["Team B", "Driver 3", 25, 43, 11, 63],            
        ],
    )

    df_expected = pd.DataFrame(
        columns=["Team", "Driver", "Race", "Points", "Season"],
        data=[
            ["Team A", "Driver 1", 1, 10, 2023],
            ["Team B", "Driver 2", 1, 12, 2023],
            ["Team B", "Driver 3", 1, 25, 2023],
            ["Team A", "Driver 1", 2, 15, 2023],
            ["Team B", "Driver 2", 2, 18, 2023],
            ["Team B", "Driver 3", 2, 43, 2023],
            ["Team A", "Driver 1", 3, 20, 2023],
            ["Team B", "Driver 2", 3, 22, 2023],
            ["Team B", "Driver 3", 3, 11, 2023],
            ["Team A", "Driver 1", 4, 25, 2023],
            ["Team B", "Driver 2", 4, 28, 2023],
            ["Team B", "Driver 3", 4, 63, 2023],
        ]
    )

    df_actual = convert_data_sheet(
        df_input=df_input,
        season=2023,
        id_cols=["Team", "Driver"],
        val_col="Points",
    )

    assert_frame_equal(df_actual, df_expected, check_dtype=False)
