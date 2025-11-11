import pandas as pd
import logging

from common import setup_logging, AssetType
from import_data.derivations import derivation_cum_tot_driver, derivation_cum_tot_constructor
from import_data.import_history import load_all_archive_data

_FILE_DERIVED = "outputs/f1_fantasy_derived_ppm.xlsx"


if __name__ == "__main__":
    setup_logging()

    df_all_archive_data_driver = load_all_archive_data(asset_type=AssetType.DRIVER)
    df_derived_data_driver = derivation_cum_tot_driver(df_all_archive_data_driver, rolling_window=3)

    df_all_archive_data_constructor = load_all_archive_data(asset_type=AssetType.CONSTRUCTOR)
    df_derived_data_constructor = derivation_cum_tot_constructor(df_all_archive_data_constructor, rolling_window=3)

    with pd.ExcelWriter(_FILE_DERIVED) as writer:
        df_derived_data_driver.to_excel(writer, sheet_name="Driver PPM Cumulative", index=False)
        df_derived_data_constructor.to_excel(writer, sheet_name="Constructor PPM Cumulative", index=False)
