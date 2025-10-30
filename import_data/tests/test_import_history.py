import pytest
from pandas.testing import assert_frame_equal
import pandas as pd

from common import AssetType
from import_data.import_history import convert_data_sheet, DataSheetType, get_archive_sheet_infos, ArchiveSheetInfo


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
        sheet_type=DataSheetType.POINTS,
    )

    assert_frame_equal(df_actual, df_expected)


def test_convert_data_sheet_one_column():
    df_input = pd.DataFrame(
        columns=["Team", 1, 2, 3, 4],
        data=[
            ["Team A", 1.1, 2.2, 3.3, 4.4],
            ["Team B", 5.5, 6.6, 7.7, 8.8],
            ["Team C", 9.9, 10.1, 11.2, 12.3],            
        ],
    )

    df_expected = pd.DataFrame(
        columns=["Team", "Race", "Price", "Season"],
        data=[
            ["Team A", 1, 1.1, 2022],
            ["Team B", 1, 5.5, 2022],
            ["Team C", 1, 9.9, 2022],
            ["Team A", 2, 2.2, 2022],
            ["Team B", 2, 6.6, 2022],
            ["Team C", 2, 10.1, 2022],
            ["Team A", 3, 3.3, 2022],
            ["Team B", 3, 7.7, 2022],
            ["Team C", 3, 11.2, 2022],
            ["Team A", 4, 4.4, 2022],
            ["Team B", 4, 8.8, 2022],
            ["Team C", 4, 12.3, 2022],
        ]
    )

    df_actual = convert_data_sheet(
        df_input=df_input,
        season=2022,
        id_cols=["Team"],
        sheet_type=DataSheetType.PRICE,
    )

    assert_frame_equal(df_actual, df_expected)


def test_get_archive_sheet_infos():
    expected_driver_sheets = [
        ArchiveSheetInfo(2023, "2023 Drivers Points", ["Team", "Driver"], DataSheetType.POINTS),
        ArchiveSheetInfo(2023, "2023 Drivers Price", ["Driver"], DataSheetType.PRICE),
    ]

    expected_team_sheets = [
        ArchiveSheetInfo(2023, "2023 Constructors Points", ["Team"], DataSheetType.POINTS),
        ArchiveSheetInfo(2023, "2023 Constructors Price", ["Team"], DataSheetType.PRICE),
    ]

    actual_driver_sheets = get_archive_sheet_infos(2023, AssetType.DRIVER)
    actual_team_sheets = get_archive_sheet_infos(2023, AssetType.CONSTRUCTOR)

    assert actual_driver_sheets == expected_driver_sheets
    assert actual_team_sheets == expected_team_sheets
