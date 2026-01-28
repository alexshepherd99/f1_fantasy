import pandas as pd
import functools
from pulp import LpProblem, LpMaximize, lpSum

from common import AssetType
from linear.strategy_base import StrategyBase, VarType


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

    # Process Odds column
    df_all["Odds"] = df_all["Odds"].apply(odds_to_pct)

    # Select asset type
    if ass_typ == AssetType.CONSTRUCTOR:
        # Constructor odds in this case is actually constructor value, so it the sum of the driver odds (value)
        df_all = df_all.groupby("Constructor").sum().reset_index()
    elif ass_typ == AssetType.DRIVER:
        df_all = df_all[~df_all["Driver"].isna()]
        df_all["Driver"] = df_all["Driver"].astype(str) + "@" + df_all["Constructor"].astype(str)

    # Convert to dictionary
    df_all = df_all[[ass_typ.value, "Odds"]]
    df_all = df_all.set_index(ass_typ.value)
    return df_all["Odds"].to_dict()


class StrategyBettingOdds(StrategyBase):
    """Strategy that maximises selection based on betting odds"""
    def __init__(self, *args, fn_odds: str=_FILE_BETTING_ODDS, **kwargs):
        super().__init__(*args, **kwargs)

        # Load and process odds
        odds_assets_drv = load_odds(AssetType.DRIVER, self._season_year, self._race_num, fn=fn_odds)
        odds_assets_con = load_odds(AssetType.CONSTRUCTOR, self._season_year, self._race_num, fn=fn_odds)
        self._odds_assets = odds_assets_drv | odds_assets_con

        # Ensure anything without odds, i.e. it's worth nothing
        all_assets = self._all_available_drivers + self._all_available_constructors + self._team_drivers + self._team_constructors
        for a in all_assets:
            if self._odds_assets.get(a) is None:
                self._odds_assets[a] = 0.0


    def get_problem(self) -> LpProblem:
        """Build an LP problem whose objective is the best odds."""
        problem = LpProblem(self.__class__.__name__, LpMaximize)

        # Odds values as based on the team selection, using the LP variables already provided by the base class
        odds_drivers = [self._odds_assets[i] * self._lp_variables[VarType.TeamDrivers][i] for i in self._all_available_drivers]
        odds_constructors = [self._odds_assets[i] * self._lp_variables[VarType.TeamConstructors][i] for i in self._all_available_constructors]

        # Variable for total odds value
        self._lp_variables[VarType.OptimiseMax] = lpSum(odds_drivers + odds_constructors)

        # Optimise for this
        problem += self._lp_variables[VarType.OptimiseMax]
        return problem


    def get_drs_driver(self) -> str:
        """Select a driver from the chosen team to assign DRS based on maximum odds value

        Returns an empty string if no suitable driver has points data.
        """
        max_odds = 0.0
        max_driver = ""

        for d in self._all_available_drivers:
            # This will only be called after the strategy has run, so self._lp_variables[VarType.TeamDrivers] will
            # represent the selected drivers
            if self._lp_variables[VarType.TeamDrivers][d].value() > 0:
                if self._odds_assets[d] > max_odds:
                    max_odds = self._odds_assets[d]
                    max_driver = d

        # If we had no odds to work with, ensure we return no driver.  This will allow the default team selection
        # to choose, which will pick driver with max current value.
        if max_odds == 0.0:
            return ""
        else:
            return max_driver
