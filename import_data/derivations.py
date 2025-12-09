import pandas as pd
import numpy as np
from enum import StrEnum

from common import AssetType


class DerivationType(StrEnum):
    POINTS_CUMULATIVE = "Points Cumulative"
    PRICE_CUMULATIVE = "Price Cumulative"
    PPM_CUMULATIVE = "PPM Cumulative"
    P2PM_CUMULATIVE = "P2PM Cumulative"


def get_derivation_name(deriv_type: DerivationType, deriv_param: int) -> str:
    if deriv_param == -1:
        return f"{deriv_type.value}"
    else:
        return f"{deriv_type.value} ({deriv_param})"


def derivation_cum_tot(
        df_input: pd.DataFrame,
        asset_type: AssetType,
        rolling_window: int = -1
    ) -> pd.DataFrame:

    col_pts = get_derivation_name(DerivationType.POINTS_CUMULATIVE, rolling_window)
    col_prc = get_derivation_name(DerivationType.PRICE_CUMULATIVE, rolling_window)
    col_ppm = get_derivation_name(DerivationType.PPM_CUMULATIVE, rolling_window)
    col_p2pm = get_derivation_name(DerivationType.P2PM_CUMULATIVE, rolling_window)

    # If no rolling window, assume total cumulative
    if rolling_window == -1:
        rolling_window = len(df_input.index)

    # Just columns of interest
    df = df_input[["Season", "Race", asset_type.value, "Points", "Price"]]

    # Group up assets, there will be duplication for drivers across constructors
    df = df.groupby(["Season", asset_type.value, "Race"]).sum().reset_index()

    # Ensure rows are ordered by the grouping keys and race
    df = df.sort_values(["Season", asset_type.value, "Race"], ignore_index=True)

    # Cumulative totals per group, treating NaN as zero
    # Shift by 1 to exclude current value and sum previous values
    df[col_pts] = df.groupby(["Season", asset_type.value])["Points"] \
                        .transform(lambda s: s.fillna(0).shift(1).rolling(window=rolling_window, min_periods=1).sum()) \
                        .fillna(0) \
                        .astype(int)  # if you know result should be integer

    df[col_prc] = df.groupby(["Season", asset_type.value])["Price"] \
                        .transform(lambda s: s.fillna(0.0).shift(1).rolling(window=rolling_window, min_periods=1).sum())  # float

    # Expected cumulative points-per-money (ppm) = cumulative points divided by cumulative price.
    # Use the computed cumulative columns to avoid relying on pre-computed input fields.
    # Leave division-by-zero results as NaN (e.g., 0/0 or x/0 -> inf replaced by NaN).
    df[col_ppm] = (
        df[col_pts].astype(float)
        .div(df[col_prc]) 
        .replace([np.inf, -np.inf], np.nan)
    )

    # Points squared per million enhanced the above to give greater emphasis to points scored, but still reflecting good
    # value drivers who return a high ppm
    df[col_p2pm] = (
        (df[col_pts].astype(float) * df[col_pts].astype(float))
        .div(df[col_prc]) 
        .replace([np.inf, -np.inf], np.nan)
    )

    return df


def derivation_cum_tot_driver(df_input: pd.DataFrame, rolling_window: int = -1) -> pd.DataFrame:
    return derivation_cum_tot(df_input, AssetType.DRIVER, rolling_window)


def derivation_cum_tot_constructor(df_input: pd.DataFrame, rolling_window: int = -1) -> pd.DataFrame:
    return derivation_cum_tot(df_input, AssetType.CONSTRUCTOR, rolling_window)


def get_race_driver_constructor_pairs(df_merged_point_price: pd.DataFrame) -> pd.DataFrame:
    df_merged_point_price = df_merged_point_price[df_merged_point_price["Price"].notna()]
    
    df_merged_point_price = df_merged_point_price[
        [
            "Constructor",
            "Driver",
            "Race",
            "Season",
        ]
    ]

    return df_merged_point_price
