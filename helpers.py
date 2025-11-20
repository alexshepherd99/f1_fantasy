import pandas as pd
import functools

from common import AssetType
from import_data.import_history import load_archive_data_season
from import_data.derivations import (
    derivation_cum_tot_constructor,
    derivation_cum_tot_driver,
    get_race_driver_constructor_pairs,
)


@functools.cache
def load_with_derivations(season: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    df_driver = load_archive_data_season(AssetType.DRIVER, season)
    df_constructor = load_archive_data_season(AssetType.CONSTRUCTOR, season)
    df_driver_pairs = get_race_driver_constructor_pairs(df_driver)
    df_driver_ppm = derivation_cum_tot_driver(df_driver, rolling_window=3)
    df_constructor_ppm = derivation_cum_tot_constructor(df_constructor, rolling_window=3)

    return (df_driver_ppm, df_constructor_ppm, df_driver_pairs)
