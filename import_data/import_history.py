import pandas as pd
from enum import Enum
from typing import NamedTuple
import logging

from common import AssetType, F1_SEASON_CONSTRUCTORS

_FILE_ARCHIVE_INPUTS = "data/f1_fantasy_archive.xlsx"


"""Utilities for loading and validating historical archive data.

This module reads the archived Excel workbook containing historical
`Points` and `Price` sheets for drivers and constructors, converts the
wide-format sheets to tidy dataframes, merges points and price sheets,
and performs basic integrity checks.
"""


class DataSheetType(Enum):
    """Enum of supported archive sheet types.

    Attributes:
        POINTS: Sheet containing points scored.
        PRICE: Sheet containing price information.
    """

    POINTS = "Points"
    PRICE = "Price"


class ArchiveSheetInfo(NamedTuple):
    """NamedTuple describing an archive sheet to load.

    Fields:
        season: The integer season year (e.g., 2023).
        sheet_name: Excel sheet name inside the archive workbook.
        id_cols: List of identifying columns (e.g., ['Constructor', 'Driver']).
        sheet_type: Type of the sheet as a `DataSheetType`.
    """

    season: int
    sheet_name: str
    id_cols: list
    sheet_type: DataSheetType


def convert_data_sheet(df_input: pd.DataFrame, season: int, id_cols: list, sheet_type: DataSheetType) -> pd.DataFrame:
    """Convert a wide-format archive sheet into tidy (long) format.

    The input dataframe is expected to have race numbers as column names
    (e.g. 1, 2, 3...). This function melts those race columns into a
    `Race` column and places values under a column named after the
    `sheet_type` value (e.g. 'Points' or 'Price'). It also adds a
    `Season` column and ensures `Race` is an integer.

    Args:
        df_input: Source dataframe read from Excel.
        season: Season year to attach to the data.
        id_cols: Columns to treat as identifier variables when melting.
        sheet_type: The type of data sheet being converted.

    Returns:
        A melted dataframe with columns: id_cols + ['Race', sheet_type.value, 'Season'].
    """
    df_melted = df_input.melt(
        id_vars=id_cols,
        var_name="Race",
        value_name=sheet_type.value,
    )

    df_melted["Season"] = season
    df_melted["Race"] = df_melted["Race"].astype(int)

    return df_melted


def load_archive_sheet(sheet_info: ArchiveSheetInfo, fn: str=_FILE_ARCHIVE_INPUTS) -> pd.DataFrame:
    """Load and convert a single archive sheet from the Excel archive.

    The sheet is read using pandas, a common misnamed column `Team` is
    normalized to `Constructor`, then the sheet is converted to tidy
    format via `convert_data_sheet`.

    Args:
        sheet_info: `ArchiveSheetInfo` describing which sheet to load.
        fn: Path to the archive Excel file.

    Returns:
        Converted tidy dataframe for the requested sheet.
    """
    df_input = pd.read_excel(fn, sheet_name=sheet_info.sheet_name)

    # Patch up column name, if incorrect in input file
    df_input = df_input.rename(columns={"Team": "Constructor"})
    
    df_converted = convert_data_sheet(
        df_input=df_input,
        season=sheet_info.season,
        id_cols=sheet_info.id_cols,
        sheet_type=sheet_info.sheet_type,
    )

    logging.info(f"Loaded {fn}({sheet_info.sheet_name}) for season {sheet_info.season}, shape: {df_converted.shape}")        
    return df_converted


def get_id_cols(asset_type: AssetType) -> list:
    """Return the identifying columns for the given `AssetType`.

    Drivers are identified by both `Constructor` and `Driver` columns,
    while constructors are identified only by `Constructor`.

    Args:
        asset_type: AssetType.DRIVER or AssetType.CONSTRUCTOR.

    Returns:
        List of identifier column names.
    """
    return ["Constructor", "Driver"] if asset_type == AssetType.DRIVER else ["Constructor"]


def get_archive_sheet_infos(season: int, asset_type: AssetType) -> dict[DataSheetType, ArchiveSheetInfo]:
    """Construct ArchiveSheetInfo objects for points and price sheets.

    The function builds the expected sheet names for both Points and
    Price sheets for the given season and asset type.

    Args:
        season: Season year.
        asset_type: AssetType.DRIVER or AssetType.CONSTRUCTOR.

    Returns:
        A dictionary mapping `DataSheetType` -> `ArchiveSheetInfo`.
    """
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
    """Merge points and price dataframes for the same season/asset.

    Performs basic shape and identifier equality checks before merging
    on the identifying columns plus `Race` and `Season`.

    Args:
        df_points: DataFrame containing points values.
        df_price: DataFrame containing price values.
        asset_type: Asset type to determine identifier columns.

    Returns:
        A merged dataframe containing both Points and Price columns.

    Raises:
        ValueError: If the input dataframes differ in shape or identifying values.
    """
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
    """Verify merged drivers dataframe integrity.

    Ensures the expected number of constructors are present and that for
    each (Season, Race, Constructor) the counts of `Points` and `Price`
    equal 2 (one per driver presumably).

    Args:
        df_merged_drivers: Merged drivers dataframe containing Points and Price.
        num_constructors: Expected number of constructors in the season.

    Raises:
        ValueError: If constructor count or per-group counts are unexpected.
    """
    all_constructors = df_merged_drivers["Constructor"].unique()
    if len(all_constructors) != num_constructors:
        raise ValueError(f"Expected {num_constructors} constructors, found {len(all_constructors)}")
    
    df_grouped = df_merged_drivers.groupby(["Season", "Race", "Constructor"]).count()
    flt_bad_points = df_grouped["Points"] != 2
    flt_bad_price = df_grouped["Price"] != 2

    df_grouped_filtered = df_grouped[flt_bad_points | flt_bad_price]
    if not df_grouped_filtered.empty:
        logging.error(df_grouped_filtered)
        raise ValueError("Merged DataFrame integrity check failed: unexpected number of drivers per race")


