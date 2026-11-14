import logging

from common import F1_SEASON_CONSTRUCTORS, AssetType, setup_logging
from import_data.import_history import (
    _DIR_ARCHIVE_INPUTS,
    check_merged_integrity_drivers,
    check_merged_integrity_constructors,
    load_all_archive_data,
    load_archive_data_season,
    check_drivers_against_constructors,
    read_archive_file,
)
from tests.boxbox_fixtures import CONSTRUCTORS_CSV, DRIVERS_CSV, write_archive


def check_archive_integrity():
    for season in F1_SEASON_CONSTRUCTORS.keys():
        num_constructors = F1_SEASON_CONSTRUCTORS[season]
        logging.info(f"Testing archive integrity for season {season} with {num_constructors} constructors")

        for asset_type in AssetType:
            logging.info(f"  Asset type: {asset_type.value}")
            df_merged = load_archive_data_season(asset_type, season)
            if asset_type == AssetType.DRIVER:
                check_merged_integrity_drivers(df_merged, num_constructors)
            elif asset_type == AssetType.CONSTRUCTOR:
                check_merged_integrity_constructors(df_merged, num_constructors)
            else:
                assert False, f"Unknown asset type: {asset_type}"

    # Check for cohesion between driver and constructor
    df_all_driver = load_all_archive_data(AssetType.DRIVER)
    df_all_constructor = load_all_archive_data(AssetType.CONSTRUCTOR)
    for season in F1_SEASON_CONSTRUCTORS.keys():
        df_season_driver = df_all_driver[df_all_driver["Season"] == season]
        df_season_constructor = df_all_constructor[df_all_constructor["Season"] == season]
        check_drivers_against_constructors(df_season_driver, df_season_constructor)


def unlisted_seasons(fn: str, listed: dict[int, int]) -> set[int]:
    """Seasons in either archive CSV that ``listed`` (``F1_SEASON_CONSTRUCTORS``) lacks.

    ``load_all_archive_data`` loads only the listed seasons, so an unlisted one would
    be left out silently. A new season's first capture prints the line to add.
    """
    return {season for asset_type in AssetType
            for season in read_archive_file(asset_type, fn)["Season"].unique()} - set(listed)


def test_archive_integrity():
    check_archive_integrity()


def test_every_archive_season_is_listed_in_common():
    assert unlisted_seasons(_DIR_ARCHIVE_INPUTS, F1_SEASON_CONSTRUCTORS) == set(), \
        "add each season to common.F1_SEASON_CONSTRUCTORS with its number of constructors"


def test_unlisted_seasons_finds_a_season_common_lacks(tmp_path):
    write_archive(tmp_path, DRIVERS_CSV + "2027,1,RED,VER,,28\n", CONSTRUCTORS_CSV + "2027,1,RED,,30\n")

    assert unlisted_seasons(str(tmp_path), {2025: 1, 2026: 2}) == {2027}
    assert unlisted_seasons(str(tmp_path), {2025: 1, 2026: 2, 2027: 1}) == set()


if __name__ == "__main__":
    setup_logging()
    check_archive_integrity()
