import pandas as pd
import numpy as np


def derivation_cum_tot_driver(df_input: pd.DataFrame) -> pd.DataFrame:
    #Ensure rows are ordered by the grouping keys and race
    df = df_input.sort_values(["Season", "Constructor", "Driver", "Race"], ignore_index=True)

    # Cumulative totals per group, treating NaN as zero
    df["Points Cumulative"] = df.groupby(["Season", "Constructor", "Driver"])["Points"] \
                        .transform(lambda s: s.fillna(0).cumsum()) \
                        .astype(int)  # if you know result should be integer

    df["Price Cumulative"] = df.groupby(["Season", "Constructor", "Driver"])["Price"] \
                        .transform(lambda s: s.fillna(0.0).cumsum())  # float

    # Expected cumulative points-per-money (ppm) = cumulative points divided by cumulative price.
    # Use the computed cumulative columns to avoid relying on pre-computed input fields.
    # Leave division-by-zero results as NaN (e.g., 0/0 or x/0 -> inf replaced by NaN).
    df["PPM Cumulative"] = (
        df["Points Cumulative"].astype(float)
        .div(df["Price Cumulative"]) 
        .replace([np.inf, -np.inf], np.nan)
    )

    return df
