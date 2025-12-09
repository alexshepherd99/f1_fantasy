import pandas as pd
import numpy as np
from pandas.testing import assert_frame_equal, assert_series_equal

from common import AssetType
from import_data.derivations import (
    derivation_cum_tot_driver,
    derivation_cum_tot_constructor,
    get_race_driver_constructor_pairs,
)
from scripts.check_run_ppm import load_all_archives_add_derived

_FILE_EXPECTED_RESULTS = "data/test_expected_values.xlsx"


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
            [2023, 3, "RED", "VER", -10, 3.3],
            [2023, 4, "RED", "VER", 33, 3.4],
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
        columns=["Season", "Race", "Driver", "Points", "Price", "exp_cum_pts", "exp_cum_prc", "exp_cum_ppm", "exp_cum_p2pm"],
        data=[
            [2023, 1, "HAM", 11, 1.1, 0, np.nan, np.nan, np.nan],  # updated order, although we'll sort below anyway
            [2023, 2, "HAM", 12, 1.2, 11, 1.1, 10.0, 110.0],
            [2023, 3, "HAM", 13, 1.3, 23, 2.3, 10.0, 230.0],
            [2023, 4, "HAM", 14, 1.4, 36, 3.6, 10.0, 360.0],
            [2023, 1, "BOT", 30, 2.0, 0, np.nan, np.nan, np.nan],  # different PPM
            [2023, 2, "BOT", 30, 4.0, 30, 2.0, 15.0, 450.0],
            [2023, 3, "BOT", 30, 4.0, 60, 6.0, 10.0, 600.0],
            [2023, 4, "BOT", 60, 6.0, 90, 12.0, 7.5, 675.0],
            [2023, 1, "VER", 31, 3.1, 0, np.nan, np.nan, np.nan],
            [2023, 2, "VER", 32, 3.2, 31, 3.1, 10.0, 310.0],
            [2023, 3, "VER", -10, 3.3, 63, 6.3, 10.0, 630.0],  
            [2023, 4, "VER", 33, 3.4, 53, 9.6, 5.5208, 292.6042],  # negative points previous race
            [2023, 1, "BEA", 41, 4.1, 0, np.nan, np.nan, np.nan],
            [2023, 2, "BEA", 42, 4.2, 41, 4.1, 10.0, 410.0],
            [2023, 3, "BEA", 43, 4.3, 83, 8.3, 10.0, 830.0],
            [2023, 4, "BEA", np.nan, np.nan, 126, 12.6, 10.0, 1260.0],
            [2023, 1, "LEC", 51, 5.1, 0, np.nan, np.nan, np.nan],
            [2023, 2, "LEC", 52, 5.2, 51, 5.1, 10.0, 510.0],
            [2023, 3, "LEC", 53, 5.3, 103, 10.3, 10.0, 1030.0],
            [2023, 4, "LEC", 54, 5.4, 156, 15.6, 10.0, 1560.0],
            [2024, 1, "HAM", 111, 11.1, 0, np.nan, np.nan, np.nan],
            [2024, 2, "HAM", 112, 11.2, 111, 11.1, 10.0, 1110.0],
            [2024, 3, "HAM", 113, 11.3, 223, 22.3, 10.0, 2230.0],
            [2024, 4, "HAM", 114, 11.4, 336, 33.6, 10.0, 3360.0],
            [2024, 1, "BOT", 121, 12.1, 0, np.nan, np.nan, np.nan],
            [2024, 2, "BOT", 122, 12.2, 121, 12.1, 10.0, 1210.0],
            [2024, 3, "BOT", 123, 12.3, 243, 24.3, 10.0, 2430.0],
            [2024, 4, "BOT", 124, 12.4, 366, 36.6, 10.0, 3660.0],
            [2024, 1, "VER", 131, 13.1, 0, np.nan, np.nan, np.nan],
            [2024, 2, "VER", 132, 13.2, 131, 13.1, 10.0, 1310.0],
            [2024, 3, "VER", 133, 13.3, 263, 26.3, 10.0, 2630.0],
            [2024, 4, "VER", 134, 13.4, 396, 39.6, 10.0, 3960.0],
            [2024, 1, "LEC", 151, 15.1, 0, np.nan, np.nan, np.nan],
            [2024, 2, "LEC", 152, 15.2, 151, 15.1, 10.0, 1510.0],
            [2024, 3, "LEC", 153, 15.3, 303, 30.3, 10.0, 3030.0],
            [2024, 4, "LEC", 154, 15.4, 456, 45.6, 10.0, 4560.0],
        ]
    )

    df_result = derivation_cum_tot_driver(df_input)

    expected_cols = ["Season", "Race", "Driver", "Points", "Price", "Points Cumulative", "Price Cumulative", "PPM Cumulative", "P2PM Cumulative"]
    result_cols = list(df_result.columns)
    expected_cols.sort()
    result_cols.sort()
    assert result_cols == expected_cols

    df_expected = df_expected.sort_values(["Season", "Driver", "Race"], ignore_index=True)

    assert_series_equal(df_expected["exp_cum_pts"], df_result["Points Cumulative"], check_names=False)
    assert_series_equal(df_expected["exp_cum_prc"], df_result["Price Cumulative"], check_names=False)
    assert_series_equal(
        df_expected["exp_cum_ppm"],
        df_result["PPM Cumulative"],
        check_names=False,
        check_exact=False,
        atol=1e-4)
    assert_series_equal(
        df_expected["exp_cum_p2pm"],
        df_result["P2PM Cumulative"],
        check_names=False,
        check_exact=False,
        atol=1e-4)

