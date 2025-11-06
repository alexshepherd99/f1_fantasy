import pandas as pd


def derivation_cum_tot_points(race: int, ser_points: pd.Series) -> int:
    # Cumulative Total Points up to (and including) the current race
    return ser_points[ser_points.index <= race].sum().astype(int)


def derivation_cum_tot_price(race: int, ser_price: pd.Series) -> float:
    # Cumulative Total Price up to (and including) the current race
    return ser_price[ser_price.index <= race].sum().astype(float)
