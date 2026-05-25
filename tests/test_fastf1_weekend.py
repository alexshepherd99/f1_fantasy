from __future__ import annotations

import pytest

from fast_f1.weekend import determine_practice_sessions, is_sprint_weekend


def test_is_sprint_weekend_true():
    sessions = ["FP1", "SprintQualifying", "Sprint", "Race"]
    assert is_sprint_weekend(sessions) is True


def test_is_sprint_weekend_false():
    sessions = ["FP1", "FP2", "FP3", "Qualifying", "Race"]
    assert is_sprint_weekend(sessions) is False


def test_determine_practice_sessions_normal():
    sessions = ["FP1", "FP2", "FP3", "Qualifying", "Race"]
    assert determine_practice_sessions(sessions) == ("FP2", "FP3")


def test_determine_practice_sessions_sprint():
    sessions = ["FP1", "SprintQualifying", "Sprint", "Race"]
    assert determine_practice_sessions(sessions) == ("FP1", "SprintQualifying")


def test_determine_practice_sessions_missing_raises():
    sessions = ["FP2", "Qualifying", "Race"]
    with pytest.raises(RuntimeError):
        determine_practice_sessions(sessions)
