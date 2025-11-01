import pandas as pd
from pandas.testing import assert_series_equal

from common import AssetType
from import_data.import_history import DataSheetType, get_archive_sheet_infos, load_archive_sheet
from import_data.process_archive import add_points_cumulative


def test_add_points_cumulative():
    archive_sheets_driver_23 = get_archive_sheet_infos(season=2023, asset_type=AssetType.DRIVER)
    archive_sheet_driver_points_23 = archive_sheets_driver_23[DataSheetType.POINTS]
    archive_sheet_driver_price_23 = archive_sheets_driver_23[DataSheetType.PRICE]

    archive_sheets_driver_24 = get_archive_sheet_infos(season=2024, asset_type=AssetType.DRIVER)
    archive_sheet_driver_points_24 = archive_sheets_driver_24[DataSheetType.POINTS]
    archive_sheet_driver_price_24 = archive_sheets_driver_24[DataSheetType.PRICE]

    df_input_driver_points = pd.concat(
        [load_archive_sheet(archive_sheet_driver_points_23), load_archive_sheet(archive_sheet_driver_points_24)],
    )
    df_actual_driver_points = add_points_cumulative(df_input_driver_points, col_asset="Driver")

    flt_23 = df_actual_driver_points["Season"] == 2023
    flt_24 = df_actual_driver_points["Season"] == 2024
    flt_max = df_actual_driver_points["Driver"] == "MAX"
    flt_ric = df_actual_driver_points["Driver"] == "RIC"
    flt_bea = df_actual_driver_points["Driver"] == "BEA"
    ser_max_points_23 = df_actual_driver_points[flt_23 & flt_max]
    ser_max_points_24 = df_actual_driver_points[flt_24 & flt_max]


    assert_series_equal
