import pytest

from boxbox.archive_file import write_change
from boxbox.change import CORRECT, ArchiveRow, CaptureRefused, Change, decide_change
from boxbox.source import parse_files
from common import AssetType
from import_data.import_history import read_archive_file
from tests.boxbox_fixtures import CONSTRUCTORS_CSV, DRIVERS_CSV, modified, raw_files, season_summary, write_archive

_DRIVERS_FILE = "f1_fantasy_drivers.csv"
_CONSTRUCTORS_FILE = "f1_fantasy_constructors.csv"
_TWO_TEAMS = {2025: 1, 2026: 2}  # the fixture's teams per season, for the integrity checks


def _decide(fn, summary=None) -> Change:
    return decide_change(read_archive_file(AssetType.DRIVER, fn), read_archive_file(AssetType.CONSTRUCTOR, fn),
                         parse_files(raw_files(summary)), {})


def test_write_capture_fills_points_and_adds_the_next_race_beside_each_asset(tmp_path):
    fn = str(write_archive(tmp_path))

    write_change(_decide(fn), fn, _TWO_TEAMS)

    assert (tmp_path / _DRIVERS_FILE).read_text() == """Season,Race,Constructor,Driver,Points,Price
2025,1,RED,VER,10,30
2026,1,RED,VER,50,27.7
2026,2,RED,VER,49,28
2026,3,RED,VER,31,28.5
2026,4,RED,VER,,28.8
2026,1,RED,HAD,5,9
2026,2,RED,HAD,-3,9.5
2026,3,RED,HAD,7.5,9.8
2026,4,RED,HAD,,10
2026,1,MER,RUS,30,27.4
2026,2,MER,RUS,12,27.3
2026,3,MER,RUS,25,27.1
2026,4,MER,RUS,,27.3
2026,1,MER,ANT,20,21
2026,2,MER,ANT,8,20.5
2026,3,MER,ANT,-2,20.2
2026,4,MER,ANT,,20
"""
    assert (tmp_path / _CONSTRUCTORS_FILE).read_text() == """Season,Race,Constructor,Points,Price
2025,1,RED,20,30
2026,1,RED,70,28.2
2026,2,RED,60,29
2026,3,RED,44,30
2026,4,RED,,30.4
2026,1,MER,55,29.3
2026,2,MER,33,30
2026,3,MER,28,31
2026,4,MER,,31.2
"""


def test_write_puts_a_new_driver_after_the_season_and_keeps_the_departed_ones_rows(tmp_path):
    fn = str(write_archive(tmp_path))

    def swap(s):
        s["driver_prices"]["LAW"] = dict(s["driver_prices"].pop("HAD"), current_price=7.0)

    write_change(_decide(fn, modified(season_summary(), swap)), fn, _TWO_TEAMS)

    lines = (tmp_path / _DRIVERS_FILE).read_text().splitlines()
    assert [line for line in lines if ",HAD," in line] == [
        "2026,1,RED,HAD,5,9", "2026,2,RED,HAD,-3,9.5", "2026,3,RED,HAD,7.5,9.8",
    ]
    assert lines[-1] == "2026,4,RED,LAW,,7"


def test_write_puts_a_new_driver_at_the_end_of_its_season_not_of_the_file(tmp_path):
    later_season = "2027,1,RED,VER,1,30\n"
    fn = str(write_archive(tmp_path, drivers=DRIVERS_CSV + later_season))

    def swap(s):
        s["driver_prices"]["LAW"] = dict(s["driver_prices"].pop("HAD"), current_price=7.0)

    write_change(_decide(fn, modified(season_summary(), swap)), fn, _TWO_TEAMS)

    assert (tmp_path / _DRIVERS_FILE).read_text().splitlines()[-2:] == ["2026,4,RED,LAW,,7", later_season.strip()]


def test_write_correct_replaces_the_race_in_place(tmp_path):
    fn = str(write_archive(tmp_path))
    change = Change(
        mode=CORRECT, season=2026, target_race=3,
        driver_rows={3: [
            ArchiveRow(2026, 3, "RED", "VER", None, 28.5),
            ArchiveRow(2026, 3, "MER", "RUS", None, 27.1),
            ArchiveRow(2026, 3, "MER", "ANT", None, 20.2),
            ArchiveRow(2026, 3, "RED", "LAW", None, 7.0),
        ]},
        constructor_rows={3: [
            ArchiveRow(2026, 3, "RED", None, None, 30.0), ArchiveRow(2026, 3, "MER", None, None, 31.0),
        ]},
    )

    write_change(change, fn, _TWO_TEAMS)

    expected = DRIVERS_CSV.replace("2026,3,RED,HAD,,9.8\n", "") + "2026,3,RED,LAW,,7\n"
    assert (tmp_path / _DRIVERS_FILE).read_text() == expected
    assert (tmp_path / _CONSTRUCTORS_FILE).read_text() == CONSTRUCTORS_CSV


def test_write_keeps_the_bytes_of_rows_it_does_not_touch(tmp_path):
    drivers = DRIVERS_CSV.replace("2025,1,RED,VER,10,30", "2025,1,RED,VER,10.0,30.00")
    fn = str(write_archive(tmp_path, drivers=drivers))

    write_change(_decide(fn), fn, _TWO_TEAMS)

    assert "2025,1,RED,VER,10.0,30.00" in (tmp_path / _DRIVERS_FILE).read_text().splitlines()


def test_write_refuses_a_result_that_fails_the_integrity_checks_and_writes_nothing(tmp_path):
    fn = str(write_archive(tmp_path))
    change = _decide(fn)
    change.driver_rows[4].append(ArchiveRow(2026, 4, "RED", "LAW", None, 7.0))  # a third Red Bull driver

    with pytest.raises(CaptureRefused, match="drivers per race"):
        write_change(change, fn, _TWO_TEAMS)

    assert (tmp_path / _DRIVERS_FILE).read_text() == DRIVERS_CSV
    assert (tmp_path / _CONSTRUCTORS_FILE).read_text() == CONSTRUCTORS_CSV
    assert sorted(p.name for p in tmp_path.iterdir()) == [_CONSTRUCTORS_FILE, _DRIVERS_FILE]
