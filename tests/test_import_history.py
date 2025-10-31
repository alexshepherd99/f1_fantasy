import pytest
from pandas.testing import assert_frame_equal
import pandas as pd

from common import AssetType
from import_data.import_history import (
    convert_data_sheet,
    DataSheetType,
    get_archive_sheet_infos,
    ArchiveSheetInfo,
    merge_sheet_points_price,
    check_merged_integrity_drivers,
    check_merged_integrity_constructors,
)

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
    expected_driver_sheets = {
        DataSheetType.POINTS: ArchiveSheetInfo(2023, "2023 Drivers Points", ["Team", "Driver"], DataSheetType.POINTS),
        DataSheetType.PRICE: ArchiveSheetInfo(2023, "2023 Drivers Price", ["Team", "Driver"], DataSheetType.PRICE),
    }

    expected_team_sheets = {
        DataSheetType.POINTS: ArchiveSheetInfo(2023, "2023 Constructors Points", ["Team"], DataSheetType.POINTS),
        DataSheetType.PRICE: ArchiveSheetInfo(2023, "2023 Constructors Price", ["Team"], DataSheetType.PRICE),
    }

    actual_driver_sheets = get_archive_sheet_infos(2023, AssetType.DRIVER)
    actual_team_sheets = get_archive_sheet_infos(2023, AssetType.CONSTRUCTOR)

    assert actual_driver_sheets == expected_driver_sheets
    assert actual_team_sheets == expected_team_sheets


def test_merge_sheet_points_price():
    df_bad_shape_1 = pd.DataFrame(columns=["A", "B"], data=[[1, 2], [3, 4]])
    df_bad_shape_2 = pd.DataFrame(columns=["A", "B", "C"], data=[[1, 2, 3], [4, 5, 6]])
    with pytest.raises(ValueError):
        merge_sheet_points_price(df_bad_shape_1, df_bad_shape_2, AssetType.DRIVER)

    df_bad_points = pd.DataFrame(
        columns=["Team", "Driver", "Race", "Points", "Season"],
        data=[
            ["Team A", "Driver 1", 1, 10, 2023],
            ["Team B", "Driver 2", 1, 12, 2023],
        ],
    )
    df_bad_price = pd.DataFrame(
        columns=["Team", "Driver", "Race", "Points", "Season"],
        data=[
            ["Team A", "Driver 1", 1, 10, 2023],
            ["Team B", "Driver 3", 1, 14, 2023],
        ],
    )
    with pytest.raises(ValueError):
        merge_sheet_points_price(df_bad_points, df_bad_price, AssetType.DRIVER)

    df_driver_good_points = pd.DataFrame(
        columns=["Team", "Driver", "Race", "Points", "Season"],
        data=[
            ["Team A", "Driver 1", 1, 10, 2023],
            ["Team B", "Driver 2", 1, 12, 2023],
        ],
    )
    df_driver_good_price = pd.DataFrame(
        columns=["Team", "Driver", "Race", "Price", "Season"],
        data=[
            ["Team B", "Driver 2", 1, 2.5, 2023],  # intentionally different order
            ["Team A", "Driver 1", 1, 1.5, 2023],
        ],
    )
    df_driver_expected = pd.DataFrame(
        columns=["Team", "Driver", "Race", "Points", "Season", "Price"],
        data=[
            ["Team A", "Driver 1", 1, 10, 2023, 1.5],
            ["Team B", "Driver 2", 1, 12, 2023, 2.5],
        ],
    )
    df_driver_actual = merge_sheet_points_price(df_driver_good_points, df_driver_good_price, AssetType.DRIVER)
    assert_frame_equal(df_driver_actual, df_driver_expected)

    df_team_good_points = pd.DataFrame(
        columns=["Team", "Race", "Points", "Season"],
        data=[
            ["Team A", 1, 30, 2023],
            ["Team B", 1, 40, 2023],
        ],
    )
    df_team_good_price = pd.DataFrame(
        columns=["Team", "Race", "Price", "Season"],
        data=[
            ["Team B", 1, 4.5, 2023],  # intentionally different order
            ["Team A", 1, 3.5, 2023],
        ],
    )
    df_team_expected = pd.DataFrame(
        columns=["Team", "Race", "Points", "Season", "Price"],
        data=[
            ["Team A", 1, 30, 2023, 3.5],
            ["Team B", 1, 40, 2023, 4.5],
        ],
    )
    df_team_actual = merge_sheet_points_price(df_team_good_points, df_team_good_price, AssetType.CONSTRUCTOR)
    assert_frame_equal(df_team_actual, df_team_expected)


