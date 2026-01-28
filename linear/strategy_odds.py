import pandas as pd
import functools

from common import AssetType

_FILE_BETTING_ODDS = "data/f1_betting_odds.csv"


def odds_to_pct(odds: str) -> float:
    if odds is None:
        raise ValueError(f"odds_to_pct invalid input {odds}")

    odds = odds.replace(":", "/")
    odds = odds.replace("-", "/")
    
    if odds.count("/") != 1:
        raise ValueError(f"odds_to_pct invalid input {odds}")

    odds_values = odds.split("/")
    if len(odds_values) != 2:
        raise ValueError(f"odds_to_pct invalid input {odds}")
    
    odds_left = int(odds_values[0])
    odds_right = int(odds_values[1])

    if odds_right > odds_left:
        raise ValueError(f"odds_to_pct invalid input {odds}")
    
    if (odds_right == 0) or (odds_left == 0):
        raise ValueError(f"odds_to_pct invalid input {odds}")

    return 1 / (odds_left / odds_right)


@functools.cache
def load_odds(ass_typ: AssetType, season_year: int, race_num: int, fn: str=_FILE_BETTING_ODDS) -> dict[str, float]:
    # Load and filter
    df_all = pd.read_csv(fn)
    df_all = df_all[df_all["Season"] == season_year]
    df_all = df_all[df_all["Race"] == race_num]

    # Select asset type
    if ass_typ == AssetType.CONSTRUCTOR:
        df_all = df_all[df_all["Driver"].isna()]
    elif ass_typ == AssetType.DRIVER:
        df_all = df_all[~df_all["Driver"].isna()]
        df_all["Driver"] = df_all["Driver"].astype(str) + "@" + df_all["Constructor"].astype(str)
    
    # Process Odds column
    df_all["Odds"] = df_all["Odds"].apply(odds_to_pct)

    # Convert to dictionary
    df_all = df_all[[ass_typ.value, "Odds"]]
    df_all = df_all.set_index(ass_typ.value)
    return df_all["Odds"].to_dict()
