"""Integration tests validating the live FastF1 API.

These tests hit the network on purpose: their job is to confirm the API still
returns the sessions, columns and values the rest of ``fast_f1`` is built on.
They call FastF1 directly rather than through ``fast_f1.api``, so a failure
here means upstream changed rather than one of our wrappers.

Two known 2025 weekends are used as fixtures:
- race 1 (Australia): normal weekend (FP1, FP2, FP3, Qualifying, Race)
- race 2 (China): sprint weekend (FP1, SprintQualifying, Sprint, Race)
"""

from __future__ import annotations

import logging

import fastf1
import pandas as pd
import pytest

from fast_f1.api import get_available_sessions_from_event
from fast_f1.cache import get_default_config_file_location, get_persisted_cache_directory
from fast_f1.weekend import determine_practice_sessions, is_sprint_weekend

logger = logging.getLogger(__name__)


@pytest.fixture(scope="module", autouse=True)
def real_fastf1_cache():
    """Serve this module's API calls from the application cache.

    ``tests/conftest.py`` points the cache config file at a tmp dir so no test
    reads or writes the real cache. These tests are the exception - they are
    the only ones that reach the API, so they should share the cache set up in
    ``.fastf1_cache_dir`` instead of quietly filling FastF1's own default one.

    Where no cache directory is configured or it is not currently reachable,
    fall back to FastF1's default rather than failing. FastF1's cache stays
    enabled for the rest of the session, which is harmless: no other test
    touches the API, and the config file remains isolated by ``conftest``.
    """
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("fast_f1.cache.CACHE_LOCATION_CONFIG_FILE", get_default_config_file_location())
        cache_dir = get_persisted_cache_directory()

    if cache_dir is None or not cache_dir.is_dir():
        logger.warning("No application FastF1 cache available; using the FastF1 default")
    else:
        fastf1.Cache.enable_cache(str(cache_dir))


def _get_event(season_year: int, race_num: int):
    """Return the FastF1 event for one race of a season."""
    schedule = fastf1.get_event_schedule(season_year, include_testing=False)
    return schedule[schedule["RoundNumber"] == race_num].iloc[0]


@pytest.fixture(scope="module")
def australia_2025_event():
    return _get_event(2025, 1)


@pytest.fixture(scope="module")
def china_2025_event():
    return _get_event(2025, 2)


def test_australia_2025_is_normal_weekend(australia_2025_event):
    """Confirm 2025 Australia (race 1) is a normal weekend with FP2/FP3."""
    sessions = get_available_sessions_from_event(australia_2025_event)
    logger.info(f"Australia 2025 sessions: {sessions}")

    assert is_sprint_weekend(sessions) is False
    assert determine_practice_sessions(sessions) == ("FP2", "FP3")
    # Verify all expected sessions are present
    assert "FP1" in sessions
    assert "FP2" in sessions
    assert "FP3" in sessions
    assert "Qualifying" in sessions
    assert "Race" in sessions


def test_china_2025_is_sprint_weekend(china_2025_event):
    """Confirm 2025 China (race 2) is a sprint weekend with FP1/SprintQualifying."""
    sessions = get_available_sessions_from_event(china_2025_event)
    logger.info(f"China 2025 sessions: {sessions}")

    assert is_sprint_weekend(sessions) is True
    assert determine_practice_sessions(sessions) == ("FP1", "SprintQualifying")
    # Verify sprint weekend structure for 2025
    assert "FP1" in sessions
    assert "SprintQualifying" in sessions
    assert "Race" in sessions
    # Normal weekends have FP2/FP3, sprint weekends should not (in 2025 China format)
    assert "FP2" not in sessions
    assert "FP3" not in sessions


def test_race_results_expose_expected_columns_and_values(australia_2025_event):
    """Confirm race results carry the columns and the finishing order we expect."""
    race = australia_2025_event.get_session("R")
    # Results come with the session either way; the rest is data we never read
    race.load(laps=False, telemetry=False, weather=False, messages=False)

    results = race.results
    assert isinstance(results, pd.DataFrame)
    assert set(results.columns) >= {
        "Abbreviation",
        "Status",
        "Position",
        "ClassifiedPosition",
        "GridPosition",
        "Points",
        "TeamName",
    }
    assert len(results) == 20

    # Known result: Norris won the 2025 Australian Grand Prix for McLaren
    winner = results.loc[results["Position"] == 1].iloc[0]
    assert winner["Abbreviation"] == "NOR"
    assert winner["TeamName"] == "McLaren"
    assert winner["Points"] == 25.0
    assert winner["Status"] == "Finished"


def test_practice_laps_expose_expected_columns(australia_2025_event):
    """Confirm practice laps carry the columns and types the metrics rely on."""
    session = australia_2025_event.get_session("FP2")
    # Only the laps are needed; telemetry is by far the slowest part of a load
    session.load(laps=True, telemetry=False, weather=False, messages=False)

    laps = session.laps
    assert isinstance(laps, pd.DataFrame)
    assert not laps.empty
    assert set(laps.columns) >= {
        "Driver",
        "LapTime",
        "LapNumber",
        "Stint",
        "PitOutTime",
        "PitInTime",
        "Compound",
        "TyreLife",
        "FreshTyre",
    }

    # metrics.py compares lap times against a 107% threshold, so these must
    # stay as timedeltas rather than becoming strings upstream
    assert laps["LapTime"].dtype == "timedelta64[ns]"
    assert set(laps["Compound"].dropna().unique()) <= {
        "SOFT",
        "MEDIUM",
        "HARD",
        "INTERMEDIATE",
        "WET",
        "UNKNOWN",
    }
