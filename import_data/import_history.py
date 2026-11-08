import os
import pandas as pd
import logging

from common import AssetType, F1_SEASON_CONSTRUCTORS

_DIR_ARCHIVE_INPUTS = "data"
_ARCHIVE_FILES = {
    AssetType.DRIVER: "f1_fantasy_drivers.csv",
    AssetType.CONSTRUCTOR: "f1_fantasy_constructors.csv",
}


"""Utilities for loading and validating historical archive data.

The archive is two long-format CSV files, one per asset type, holding one row
per asset per race it took part in: `Season`, `Race`, the identifying columns,
`Points` and `Price`. An asset that did not take part in a race has no row. A
race not yet run has its prices and empty `Points`.

Rows are grouped by season, then by asset, then by race, and the asset order
is kept: the loaders return assets in the order the file holds them, because
callers that enumerate teams (and the back-tests that sample from them) depend
on it.

The loaders return the same frames the archive's earlier wide-format workbook
gave: every asset of a season against every race in it, with empty points and
price where the asset has no row, and points of 0 for a race not yet run.
"""


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


def read_archive_file(asset_type: AssetType, fn: str = _DIR_ARCHIVE_INPUTS) -> pd.DataFrame:
    """Read one asset type's archive CSV as stored, rejecting a malformed file.

    Args:
        asset_type: Asset type whose file to read.
        fn: Directory holding the archive CSVs.

    Returns:
        The file's rows, in file order, with `Driver` as the bare driver code.

    Raises:
        ValueError: If the file's columns are not exactly the expected ones, a
            season/race/asset appears twice, or a row has no price.
    """
    path = os.path.join(fn, _ARCHIVE_FILES[asset_type])
    id_cols = get_id_cols(asset_type)
    expected_cols = ["Season", "Race"] + id_cols + ["Points", "Price"]

    df = pd.read_csv(path, dtype={c: str for c in id_cols})

    if list(df.columns) != expected_cols:
        raise ValueError(f"{path}: expected columns {expected_cols}, found {list(df.columns)}")

    key_cols = ["Season", "Race"] + id_cols
    df_dupes = df[df.duplicated(subset=key_cols, keep=False)]
    if not df_dupes.empty:
        logging.error(df_dupes)
        raise ValueError(f"{path}: duplicate season/race/asset rows")

    df_no_price = df[df["Price"].isna()]
    if not df_no_price.empty:
        logging.error(df_no_price)
        raise ValueError(f"{path}: rows without a price; an asset not taking part has no row")

    return df


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


def load_archive_data_season(asset_type: AssetType, season: int, fn: str=_DIR_ARCHIVE_INPUTS) -> pd.DataFrame:
    """Load one season of one asset type, as a full asset-by-race grid.

    Every asset of the season appears against every race of the season, races
    in order and, within each race, assets in the order the file holds them.
    Where an asset has no row for a race, its points and price are empty. Where
    a race is priced but not yet run, its points are 0. Drivers are identified
    as `DRIVER@CONSTRUCTOR`.

    Args:
        asset_type: Asset type to load (driver or constructor).
        season: Season year to load.
        fn: Directory holding the archive CSVs.

    Returns:
        Columns `Constructor`[, `Driver`], `Race`, `Points`, `Season`, `Price`.
        Driver points and all prices are floats; constructor points are integers.

    Raises:
        ValueError: If the season is not in the archive, or the file is malformed.
    """
    id_cols = get_id_cols(asset_type)
    logging.info(f"Loading season {season} {asset_type.value}...")

    df = read_archive_file(asset_type, fn)
    df = df[df["Season"] == season]
    if df.empty:
        raise ValueError(f"Season {season} not found in the {asset_type.value} archive")

    if asset_type == AssetType.DRIVER:
        df = df.assign(Driver=df["Driver"] + "@" + df["Constructor"])

    df_assets = df[id_cols].drop_duplicates()
    races = sorted(df["Race"].unique())
    df_grid = pd.concat([df_assets.assign(Race=race) for race in races], ignore_index=True)

    df_merged = pd.merge(
        left=df_grid,
        right=df[id_cols + ["Race", "Points", "Price"]],
        on=id_cols + ["Race"],
        how="left",
    )

    not_yet_run = df_merged["Points"].isna() & df_merged["Price"].notna()
    df_merged.loc[not_yet_run, "Points"] = 0

    points_type = "float64" if asset_type == AssetType.DRIVER else "int64"
    df_merged = df_merged.astype({"Race": "int64", "Points": points_type, "Price": "float64"})
    df_merged.insert(len(id_cols) + 2, "Season", season)

    logging.info(f"Loaded season {season} {asset_type.value}, shape: {df_merged.shape}")
    return df_merged


def load_all_archive_data(asset_type: AssetType, fn: str=_DIR_ARCHIVE_INPUTS) -> pd.DataFrame:
    """Load and concatenate archive data for all known seasons.

    Iterates over seasons declared in `F1_SEASON_CONSTRUCTORS`, loads the
    merged points/price data for each season and concatenates them into a
    single dataframe.

    Args:
        asset_type: Asset type to load (driver or constructor).
        fn: Directory holding the archive CSVs.

    Returns:
        A dataframe containing merged archive data for all seasons.
    """
    df_all_data = pd.DataFrame()

    for season in F1_SEASON_CONSTRUCTORS.keys():
        df_merged = load_archive_data_season(asset_type=asset_type, season=season, fn=fn)
        df_all_data = pd.concat([df_all_data, df_merged], ignore_index=True).reset_index(drop=True)

    return df_all_data
