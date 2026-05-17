from __future__ import annotations

import pandas as pd


def get_race_results(season_year: int, race_num: int) -> pd.DataFrame:
    """Return race results for a given season and race.

    This is a placeholder for the eventual FastF1 wrapper. The legacy
    implementation in ``external_data.get_data`` should be used as the
    production reference when implementing this function.
    """
    raise NotImplementedError("get_race_results is not implemented yet")


def get_session_laps(season_year: int, race_num: int, session_type: str) -> pd.DataFrame:
    """Return session laps for a given season, race, and session."""
    raise NotImplementedError("get_session_laps is not implemented yet")
