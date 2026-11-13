from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import pytest

from fast_f1.weekend import determine_practice_sessions, is_sprint_weekend, unrun_sessions


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


def test_is_sprint_weekend_true_for_sprint_shootout():
    sessions = ["FP1", "SprintShootout", "Qualifying", "Race"]
    assert is_sprint_weekend(sessions) is True


def test_determine_practice_sessions_sprint_shootout_uses_fp1_only():
    # Teams locked at Friday's Grand Prix qualifying, before Saturday's Shootout
    sessions = ["FP1", "SprintShootout", "Qualifying", "Race"]
    assert determine_practice_sessions(sessions) == ("FP1",)


def test_determine_practice_sessions_sprint_shootout_missing_fp1_raises():
    sessions = ["SprintShootout", "Qualifying", "Race"]
    with pytest.raises(RuntimeError, match=r"\['FP1'\]"):
        determine_practice_sessions(sessions)


def test_determine_practice_sessions_missing_raises():
    sessions = ["FP2", "Qualifying", "Race"]
    with pytest.raises(RuntimeError):
        determine_practice_sessions(sessions)


def _event(names: list[str], first_start: str = "2026-11-20 00:30") -> pd.Series:
    """A schedule row in FastF1's shape, its sessions a day apart, with naive UTC times."""
    row = {}
    for i, name in enumerate(names, start=1):
        row[f"Session{i}"] = name
        row[f"Session{i}DateUtc"] = pd.Timestamp(first_start) + pd.Timedelta(days=i - 1)
    return pd.Series(row)


_CONVENTIONAL = ["Practice 1", "Practice 2", "Practice 3", "Qualifying", "Race"]
_SPRINT = ["Practice 1", "Sprint Qualifying", "Sprint", "Qualifying", "Race"]
_SHOOTOUT_2023 = ["Practice 1", "Qualifying", "Sprint Shootout", "Sprint", "Race"]


def _utc(text: str) -> datetime:
    return datetime.fromisoformat(text).replace(tzinfo=timezone.utc)


@pytest.mark.parametrize("names, now, expected", [
    (_CONVENTIONAL, "2026-11-20 12:00", ["FP2", "FP3"]),
    (_CONVENTIONAL, "2026-11-21 12:00", ["FP3"]),
    (_CONVENTIONAL, "2026-11-22 12:00", []),
    (_SPRINT, "2026-11-20 12:00", ["SQ"]),
    (_SPRINT, "2026-11-19 12:00", ["FP1", "SQ"]),
    (_SHOOTOUT_2023, "2026-11-20 12:00", []),
], ids=["conventional, FP1 run", "conventional, FP2 run", "conventional, all run", "sprint, FP1 run",
        "sprint, none run", "2023 sprint, FP1 run"])
def test_unrun_sessions_lists_the_required_sessions_not_yet_run(names, now, expected):
    assert list(unrun_sessions(_event(names), _utc(now))) == expected


def test_unrun_sessions_gives_each_start():
    assert unrun_sessions(_event(_CONVENTIONAL), _utc("2026-11-21 12:00")) == {"FP3": _utc("2026-11-22 00:30")}


def test_unrun_sessions_counts_a_session_as_run_an_hour_after_its_start():
    event = _event(_CONVENTIONAL)

    assert list(unrun_sessions(event, _utc("2026-11-22 01:29"))) == ["FP3"]
    assert list(unrun_sessions(event, _utc("2026-11-22 01:30"))) == []


def test_unrun_sessions_raises_when_the_weekend_lacks_a_required_session():
    with pytest.raises(RuntimeError, match="FP3"):
        unrun_sessions(_event(["Practice 1", "Practice 2", "Qualifying", "Race"]), _utc("2026-11-25 00:00"))