def check_merged_integrity_constructors(df_merged_constructors: pd.DataFrame, num_constructors: int):
    """Verify merged constructors dataframe integrity.

    Ensures the expected number of constructors are present and that for
    each (Season, Race) the counts of `Points` and `Price` equal the
    expected number of constructors.

    Args:
        df_merged_constructors: Merged constructors dataframe.
        num_constructors: Expected number of constructors in the season.

    Raises:
        ValueError: If constructor count or per-group counts are unexpected.
    """
    all_constructors = df_merged_constructors["Constructor"].unique()
    if len(all_constructors) != num_constructors:
        raise ValueError(f"Expected {num_constructors} constructors, found {len(all_constructors)}")
    
    df_grouped = df_merged_constructors.groupby(["Season", "Race"]).count()
    flt_bad_points = df_grouped["Points"] != num_constructors
    flt_bad_price = df_grouped["Price"] != num_constructors

    df_grouped_filtered = df_grouped[flt_bad_points | flt_bad_price]
    if not df_grouped_filtered.empty:
        logging.error(df_grouped_filtered)
        raise ValueError("Merged DataFrame integrity check failed: unexpected number of constructors per race")


def check_drivers_against_constructors(df_merged_drivers: pd.DataFrame, df_merged_constructors: pd.DataFrame):
    """Ensure constructors referenced by drivers match the constructors list.

    Compares the unique `Constructor` values in the drivers and
    constructors dataframes and raises if there are mismatches.

    Args:
        df_merged_drivers: Merged drivers dataframe.
        df_merged_constructors: Merged constructors dataframe.

    Raises:
        ValueError: If there are constructor names present in one dataframe
            but not the other.
    """
    drivers_constructors = set(df_merged_drivers["Constructor"].unique())
    constructors_constructors = set(df_merged_constructors["Constructor"].unique())

    diffs_1 = list(drivers_constructors - constructors_constructors)
    diffs_2 = list(constructors_constructors - drivers_constructors)
    diffs = diffs_1 + diffs_2
    if len(diffs) > 0:
        logging.error(f"Mismatched constructors and drivers {diffs}")
        logging.error(f"Drivers: {drivers_constructors}")
        logging.error(f"Constructors: {constructors_constructors}")
        raise ValueError(f"Mismatched constructors and drivers {diffs}")


def load_archive_data_season(asset_type: AssetType, season: int, fn: str=_FILE_ARCHIVE_INPUTS) -> pd.DataFrame:
    """Load and merge Points and Price sheets for a single season.

    Args:
        asset_type: Asset type to load (driver or constructor).
        season: Season year to load.
        fn: Path to archive Excel file.

    Returns:
        Merged dataframe for the requested season and asset type.
    """
    archive_sheets = get_archive_sheet_infos(season, asset_type)
    logging.info(f"Loading season {season} {asset_type.value}...")

    df_points = load_archive_sheet(archive_sheets[DataSheetType.POINTS])
    df_price = load_archive_sheet(archive_sheets[DataSheetType.PRICE])
    return merge_sheet_points_price(df_points, df_price, asset_type)


def load_all_archive_data(asset_type: AssetType, fn: str=_FILE_ARCHIVE_INPUTS) -> pd.DataFrame:
    """Load and concatenate archive data for all known seasons.

    Iterates over seasons declared in `F1_SEASON_CONSTRUCTORS`, loads the
    merged points/price data for each season and concatenates them into a
    single dataframe.

    Args:
        asset_type: Asset type to load (driver or constructor).
        fn: Path to archive Excel file.

    Returns:
        A dataframe containing merged archive data for all seasons.
    """
    df_all_data = pd.DataFrame()

    for season in F1_SEASON_CONSTRUCTORS.keys():
        df_merged = load_archive_data_season(asset_type=asset_type, season=season, fn=fn)
        df_all_data = pd.concat([df_all_data, df_merged], ignore_index=True).reset_index(drop=True)

    return df_all_data
