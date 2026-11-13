import json
from functools import partial

from boxbox import cli
from boxbox.source import BOXBOX_URLS
from tests.boxbox_fixtures import (
    CONSTRUCTORS_CSV,
    DRIVERS_CSV,
    RACE_3_PRICES,
    modified,
    predictions,
    raw_files,
    season_summary,
    set_prices,
    swap_driver,
    write_archive,
)

# The writer's integrity checks expect the fixture's two teams, not 2026's eleven.
main = partial(cli.main, season_constructors={2025: 1, 2026: 2})


def _saved_copy(folder, prediction=None):
    folder.mkdir()
    for name, body in raw_files(prediction=prediction).items():
        (folder / f"{name}.json").write_bytes(body)
    return folder


def _archive(tmp_path):
    folder = tmp_path / "data"
    folder.mkdir()
    return write_archive(folder)


def test_capture_from_a_saved_copy_writes_and_reports(tmp_path, capsys):
    archive = _archive(tmp_path)
    copy = _saved_copy(tmp_path / "copy")

    code = main(["--from-copy", str(copy), "--archive-dir", str(archive)])

    assert code == 0
    assert "2026,4,RED,VER,,28.8" in (archive / "f1_fantasy_drivers.csv").read_text()
    out = capsys.readouterr().out
    assert "capture" in out and "race 3" in out
    assert "VER@RED" in out and "31" in out


def test_report_shows_old_price_new_price_and_difference(tmp_path, capsys):
    archive = _archive(tmp_path)

    copy = _saved_copy(tmp_path / "copy", modified(predictions(), lambda p: swap_driver(p, "HAD", "LAW", 7.0)))

    main(["--from-copy", str(copy), "--archive-dir", str(archive), "--dry-run"])

    lines = {" ".join(line.split()) for line in capsys.readouterr().out.splitlines()}
    assert {
        "VER@RED 28.5 -> 28.8 +0.3",
        "RUS@MER 27.1 -> 27.3 +0.2",
        "ANT@MER 20.2 -> 20.0 -0.2",
        "LAW@RED new -> 7.0",
        "HAD@RED 9.8 -> dropped",
        "RED 30.0 -> 30.4 +0.4",
        "MER 31.0 -> 31.2 +0.2",
    } <= lines


def test_dry_run_writes_nothing(tmp_path, capsys):
    archive = _archive(tmp_path)
    copy = _saved_copy(tmp_path / "copy")

    code = main(["--from-copy", str(copy), "--archive-dir", str(archive), "--dry-run"])

    assert code == 0
    assert (archive / "f1_fantasy_drivers.csv").read_text() == DRIVERS_CSV
    assert (archive / "f1_fantasy_constructors.csv").read_text() == CONSTRUCTORS_CSV
    assert "dry run" in capsys.readouterr().out.lower()


def test_refusal_exits_1_and_writes_nothing(tmp_path, capsys):
    archive = _archive(tmp_path)
    copy = _saved_copy(tmp_path / "copy", modified(predictions(), lambda p: set_prices(p, RACE_3_PRICES)))

    code = main(["--from-copy", str(copy), "--archive-dir", str(archive)])

    assert code == 1
    assert (archive / "f1_fantasy_drivers.csv").read_text() == DRIVERS_CSV
    assert "not updated" in capsys.readouterr().err


def test_unreadable_files_exit_1(tmp_path, capsys):
    archive = _archive(tmp_path)
    copy = _saved_copy(tmp_path / "copy")
    (copy / "season_summary.json").write_text("<html>maintenance</html>")

    code = main(["--from-copy", str(copy), "--archive-dir", str(archive)])

    assert code == 1
    assert "season_summary" in capsys.readouterr().err


def test_download_saves_a_copy_then_writes(tmp_path):
    archive = _archive(tmp_path)
    by_url = {url: raw_files()[name] for name, url in BOXBOX_URLS.items()}

    code = main(["--archive-dir", str(archive), "--copy-dir", str(tmp_path / "copies")], fetch=by_url.__getitem__)

    assert code == 0
    [saved] = list((tmp_path / "copies").iterdir())
    assert json.loads((saved / "season_summary.json").read_bytes()) == season_summary()
    assert "2026,4,RED,VER,,28.8" in (archive / "f1_fantasy_drivers.csv").read_text()


def test_a_failed_download_exits_1_and_saves_nothing(tmp_path, capsys):
    archive = _archive(tmp_path)

    def failing(url):
        raise ConnectionError("no network")

    code = main(["--archive-dir", str(archive), "--copy-dir", str(tmp_path / "copies")], fetch=failing)

    assert code == 1
    assert not (tmp_path / "copies").exists()
    assert "no network" in capsys.readouterr().err
