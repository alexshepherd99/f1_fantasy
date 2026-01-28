import pandas as pd
import functools
from pulp import LpProblem, LpMaximize, lpSum

from common import AssetType
from linear.strategy_base import StrategyBase


_FILE_BETTING_ODDS = "data/f1_betting_odds.xslx"


def odds_to_pct(odds: str) -> float:
    if (odds is None) or (odds == ""):
        return 0.0

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
    df_all = pd.read_excel(fn)
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


class StrategyBettingOdds(StrategyBase):
    """Strategy that maximises selection based on betting odds"""
    def __init__(self, *args, fn_odds: str=_FILE_BETTING_ODDS, **kwargs):
        super().__init__(*args, **kwargs)

        odds_assets_drv = load_odds(AssetType.DRIVER, self._season_year, self._race_num, fn=fn_odds)
        odds_assets_con = load_odds(AssetType.CONSTRUCTOR, self._season_year, self._race_num, fn=fn_odds)

        self._odds_assets = odds_assets_drv | odds_assets_con

    def get_problem(self) -> LpProblem:
        return None

