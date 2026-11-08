import csv
import os
import sys
from datetime import datetime, timezone

import pandas as pd
import pytest

from odds_source import cli

_TEST_PAGE = "data/test_oddschecker_winner.mhtml"
_HEADER = "Driver,Constructor,Season,Race,Odds,Odds_Pre_Weekend,Odds_Pre_Quali,Odds_Post_FP2,Odds_Post_Quali\n"


def _utc(day: int, hour: int, minute: int = 0) -> pd.Timestamp:
    return pd.Timestamp(datetime(2026, 11, day, hour, minute, tzinfo=timezone.utc)).tz_convert(None)


# The fixture page is for a race at 20:00 UTC on 8 November, saved at 16:01 that day
_SCHEDULE = pd.DataFrame([{
    "RoundNumber": 20,
    "EventName": "Test Grand Prix",
    **{f"Session{i}": name for i, name in enumerate(
        ["Practice 1", "Practice 2", "Practice 3", "Qualifying", "Race"], start=1)},
    **{f"Session{i}DateUtc": start for i, start in enumerate(
        [_utc(6, 15, 30), _utc(6, 19), _utc(7, 14, 30), _utc(7, 18), _utc(8, 17)], start=1)},
}])
_QUALIFYING = pd.DataFrame(
    [("VER", "Red Bull Racing", "Max", "Verstappen"),
     ("ANT", "Mercedes", "Kimi", "Antonelli"),
     ("HUL", "Audi", "Nico", "Hulkenberg")],
    columns=["Abbreviation", "TeamName", "FirstName", "LastName"],
)


@pytest.fixture
def fastf1_calls(monkeypatch, tmp_path):
    """Stand in for FastF1: cache setup, the schedule and the driver lists."""
    calls = []
    monkeypatch.setattr(cli, "setup_fastf1_cache", lambda cache_dir=None, interactive=True: calls.append(
        ("cache", cache_dir, interactive)) or (tmp_path, tmp_path / "local_cache"))
    monkeypatch.setattr(cli, "get_event_schedule", lambda season: calls.append(("schedule", season)) or _SCHEDULE)
    monkeypatch.setattr(cli, "get_session_drivers", lambda season, race, session: calls.append(
        ("drivers", season, race, session)) or (_QUALIFYING if (season, race, session) == (2026, 20, "Q") else
                                                pd.DataFrame(columns=_QUALIFYING.columns)))
    return calls


def _odds_file(tmp_path):
    path = tmp_path / "odds.csv"
    path.write_text(_HEADER + "VER,RED,2026,20,5-4,5-4,,,\n")
    return path


def _race_20(path) -> list[tuple[str, str, str, str]]:
    with open(path, newline="", encoding="utf-8") as handle:
        return [(row["Driver"], row["Constructor"], row["Odds"], row["Odds_Q"]) for row in csv.DictReader(handle)]


def test_captures_a_saved_page_into_the_odds_file(monkeypatch, tmp_path, fastf1_calls, capsys):
    odds_file = _odds_file(tmp_path)
    monkeypatch.setattr(sys, "argv", ["odds_source", _TEST_PAGE, "--odds-file", str(odds_file)])

    cli.main()

    assert _race_20(odds_file) == [
        ("VER", "RED", "9/2", "9/2"),
        ("ANT", "MER", "23/16", "23/16"),
        ("HUL", "AUD", "150/1", "150/1"),
    ]
    assert fastf1_calls == [("cache", None, True), ("schedule", 2026), ("drivers", 2026, 20, "Q")]
    printed = capsys.readouterr().out
    assert "Odds_Q" in printed and "Test Grand Prix" in printed


def test_a_cache_dir_is_passed_on_without_prompting(monkeypatch, tmp_path, fastf1_calls):
    monkeypatch.setattr(sys, "argv", [
        "odds_source", _TEST_PAGE, "--odds-file", str(_odds_file(tmp_path)), "--cache-dir", str(tmp_path)])

    cli.main()

    assert fastf1_calls[0] == ("cache", str(tmp_path), False)


def test_loads_f1_credentials(monkeypatch, tmp_path, fastf1_calls):
    monkeypatch.setattr(sys, "argv", ["odds_source", _TEST_PAGE, "--odds-file", str(_odds_file(tmp_path))])

    cli.main()

    assert os.environ["F1_USERNAME"] == "test-user"


def test_exits_before_any_work_without_f1_credentials(monkeypatch, tmp_path, fastf1_calls, caplog):
    monkeypatch.setattr("fast_f1.auth.CREDENTIALS_FILE", tmp_path / "absent")
    odds_file = _odds_file(tmp_path)
    monkeypatch.setattr(sys, "argv", ["odds_source", _TEST_PAGE, "--odds-file", str(odds_file)])

    with pytest.raises(SystemExit) as excinfo:
        cli.main()

    assert excinfo.value.code == 1
    assert fastf1_calls == []
    assert odds_file.read_text() == _HEADER + "VER,RED,2026,20,5-4,5-4,,,\n"


def test_a_page_without_odds_exits_and_leaves_the_file_alone(monkeypatch, tmp_path, fastf1_calls, caplog):
    page = tmp_path / "blocked.mhtml"
    page.write_text(
        'From: <Saved by Blink>\nDate: Sun, 08 Nov 2026 16:01:41 GMT\nMIME-Version: 1.0\n'
        'Content-Type: multipart/related; type="text/html"; boundary="b"\n\n'
        "--b\nContent-Type: text/html\n\n<html><body>Checking your browser</body></html>\n--b--\n"
    )
    odds_file = _odds_file(tmp_path)
    monkeypatch.setattr(sys, "argv", ["odds_source", str(page), "--odds-file", str(odds_file)])

    with pytest.raises(SystemExit) as excinfo:
        cli.main()

    assert excinfo.value.code == 1
    assert odds_file.read_text() == _HEADER + "VER,RED,2026,20,5-4,5-4,,,\n"
    assert "odds grid" in caplog.text


def test_with_no_page_named_takes_the_newest_saved_page(tmp_path):
    older, newer = tmp_path / "older.mhtml", tmp_path / "newer.mhtml"
    for path, mtime in ((older, 1_000_000), (newer, 2_000_000)):
        path.write_text("")
        os.utime(path, (mtime, mtime))
    (tmp_path / "newest_but_not_a_page.xlsx").write_text("")

    assert cli.newest_saved_page(tmp_path) == newer


def test_with_no_page_named_and_none_saved_exits(monkeypatch, tmp_path, fastf1_calls, caplog):
    monkeypatch.setattr(cli, "DEFAULT_OUTPUT_DIRECTORY", tmp_path)
    monkeypatch.setattr(sys, "argv", ["odds_source", "--odds-file", str(_odds_file(tmp_path))])

    with pytest.raises(SystemExit) as excinfo:
        cli.main()

    assert excinfo.value.code == 1
    assert "No saved page" in caplog.text
