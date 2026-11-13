import pandas as pd
import pytest

from boxbox.source import BOXBOX_URLS
from live.collect import DONE, FAILED, NOT_YET, REFUSED, OddsApi, collect_boxbox, collect_odds, odds_present
from tests.boxbox_fixtures import DRIVERS_CSV, RACE_3_PRICES, modified, predictions, raw_files, set_prices, write_archive
from tests.test_odds_source_cli import _HEADER, _QUALIFYING, _SCHEDULE, _TEST_PAGE

# The writer's integrity checks expect the BoxBox fixture's two teams
TEAMS = {2025: 1, 2026: 2}


def _boxbox(tmp_path, prediction=None, drivers_csv=DRIVERS_CSV):
    archive = tmp_path / "data"
    archive.mkdir()
    write_archive(archive, drivers=drivers_csv)
    by_url = {url: raw_files(prediction=prediction)[name] for name, url in BOXBOX_URLS.items()}
    return archive, by_url.__getitem__


def test_boxbox_done_writes_the_capture(tmp_path):
    archive, fetch = _boxbox(tmp_path)

    outcome = collect_boxbox(str(archive), str(tmp_path / "copies"), fetch, TEAMS)

    assert (outcome.step, outcome.status) == ("BoxBox", DONE)
    assert "race 3" in outcome.detail
    assert "2026,4,RED,VER,,28.8" in (archive / "f1_fantasy_drivers.csv").read_text()


def test_boxbox_not_updated_is_not_yet(tmp_path):
    stale = modified(predictions(), lambda p: set_prices(p, RACE_3_PRICES))
    archive, fetch = _boxbox(tmp_path, prediction=stale)

    outcome = collect_boxbox(str(archive), str(tmp_path / "copies"), fetch, TEAMS)

    assert (outcome.status, "price" in outcome.detail) == (NOT_YET, True)


def test_boxbox_doubtful_is_refused(tmp_path):
    archive, fetch = _boxbox(tmp_path, drivers_csv=DRIVERS_CSV.replace("2026,3,RED,VER,,28.5", "2026,3,RED,VER,31,28.5"))

    outcome = collect_boxbox(str(archive), str(tmp_path / "copies"), fetch, TEAMS)

    assert (outcome.status, "already has points" in outcome.detail) == (REFUSED, True)


def test_boxbox_download_error_is_failed(tmp_path):
    archive, _ = _boxbox(tmp_path)

    def failing(url):
        raise ConnectionError("no network")

    outcome = collect_boxbox(str(archive), str(tmp_path / "copies"), failing, TEAMS)

    assert (outcome.status, "no network" in outcome.detail) == (FAILED, True)


def _drivers(season, race, session):
    return _QUALIFYING if (season, race, session) == (2026, 20, "Q") else pd.DataFrame(columns=_QUALIFYING.columns)


API = OddsApi(schedule=lambda season: _SCHEDULE, drivers=_drivers)
TEST_PAGE_SAVED = "Date: Sun, 08 Nov 2026 16:01:41 GMT"


def _pages(tmp_path, **pages: str):
    """Saved pages by file name, each the test page saved at the given time."""
    folder = tmp_path / "pages"
    folder.mkdir()
    text = open(_TEST_PAGE, encoding="utf-8").read()
    for name, saved in pages.items():
        (folder / f"{name}.mhtml").write_text(text.replace(TEST_PAGE_SAVED, f"Date: {saved}"), encoding="utf-8")
    return folder


def _odds_file(tmp_path):
    path = tmp_path / "odds.csv"
    path.write_text(_HEADER + "VER,RED,2026,19,5-4,5-4,,,\n")
    return path


def test_odds_with_no_saved_page_is_not_yet(tmp_path):
    folder = tmp_path / "pages"
    folder.mkdir()

    outcome = collect_odds(folder, str(_odds_file(tmp_path)), 2026, 20, API)

    assert (outcome.step, outcome.status) == ("Odds", NOT_YET)


def test_odds_writes_each_page_for_the_race_oldest_first(tmp_path, capsys):
    folder = _pages(tmp_path, a_newer="Sun, 08 Nov 2026 16:01:41 GMT", b_older="Sun, 08 Nov 2026 12:00:00 GMT")
    odds_file = _odds_file(tmp_path)

    outcome = collect_odds(folder, str(odds_file), 2026, 20, API)

    assert (outcome.status, "2 pages" in outcome.detail) == (DONE, True)
    out = capsys.readouterr().out
    assert out.index("b_older.mhtml") < out.index("a_newer.mhtml")
    assert odds_present(str(odds_file), 2026, 20)


def test_odds_skips_a_page_for_another_race(tmp_path, capsys):
    folder = _pages(tmp_path, page="Sun, 08 Nov 2026 16:01:41 GMT")

    outcome = collect_odds(folder, str(_odds_file(tmp_path)), 2026, 21, API)

    assert outcome.status == NOT_YET
    assert "Skipped page.mhtml: season 2026 race 20" in capsys.readouterr().out


def test_odds_page_that_cannot_be_placed_is_failed(tmp_path):
    folder = _pages(tmp_path, good="Sun, 08 Nov 2026 16:01:41 GMT", late="Mon, 09 Nov 2026 12:00:00 GMT")
    odds_file = _odds_file(tmp_path)

    outcome = collect_odds(folder, str(odds_file), 2026, 20, API)

    assert (outcome.status, "late.mhtml" in outcome.detail, "1 page" in outcome.detail) == (FAILED, True, True)
    assert odds_present(str(odds_file), 2026, 20)


def test_odds_fastf1_unreachable_is_failed(tmp_path):
    folder = _pages(tmp_path, page="Sun, 08 Nov 2026 16:01:41 GMT")

    def unreachable(season):
        raise ConnectionError("no network")

    outcome = collect_odds(folder, str(_odds_file(tmp_path)), 2026, 20, OddsApi(unreachable, _drivers))

    assert (outcome.status, "no network" in outcome.detail) == (FAILED, True)


def test_odds_without_fastf1_credentials_is_failed(tmp_path, monkeypatch):
    monkeypatch.setattr("fast_f1.auth.CREDENTIALS_FILE", tmp_path / "absent")
    folder = _pages(tmp_path, page="Sun, 08 Nov 2026 16:01:41 GMT")

    outcome = collect_odds(folder, str(_odds_file(tmp_path)), 2026, 20)

    assert (outcome.status, str(tmp_path / "absent") in outcome.detail) == (FAILED, True)


@pytest.mark.parametrize("race, present", [(19, True), (20, False)])
def test_odds_present_reads_the_races_odds(tmp_path, race, present):
    assert odds_present(str(_odds_file(tmp_path)), 2026, race) == present


def test_odds_present_ignores_a_race_with_blank_odds(tmp_path):
    path = tmp_path / "odds.csv"
    path.write_text(_HEADER + "VER,RED,2026,20,,5-4,,,\n")

    assert not odds_present(str(path), 2026, 20)
