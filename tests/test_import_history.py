import numpy as np
import pytest
from pandas.testing import assert_frame_equal
import pandas as pd

from common import AssetType
from import_data import import_history
from import_data.import_history import (
    check_merged_integrity_drivers,
    check_merged_integrity_constructors,
    check_drivers_against_constructors,
    load_all_archive_data,
    load_archive_data_season,
)

def test_check_merged_integrity_drivers():
    df_driver_missing_price = pd.DataFrame(
        columns=["Constructor", "Driver", "Race", "Points", "Season", "Price"],
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
        columns=["Constructor", "Driver", "Race", "Points", "Season", "Price"],
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
        columns=["Constructor", "Driver", "Race", "Points", "Season", "Price"],
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
        columns=["Constructor", "Driver", "Race", "Points", "Season", "Price"],
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
        columns=["Constructor", "Driver", "Race", "Points", "Season", "Price"],
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
        columns=["Constructor", "Driver", "Race", "Points", "Season", "Price"],
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
    check_merged_integrity_drivers(df_ok, num_constructors=2)


def test_check_merged_integrity_constructors():
    df_driver_missing_price = pd.DataFrame(
        columns=["Constructor", "Race", "Points", "Season", "Price"],
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
        columns=["Constructor", "Race", "Points", "Season", "Price"],
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
        columns=["Constructor", "Race", "Points", "Season", "Price"],
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
        columns=["Constructor", "Race", "Points", "Season", "Price"],
        data=[
            ["Team A", 1, 10, 2023, 1.5],
            ["Team A", 2, 10, 2023, 1.5],
            ["Team B", 2, 10, 2023, 1.5],
        ],
    )
    with pytest.raises(ValueError):
        check_merged_integrity_constructors(df_driver_too_few_constructors, num_constructors=2)

    df_ok = pd.DataFrame(
        columns=["Constructor", "Race", "Points", "Season", "Price"],
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


def test_check_drivers_against_constructors():
    df_drivers_ok = pd.DataFrame(
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
        ]
    )
    df_constructors_ok = pd.DataFrame(
        columns=["Constructor", "Race", "Season"],
        data=[
            ["Team A", 1, 2023],
            ["Team B", 1, 2023],
            ["Team A", 2, 2023],
            ["Team B", 2, 2023],
        ]
    )
    check_drivers_against_constructors(df_drivers_ok, df_constructors_ok)

    # Add a constructor with no drivers - should error
    df_constructors_extra = pd.concat(
        [
            df_constructors_ok,
            pd.DataFrame([{"Constructor": "Team C", "Race": 2, "Season": 2023}])
        ]
    )
    with pytest.raises(ValueError):
        check_drivers_against_constructors(df_drivers_ok, df_constructors_extra)

    # Remove a contructor - should error
    df_constructors_removed = df_constructors_ok[df_constructors_ok["Constructor"] == "Team A"]
    with pytest.raises(ValueError):
        check_drivers_against_constructors(df_drivers_ok, df_constructors_removed)

    # Add a driver with an unknown constructor - should error
    df_drivers_extra = pd.concat(
        [
            df_drivers_ok,
            pd.DataFrame([{"Driver": "Bob", "Constructor": "Team C", "Race": 2, "Season": 2023}])            
        ]
    )
    with pytest.raises(ValueError):
        check_drivers_against_constructors(df_drivers_extra, df_constructors_ok)

    # Remove references to a given constructor from drivers
    df_drivers_removed = df_drivers_ok[df_drivers_ok["Constructor"] == "Team A"]
    with pytest.raises(ValueError):
        check_drivers_against_constructors(df_drivers_removed, df_constructors_ok)


_DRIVERS_HEADER = "Season,Race,Constructor,Driver,Points,Price"
_CONSTRUCTORS_HEADER = "Season,Race,Constructor,Points,Price"


def _write_archive(tmp_path, drivers: list[str], constructors: list[str]) -> str:
    """Write a fixture archive directory holding the two CSVs, returning its path."""
    (tmp_path / "f1_fantasy_drivers.csv").write_text("\n".join(drivers) + "\n")
    (tmp_path / "f1_fantasy_constructors.csv").write_text("\n".join(constructors) + "\n")
    return str(tmp_path)


def _fixture_archive(tmp_path) -> str:
    """Two seasons. HAM sits out 2023 race 2, and 2024 race 2 is priced but not yet run.

    Rows are grouped by asset, in the order the loader must keep: BOT before HAM in
    the file, although it sorts after it.
    """
    return _write_archive(
        tmp_path,
        [
            _DRIVERS_HEADER,
            "2023,1,MER,BOT,30,2",
            "2023,2,MER,BOT,31,2.1",
            "2023,1,MER,HAM,11,1.1",
            "2024,1,MER,BOT,20,3",
            "2024,2,MER,BOT,,3.2",
            "2024,1,MER,HAM,12,1.5",
            "2024,2,MER,HAM,,1.4",
        ],
        [
            _CONSTRUCTORS_HEADER,
            "2023,1,RED,50,30",
            "2023,2,RED,-5,30.2",
            "2023,1,MER,40,25.5",
            "2023,2,MER,45,25.6",
            "2024,1,MER,41,26",
            "2024,2,MER,,26.1",
        ],
    )


def test_load_archive_data_season_rebuilds_grid_in_file_order(tmp_path):
    fn = _fixture_archive(tmp_path)

    df_expected = pd.DataFrame(
        columns=["Constructor", "Driver", "Race", "Points", "Season", "Price"],
        data=[
            ["MER", "BOT@MER", 1, 30.0, 2023, 2.0],
            ["MER", "HAM@MER", 1, 11.0, 2023, 1.1],
            ["MER", "BOT@MER", 2, 31.0, 2023, 2.1],
            ["MER", "HAM@MER", 2, np.nan, 2023, np.nan],
        ],
    )
    df_actual = load_archive_data_season(AssetType.DRIVER, 2023, fn=fn)
    assert_frame_equal(df_actual, df_expected)


def test_load_archive_data_season_fills_points_for_race_not_yet_run(tmp_path):
    fn = _fixture_archive(tmp_path)

    df_drivers = load_archive_data_season(AssetType.DRIVER, 2024, fn=fn)
    assert df_drivers[df_drivers["Race"] == 2]["Points"].tolist() == [0.0, 0.0]
    assert df_drivers[df_drivers["Race"] == 2]["Price"].tolist() == [3.2, 1.4]

    df_constructors = load_archive_data_season(AssetType.CONSTRUCTOR, 2024, fn=fn)
    df_expected = pd.DataFrame(
        columns=["Constructor", "Race", "Points", "Season", "Price"],
        data=[["MER", 1, 41, 2024, 26.0], ["MER", 2, 0, 2024, 26.1]],
    )
    assert_frame_equal(df_constructors, df_expected)


def test_load_archive_data_season_constructor_points_are_integers(tmp_path):
    fn = _fixture_archive(tmp_path)

    df_actual = load_archive_data_season(AssetType.CONSTRUCTOR, 2023, fn=fn)
    df_expected = pd.DataFrame(
        columns=["Constructor", "Race", "Points", "Season", "Price"],
        data=[
            ["RED", 1, 50, 2023, 30.0],
            ["MER", 1, 40, 2023, 25.5],
            ["RED", 2, -5, 2023, 30.2],
            ["MER", 2, 45, 2023, 25.6],
        ],
    )
    assert_frame_equal(df_actual, df_expected)
    assert df_actual["Points"].dtype == "int64"


def test_load_all_archive_data_concatenates_seasons(tmp_path, monkeypatch):
    fn = _fixture_archive(tmp_path)
    monkeypatch.setattr(import_history, "F1_SEASON_CONSTRUCTORS", {2023: 2, 2024: 1})

    df_actual = load_all_archive_data(AssetType.CONSTRUCTOR, fn=fn)
    assert df_actual["Season"].tolist() == [2023] * 4 + [2024] * 2
    assert df_actual.index.tolist() == list(range(6))


def test_load_archive_data_season_rejects_unknown_season(tmp_path):
    fn = _fixture_archive(tmp_path)
    with pytest.raises(ValueError, match="2022"):
        load_archive_data_season(AssetType.DRIVER, 2022, fn=fn)


@pytest.mark.parametrize(
    "bad_row, message",
    [
        ("2023,1,MER,HAM,12,1.2", "duplicate"),  # second row for HAM in race 1
        ("2023,3,MER,HAM,10,", "price"),  # points without a price
        ("2023,3,MER,HAM,,", "price"),  # an empty pair: absence is shown by having no row
    ],
)
def test_load_archive_data_season_rejects_malformed_rows(tmp_path, bad_row, message):
    fn = _write_archive(
        tmp_path,
        [_DRIVERS_HEADER, "2023,1,MER,HAM,11,1.1", bad_row],
        [_CONSTRUCTORS_HEADER, "2023,1,MER,40,25.5"],
    )
    with pytest.raises(ValueError, match=message):
        load_archive_data_season(AssetType.DRIVER, 2023, fn=fn)


@pytest.mark.parametrize(
    "header",
    [
        "Season,Race,Constructor,Driver,Points,Price,Notes",  # a column it does not know
        "Season,Race,Constructor,Driver,Points",  # a column missing
    ],
)
def test_load_archive_data_season_rejects_unexpected_columns(tmp_path, header):
    rows = {7: "2023,1,MER,HAM,11,1.1,x", 6: "2023,1,MER,HAM,11,1.1", 5: "2023,1,MER,HAM,11"}
    fn = _write_archive(
        tmp_path,
        [header, rows[header.count(",") + 1]],
        [_CONSTRUCTORS_HEADER, "2023,1,MER,40,25.5"],
    )
    with pytest.raises(ValueError, match="columns"):
        load_archive_data_season(AssetType.DRIVER, 2023, fn=fn)
