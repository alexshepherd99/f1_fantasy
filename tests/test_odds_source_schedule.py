from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from odds_source.page import SavedOddsPage
from odds_source.schedule import CapturePoint, find_capture_point

_CONVENTIONAL = ("Practice 1", "Practice 2", "Practice 3", "Qualifying", "Race")
_SPRINT = ("Practice 1", "Sprint Qualifying", "Sprint", "Qualifying", "Race")


def _utc(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 11, day, hour, minute, tzinfo=timezone.utc)


def _event(round_number: int, sessions: tuple[str, ...], starts: list[datetime]) -> dict:
    """One schedule row as FastF1 gives it: session names and naive UTC start times."""
    row = {"RoundNumber": round_number, "EventName": f"Round {round_number} Grand Prix"}
    for i, (name, start) in enumerate(zip(sessions, starts), start=1):
        row[f"Session{i}"] = name
        row[f"Session{i}DateUtc"] = pd.Timestamp(start).tz_convert(None)
    return row


# Round 20 runs Friday 6th to Sunday 8th November, the race at 17:00 UTC.
_ROUND_20_STARTS = [_utc(6, 15, 30), _utc(6, 19), _utc(7, 14, 30), _utc(7, 18), _utc(8, 17)]
_SCHEDULE = pd.DataFrame([
    _event(19, _CONVENTIONAL, [start - timedelta(days=7) for start in _ROUND_20_STARTS]),
    _event(20, _CONVENTIONAL, _ROUND_20_STARTS),
])


def _page(saved_at: datetime, race_start: datetime = _utc(8, 20)) -> SavedOddsPage:
    # Oddschecker gave Brazil 2026 a start three hours after FastF1's
    return SavedOddsPage(race_name="Round 20 Grand Prix", race_start=race_start, saved_at=saved_at, prices={})


def test_finds_the_race_whose_start_is_near_the_pages():
    point = find_capture_point(_page(saved_at=_utc(8, 16)), _SCHEDULE)

    assert point == CapturePoint(season=2026, race=20, column="Odds_Q")


def test_stops_when_no_race_starts_near_the_pages():
    page = _page(saved_at=_utc(1, 12), race_start=_utc(4, 17))

    with pytest.raises(ValueError, match="No race"):
        find_capture_point(page, _SCHEDULE)


def test_stops_when_the_page_was_saved_after_the_race_started():
    with pytest.raises(ValueError, match="after the race"):
        find_capture_point(_page(saved_at=_utc(8, 17, 1)), _SCHEDULE)


def test_a_page_saved_before_first_practice_is_pre_fp1():
    assert find_capture_point(_page(saved_at=_utc(6, 9)), _SCHEDULE).column == "Odds_PreFP1"


def test_a_session_counts_an_hour_after_its_start():
    # Second practice starts at 19:00
    assert find_capture_point(_page(saved_at=_utc(6, 19, 59)), _SCHEDULE).column == "Odds_FP1"
    assert find_capture_point(_page(saved_at=_utc(6, 20)), _SCHEDULE).column == "Odds_FP2"


def test_third_practice_has_its_own_column():
    assert find_capture_point(_page(saved_at=_utc(7, 16)), _SCHEDULE).column == "Odds_FP3"


def test_sprint_weekends_use_the_sprint_columns():
    schedule = pd.DataFrame([_event(20, _SPRINT, _ROUND_20_STARTS)])

    # Sprint Qualifying on Friday at 19:00, the sprint on Saturday at 14:30
    assert find_capture_point(_page(saved_at=_utc(7, 9)), schedule).column == "Odds_SQ"
    assert find_capture_point(_page(saved_at=_utc(7, 16)), schedule).column == "Odds_Sprint"


def test_stops_on_a_session_it_has_no_column_for():
    schedule = pd.DataFrame([_event(20, ("Practice 1", "Hyperpole", "Practice 3", "Qualifying", "Race"), _ROUND_20_STARTS)])

    with pytest.raises(ValueError, match="Hyperpole"):
        find_capture_point(_page(saved_at=_utc(8, 16)), schedule)
