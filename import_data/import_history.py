import pandas as pd
from enum import Enum
from typing import NamedTuple
import logging

from common import AssetType

_FILE_ARCHIVE_INPUTS = "data/f1_fantasy_archive.xlsx"


class DataSheetType(Enum):
    POINTS = "Points"
    PRICE = "Price"


class ArchiveSheetInfo(NamedTuple):
    season: int
    sheet_name: str
    id_cols: list
    sheet_type: DataSheetType


def convert_data_sheet(df_input: pd.DataFrame, season: int, id_cols: list, sheet_type: DataSheetType) -> pd.DataFrame:
    df_melted = df_input.melt(
        id_vars=id_cols,
        var_name="Race",
        value_name=sheet_type.value,
    )

    df_melted["Season"] = season
    df_melted["Race"] = df_melted["Race"].astype(int)

    return df_melted


def load_archive_sheet(sheet_info: ArchiveSheetInfo, fn: str=_FILE_ARCHIVE_INPUTS) -> pd.DataFrame:
    df_input = pd.read_excel(fn, sheet_name=sheet_info.sheet_name)

    df_converted = convert_data_sheet(
        df_input=df_input,
        season=sheet_info.season,
        id_cols=sheet_info.id_cols,
        sheet_type=sheet_info.sheet_type,
    )

    logging.info(f"Loaded {fn}({sheet_info.sheet_name}) for season {sheet_info.season}, shape: {df_converted.shape}")        
    return df_converted


def get_id_cols(asset_type: AssetType) -> list:
    return ["Team", "Driver"] if asset_type == AssetType.DRIVER else ["Team"]


def get_archive_sheet_infos(season: int, asset_type: AssetType) -> dict[DataSheetType, ArchiveSheetInfo]:
    return {
        DataSheetType.POINTS: ArchiveSheetInfo(
            season=season,
            sheet_name=f"{season} {asset_type.value}s Points",
            id_cols=get_id_cols(asset_type),
            sheet_type=DataSheetType.POINTS,
        ),
        DataSheetType.PRICE: ArchiveSheetInfo(
            season=season,
            sheet_name=f"{season} {asset_type.value}s Price",
            id_cols=get_id_cols(asset_type),
            sheet_type=DataSheetType.PRICE,
        ),
    }


def merge_sheet_points_price(df_points: pd.DataFrame, df_price: pd.DataFrame, asset_type: AssetType) -> pd.DataFrame:
    cols_merge = get_id_cols(asset_type) + ["Race", "Season"]

    if df_points.shape != df_price.shape:
        logging.error(pd.concat([df_points, df_price]).drop_duplicates(keep=False))
        raise ValueError("DataFrames to merge must have the same shape")
    
    df_points_check = df_points.dropna()[cols_merge].sort_values(by=cols_merge).reset_index(drop=True)
    df_price_check = df_price.dropna()[cols_merge].sort_values(by=cols_merge).reset_index(drop=True)
    if not df_points_check.reset_index().equals(df_price_check.reset_index()):
        logging.error(pd.concat([df_points_check, df_price_check]).drop_duplicates(keep=False))
        raise ValueError("DataFrames to merge must have the same identifying columns and values")

    df_merged = pd.merge(
        left=df_points,
        right=df_price,
        on=cols_merge,
        how="left",
    )
    return df_merged


def check_merged_integrity_drivers(df_merged_drivers: pd.DataFrame, num_constructors: int):
    all_constructors = df_merged_drivers["Team"].unique()
    if len(all_constructors) != num_constructors:
        raise ValueError(f"Expected {num_constructors} constructors, found {len(all_constructors)}")
    
    df_grouped = df_merged_drivers.groupby(["Season", "Race", "Team"]).count()
    flt_bad_points = df_grouped["Points"] != 2
    flt_bad_price = df_grouped["Price"] != 2

    df_grouped_filtered = df_grouped[flt_bad_points | flt_bad_price]
    if not df_grouped_filtered.empty:
        logging.error(df_grouped_filtered)
        raise ValueError("Merged DataFrame integrity check failed: unexpected number of drivers per race")


def check_merged_integrity_constructors(df_merged_constructors: pd.DataFrame, num_constructors: int):
    all_constructors = df_merged_constructors["Team"].unique()
    if len(all_constructors) != num_constructors:
        raise ValueError(f"Expected {num_constructors} constructors, found {len(all_constructors)}")
    
    df_grouped = df_merged_constructors.groupby(["Season", "Race"]).count()
    flt_bad_points = df_grouped["Points"] != num_constructors
    flt_bad_price = df_grouped["Price"] != num_constructors

    df_grouped_filtered = df_grouped[flt_bad_points | flt_bad_price]
    if not df_grouped_filtered.empty:
        logging.error(df_grouped_filtered)
        raise ValueError("Merged DataFrame integrity check failed: unexpected number of constructors per race")
