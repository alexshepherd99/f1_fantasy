import pandas as pd
from pandas.testing import assert_series_equal

from common import AssetType
from import_data.import_history import get_archive_sheet_infos, load_archive_sheet
from import_data.process_archive import add_points_cumulative


def test_add_points_cumulative():
    archive_sheets_driver = get_archive_sheet_infos(season=2023, asset_type=AssetType.DRIVER)
    archive_sheet_driver_points = archive_sheets_driver[0]
    archive_sheet_driver_price = archive_sheets_driver[1]

    df_input_driver_points = load_archive_sheet(archive_sheet_driver_points)
    df_actual_driver_points = add_points_cumulative(df_input_driver_points, col_asset="Driver")

    assert_series_equal
