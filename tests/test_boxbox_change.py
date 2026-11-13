import pytest

from boxbox.change import CAPTURE, CORRECT, ArchiveRow, CaptureNotYet, CaptureRefused, decide_change
from boxbox.source import parse_files
from common import AssetType
from import_data.import_history import read_archive_file
from tests.boxbox_fixtures import (
    CONSTRUCTORS_CSV,
    DRIVERS_CSV,
    RACE_3_PRICES,
    driver_history,
    modified,
    predictions,
    raw_files,
    season_summary,
    set_prices,
    swap_driver,
    write_archive,
)


def _decide(tmp_path, summary=None, history=None, prediction=None, drivers_csv=DRIVERS_CSV,
            constructors_csv=CONSTRUCTORS_CSV, golden=None):
    fn = str(write_archive(tmp_path, drivers_csv, constructors_csv))
    return decide_change(
        read_archive_file(AssetType.DRIVER, fn),
        read_archive_file(AssetType.CONSTRUCTOR, fn),
        parse_files(raw_files(summary, history, prediction)),
        golden if golden is not None else {},
    )


def _race_3_prices(prediction: dict) -> None:
    set_prices(prediction, RACE_3_PRICES)


def _swap_had_for_law(prediction: dict) -> None:
    swap_driver(prediction, "HAD", "LAW", 7.0)


def _before_update(tmp_path, change=None, golden=None):
    """Decide with BoxBox as before round 4 is held: no results for it, prices still race 3's."""
    def prices(prediction):
        _race_3_prices(prediction)
        if change:
            change(prediction)

    summary = modified(season_summary(), lambda s: s["rounds"][2].update(has_actual=False))
    return _decide(tmp_path, summary=summary, prediction=modified(predictions(), prices), golden=golden)


def test_capture_fills_the_race_just_held_and_prices_the_next(tmp_path):
    change = _decide(tmp_path)

    assert (change.mode, change.season, change.target_race, change.warnings) == (CAPTURE, 2026, 3, [])
    assert change.driver_rows == {
        3: [
            ArchiveRow(2026, 3, "RED", "VER", 31.0, 28.5),
            ArchiveRow(2026, 3, "RED", "HAD", 7.5, 9.8),
            ArchiveRow(2026, 3, "MER", "RUS", 25.0, 27.1),
            ArchiveRow(2026, 3, "MER", "ANT", -2.0, 20.2),
        ],
        4: [
            ArchiveRow(2026, 4, "RED", "VER", None, 28.8),
            ArchiveRow(2026, 4, "RED", "HAD", None, 10.0),
            ArchiveRow(2026, 4, "MER", "RUS", None, 27.3),
            ArchiveRow(2026, 4, "MER", "ANT", None, 20.0),
        ],
    }
    assert change.constructor_rows == {
        3: [ArchiveRow(2026, 3, "RED", None, 44.0, 30.0), ArchiveRow(2026, 3, "MER", None, 28.0, 31.0)],
        4: [ArchiveRow(2026, 4, "RED", None, None, 30.4), ArchiveRow(2026, 4, "MER", None, None, 31.2)],
    }


def test_capture_takes_the_next_line_up_from_the_prices(tmp_path):
    change = _decide(tmp_path, prediction=modified(predictions(), _swap_had_for_law))

    assert [(r.driver, r.price) for r in change.driver_rows[4]] == [
        ("VER", 28.8), ("RUS", 27.3), ("ANT", 20.0), ("LAW", 7.0)
    ]


def test_capture_on_the_last_race_fills_points_only(tmp_path):
    change = _decide(tmp_path, summary=modified(season_summary(), lambda s: s["rounds"].pop()))

    assert sorted(change.driver_rows) == [3]
    assert sorted(change.constructor_rows) == [3]


def test_capture_refuses_when_prices_have_not_moved(tmp_path):
    with pytest.raises(CaptureNotYet, match="price"):
        _decide(tmp_path, prediction=modified(predictions(), _race_3_prices))


