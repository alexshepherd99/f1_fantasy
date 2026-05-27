from __future__ import annotations

import pandas as pd
import pytest

from fast_f1.output import build_race_metrics


class DummySession:
    def __init__(self, laps: pd.DataFrame):
        self.laps = laps

    def load(self) -> None:
        pass


class DummyRaceSession:
    def __init__(self, results: pd.DataFrame):
        self.results = results

    def load(self) -> None:
        pass


class DummyEvent:
    def __init__(self, sessions: dict[str, DummySession | DummyRaceSession]):
        self._sessions = sessions

    def get_session(self, code: str):
        if code not in self._sessions:
            raise ValueError(f"Session {code} unavailable")
        return self._sessions[code]


def test_build_race_metrics_merges_driver_and_constructor_ranks(monkeypatch):
    season_year = 2025
    race_num = 4

    def fake_get_event_for_race(season: int, race: int):
        return DummyEvent({"FP2": DummySession(pd.DataFrame()), "FP3": DummySession(pd.DataFrame())})

    def fake_select_practice_sessions_from_event(event):
        return ("FP2", "FP3")

    fp2_laps = pd.DataFrame(
        {
            "Driver": ["HAM", "VER"],
            "LapTime": [80.0, 81.0],
            "LapNumber": [1, 1],
            "Stint": [1, 1],
            "PitOutTime": [0, 0],
            "PitInTime": [0, 0],
            "Compound": ["C1", "C1"],
            "TyreLife": [5, 5],
            "FreshTyre": [True, True],
            "Season": [season_year, season_year],
            "Race": [race_num, race_num],
            "SessionType": ["FP2", "FP2"],
        }
    )
    fp3_laps = pd.DataFrame(
        {
            "Driver": ["HAM", "VER"],
            "LapTime": [79.0, 82.0],
            "LapNumber": [1, 1],
            "Stint": [1, 1],
            "PitOutTime": [0, 0],
            "PitInTime": [0, 0],
            "Compound": ["C1", "C1"],
            "TyreLife": [4, 4],
            "FreshTyre": [True, True],
            "Season": [season_year, season_year],
            "Race": [race_num, race_num],
            "SessionType": ["FP3", "FP3"],
        }
    )
    current_results = pd.DataFrame(
        {
            "Abbreviation": ["HAM", "VER"],
            "Status": ["Finished", "Finished"],
            "Position": [1, 2],
            "ClassifiedPosition": [1, 2],
            "GridPosition": [2, 1],
            "Points": [25, 18],
            "Constructor": ["Mercedes", "Red Bull"],
            "Season": [season_year, season_year],
            "Race": [race_num, race_num],
        }
    )

    prior_results = pd.concat(
        [
            pd.DataFrame(
                {
                    "Abbreviation": ["HAM", "VER"],
                    "Points": [18, 25],
                    "Constructor": ["Mercedes", "Red Bull"],
                    "Season": [season_year, season_year],
                    "Race": [race_num - 1, race_num - 1],
                }
            ),
            pd.DataFrame(
                {
                    "Abbreviation": ["HAM", "VER"],
                    "Points": [12, 15],
                    "Constructor": ["Mercedes", "Red Bull"],
                    "Season": [season_year, season_year],
                    "Race": [race_num - 2, race_num - 2],
                }
            ),
            pd.DataFrame(
                {
                    "Abbreviation": ["HAM", "VER"],
                    "Points": [15, 18],
                    "Constructor": ["Mercedes", "Red Bull"],
                    "Season": [season_year, season_year],
                    "Race": [race_num - 3, race_num - 3],
                }
            ),
        ],
        ignore_index=True,
    )

    def fake_get_session_laps(season, race, session_type):
        if session_type == "FP2":
            return fp2_laps
        if session_type == "FP3":
            return fp3_laps
        raise ValueError("Unexpected session type")

    def fake_get_race_results(season, race):
        if race == race_num:
            return current_results
        return prior_results[prior_results["Race"] == race].reset_index(drop=True)

    monkeypatch.setattr("fast_f1.output.get_event_for_race", fake_get_event_for_race)
    monkeypatch.setattr("fast_f1.output.select_practice_sessions_from_event", fake_select_practice_sessions_from_event)
    monkeypatch.setattr("fast_f1.output.get_session_laps", fake_get_session_laps)
    monkeypatch.setattr("fast_f1.output.get_race_results", fake_get_race_results)

    metrics = build_race_metrics(season_year, race_num)

    assert "AggregateRank" in metrics.columns
    assert "RollingPointsRank" in metrics.columns
    assert "ConstructorRollingPointsRank" in metrics.columns
    assert "FP2_MinLapTime_rank" in metrics.columns
    assert "FP3_MinLapTime_rank" in metrics.columns
    assert metrics.loc[metrics["Driver"] == "HAM", "AggregateRank"].iloc[0] >= 0
    assert metrics.loc[metrics["Driver"] == "VER", "AggregateRank"].iloc[0] >= 0