def test_check_merged_integrity_drivers():
    df_driver_missing_price = pd.DataFrame(
        columns=["Team", "Driver", "Race", "Points", "Season", "Price"],
        data=[
            ["Team A", "Driver 1", 1, 10, 2023, 1.5],
            ["Team A", "Driver 2", 1, 12, 2023, 2.5],
            ["Team B", "Driver 3", 1, 10, 2023, 1.5],
            ["Team B", "Driver 4", 1, 12, 2023, ],
            ["Team A", "Driver 1", 2, 10, 2023, 1.5],
            ["Team A", "Driver 2", 2, 12, 2023, 2.5],
            ["Team B", "Driver 3", 2, 10, 2023, 1.5],
            ["Team B", "Driver 4", 2, 12, 2023, 2.5],
        ],
    )
    with pytest.raises(ValueError):
        check_merged_integrity_drivers(df_driver_missing_price, num_constructors=2)

    df_driver_missing_points = pd.DataFrame(
        columns=["Team", "Driver", "Race", "Points", "Season", "Price"],
        data=[
            ["Team A", "Driver 1", 1, 10, 2023, 1.5],
            ["Team A", "Driver 2", 1, 12, 2023, 2.5],
            ["Team B", "Driver 3", 1, 10, 2023, 1.5],
            ["Team B", "Driver 4", 1, None, 2023, 2.5],
            ["Team A", "Driver 1", 2, 10, 2023, 1.5],
            ["Team A", "Driver 2", 2, 12, 2023, 2.5],
            ["Team B", "Driver 3", 2, 10, 2023, 1.5],
            ["Team B", "Driver 4", 2, 12, 2023, 2.5],
        ],
    )
    with pytest.raises(ValueError):
        check_merged_integrity_drivers(df_driver_missing_points, num_constructors=2)

    df_driver_too_many_drivers = pd.DataFrame(
        columns=["Team", "Driver", "Race", "Points", "Season", "Price"],
        data=[
            ["Team A", "Driver 1", 1, 10, 2023, 1.5],
            ["Team A", "Driver 2", 1, 12, 2023, 2.5],
            ["Team A", "Driver 9", 1, 12, 2023, 2.5],
            ["Team B", "Driver 3", 1, 10, 2023, 1.5],
            ["Team B", "Driver 4", 1, 12, 2023, 2.5],
            ["Team A", "Driver 1", 2, 10, 2023, 1.5],
            ["Team A", "Driver 2", 2, 12, 2023, 2.5],
            ["Team B", "Driver 3", 2, 10, 2023, 1.5],
            ["Team B", "Driver 4", 2, 12, 2023, 2.5],
        ],
    )
    with pytest.raises(ValueError):
        check_merged_integrity_drivers(df_driver_too_many_drivers, num_constructors=2)

    df_driver_too_few_drivers = pd.DataFrame(
        columns=["Team", "Driver", "Race", "Points", "Season", "Price"],
        data=[
            ["Team A", "Driver 1", 1, 10, 2023, 1.5],
            ["Team B", "Driver 3", 1, 10, 2023, 1.5],
            ["Team B", "Driver 4", 1, 12, 2023, 2.5],
            ["Team A", "Driver 1", 2, 10, 2023, 1.5],
            ["Team A", "Driver 2", 2, 12, 2023, 2.5],
            ["Team B", "Driver 3", 2, 10, 2023, 1.5],
            ["Team B", "Driver 4", 2, 12, 2023, 2.5],
        ],
    )
    with pytest.raises(ValueError):
        check_merged_integrity_drivers(df_driver_too_few_drivers, num_constructors=2)

    df_driver_too_many_constructors = pd.DataFrame(
        columns=["Team", "Driver", "Race", "Points", "Season", "Price"],
        data=[
            ["Team A", "Driver 1", 1, 10, 2023, 1.5],
            ["Team C", "Driver 2", 1, 12, 2023, 2.5],
            ["Team B", "Driver 3", 1, 10, 2023, 1.5],
            ["Team B", "Driver 4", 1, 12, 2023, 2.5],
            ["Team A", "Driver 1", 2, 10, 2023, 1.5],
            ["Team A", "Driver 2", 2, 12, 2023, 2.5],
            ["Team B", "Driver 3", 2, 10, 2023, 1.5],
            ["Team B", "Driver 4", 2, 12, 2023, 2.5],
        ],
    )
    with pytest.raises(ValueError):
        check_merged_integrity_drivers(df_driver_too_many_constructors, num_constructors=2)

    df_driver_too_few_constructors = pd.DataFrame(
        columns=["Team", "Driver", "Race", "Points", "Season", "Price"],
        data=[
            ["Team B", "Driver 1", 1, 10, 2023, 1.5],
            ["Team B", "Driver 2", 1, 12, 2023, 2.5],
            ["Team B", "Driver 3", 1, 10, 2023, 1.5],
            ["Team B", "Driver 4", 1, 12, 2023, 2.5],
            ["Team A", "Driver 1", 2, 10, 2023, 1.5],
            ["Team A", "Driver 2", 2, 12, 2023, 2.5],
            ["Team B", "Driver 3", 2, 10, 2023, 1.5],
            ["Team B", "Driver 4", 2, 12, 2023, 2.5],
        ],
    )
    with pytest.raises(ValueError):
        check_merged_integrity_drivers(df_driver_too_few_constructors, num_constructors=2)

    df_ok = pd.DataFrame(
        columns=["Team", "Driver", "Race", "Points", "Season", "Price"],
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
    check_merged_integrity_drivers(df_ok, num_constructors=2)


def test_check_merged_integrity_constructors():
    df_driver_missing_price = pd.DataFrame(
        columns=["Team", "Race", "Points", "Season", "Price"],
        data=[
            ["Team A", 1, 10, 2023, 1.5],
            ["Team B", 1, 12, 2023, ],
            ["Team A", 2, 10, 2023, 1.5],
            ["Team B", 2, 10, 2023, 1.5],
        ],
    )
    with pytest.raises(ValueError):
        check_merged_integrity_constructors(df_driver_missing_price, num_constructors=2)

    df_driver_missing_points = pd.DataFrame(
        columns=["Team", "Race", "Points", "Season", "Price"],
        data=[
            ["Team A", 1, 10, 2023, 1.5],
            ["Team B", 1, None, 2023, 1.5],
            ["Team A", 2, 10, 2023, 1.5],
            ["Team B", 2, 10, 2023, 1.5],
        ],
    )
    with pytest.raises(ValueError):
        check_merged_integrity_constructors(df_driver_missing_points, num_constructors=2)

    df_driver_too_many_constructors = pd.DataFrame(
        columns=["Team", "Race", "Points", "Season", "Price"],
        data=[
            ["Team A", 1, 10, 2023, 1.5],
            ["Team B", 1, 10, 2023, 1.5],
            ["Team C", 1, 10, 2023, 1.5],
            ["Team A", 2, 10, 2023, 1.5],
            ["Team B", 2, 10, 2023, 1.5],
        ],
    )
    with pytest.raises(ValueError):
        check_merged_integrity_constructors(df_driver_too_many_constructors, num_constructors=2)

    df_driver_too_few_constructors = pd.DataFrame(
        columns=["Team", "Race", "Points", "Season", "Price"],
        data=[
            ["Team A", 1, 10, 2023, 1.5],
            ["Team A", 2, 10, 2023, 1.5],
            ["Team B", 2, 10, 2023, 1.5],
        ],
    )
    with pytest.raises(ValueError):
        check_merged_integrity_constructors(df_driver_too_few_constructors, num_constructors=2)

    df_ok = pd.DataFrame(
        columns=["Team", "Race", "Points", "Season", "Price"],
        data=[
            ["Team A", 1, 10, 2023, 1.5],
            ["Team B", 1, 10, 2023, 1.5],
            ["Team A", 2, 10, 2023, 1.5],
            ["Team B", 2, 10, 2023, 1.5],
            ["Team A", 3, 10, 2023, 1.5],
            ["Team B", 3, 10, 2023, 1.5],
        ]
    )
    check_merged_integrity_constructors(df_ok, num_constructors=2)
