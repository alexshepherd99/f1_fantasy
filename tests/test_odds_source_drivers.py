import pandas as pd
import pytest

from odds_source.drivers import OddsEntry, load_entry_list, match_drivers
from odds_source.schedule import CapturePoint


def _entry_list(*drivers: tuple[str, str, str, str]) -> pd.DataFrame:
    """A driver list as `fast_f1.api.get_session_drivers` returns it."""
    return pd.DataFrame(drivers, columns=["Abbreviation", "TeamName", "FirstName", "LastName"])


_ENTRY_LIST = _entry_list(
    ("ALB", "Williams", "Alexander", "Albon"),
    ("CAM", "Haas F1 Team", "Rafael", "Câmara"),
    ("HUL", "Audi", "Nico", "Hulkenberg"),
    ("VER", "Red Bull Racing", "Max", "Verstappen"),
)


def test_matches_on_surname_when_first_names_differ():
    assert match_drivers({"Alex Albon": "500/1"}, _ENTRY_LIST) == [OddsEntry("ALB", "WIL", "500/1")]


def test_matches_whichever_side_carries_an_accent():
    entries = match_drivers({"Rafael Camara": "500/1", "Nico Hülkenberg": "100/1"}, _ENTRY_LIST)

    assert entries == [OddsEntry("CAM", "HAA", "500/1"), OddsEntry("HUL", "AUD", "100/1")]


def test_a_shared_surname_falls_back_to_the_full_name():
    entry_list = _entry_list(
        ("MSC", "Haas F1 Team", "Mick", "Schumacher"),
        ("RSC", "Williams", "Ralf", "Schumacher"),
    )

    assert match_drivers({"Mick Schumacher": "200/1"}, entry_list) == [OddsEntry("MSC", "HAA", "200/1")]


def test_an_unmatched_name_is_kept_with_no_constructor(caplog):
    caplog.set_level("WARNING", logger="odds_source.drivers")

    entries = match_drivers({"Esteban Ocon": "500/1", "Max Verstappen": "5/1"}, _ENTRY_LIST)

    assert entries == [OddsEntry("Esteban Ocon", "", "500/1"), OddsEntry("VER", "RED", "5/1")]
    assert "Esteban Ocon" in caplog.text


def test_stops_on_a_team_missing_from_the_table():
    entry_list = _entry_list(("VER", "Red Bull Honda", "Max", "Verstappen"))

    with pytest.raises(ValueError, match="Red Bull Honda"):
        match_drivers({"Max Verstappen": "5/1"}, entry_list)


def test_stops_when_two_names_match_one_driver():
    with pytest.raises(ValueError, match="VER"):
        match_drivers({"Max Verstappen": "5/1", "M. Verstappen": "6/1"}, _ENTRY_LIST)


def _fetch_recorder(lists: dict[tuple[int, int, str], pd.DataFrame]):
    calls = []

    def fetch(season: int, race: int, session: str) -> pd.DataFrame:
        calls.append((season, race, session))
        return lists.get((season, race, session), _entry_list())

    return fetch, calls


def test_reads_the_driver_list_of_the_session_the_odds_follow():
    fetch, calls = _fetch_recorder({(2026, 20, "Q"): _ENTRY_LIST})

    entry_list = load_entry_list(CapturePoint(2026, 20, "Odds_Q"), fetch=fetch)

    assert calls == [(2026, 20, "Q")]
    assert entry_list.equals(_ENTRY_LIST)


def test_a_sprint_capture_reads_the_sprint():
    fetch, calls = _fetch_recorder({(2026, 20, "S"): _ENTRY_LIST})

    load_entry_list(CapturePoint(2026, 20, "Odds_Sprint"), fetch=fetch)

    assert calls == [(2026, 20, "S")]


def test_before_first_practice_reads_the_previous_race():
    fetch, calls = _fetch_recorder({(2026, 19, "R"): _ENTRY_LIST})

    entry_list = load_entry_list(CapturePoint(2026, 20, "Odds_PreFP1"), fetch=fetch)

    assert calls == [(2026, 19, "R")]
    assert entry_list.equals(_ENTRY_LIST)


def test_a_session_not_yet_published_falls_back_to_the_previous_race():
    fetch, calls = _fetch_recorder({(2026, 19, "R"): _ENTRY_LIST})

    entry_list = load_entry_list(CapturePoint(2026, 20, "Odds_FP2"), fetch=fetch)

    assert calls == [(2026, 20, "FP2"), (2026, 19, "R")]
    assert entry_list.equals(_ENTRY_LIST)


def test_the_first_race_before_practice_has_no_list(caplog):
    caplog.set_level("WARNING", logger="odds_source.drivers")
    fetch, calls = _fetch_recorder({})

    entry_list = load_entry_list(CapturePoint(2026, 1, "Odds_PreFP1"), fetch=fetch)

    assert calls == []
    assert entry_list.empty
    assert "no driver list" in caplog.text.lower()
