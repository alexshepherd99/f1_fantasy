import pandas as pd
import logging

from common import setup_logging, AssetType
from import_data.derivations import derivation_cum_tot
from import_data.import_history import load_all_archive_data

_FILE_DERIVED = "outputs/f1_fantasy_derived_ppm.xlsx"


def load_all_archives_add_derived(asset_type: AssetType, rolling_window: int = -1) -> pd.DataFrame:
    df = load_all_archive_data(asset_type)
    df = derivation_cum_tot(df, asset_type=asset_type, rolling_window=rolling_window)
    return df


if __name__ == "__main__":
    setup_logging()

    df_derived_data_driver = load_all_archives_add_derived(asset_type=AssetType.DRIVER, rolling_window=3)
    df_derived_data_constructor = load_all_archives_add_derived(asset_type=AssetType.CONSTRUCTOR, rolling_window=3)

    with pd.ExcelWriter(_FILE_DERIVED) as writer:
        df_derived_data_driver.to_excel(writer, sheet_name="Driver PPM Cumulative", index=False)
        df_derived_data_constructor.to_excel(writer, sheet_name="Constructor PPM Cumulative", index=False)
