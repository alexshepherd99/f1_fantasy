"""Integration tests validating FastF1 API session type names.

These tests fetch real data from the FastF1 API for known race weekends:
- 2025 race 1 (Australia): normal weekend (FP1, FP2, FP3, Qualifying, Race)
- 2025 race 2 (China): sprint weekend (FP1, SprintQualifying, Sprint, Race)

They confirm that session type names match our weekend detection expectations.
"""

from __future__ import annotations

import logging

import fastf1
import pandas as pd
import pytest

from fast_f1.api import get_available_sessions_from_event, get_race_results, get_session_laps
from fast_f1.weekend import determine_practice_sessions, is_sprint_weekend

logger = logging.getLogger(__name__)


def test_australia_2025_is_normal_weekend():
    """Confirm 2025 Australia (race 1) is a normal weekend with FP2/FP3."""
    schedule = fastf1.get_event_schedule(2025, include_testing=False)
    event = schedule[schedule["RoundNumber"] == 1].iloc[0]
    
    sessions = get_available_sessions_from_event(event)
    logger.info(f"Australia 2025 sessions: {sessions}")
    
    assert is_sprint_weekend(sessions) is False
    assert determine_practice_sessions(sessions) == ("FP2", "FP3")
    # Verify all expected sessions are present
    assert "FP1" in sessions
    assert "FP2" in sessions
    assert "FP3" in sessions
    assert "Qualifying" in sessions
    assert "Race" in sessions


def test_china_2025_is_sprint_weekend():
    """Confirm 2025 China (race 2) is a sprint weekend with FP1/SprintQualifying."""
    schedule = fastf1.get_event_schedule(2025, include_testing=False)
    event = schedule[schedule["RoundNumber"] == 2].iloc[0]
    
    sessions = get_available_sessions_from_event(event)
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


def test_get_race_results_returns_expected_columns():
    df = get_race_results(2025, 1)
    assert isinstance(df, pd.DataFrame)
    assert set(df.columns) >= {
        "Season",
        "Race",
        "Abbreviation",
        "Status",
        "Position",
        "ClassifiedPosition",
        "GridPosition",
        "Points",
    }
    assert df["Season"].nunique() == 1
    assert df["Race"].nunique() == 1
    assert df["Season"].iloc[0] == 2025
    assert df["Race"].iloc[0] == 1


def test_get_session_laps_returns_expected_columns():
    df = get_session_laps(2025, 1, "FP2")
    assert isinstance(df, pd.DataFrame)
    assert "SessionType" in df.columns
    assert df["SessionType"].nunique() == 1
    assert df["SessionType"].iloc[0] == "FP2"
    assert set(df.columns) >= {
        "Season",
        "Race",
        "SessionType",
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
    assert not df.empty
