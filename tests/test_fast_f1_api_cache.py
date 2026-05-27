from __future__ import annotations

import logging

import pandas as pd

from fast_f1.api import get_race_results, get_session_laps
from fast_f1.cache import setup_fastf1_cache


class FakeSession:
    def __init__(self, laps: pd.DataFrame):
        self.laps = laps

    def load(self):
        pass


class FakeRaceSession:
    def __init__(self, results: pd.DataFrame):
        self.results = results

    def load(self):
        pass


class FakeEvent:
    def __init__(self, session_map):
        self._session_map = session_map

    def get_session(self, session_code: str):
        return self._session_map[session_code]


def test_api_caches_race_results_and_session_laps(monkeypatch, tmp_path):
    setup_fastf1_cache(cache_dir=tmp_path, interactive=False)

    race_results = pd.DataFrame(
        {
            "Abbreviation": ["HAM"],
            "Status": ["Finished"],
            "Position": [1],
            "ClassifiedPosition": [1],
            "GridPosition": [2],
            "Points": [25],
            "TeamName": ["Mercedes"],
        }
    )
    session_laps = pd.DataFrame(
        {
            "Driver": ["HAM"],
            "LapTime": [80.0],
            "LapNumber": [1],
            "Stint": [1],
            "PitOutTime": [0],
            "PitInTime": [0],
            "Compound": ["C1"],
            "TyreLife": [5],
            "FreshTyre": [True],
        }
    )

    event = FakeEvent({
        "R": FakeRaceSession(race_results),
        "FP2": FakeSession(session_laps),
    })

    def fake_get_event_for_race(season, race):
        return event

    monkeypatch.setattr("fast_f1.api.get_event_for_race", fake_get_event_for_race)

    first_result = get_race_results(2025, 1)
    assert not first_result.empty
    cache_file = tmp_path / "local_cache" / "race_results_2025_1.pkl"
    assert cache_file.exists()

    monkeypatch.setattr("fast_f1.api.get_event_for_race", lambda season, race: (_ for _ in ()).throw(RuntimeError("Should not be called")))
    second_result = get_race_results(2025, 1)
    assert not second_result.empty
    assert second_result.equals(first_result)

    first_session = get_session_laps(2025, 1, "FP2")
    assert not first_session.empty
    session_cache_file = tmp_path / "local_cache" / "session_laps_2025_1_FP2.pkl"
    assert session_cache_file.exists()

    monkeypatch.setattr("fast_f1.api.get_event_for_race", lambda season, race: (_ for _ in ()).throw(RuntimeError("Should not be called")))
    second_session = get_session_laps(2025, 1, "FP2")
    assert not second_session.empty
    assert second_session.equals(first_session)


def test_api_logs_cache_hits(monkeypatch, tmp_path, caplog):
    setup_fastf1_cache(cache_dir=tmp_path, interactive=False)

    race_results = pd.DataFrame(
        {
            "Abbreviation": ["HAM"],
            "Status": ["Finished"],
            "Position": [1],
            "ClassifiedPosition": [1],
            "GridPosition": [2],
            "Points": [25],
            "TeamName": ["Mercedes"],
        }
    )
    session_laps = pd.DataFrame(
        {
            "Driver": ["HAM"],
            "LapTime": [80.0],
            "LapNumber": [1],
            "Stint": [1],
            "PitOutTime": [0],
            "PitInTime": [0],
            "Compound": ["C1"],
            "TyreLife": [5],
            "FreshTyre": [True],
        }
    )

    event = FakeEvent({
        "R": FakeRaceSession(race_results),
        "FP2": FakeSession(session_laps),
    })

    def fake_get_event_for_race(season, race):
        return event

    monkeypatch.setattr("fast_f1.api.get_event_for_race", fake_get_event_for_race)

    # Prime the cache with initial calls.
    get_race_results(2025, 1)
    get_session_laps(2025, 1, "FP2")

    monkeypatch.setattr("fast_f1.api.get_event_for_race", lambda season, race: (_ for _ in ()).throw(RuntimeError("Should not be called")))
    caplog.set_level(logging.INFO, logger="fast_f1.api")

    get_race_results(2025, 1)
    assert "Loaded cached DataFrame from" in caplog.text
    caplog.clear()

    get_session_laps(2025, 1, "FP2")
    assert "Loaded cached DataFrame from" in caplog.text


def test_api_returns_empty_dataframe_when_race_data_is_missing(monkeypatch, tmp_path, caplog):
    setup_fastf1_cache(cache_dir=tmp_path, interactive=False)

    monkeypatch.setattr(
        "fast_f1.api.get_event_for_race",
        lambda season, race: (_ for _ in ()).throw(RuntimeError("Event unavailable")),
    )

    result = get_race_results(2025, 99)
    assert result.empty
    assert "Could not load race results for season 2025 race 99" in caplog.text


def test_api_returns_empty_dataframe_when_session_data_is_missing(monkeypatch, tmp_path, caplog):
    setup_fastf1_cache(cache_dir=tmp_path, interactive=False)

    monkeypatch.setattr(
        "fast_f1.api.get_event_for_race",
        lambda season, race: (_ for _ in ()).throw(RuntimeError("Event unavailable")),
    )

    result = get_session_laps(2025, 99, "FP2")
    assert result.empty
    assert "Could not load session laps for season 2025 race 99 session FP2" in caplog.text