def test_derivation_tot_constructor():
    df_input = pd.DataFrame(
        columns=[
            "Season",
            "Race",
            "Constructor",
            "Points",
            "Price",
            "exp_cum_pts",
            "exp_cum_prc",
            "exp_cum_ppm",
            "exp_roll_pts",
            "exp_roll_prc",
            "exp_roll_ppm",
            "exp_cum_p2pm",
            "exp_roll_p2pm",
        ],
        data=[
            [2023, 2, "MER", 12, 1.2, 11, 1.1, 10.0, 11, 1.1, 10.0, 110.0, 110.0],
            [2023, 1, "MER", 11, 1.1, 0, np.nan, np.nan, 0, np.nan, np.nan, np.nan, np.nan],  # out of order to test sorting
            [2023, 3, "MER", 13, 1.3, 23, 2.3, 10.0, 23, 2.3, 10.0, 230.0, 230.0],
            [2023, 4, "MER", 14, 1.4, 36, 3.6, 10.0, 25, 2.5, 10.0, 360.0, 250.0],
            [2023, 1, "RED", 31, 3.1, 0, np.nan, np.nan, 0, np.nan, np.nan, np.nan, np.nan],
            [2023, 2, "RED", 32, 3.2, 31, 3.1, 10.0, 31, 3.1, 10.0, 310.0, 310.0],
            [2023, 3, "RED", -10, 3.3, 63, 6.3, 10.0, 63, 6.3, 10.0, 630.0, 630.0],  # negative points
            [2023, 4, "RED", 33, 3.4, 53, 9.6, 5.5208, 22, 6.5, 3.3846, 292.6042, 74.4615],
            [2024, 1, "MER", 30, 2.0, 0, np.nan, np.nan, 0, np.nan, np.nan, np.nan, np.nan],
            [2024, 2, "MER", 30, 4.0, 30, 2.0, 15.0, 30, 2.0, 15.0, 450.0, 450.0],
            [2024, 3, "MER", 60, 6.0, 60, 6.0, 10.0, 60, 6.0, 10.0, 600.0, 600.0],  # different PPM
            [2024, 4, "MER", 60, 8.0, 120, 12, 10.0, 90, 10.0, 9.0, 1200.0, 810.0],
            [2024, 1, "ALT", 131, 13.1, 0, np.nan, np.nan, 0, np.nan, np.nan, np.nan, np.nan],
            [2024, 2, "ALT", 132, 13.2, 131, 13.1, 10.0, 131, 13.1, 10.0, 1310.0, 1310.0],
            [2024, 3, "ALT", 133, 13.3, 263, 26.3, 10.0, 263, 26.3, 10.0, 2630.0, 2630.0],
            [2024, 4, "ALT", 134, 13.4, 396, 39.6, 10.0, 265, 26.5, 10.0, 3960.0, 2650.0],
        ]
    )

    df_result = derivation_cum_tot_constructor(df_input)

    expected_cols = ["Season", "Race", "Constructor", "Points", "Price", "Points Cumulative", "Price Cumulative", "PPM Cumulative", "P2PM Cumulative"]
    result_cols = list(df_result.columns)
    expected_cols.sort()
    result_cols.sort()
    assert result_cols == expected_cols

    df_expected = df_input.sort_values(["Season", "Constructor", "Race"], ignore_index=True)

    assert_series_equal(df_expected["exp_cum_pts"], df_result["Points Cumulative"], check_names=False)
    assert_series_equal(df_expected["exp_cum_prc"], df_result["Price Cumulative"], check_names=False)
    assert_series_equal(
        df_expected["exp_cum_ppm"],
        df_result["PPM Cumulative"],
        check_names=False,
        check_exact=False,
        atol=1e-4)
    assert_series_equal(
        df_expected["exp_cum_p2pm"],
        df_result["P2PM Cumulative"],
        check_names=False,
        check_exact=False,
        atol=1e-4)

    df_result_roll = derivation_cum_tot_constructor(df_input, rolling_window=2)

    assert_series_equal(df_expected["exp_roll_pts"], df_result_roll["Points Cumulative (2)"], check_names=False)
    assert_series_equal(df_expected["exp_roll_prc"], df_result_roll["Price Cumulative (2)"], check_names=False)
    assert_series_equal(
        df_expected["exp_roll_ppm"],
        df_result_roll["PPM Cumulative (2)"],
        check_names=False,
        check_exact=False,
        atol=1e-4)
    assert_series_equal(
        df_expected["exp_roll_p2pm"],
        df_result_roll["P2PM Cumulative (2)"],
        check_names=False,
        check_exact=False,
        atol=1e-4)


