import pandas as pd
import logging

from common import setup_logging, AssetType
from import_data.derivations import derivation_cum_tot
from import_data.import_history import load_all_archive_data

_FILE_DERIVED_DRIVER = "outputs/f1_fantasy_derived_ppm_driver.xlsx"
_FILE_DERIVED_CONSTRUCTOR = "outputs/f1_fantasy_derived_ppm_constructor.xlsx"


def load_all_archives_add_derived(asset_type: AssetType, rolling_window: int = -1) -> pd.DataFrame:
    df = load_all_archive_data(asset_type)
    df = derivation_cum_tot(df, asset_type=asset_type, rolling_window=rolling_window)
    return df


if __name__ == "__main__":
    setup_logging()

    df_derived_data_driver = load_all_archives_add_derived(asset_type=AssetType.DRIVER, rolling_window=3)
    df_derived_data_constructor = load_all_archives_add_derived(asset_type=AssetType.CONSTRUCTOR, rolling_window=3)

    df_derived_data_driver.to_excel(_FILE_DERIVED_DRIVER, sheet_name="Driver PPM Cumulative", index=False)
    df_derived_data_constructor.to_excel(_FILE_DERIVED_CONSTRUCTOR, sheet_name="Constructor PPM Cumulative", index=False)
