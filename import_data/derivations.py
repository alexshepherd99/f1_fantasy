import pandas as pd
import numpy as np

from common import AssetType


def derivation_cum_tot(
        df_input: pd.DataFrame,
        asset_type: AssetType,
        rolling_window: int = -1
    ) -> pd.DataFrame:

    # If no rolling window, assume total cumulative
    if rolling_window == -1:
        rolling_window = len(df_input.index)
        col_pts = "Points Cumulative"
        col_prc = "Price Cumulative"
        col_ppm = "PPM Cumulative"
    else:
        col_pts = f"Points Cumulative ({rolling_window})"
        col_prc = f"Price Cumulative ({rolling_window})"
        col_ppm = f"PPM Cumulative ({rolling_window})"

    # Just columns of interest
    df = df_input[["Season", "Race", asset_type.value, "Points", "Price"]]

    # Group up assets, there will be duplication for drivers across constructors
    df = df.groupby(["Season", asset_type.value, "Race"]).sum().reset_index()

    # Ensure rows are ordered by the grouping keys and race
    df = df.sort_values(["Season", asset_type.value, "Race"], ignore_index=True)

    # Cumulative totals per group, treating NaN as zero
    df[col_pts] = df.groupby(["Season", asset_type.value])["Points"] \
                        .transform(lambda s: s.fillna(0).rolling(window=rolling_window, min_periods=1).sum()) \
                        .astype(int)  # if you know result should be integer

    df[col_prc] = df.groupby(["Season", asset_type.value])["Price"] \
                        .transform(lambda s: s.fillna(0.0).rolling(window=rolling_window, min_periods=1).sum())  # float

    # Expected cumulative points-per-money (ppm) = cumulative points divided by cumulative price.
    # Use the computed cumulative columns to avoid relying on pre-computed input fields.
    # Leave division-by-zero results as NaN (e.g., 0/0 or x/0 -> inf replaced by NaN).
    df[col_ppm] = (
        df[col_pts].astype(float)
        .div(df[col_prc]) 
        .replace([np.inf, -np.inf], np.nan)
    )

    return df


def derivation_cum_tot_driver(df_input: pd.DataFrame, rolling_window: int = -1) -> pd.DataFrame:
    return derivation_cum_tot(df_input, AssetType.DRIVER, rolling_window)


def derivation_cum_tot_constructor(df_input: pd.DataFrame, rolling_window: int = -1) -> pd.DataFrame:
    return derivation_cum_tot(df_input, AssetType.CONSTRUCTOR, rolling_window)
