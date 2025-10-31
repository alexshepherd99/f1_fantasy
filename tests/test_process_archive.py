import pandas as pd
from pandas.testing import assert_frame_equal

from import_data.process_archive import add_points_cumulative


def test_add_points_cumulative():
    df_input_driver = pd.DataFrame(
        columns=["Team", "Race", "Points", "Season"],
        data=[
            ["Team A", 1, 10, 2020],
        ]
    )

    df_actual = add_points_cumulative(df_input_driver, col_asset="Driver")

    assert_frame_equal
