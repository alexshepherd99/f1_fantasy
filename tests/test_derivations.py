import pandas as pd
import pytest
import numpy as np
from pandas.testing import assert_series_equal

from import_data.derivations import (
    derivation_cum_tot_driver,
)


@pytest.fixture
def df_input_data_driver():
    return pd.DataFrame(
        columns=["Season", "Race", "Constructor", "Driver", "Points", "Price", "exp_cum_pts", "exp_cum_prc"],
        data=[
            [2023, 2, "MER", "HAM", 12, 1.2, 23, 2.3],  # intentionally out of order
            [2023, 1, "MER", "HAM", 11, 1.1, 11, 1.1],
            [2023, 3, "MER", "HAM", 13, 1.3, 36, 3.6],
            [2023, 4, "MER", "HAM", 14, 1.4, 50, 5.0],
            [2023, 1, "MER", "BOT", 21, 2.1, 21, 2.1],
            [2023, 2, "MER", "BOT", 22, 2.2, 43, 4.3],
            [2023, 3, "MER", "BOT", 23, 2.3, 66, 6.6],
            [2023, 4, "MER", "BOT", 24, 2.4, 90, 9.0],
            [2023, 1, "RED", "VER", 31, 3.1, 31, 3.1],
            [2023, 2, "RED", "VER", 32, 3.2, 63, 6.3],
            [2023, 3, "RED", "VER", 33, 3.3, 96, 9.6],
            [2023, 4, "RED", "VER", 34, 3.4, 130, 13.0],
            [2023, 1, "HAA", "BEA", 41, 4.1, 41, 4.1],
            [2023, 2, "HAA", "BEA", 42, 4.2, 83, 8.3],
            [2023, 3, "HAA", "BEA", np.nan, np.nan, 83, 8.3],
            [2023, 4, "HAA", "BEA", np.nan, np.nan, 83, 8.3],
            [2023, 1, "FER", "BEA", np.nan, np.nan, 0, 0.0],
            [2023, 2, "FER", "BEA", np.nan, np.nan, 0, 0.0],
            [2023, 3, "FER", "BEA", 43, 4.3, 43, 4.3],
            [2023, 4, "FER", "BEA", 44, 4.4, 87, 8.7],
            [2023, 1, "FER", "LEC", 51, 5.1, 51, 5.1],
            [2023, 2, "FER", "LEC", 52, 5.2, 103, 10.3],
            [2023, 3, "FER", "LEC", 53, 5.3, 156, 15.6],
            [2023, 4, "FER", "LEC", 54, 5.4, 210, 21.0],
            [2024, 1, "FER", "HAM", 111, 11.1, 111, 11.1],
            [2024, 2, "FER", "HAM", 112, 11.2, 223, 22.3],
            [2024, 3, "FER", "HAM", 113, 11.3, 336, 33.6],
            [2024, 4, "FER", "HAM", 114, 11.4, 450, 45.0],
            [2024, 1, "MER", "BOT", 121, 12.1, 121, 12.1],
            [2024, 2, "MER", "BOT", 122, 12.2, 243, 24.3],
            [2024, 3, "MER", "BOT", 123, 12.3, 366, 36.6],
            [2024, 4, "MER", "BOT", 124, 12.4, 490, 49.0],
            [2024, 1, "RED", "VER", 131, 13.1, 131, 13.1],
            [2024, 2, "RED", "VER", 132, 13.2, 263, 26.3],
            [2024, 3, "RED", "VER", 133, 13.3, 396, 39.6],
            [2024, 4, "RED", "VER", 134, 13.4, 530, 53.0],
            [2024, 1, "FER", "LEC", 151, 15.1, 151, 15.1],
            [2024, 2, "FER", "LEC", 152, 15.2, 303, 30.3],
            [2024, 3, "FER", "LEC", 153, 15.3, 456, 45.6],
            [2024, 4, "FER", "LEC", 154, 15.4, 610, 61.0],
        ]
    )


def test_derivation_cum_tot(df_input_data_driver):
    df_result = derivation_cum_tot_driver(df_input_data_driver)

    df_expected = df_input_data_driver.sort_values(
        ["Season", "Constructor", "Driver", "Race"], ignore_index=True
    )

    assert_series_equal(df_expected["exp_cum_pts"], df_result["Points Cumulative"], check_names=False)
    assert_series_equal(df_expected["exp_cum_prc"], df_result["Price Cumulative"], check_names=False)
