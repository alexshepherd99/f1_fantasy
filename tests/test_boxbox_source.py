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
from tests.boxbox_fixtures import driver_history, modified, predictions, raw_files, season_summary, set_prices


def test_download_files_fetches_the_three_files():
    requested = []

    def fake_fetch(url: str) -> bytes:
        requested.append(url)
        return b"{}"

    download_files(fetch=fake_fetch)

    assert sorted(requested) == [
        "https://boxboxf1fantasy.com/data/driver_history.json",
        "https://boxboxf1fantasy.com/data/predictions.json",
        "https://boxboxf1fantasy.com/data/season_summary.json",
    ]


def test_download_files_keys_each_body_by_its_name():
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


def test_parse_files_takes_prices_from_predictions_not_the_summary():
    prediction = modified(predictions(), lambda p: set_prices(p, {"VER": 29.1, "mercedes": 31.5}))

    data = parse_files(raw_files(prediction=prediction))

    assert data.driver_prices == {
        "VER": ("red_bull", 29.1), "HAD": ("red_bull", 10.0), "RUS": ("mercedes", 27.3), "ANT": ("mercedes", 20.0),
    }
    assert data.constructor_prices == {"red_bull": 30.4, "mercedes": 31.5}


def test_parse_files_reads_the_round_and_time_of_the_prices():
    data = parse_files(raw_files())

    assert (data.prices_round, data.prices_generated_at) == (5, "2026-11-10T07:00:01+00:00")


def test_parse_files_lists_drivers_whose_price_is_provisional():
    def flag(p):
        p["drivers"][1]["price_provisional"] = True
        p["drivers"][2].pop("price_provisional")  # optional in BoxBox's schema: absent is not provisional

    assert parse_files(raw_files()).provisional_prices == []
    assert parse_files(raw_files(prediction=modified(predictions(), flag))).provisional_prices == ["HAD"]


@pytest.mark.parametrize(
    "change, message",
    [
        (lambda p: p.update(season=2025), "season"),
        (lambda p: p.pop("round"), "round"),
        (lambda p: p.update(round="5"), "round"),
        (lambda p: p.pop("generated_at"), "generated_at"),
        (lambda p: p.pop("drivers"), "drivers"),
        (lambda p: p["drivers"][0].pop("constructor"), "constructor"),
        (lambda p: p["drivers"][0].update(current_price="28.8"), "current_price"),
        (lambda p: p["constructors"][1].pop("current_price"), "current_price"),
        (lambda p: p["constructors"][0].pop("constructor_id"), "constructor_id"),
        (lambda p: p["drivers"].append(dict(p["drivers"][0])), "twice"),
        (lambda p: p["drivers"][0].update(price_provisional="no"), "price_provisional"),
    ],
)
def test_parse_files_rejects_unexpected_predictions(change, message):
    with pytest.raises(BoxBoxDataError, match=message):
        parse_files(raw_files(prediction=modified(predictions(), change)))


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
