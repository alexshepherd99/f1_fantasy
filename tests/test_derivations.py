import pandas as pd
import pytest
import numpy as np
from pandas.testing import assert_series_equal

from import_data.derivations import (
    derivation_cum_tot_driver,
    derivation_cum_tot_constructor,
)


def test_derivation_cum_tot_driver():
    df_input = pd.DataFrame(
        columns=["Season", "Race", "Constructor", "Driver", "Points", "Price"],
        data=[
            [2023, 2, "MER", "HAM", 12, 1.2],
            [2023, 1, "MER", "HAM", 11, 1.1],  # out of order to test sorting
            [2023, 3, "MER", "HAM", 13, 1.3],
            [2023, 4, "MER", "HAM", 14, 1.4],
            [2023, 1, "MER", "BOT", 30, 2.0],
            [2023, 2, "MER", "BOT", 30, 4.0],
            [2023, 3, "MER", "BOT", 30, 6.0],
            [2023, 4, "MER", "BOT", 60, 48.0],
            [2023, 1, "RED", "VER", 31, 3.1],
            [2023, 2, "RED", "VER", 32, 3.2],
            [2023, 3, "RED", "VER", 33, 3.3],
            [2023, 4, "RED", "VER", -10, 3.4],
            [2023, 1, "HAA", "BEA", 41, 4.1],
            [2023, 2, "HAA", "BEA", 42, 4.2],
            [2023, 3, "HAA", "BEA", np.nan, np.nan],
            [2023, 4, "HAA", "BEA", np.nan, np.nan],
            [2023, 1, "FER", "BEA", np.nan, np.nan],
            [2023, 2, "FER", "BEA", np.nan, np.nan],
            [2023, 3, "FER", "BEA", 43, 4.3],
            [2023, 4, "FER", "BEA", np.nan, np.nan],
            [2023, 1, "FER", "LEC", 51, 5.1],
            [2023, 2, "FER", "LEC", 52, 5.2],
            [2023, 3, "FER", "LEC", 53, 5.3],
            [2023, 4, "FER", "LEC", 54, 5.4],
            [2024, 1, "FER", "HAM", 111, 11.1],
            [2024, 2, "FER", "HAM", 112, 11.2],
            [2024, 3, "FER", "HAM", 113, 11.3],
            [2024, 4, "FER", "HAM", 114, 11.4],
            [2024, 1, "MER", "BOT", 121, 12.1],
            [2024, 2, "MER", "BOT", 122, 12.2],
            [2024, 3, "MER", "BOT", 123, 12.3],
            [2024, 4, "MER", "BOT", 124, 12.4],
            [2024, 1, "RED", "VER", 131, 13.1],
            [2024, 2, "RED", "VER", 132, 13.2],
            [2024, 3, "RED", "VER", 133, 13.3],
            [2024, 4, "RED", "VER", 134, 13.4],
            [2024, 1, "FER", "LEC", 151, 15.1],
            [2024, 2, "FER", "LEC", 152, 15.2],
            [2024, 3, "FER", "LEC", 153, 15.3],
            [2024, 4, "FER", "LEC", 154, 15.4],
        ]
    )

    df_expected = pd.DataFrame(
        columns=["Season", "Race", "Driver", "Points", "Price", "exp_cum_pts", "exp_cum_prc", "exp_cum_ppm"],
        data=[
            [2023, 1, "HAM", 11, 1.1, 11, 1.1, 10.0],  # updated order, although we'll sort below anyway
            [2023, 2, "HAM", 12, 1.2, 23, 2.3, 10.0],
            [2023, 3, "HAM", 13, 1.3, 36, 3.6, 10.0],
            [2023, 4, "HAM", 14, 1.4, 50, 5.0, 10.0],
            [2023, 1, "BOT", 30, 2.0, 30, 2.0, 15.0],  # different PPM
            [2023, 2, "BOT", 30, 4.0, 60, 6.0, 10.0],
            [2023, 3, "BOT", 30, 6.0, 90, 12.0, 7.5],
            [2023, 4, "BOT", 60, 48.0, 150, 60.0, 2.5],
            [2023, 1, "VER", 31, 3.1, 31, 3.1, 10.0],
            [2023, 2, "VER", 32, 3.2, 63, 6.3, 10.0],
            [2023, 3, "VER", 33, 3.3, 96, 9.6, 10.0],
            [2023, 4, "VER", -10, 3.4, 86, 13.0, 6.6154],  # negative points
            [2023, 1, "BEA", 41, 4.1, 41, 4.1, 10.0],
            [2023, 2, "BEA", 42, 4.2, 83, 8.3, 10.0],
            [2023, 3, "BEA", 43, 4.3, 126, 12.6, 10.0],
            [2023, 4, "BEA", np.nan, np.nan, 126, 12.6, 10.0],
            [2023, 1, "LEC", 51, 5.1, 51, 5.1, 10.0],
            [2023, 2, "LEC", 52, 5.2, 103, 10.3, 10.0],
            [2023, 3, "LEC", 53, 5.3, 156, 15.6, 10.0],
            [2023, 4, "LEC", 54, 5.4, 210, 21.0, 10.0],
            [2024, 1, "HAM", 111, 11.1, 111, 11.1, 10.0],
            [2024, 2, "HAM", 112, 11.2, 223, 22.3, 10.0],
            [2024, 3, "HAM", 113, 11.3, 336, 33.6, 10.0],
            [2024, 4, "HAM", 114, 11.4, 450, 45.0, 10.0],
            [2024, 1, "BOT", 121, 12.1, 121, 12.1, 10.0],
            [2024, 2, "BOT", 122, 12.2, 243, 24.3, 10.0],
            [2024, 3, "BOT", 123, 12.3, 366, 36.6, 10.0],
            [2024, 4, "BOT", 124, 12.4, 490, 49.0, 10.0],
            [2024, 1, "VER", 131, 13.1, 131, 13.1, 10.0],
            [2024, 2, "VER", 132, 13.2, 263, 26.3, 10.0],
            [2024, 3, "VER", 133, 13.3, 396, 39.6, 10.0],
            [2024, 4, "VER", 134, 13.4, 530, 53.0, 10.0],
            [2024, 1, "LEC", 151, 15.1, 151, 15.1, 10.0],
            [2024, 2, "LEC", 152, 15.2, 303, 30.3, 10.0],
            [2024, 3, "LEC", 153, 15.3, 456, 45.6, 10.0],
            [2024, 4, "LEC", 154, 15.4, 610, 61.0, 10.0],
        ]
    )

    df_result = derivation_cum_tot_driver(df_input)

    df_expected = df_expected.sort_values(["Season", "Driver", "Race"], ignore_index=True)

    assert_series_equal(df_expected["exp_cum_pts"], df_result["Points Cumulative"], check_names=False)
    assert_series_equal(df_expected["exp_cum_prc"], df_result["Price Cumulative"], check_names=False)
    assert_series_equal(
        df_expected["exp_cum_ppm"],
        df_result["PPM Cumulative"],
        check_names=False,
        check_exact=False,
        atol=1e-4)


