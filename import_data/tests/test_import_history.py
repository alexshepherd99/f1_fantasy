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
        columns=["Season", "Race", "Team", "Driver", "Points"],
        data=[
            [2023, 1, "Team A", "Driver 1", 10],
            [2023, 2, "Team A", "Driver 1", 15],
            [2023, 3, "Team A", "Driver 1", 20],
            [2023, 4, "Team A", "Driver 1", 25],
            [2023, 1, "Team B", "Driver 2", 12],
            [2023, 2, "Team B", "Driver 2", 18],
            [2023, 3, "Team B", "Driver 2", 22],
            [2023, 4, "Team B", "Driver 2", 28],
            [2023, 1, "Team B", "Driver 3", 25],
            [2023, 2, "Team B", "Driver 3", 43],
            [2023, 3, "Team B", "Driver 3", 11],
            [2023, 4, "Team B", "Driver 3", 63],
        ]
    )

    df_actual = convert_data_sheet(
        df_input=df_input,
        season=2023,
        id_cols=["Team", "Driver"],
        val_col="Points",
    )

    assert_frame_equal(df_actual, df_expected)
