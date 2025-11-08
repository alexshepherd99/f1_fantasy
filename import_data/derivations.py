import pandas as pd


def derivation_cum_tot_driver(df_input: pd.DataFrame) -> pd.DataFrame:
    #Ensure rows are ordered by the grouping keys and race
    df = df_input.sort_values(["Season", "Constructor", "Driver", "Race"], ignore_index=True)

    # Cumulative totals per group, treating NaN as zero
    df["Points Cumulative"] = df.groupby(["Season", "Constructor", "Driver"])["Points"] \
                        .transform(lambda s: s.fillna(0).cumsum()) \
                        .astype(int)  # if you know result should be integer

    df["Price Cumulative"] = df.groupby(["Season", "Constructor", "Driver"])["Price"] \
                        .transform(lambda s: s.fillna(0.0).cumsum())  # float

    return df
