import pandas as pd
import numpy as np
from enum import StrEnum

from common import AssetType


class DerivationType(StrEnum):
    """Enumeration of supported derivation types.

    Members represent computed cumulative metrics that can be added to
    point/price dataframes. Values are human-readable names used
    to label derived columns added to output dataframes.
    """

    POINTS_CUMULATIVE = "Points Cumulative"
    PRICE_CUMULATIVE = "Price Cumulative"
    PPM_CUMULATIVE = "PPM Cumulative"
    P2PM_CUMULATIVE = "P2PM Cumulative"


def get_derivation_name(deriv_type: DerivationType, deriv_param: int) -> str:
    """Return a standardized column name for a derivation.

    Args:
        deriv_type: A member of :class:`DerivationType` indicating the
            kind of derived metric.
        deriv_param: Integer parameter for the derivation (for example
            a rolling window size). A value of ``-1`` denotes no
            parameter and results in the plain derivation name.

    Returns:
        A formatted string to use as a dataframe column name for the
        requested derivation.
    """

    if deriv_param == -1:
        return f"{deriv_type.value}"
    else:
        return f"{deriv_type.value} ({deriv_param})"


def derivation_cum_tot(
        df_input: pd.DataFrame,
        asset_type: AssetType,
        rolling_window: int = -1
    ) -> pd.DataFrame:
    """Compute cumulative derived metrics grouped by season and asset.

    For each asset (driver or constructor) this function computes the
    cumulative totals (excluding the current race) for points and price
    and derives points-per-money metrics from those cumulative values.

    The input dataframe is expected to contain at least the columns:
    ``Season``, ``Race``, the asset-type column (e.g. ``Driver`` or
    ``Constructor``), ``Points``, and ``Price``. The returned dataframe
    will be grouped and sorted by ``Season``, the asset column, and
    ``Race`` and will include additional columns named using
    :func:`get_derivation_name` for the requested ``rolling_window``.

    Args:
        df_input: Source dataframe containing race-level points and
            prices for assets.
        asset_type: An :class:`AssetType` enum value specifying whether
            to aggregate by driver or constructor.
        rolling_window: Number of previous races to include when
            computing the cumulative totals. Use ``-1`` to include all
            previous races in the season (default: ``-1``).

    Returns:
        A dataframe with grouped rows and additional cumulative
        derivation columns for points, price, ppm and p2pm.
    """
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
    # value drivers who return a high ppm.
    # Use an absolute value for one of the points numbers, to ensure that negative points gives a negative squared value.
    df[col_p2pm] = (
        (df[col_pts].astype(float) * abs(df[col_pts].astype(float)))
        .div(df[col_prc]) 
        .replace([np.inf, -np.inf], np.nan)
    )

    return df


def derivation_cum_tot_driver(df_input: pd.DataFrame, rolling_window: int = -1) -> pd.DataFrame:
    """Convenience wrapper to compute cumulative derivations for drivers.

    See :func:`derivation_cum_tot` for behavior and expected input
    columns. This simply calls that function with ``AssetType.DRIVER``.
    """

    return derivation_cum_tot(df_input, AssetType.DRIVER, rolling_window)


def derivation_cum_tot_constructor(df_input: pd.DataFrame, rolling_window: int = -1) -> pd.DataFrame:
    """Convenience wrapper to compute cumulative derivations for constructors.

    See :func:`derivation_cum_tot` for behavior and expected input
    columns. This simply calls that function with
    ``AssetType.CONSTRUCTOR``.
    """

    return derivation_cum_tot(df_input, AssetType.CONSTRUCTOR, rolling_window)


def get_race_driver_constructor_pairs(df_merged_point_price: pd.DataFrame) -> pd.DataFrame:
    """Extract race-level driver/constructor pairs with valid prices.

    Filters out rows with missing ``Price`` values and returns a
    reduced dataframe containing the columns: ``Constructor``,
    ``Driver``, ``Race``, and ``Season``. This is useful for building
    mappings between drivers and constructors per race.

    Args:
        df_merged_point_price: Dataframe containing at minimum the
            columns used for filtering and selection (including
            ``Price``).

    Returns:
        A filtered dataframe with the four columns listed above.
    """

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
