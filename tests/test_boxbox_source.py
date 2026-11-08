from datetime import datetime, timezone

import pytest

from boxbox.source import (
    DRIVER_HISTORY,
    SEASON_SUMMARY,
    BOXBOX_URLS,
    BoxBoxDataError,
    BoxBoxRound,
    download_files,
    parse_files,
    save_copy,
)
from tests.boxbox_fixtures import driver_history, modified, raw_files, season_summary


def test_download_files_fetches_both_urls():
    requested = []

    def fake_fetch(url: str) -> bytes:
        requested.append(url)
        return url.encode()

    raw = download_files(fetch=fake_fetch)

    assert sorted(requested) == sorted(BOXBOX_URLS.values())
    assert raw == {name: url.encode() for name, url in BOXBOX_URLS.items()}


def test_download_files_lets_a_failed_fetch_propagate():
    def failing_fetch(url: str) -> bytes:
        raise ConnectionError("no network")

    with pytest.raises(ConnectionError):
        download_files(fetch=failing_fetch)


def test_save_copy_writes_both_files_into_a_timestamped_folder(tmp_path):
    raw = raw_files()
    now = datetime(2026, 11, 10, 7, 30, 5, tzinfo=timezone.utc)

    folder = save_copy(raw, tmp_path, now)

    assert folder == tmp_path / "2026-11-10T073005Z"
    assert (folder / "driver_history.json").read_bytes() == raw[DRIVER_HISTORY]
    assert (folder / "season_summary.json").read_bytes() == raw[SEASON_SUMMARY]


def test_save_copy_never_overwrites(tmp_path):
    now = datetime(2026, 11, 10, 7, 30, 5, tzinfo=timezone.utc)
    save_copy(raw_files(), tmp_path, now)

    with pytest.raises(FileExistsError):
        save_copy(raw_files(), tmp_path, now)


def test_parse_files_reads_rounds_results_and_prices():
    data = parse_files(raw_files())

    assert data.season == 2026
    assert data.generated_at == "2026-11-10T07:00:00+00:00"
    assert data.rounds == [
        BoxBoxRound(1, True), BoxBoxRound(2, True), BoxBoxRound(4, True), BoxBoxRound(5, False),
    ]
    assert data.driver_results["VER"] == {1: 50.0, 2: 49.0, 4: 31.0}
    assert data.constructor_results["mercedes"] == {1: 55.0, 2: 33.0, 4: 28.0}
    assert data.driver_prices["HAD"] == ("red_bull", 10.0)
    assert data.constructor_prices == {"red_bull": 30.4, "mercedes": 31.2}


@pytest.mark.parametrize(
    "summary, history, message",
    [
        (modified(season_summary(), lambda s: s.update(season=2025)), None, "season"),
        (modified(season_summary(), lambda s: s.pop("driver_prices")), None, "driver_prices"),
        (modified(season_summary(), lambda s: s["rounds"].reverse()), None, "rounds"),
        (modified(season_summary(), lambda s: s["driver_prices"]["VER"].update(current_price="28.8")), None,
         "current_price"),
        (modified(season_summary(), lambda s: s["constructor_prices"]["mercedes"].pop("current_price")), None,
         "current_price"),
        (None, modified(driver_history(), lambda h: h["drivers"]["VER"]["rounds"][0].update(points=None)),
         "points"),
        (None, modified(driver_history(), lambda h: h["drivers"]["VER"]["rounds"].append(
            {"round": 1, "points": 3})), "twice"),
        (None, modified(driver_history(), lambda h: h.pop("constructors")), "constructors"),
    ],
)
def test_parse_files_rejects_unexpected_structure(summary, history, message):
    with pytest.raises(BoxBoxDataError, match=message):
        parse_files(raw_files(summary, history))


def test_parse_files_rejects_a_file_that_is_not_json():
    raw = raw_files()
    raw[SEASON_SUMMARY] = b"<html>maintenance</html>"

    with pytest.raises(BoxBoxDataError, match="season_summary"):
        parse_files(raw)
