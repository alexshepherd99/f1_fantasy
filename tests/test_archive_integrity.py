import logging

from common import F1_SEASON_CONSTRUCTORS, AssetType
from import_data.import_history import (
    get_archive_sheet_infos,
    load_archive_sheet,
    merge_sheet_points_price,
    check_merged_integrity_drivers,
    check_merged_integrity_constructors,
)


def test_archive_integrity():
    for season in F1_SEASON_CONSTRUCTORS.keys():
        num_constructors = F1_SEASON_CONSTRUCTORS[season]
        logging.info(f"Testing archive integrity for season {season} with {num_constructors} constructors")

        for asset_type in AssetType:
            logging.info(f"  Asset type: {asset_type.value}")
            archive_sheets = get_archive_sheet_infos(season, asset_type)
            assert len(archive_sheets) == 2, "Expected 2 archive sheets (Points and Price)"
            
            df_points = load_archive_sheet(archive_sheets[0])
            df_price = load_archive_sheet(archive_sheets[1])

            df_merged = merge_sheet_points_price(df_points, df_price, asset_type)
            if asset_type == AssetType.DRIVER:
                check_merged_integrity_drivers(df_merged, num_constructors)
            elif asset_type == AssetType.CONSTRUCTOR:
                check_merged_integrity_constructors(df_merged, num_constructors)
            else:
                assert False, f"Unknown asset type: {asset_type}"
