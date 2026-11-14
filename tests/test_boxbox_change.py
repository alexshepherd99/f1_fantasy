import pytest

from boxbox.change import (
    CAPTURE,
    COMPLETE,
    CORRECT,
    START,
    ArchiveRow,
    CaptureNotYet,
    CaptureRefused,
    decide_change,
)
from boxbox.source import parse_files
from common import AssetType
from import_data.import_history import read_archive_file
from tests.boxbox_fixtures import (
    CONSTRUCTORS_CSV,
    CONSTRUCTORS_CSV_RACE_3_CAPTURED,
    DRIVERS_CSV,
    DRIVERS_CSV_RACE_3_CAPTURED,
    RACE_3_PRICES,
    driver_history,
    modified,
    new_season_files,
    new_season_history,
    new_season_predictions,
    new_season_summary,
    predictions,
    raw_files,
    season_ends_at_round_4,
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
        prediction["round"] = 4
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


def test_capture_refuses_while_the_prices_are_still_for_the_race_just_held(tmp_path):
    prediction = modified(predictions(), lambda p: p.update(round=4))

    with pytest.raises(CaptureNotYet, match="round 4"):
        _decide(tmp_path, prediction=prediction)


@pytest.mark.parametrize("prices_round", [2, 6])
def test_capture_refuses_prices_for_another_round(tmp_path, prices_round):
    prediction = modified(predictions(), lambda p: p.update(round=prices_round))

    with pytest.raises(CaptureRefused, match=f"round {prices_round}") as refused:
        _decide(tmp_path, prediction=prediction)
    assert not isinstance(refused.value, CaptureNotYet)


def test_correct_refuses_prices_for_another_round(tmp_path):
    with pytest.raises(CaptureRefused, match="round 5"):
        _before_update(tmp_path, lambda p: p.update(round=5))


def _summary_disagrees(summary: dict) -> None:
    summary["driver_prices"]["VER"]["current_price"] = 28.5
    summary["driver_prices"].pop("ANT")
    summary["constructor_prices"]["mercedes"]["current_price"] = 31.0


_SUMMARY_WARNING = ("season_summary.json's prices differ from predictions.json's, which are used "
                    "(season_summary.json's first): ANT none against 20, VER 28.5 against 28.8, "
                    "mercedes 31 against 31.2")


def test_capture_warns_when_the_summary_prices_disagree(tmp_path):
    change = _decide(tmp_path, summary=modified(season_summary(), _summary_disagrees))

    assert change.warnings == [_SUMMARY_WARNING]
    assert [row.price for row in change.driver_rows[4]][0] == 28.8


def test_correct_warns_when_the_summary_prices_disagree(tmp_path):
    def summary_before_update(s):
        s["rounds"][2]["has_actual"] = False
        for key, entry in list(s["driver_prices"].items()) + list(s["constructor_prices"].items()):
            entry["current_price"] = RACE_3_PRICES[key]

    def prediction_before_update(p):
        _race_3_prices(p)
        p["round"] = 4
        set_prices(p, {"VER": 28.9})

    change = _decide(tmp_path, summary=modified(season_summary(), summary_before_update),
                     prediction=modified(predictions(), prediction_before_update))

    assert change.mode == CORRECT
    assert change.warnings == ["season_summary.json's prices differ from predictions.json's, which are used "
                               "(season_summary.json's first): VER 28.5 against 28.9"]


def test_capture_of_the_last_race_reads_no_prices_so_does_not_warn(tmp_path):
    def last_round_and_disagreeing(s):
        s["rounds"].pop()
        _summary_disagrees(s)

    assert _decide(tmp_path, summary=modified(season_summary(), last_round_and_disagreeing)).warnings == []


def _provisional_had(prediction: dict) -> None:
    prediction["drivers"][1]["price_provisional"] = True


def test_capture_refuses_a_provisional_price(tmp_path):
    with pytest.raises(CaptureNotYet, match="HAD provisional"):
        _decide(tmp_path, prediction=modified(predictions(), _provisional_had))


def test_correct_refuses_a_provisional_price(tmp_path):
    with pytest.raises(CaptureNotYet, match="HAD provisional"):
        _before_update(tmp_path, _provisional_had)


def test_capture_refuses_when_the_race_already_has_points(tmp_path):
    drivers = DRIVERS_CSV.replace("2026,3,RED,VER,,28.5", "2026,3,RED,VER,31,28.5")

    with pytest.raises(CaptureRefused, match="already has points") as refused:
        _decide(tmp_path, drivers_csv=drivers)
    assert not isinstance(refused.value, CaptureNotYet)


def _complete(tmp_path, history=None, summary_change=season_ends_at_round_4):
    """Decide with the season's last race already captured."""
    return _decide(tmp_path, summary=modified(season_summary(), summary_change), history=history,
                   drivers_csv=DRIVERS_CSV_RACE_3_CAPTURED, constructors_csv=CONSTRUCTORS_CSV_RACE_3_CAPTURED)


def test_a_finished_season_is_complete_and_writes_nothing(tmp_path):
    change = _complete(tmp_path)

    assert (change.mode, change.season, change.target_race) == (COMPLETE, 2026, 3)
    assert (change.driver_rows, change.constructor_rows, change.warnings) == ({}, {}, [])


def test_a_finished_season_still_warns_on_differences_including_its_last_race(tmp_path):
    history = modified(driver_history(), lambda h: h["drivers"]["VER"]["rounds"][2].update(points=30))

    change = _complete(tmp_path, history=history)

    assert change.mode == COMPLETE
    assert len(change.warnings) == 1
    assert "VER" in change.warnings[0] and "race 3" in change.warnings[0]


def test_a_last_race_with_points_but_not_held_on_boxbox_is_refused(tmp_path):
    def last_round_not_held(summary):
        season_ends_at_round_4(summary)
        summary["rounds"][-1]["has_actual"] = False

    with pytest.raises(CaptureRefused, match="already has points") as refused:
        _complete(tmp_path, summary_change=last_round_not_held)
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


def _start(tmp_path, summary=None, history=None, prediction=None, drivers_csv=DRIVERS_CSV_RACE_3_CAPTURED,
           constructors_csv=CONSTRUCTORS_CSV_RACE_3_CAPTURED):
    """Decide with BoxBox serving 2027 before its first race, and 2026 complete in the archive.

    BoxBox's pre-season ``driver_history.json`` has no results, which a start never reads.
    """
    fn = str(write_archive(tmp_path, drivers_csv, constructors_csv))
    return decide_change(
        read_archive_file(AssetType.DRIVER, fn),
        read_archive_file(AssetType.CONSTRUCTOR, fn),
        parse_files(new_season_files(summary, history, prediction)),
        {2026: 2},
    )


def test_start_writes_race_1_in_the_previous_seasons_order_with_new_assets_after(tmp_path):
    change = _start(tmp_path)

    assert (change.mode, change.season, change.target_race, change.warnings) == (START, 2027, 1, [])
    assert change.driver_rows == {1: [
        ArchiveRow(2027, 1, "RED", "VER", None, 29.0),
        ArchiveRow(2027, 1, "MER", "RUS", None, 27.5),
        ArchiveRow(2027, 1, "MER", "ANT", None, 21.0),
        ArchiveRow(2027, 1, "CAD", "BOT", None, 6.0),
        ArchiveRow(2027, 1, "RED", "LAW", None, 8.0),
        ArchiveRow(2027, 1, "CAD", "PER", None, 6.5),
    ]}
    assert change.constructor_rows == {1: [
        ArchiveRow(2027, 1, "RED", None, None, 30.5),
        ArchiveRow(2027, 1, "MER", None, None, 31.5),
        ArchiveRow(2027, 1, "CAD", None, None, 6.2),
    ]}
    assert change.new_season_constructors == 3


@pytest.mark.parametrize("season", [2022, 2028])
def test_refuses_a_season_that_is_not_the_next_one(tmp_path, season):
    summary = modified(new_season_summary(), lambda s: s.update(season=season))
    history = modified(new_season_history(), lambda h: h.update(season=season))
    prediction = modified(new_season_predictions(), lambda p: p.update(season=season))

    with pytest.raises(CaptureRefused, match=f"{season}.*not the next season") as refused:
        _start(tmp_path, summary=summary, history=history, prediction=prediction)
    assert not isinstance(refused.value, CaptureNotYet)


def test_start_refuses_once_a_round_is_held(tmp_path):
    summary = modified(new_season_summary(), lambda s: s["rounds"][0].update(has_actual=True))

    with pytest.raises(CaptureRefused, match="by hand") as refused:
        _start(tmp_path, summary=summary)
    assert not isinstance(refused.value, CaptureNotYet)


def test_start_waits_for_prices_for_the_first_round(tmp_path):
    with pytest.raises(CaptureNotYet, match="round 2"):
        _start(tmp_path, prediction=modified(new_season_predictions(), lambda p: p.update(round=2)))


def test_start_waits_for_a_provisional_price(tmp_path):
    prediction = modified(new_season_predictions(), lambda p: p["drivers"][0].update(price_provisional=True))

    with pytest.raises(CaptureNotYet, match="ANT provisional"):
        _start(tmp_path, prediction=prediction)


def test_start_waits_while_every_carried_over_price_is_last_seasons(tmp_path):
    with pytest.raises(CaptureNotYet, match="2026"):
        _start(tmp_path, prediction=modified(new_season_predictions(), _race_3_prices))


def test_start_goes_ahead_when_some_carried_over_prices_are_last_seasons(tmp_path):
    prediction = modified(new_season_predictions(), lambda p: set_prices(p, {"VER": 28.5, "mercedes": 31.0}))

    assert _start(tmp_path, prediction=prediction).mode == START


def test_start_refuses_a_season_in_only_one_archive_file(tmp_path):
    with pytest.raises(CaptureRefused, match="only"):
        _start(tmp_path, drivers_csv=DRIVERS_CSV_RACE_3_CAPTURED + "2027,1,RED,VER,,29\n")


def test_a_rerun_before_race_1_is_held_corrects_it(tmp_path):
    drivers = DRIVERS_CSV_RACE_3_CAPTURED + "2027,1,RED,VER,,29\n2027,1,RED,HAD,,9\n"
    constructors = CONSTRUCTORS_CSV_RACE_3_CAPTURED + "2027,1,RED,,30.5\n"

    def red_bull_only(prediction):
        prediction["drivers"] = [d for d in prediction["drivers"] if d["constructor"] == "red_bull"]
        prediction["constructors"] = [c for c in prediction["constructors"] if c["constructor_id"] == "red_bull"]

    prediction = modified(new_season_predictions(), red_bull_only)

    change = _start(tmp_path, prediction=prediction, drivers_csv=drivers, constructors_csv=constructors)

    assert (change.mode, change.season, change.target_race) == (CORRECT, 2027, 1)
    assert change.driver_rows == {1: [ArchiveRow(2027, 1, "RED", "VER", None, 29.0),
                                      ArchiveRow(2027, 1, "RED", "LAW", None, 8.0)]}


def test_refuses_when_drivers_and_constructors_end_at_different_races(tmp_path):
    constructors = CONSTRUCTORS_CSV.replace("2026,3,RED,,30\n", "").replace("2026,3,MER,,31\n", "")

    with pytest.raises(CaptureRefused, match="different races"):
        _decide(tmp_path, constructors_csv=constructors)