def test_actual_derivations():
    df_derived_data_driver = load_all_archives_add_derived(asset_type=AssetType.DRIVER, rolling_window=3)
    df_derived_data_constructor = load_all_archives_add_derived(asset_type=AssetType.CONSTRUCTOR, rolling_window=3)

    flt_23_drv = df_derived_data_driver["Season"] == 2023
    flt_23_con = df_derived_data_constructor["Season"] == 2023
    flt_24_drv = df_derived_data_driver["Season"] == 2024

    flt_ver = df_derived_data_driver["Driver"] == "VER"
    flt_ric = df_derived_data_driver["Driver"] == "RIC"
    flt_bea = df_derived_data_driver["Driver"] == "BEA"
    flt_red = df_derived_data_constructor["Constructor"] == "RED"

    df_ver_points_23 = df_derived_data_driver[flt_23_drv & flt_ver][["Race", "PPM Cumulative (3)"]].reset_index(drop=True)
    df_ric_points_23 = df_derived_data_driver[flt_23_drv & flt_ric][["Race", "PPM Cumulative (3)"]].reset_index(drop=True)
    df_red_points_23 = df_derived_data_constructor[flt_23_con & flt_red][["Race", "PPM Cumulative (3)"]].reset_index(drop=True)
    df_bea_points_24 = df_derived_data_driver[flt_24_drv & flt_bea][["Race", "PPM Cumulative (3)"]].reset_index(drop=True)

    df_expected_23 = pd.read_excel(_FILE_EXPECTED_RESULTS, sheet_name="2003 Expected", engine="openpyxl")  # typo!
    df_expected_24 = pd.read_excel(_FILE_EXPECTED_RESULTS, sheet_name="2004 Expected", engine="openpyxl")  # typo!

    df_exp_ver_points_23 = df_expected_23[["Race", "VER-RED-2003-ppm"]].rename(columns={"VER-RED-2003-ppm": "PPM Cumulative (3)"})
    df_exp_ric_points_23 = df_expected_23[["Race", "RIC-ALT-2003-ppm"]].rename(columns={"RIC-ALT-2003-ppm": "PPM Cumulative (3)"})
    df_exp_red_points_23 = df_expected_23[["Race", "RED-2003-ppm"]].rename(columns={"RED-2003-ppm": "PPM Cumulative (3)"})  # typo in sheet name!
    df_exp_bea_points_24 = df_expected_24[["Race", "BEA-2003-ppm"]].rename(columns={"BEA-2003-ppm": "PPM Cumulative (3)"})  # typo in sheet name!

    assert_frame_equal(df_ver_points_23, df_exp_ver_points_23)
    assert_frame_equal(df_ric_points_23, df_exp_ric_points_23)
    assert_frame_equal(df_red_points_23, df_exp_red_points_23)
    assert_frame_equal(df_bea_points_24, df_exp_bea_points_24)


def test_get_race_driver_constructor_pairs():
    df_merged = pd.DataFrame(
        columns=["Constructor", "Driver", "Race", "Points", "Season", "Price"],
        data=[
            ["Team A", "Driver 1", 1, 10, 2023, 1.5],
            ["Team A", "Driver 2", 1, 12, 2023, 2.5],
            ["Team B", "Driver 3", 1, 10, 2023, 1.5],
            ["Team B", "Driver 4", 1, 12, 2023, 2.5],
            ["Team B", "Driver 5", 1, None, 2023, None],
            ["Team A", "Driver 1", 2, 10, 2023, 1.5],
            ["Team A", "Driver 2", 2, 12, 2023, 2.5],
            ["Team B", "Driver 3", 2, 10, 2023, 1.5],
            ["Team B", "Driver 4", 2, 12, 2023, 2.5],
            ["Team B", "Driver 5", 2, None, 2023, None],
            ["Team A", "Driver 1", 3, 10, 2023, 1.5],
            ["Team A", "Driver 2", 3, 12, 2023, 2.5],
            ["Team B", "Driver 3", 3, None, 2023, None],
            ["Team B", "Driver 4", 3, 12, 2023, 2.5],
            ["Team B", "Driver 5", 3, 10, 2023, 1.5],
        ]
    )

    df_expected = pd.DataFrame(
        columns=["Constructor", "Driver", "Race", "Season"],
        data=[
            ["Team A", "Driver 1", 1, 2023],
            ["Team A", "Driver 2", 1, 2023],
            ["Team B", "Driver 3", 1, 2023],
            ["Team B", "Driver 4", 1, 2023],
            ["Team A", "Driver 1", 2, 2023],
            ["Team A", "Driver 2", 2, 2023],
            ["Team B", "Driver 3", 2, 2023],
            ["Team B", "Driver 4", 2, 2023],
            ["Team A", "Driver 1", 3, 2023],
            ["Team A", "Driver 2", 3, 2023],
            ["Team B", "Driver 4", 3, 2023],
            ["Team B", "Driver 5", 3, 2023],            
        ]
    )
    
    df_resuls = get_race_driver_constructor_pairs(df_merged)

    assert_frame_equal(df_resuls.reset_index(drop=True), df_expected.reset_index(drop=True))