def test_capture_refuses_unmoved_prices_even_with_a_new_driver(tmp_path):
    def stale_with_swap(p):
        _race_3_prices(p)
        _swap_had_for_law(p)

    with pytest.raises(CaptureNotYet, match="price"):
        _decide(tmp_path, prediction=modified(predictions(), stale_with_swap))


def test_capture_refuses_when_the_race_already_has_points(tmp_path):
    drivers = DRIVERS_CSV.replace("2026,3,RED,VER,,28.5", "2026,3,RED,VER,31,28.5")

    with pytest.raises(CaptureRefused, match="already has points") as refused:
        _decide(tmp_path, drivers_csv=drivers)
    assert not isinstance(refused.value, CaptureNotYet)


def test_capture_refuses_when_a_driver_in_the_race_has_no_result(tmp_path):
    history = modified(driver_history(), lambda h: h["drivers"]["ANT"]["rounds"].pop())

    with pytest.raises(CaptureRefused, match="ANT") as refused:
        _decide(tmp_path, history=history)
    assert not isinstance(refused.value, CaptureNotYet)


def test_capture_refuses_a_result_for_a_driver_not_in_the_race(tmp_path):
    history = modified(driver_history(), lambda h: h["drivers"].update(
        LAW={"rounds": [{"round": 4, "points": 3}]}))

    with pytest.raises(CaptureRefused, match="LAW"):
        _decide(tmp_path, history=history)


def test_capture_refuses_when_a_constructor_has_no_result(tmp_path):
    history = modified(driver_history(), lambda h: h["constructors"]["mercedes"]["rounds"].pop())

    with pytest.raises(CaptureRefused, match="MER"):
        _decide(tmp_path, history=history)


def test_capture_warns_on_an_earlier_race_that_differs(tmp_path):
    history = modified(driver_history(), lambda h: h["drivers"]["VER"]["rounds"][0].update(points=51))

    change = _decide(tmp_path, history=history)

    assert len(change.warnings) == 1
    assert "VER" in change.warnings[0] and "race 1" in change.warnings[0]
    assert change.driver_rows[3][0].points == 31.0


def test_correct_rewrites_the_race_not_yet_held(tmp_path):
    change = _before_update(tmp_path, _swap_had_for_law)

    assert (change.mode, change.target_race) == (CORRECT, 3)
    assert change.driver_rows == {3: [
        ArchiveRow(2026, 3, "RED", "VER", None, 28.5),
        ArchiveRow(2026, 3, "MER", "RUS", None, 27.1),
        ArchiveRow(2026, 3, "MER", "ANT", None, 20.2),
        ArchiveRow(2026, 3, "RED", "LAW", None, 7.0),
    ]}
    assert change.constructor_rows == {3: [
        ArchiveRow(2026, 3, "RED", None, None, 30.0), ArchiveRow(2026, 3, "MER", None, None, 31.0),
    ]}


def test_correct_refuses_a_race_from_the_workbook(tmp_path):
    with pytest.raises(CaptureNotYet, match="workbook"):
        _before_update(tmp_path, golden={2026: 3})


def test_refuses_when_an_earlier_round_is_not_held(tmp_path):
    summary = modified(season_summary(), lambda s: s["rounds"][1].update(has_actual=False))

    with pytest.raises(CaptureRefused, match="round 2"):
        _decide(tmp_path, summary=summary)


def test_refuses_a_season_not_in_the_archive(tmp_path):
    summary = modified(season_summary(), lambda s: s.update(season=2027))
    history = modified(driver_history(), lambda h: h.update(season=2027))
    prediction = modified(predictions(), lambda p: p.update(season=2027))

    with pytest.raises(CaptureRefused, match="2027"):
        _decide(tmp_path, summary=summary, history=history, prediction=prediction)


def test_refuses_when_drivers_and_constructors_end_at_different_races(tmp_path):
    constructors = CONSTRUCTORS_CSV.replace("2026,3,RED,,30\n", "").replace("2026,3,MER,,31\n", "")

    with pytest.raises(CaptureRefused, match="different races"):
        _decide(tmp_path, constructors_csv=constructors)
