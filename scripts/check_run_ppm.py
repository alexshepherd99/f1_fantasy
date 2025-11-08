import logging

from common import setup_logging, AssetType
from import_data.derivations import derivation_cum_tot_driver
from import_data.import_history import load_all_archive_data


if __name__ == "__main__":
    setup_logging()
    df_all_archive_data_driver = load_all_archive_data(asset_type=AssetType.DRIVER)
    df_derived_data_driver = derivation_cum_tot_driver(df_all_archive_data_driver)
    logging.info(df_derived_data_driver.head(15))
