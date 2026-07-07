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


def test_build_race_metrics_adds_final_position_from_aggregate_rank(monkeypatch):
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

    assert "FinalPosition" in metrics.columns
    sorted_metrics = metrics.sort_values("AggregateRank", ascending=False).reset_index(drop=True)
    assert sorted_metrics["FinalPosition"].tolist() == [1, 2]


def test_build_race_metrics_works_when_race_results_missing(monkeypatch):
    """If official Race results are not yet published, metrics should still be computed
    using practice session drivers and prior-results constructor mapping."""
    season_year = 2026
    race_num = 6

    def fake_get_event_for_race(season: int, race: int):
        return DummyEvent({"FP2": DummySession(pd.DataFrame()), "FP3": DummySession(pd.DataFrame())})

    def fake_select_practice_sessions_from_event(event):
        return ("FP2", "FP3")

    fp2_laps = pd.DataFrame(
        {
            "Driver": ["ALO", "PER"],
            "LapTime": [85.0, 86.0],
            "LapNumber": [1, 1],
            "Stint": [1, 1],
            "PitOutTime": [0, 0],
            "PitInTime": [0, 0],
            "Compound": ["C1", "C1"],
            "TyreLife": [3, 3],
            "FreshTyre": [True, True],
            "Season": [season_year, season_year],
            "Race": [race_num, race_num],
            "SessionType": ["FP2", "FP2"],
        }
    )
    fp3_laps = pd.DataFrame(
        {
            "Driver": ["ALO", "PER"],
            "LapTime": [84.0, 87.0],
            "LapNumber": [1, 1],
            "Stint": [1, 1],
            "PitOutTime": [0, 0],
            "PitInTime": [0, 0],
            "Compound": ["C1", "C1"],
            "TyreLife": [2, 2],
            "FreshTyre": [True, True],
            "Season": [season_year, season_year],
            "Race": [race_num, race_num],
            "SessionType": ["FP3", "FP3"],
        }
    )

    # Prior results include constructor mapping for drivers
    prior_results = pd.concat(
        [
            pd.DataFrame(
                {
                    "Abbreviation": ["ALO", "PER"],
                    "Points": [10, 8],
                    "Constructor": ["Alfa", "Perse"],
                    "Season": [season_year, season_year],
                    "Race": [race_num - 1, race_num - 1],
                }
            ),
            pd.DataFrame(
                {
                    "Abbreviation": ["ALO", "PER"],
                    "Points": [12, 6],
                    "Constructor": ["Alfa", "Perse"],
                    "Season": [season_year, season_year],
                    "Race": [race_num - 2, race_num - 2],
                }
            ),
            pd.DataFrame(
                {
                    "Abbreviation": ["ALO", "PER"],
                    "Points": [9, 10],
                    "Constructor": ["Alfa", "Perse"],
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
        # Return empty for current race to simulate unpublished results
        if race == race_num:
            return pd.DataFrame()
        return prior_results[prior_results["Race"] == race].reset_index(drop=True)

    monkeypatch.setattr("fast_f1.output.get_event_for_race", fake_get_event_for_race)
    monkeypatch.setattr("fast_f1.output.select_practice_sessions_from_event", fake_select_practice_sessions_from_event)
    monkeypatch.setattr("fast_f1.output.get_session_laps", fake_get_session_laps)
    monkeypatch.setattr("fast_f1.output.get_race_results", fake_get_race_results)

    metrics = build_race_metrics(season_year, race_num)

    # Drivers derived from practice should be present
    assert set(metrics["Driver"]) >= {"ALO", "PER"}
    # Constructor mapping from prior results should be present
    assert "ConstructorRollingPointsRank" in metrics.columns
    assert "AggregateRank" in metrics.columns

    rank_columns = [
        col for col in metrics.columns
        if col != "AggregateRank" and (col.endswith("Rank") or col.endswith("_rank"))
    ]
    assert "ConstructorRollingPointsRank" in rank_columns

    for driver in ["ALO", "PER"]:
        driver_row = metrics[metrics["Driver"] == driver].iloc[0]
        expected_aggregate = sum(driver_row[col] for col in rank_columns)
        assert driver_row["AggregateRank"] == pytest.approx(expected_aggregate)
