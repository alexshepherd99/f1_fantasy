from __future__ import annotations

import logging

import pandas as pd
import pytest

from fast_f1.api import get_event_for_race, get_race_results, get_session_laps
from fast_f1.cache import setup_fastf1_cache


def _event_schedule() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "RoundNumber": [1, 2],
            "EventName": ["Australian Grand Prix", "Chinese Grand Prix"],
        }
    )


class FakeSession:
    def __init__(self, laps: pd.DataFrame):
        self.laps = laps
        self.load_kwargs = None

    def load(self, **kwargs):
        self.load_kwargs = kwargs


class FakeRaceSession:
    def __init__(self, results: pd.DataFrame):
        self.results = results
        self.load_kwargs = None

    def load(self, **kwargs):
        self.load_kwargs = kwargs


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


def test_api_loads_only_the_session_data_it_reads(monkeypatch, tmp_path):
    """Telemetry and weather are never read and dominate load time, so stay off.

    Race control messages stay on - they are what populate a lap's Deleted flag.
    """
    setup_fastf1_cache(cache_dir=tmp_path, interactive=False)

    race_session = FakeRaceSession(
        pd.DataFrame(
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
    )
    practice_session = FakeSession(
        pd.DataFrame(
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
    )

    event = FakeEvent({"R": race_session, "FP2": practice_session})
    monkeypatch.setattr("fast_f1.api.get_event_for_race", lambda season, race: event)

    get_race_results(2025, 1)
    get_session_laps(2025, 2, "FP2")

    for session in (race_session, practice_session):
        assert session.load_kwargs is not None
        assert session.load_kwargs["telemetry"] is False
        assert session.load_kwargs["weather"] is False
        assert session.load_kwargs["messages"] is True

    # Race results need no laps; a laps request obviously does
    assert race_session.load_kwargs["laps"] is False
    assert practice_session.load_kwargs["laps"] is True


def test_api_caches_the_event_schedule_once_per_season(monkeypatch, tmp_path):
    """One schedule fetch serves every race in that season."""
    setup_fastf1_cache(cache_dir=tmp_path, interactive=False)

    fetches = []

    def fake_get_event_schedule(season_year, include_testing=False):
        fetches.append(season_year)
        return _event_schedule()

    monkeypatch.setattr("fastf1.get_event_schedule", fake_get_event_schedule)

    first_event = get_event_for_race(2025, 1)
    assert first_event["EventName"] == "Australian Grand Prix"
    assert (tmp_path / "local_cache" / "event_schedule_2025.pkl").exists()

    monkeypatch.setattr(
        "fastf1.get_event_schedule",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("Should not be called")),
    )
    assert get_event_for_race(2025, 1)["EventName"] == "Australian Grand Prix"
    assert get_event_for_race(2025, 2)["EventName"] == "Chinese Grand Prix"
    assert fetches == [2025]


def test_api_does_not_cache_an_empty_event_schedule(monkeypatch, tmp_path):
    """An empty schedule is a failed fetch, not a season with no races."""
    setup_fastf1_cache(cache_dir=tmp_path, interactive=False)

    monkeypatch.setattr(
        "fastf1.get_event_schedule",
        lambda season_year, include_testing=False: pd.DataFrame(columns=["RoundNumber"]),
    )

    with pytest.raises(ValueError):
        get_event_for_race(2025, 1)
    assert not (tmp_path / "local_cache" / "event_schedule_2025.pkl").exists()


def test_api_logs_event_schedule_cache_hits(monkeypatch, tmp_path, caplog):
    setup_fastf1_cache(cache_dir=tmp_path, interactive=False)

    monkeypatch.setattr(
        "fastf1.get_event_schedule",
        lambda season_year, include_testing=False: _event_schedule(),
    )

    # Prime the cache with an initial call.
    get_event_for_race(2025, 1)

    monkeypatch.setattr(
        "fastf1.get_event_schedule",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("Should not be called")),
    )
    caplog.set_level(logging.INFO, logger="fast_f1.api")

    get_event_for_race(2025, 1)
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