def test_derivation_cum_tot_constructor():
    df_input = pd.DataFrame(
        columns=["Season", "Race", "Constructor", "Points", "Price", "exp_cum_pts", "exp_cum_prc", "exp_cum_ppm"],
        data=[
            [2023, 2, "MER", 12, 1.2, 23, 2.3, 10.0],
            [2023, 1, "MER", 11, 1.1, 11, 1.1, 10.0],  # out of order to test sorting
            [2023, 3, "MER", 13, 1.3, 36, 3.6, 10.0],
            [2023, 4, "MER", 14, 1.4, 50, 5.0, 10.0],
            [2023, 1, "RED", 31, 3.1, 31, 3.1, 10.0],
            [2023, 2, "RED", 32, 3.2, 63, 6.3, 10.0],
            [2023, 3, "RED", 33, 3.3, 96, 9.6, 10.0],
            [2023, 4, "RED", -10, 3.4, 86, 13.0, 6.6154],  # negative points
            [2024, 1, "MER", 30, 2.0, 30, 2.0, 15.0],
            [2024, 2, "MER", 30, 4.0, 60, 6.0, 10.0],
            [2024, 3, "MER", 30, 6.0, 90, 12.0, 7.5],
            [2024, 4, "MER", 60, 48.0, 150, 60.0, 2.5],  # different PPM
            [2024, 1, "ALT", 131, 13.1, 131, 13.1, 10.0],
            [2024, 2, "ALT", 132, 13.2, 263, 26.3, 10.0],
            [2024, 3, "ALT", 133, 13.3, 396, 39.6, 10.0],
            [2024, 4, "ALT", 134, 13.4, 530, 53.0, 10.0],
        ]
    )

    df_result = derivation_cum_tot_constructor(df_input)

    df_expected = df_input.sort_values(["Season", "Constructor", "Race"], ignore_index=True)

    assert_series_equal(df_expected["exp_cum_pts"], df_result["Points Cumulative"], check_names=False)
    assert_series_equal(df_expected["exp_cum_prc"], df_result["Price Cumulative"], check_names=False)
    assert_series_equal(
        df_expected["exp_cum_ppm"],
        df_result["PPM Cumulative"],
        check_names=False,
        check_exact=False,
        atol=1e-4)
