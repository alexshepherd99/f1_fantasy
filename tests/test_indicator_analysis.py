import pandas as pd
import pytest

from fast_f1.indicator_analysis import build_analysis_frame


def _metrics_row(season: int, race: int, driver: str, **overrides) -> dict:
    """One metrics row holding a normal weekend's columns, with distinct values."""
    row = {
        "Season": season,
        "Race": race,
        "Driver": driver,
        "Status": "Finished",
        "Position": 1.0,
        "GridPosition": 1.0,
        "RollingPointsRank": 0.1,
        "ConstructorRollingPointsRank": 0.2,
        "FP1_MinLapTime": None,
        "FP1_MinLapTime_rank": None,
        "FP1_TotalLapCount": None,
        "FP1_MaxLapsInStint": None,
        "FP2_MinLapTime": 90.0,
        "FP2_MinLapTime_rank": 0.3,
        "FP2_TotalLapCount": 20.0,
        "FP2_MaxLapsInStint": 8.0,
        "FP3_MinLapTime": 89.0,
        "FP3_MinLapTime_rank": 0.4,
        "FP3_TotalLapCount": 15.0,
        "FP3_MaxLapsInStint": 5.0,
        "SQ_MinLapTime": None,
        "SQ_MinLapTime_rank": None,
        "SQ_TotalLapCount": None,
        "SQ_MaxLapsInStint": None,
        "OddsRank": 0.5,
    }
    return row | overrides


def _sprint_row(season: int, race: int, driver: str, **overrides) -> dict:
    """One metrics row holding a sprint weekend's FP1 and SQ columns."""
    return _metrics_row(
        season,
        race,
        driver,
        **{
            "FP1_MinLapTime": 91.0,
            "FP1_MinLapTime_rank": 0.6,
            "FP1_TotalLapCount": 25.0,
            "FP1_MaxLapsInStint": 9.0,
            "FP2_MinLapTime": None,
            "FP2_MinLapTime_rank": None,
            "FP2_TotalLapCount": None,
            "FP2_MaxLapsInStint": None,
            "FP3_MinLapTime": None,
            "FP3_MinLapTime_rank": None,
            "FP3_TotalLapCount": None,
            "FP3_MaxLapsInStint": None,
            "SQ_MinLapTime": 88.0,
            "SQ_MinLapTime_rank": 0.7,
            "SQ_TotalLapCount": 12.0,
            "SQ_MaxLapsInStint": 3.0,
        } | overrides,
    )


def _archive_row(season: int, race: int, driver_id: str, points: float | None = 10.0) -> dict:
    return {"Season": season, "Race": race, "Driver": driver_id, "Points": points}


def _frame(rows: list[dict], archive: list[dict]) -> pd.DataFrame:
    return build_analysis_frame(pd.DataFrame(rows), pd.DataFrame(archive))


def test_fantasy_points_join_ignores_the_constructor_in_the_archive_id():
    frame = _frame(
        [_metrics_row(2024, 2, "HAM")],
        [_archive_row(2024, 2, "HAM@MER", 37.0)],
    )
    assert frame["target_fantasy"].tolist() == [37.0]


def test_mid_season_switch_takes_the_row_for_the_constructor_actually_driven_for():
    frame = _frame(
        [_metrics_row(2024, 2, "BEA")],
        [_archive_row(2024, 2, "BEA@FER", None), _archive_row(2024, 2, "BEA@HAA", 12.0)],
    )
    assert frame["target_fantasy"].tolist() == [12.0]


def test_driver_with_no_fantasy_points_is_an_error_not_a_silent_gap():
    with pytest.raises(ValueError, match="2024 race 2.*HAM"):
        _frame(
            [_metrics_row(2024, 2, "HAM"), _metrics_row(2024, 2, "VER")],
            [_archive_row(2024, 2, "VER@RED")],
        )


def test_finish_target_is_negated_so_that_higher_is_better_like_fantasy_points():
    frame = _frame(
        [_metrics_row(2024, 2, "HAM", Position=3.0)],
        [_archive_row(2024, 2, "HAM@MER")],
    )
    assert frame["target_finish"].tolist() == [-3.0]


def test_race_one_is_excluded():
    frame = _frame(
        [_metrics_row(2024, 1, "HAM"), _metrics_row(2024, 2, "HAM")],
        [_archive_row(2024, 1, "HAM@MER"), _archive_row(2024, 2, "HAM@MER")],
    )
    assert frame["Race"].tolist() == [2]


@pytest.mark.parametrize("status", ["Did not start", "Withdrew"])
def test_drivers_who_never_raced_are_dropped_even_with_no_fantasy_row(status: str):
    frame = _frame(
        [_metrics_row(2024, 2, "HAM"), _metrics_row(2024, 2, "VER", Status=status)],
        [_archive_row(2024, 2, "HAM@MER")],
    )
    assert frame["Driver"].tolist() == ["HAM"]


def test_retirements_stay_in_and_are_flagged_as_non_finishers():
    frame = _frame(
        [
            _metrics_row(2024, 2, "HAM", Status="Retired"),
            _metrics_row(2024, 2, "VER", Status="Lapped"),
            _metrics_row(2024, 2, "NOR", Status="Finished"),
        ],
        [_archive_row(2024, 2, f"{d}@X") for d in ("HAM", "VER", "NOR")],
    )
    finished = frame.set_index("Driver")["finished"].to_dict()
    assert finished == {"HAM": False, "VER": True, "NOR": True}


def test_normal_weekend_slots():
    row = _frame([_metrics_row(2024, 2, "HAM")], [_archive_row(2024, 2, "HAM@MER")]).iloc[0]
    assert row["format"] == "normal"
    assert row["driver_rolling"] == 0.1
    assert row["constructor_rolling"] == 0.2
    assert row["early"] == 0.3
    assert row["late"] == 0.4
    assert row["odds"] == 0.5
    assert row["early_laps"] == 20.0
    assert row["late_laps"] == 15.0
    assert row["early_stint"] == 8.0
    assert row["late_stint"] == 5.0


def test_sprint_weekend_slots():
    row = _frame([_sprint_row(2024, 2, "HAM")], [_archive_row(2024, 2, "HAM@MER")]).iloc[0]
    assert row["format"] == "sprint"
    assert row["early"] == 0.6
    assert row["late"] == 0.7
    assert row["early_laps"] == 25.0
    assert row["late_laps"] == 12.0
    assert row["early_stint"] == 9.0
    assert row["late_stint"] == 3.0


def test_2023_sprint_weekend_has_its_own_format_and_no_late_slot():
    row = _frame(
        [_sprint_row(2023, 2, "HAM", **{
            "SQ_MinLapTime": None,
            "SQ_MinLapTime_rank": None,
            "SQ_TotalLapCount": None,
            "SQ_MaxLapsInStint": None,
        })],
        [_archive_row(2023, 2, "HAM@MER")],
    ).iloc[0]
    assert row["format"] == "sprint_fp1"
    assert row["early"] == 0.6
    assert pd.isna(row["late"])


def test_format_is_set_by_the_race_not_by_one_driver_missing_a_session():
    frame = _frame(
        [
            _sprint_row(2024, 2, "HAM"),
            _sprint_row(2024, 2, "VER", **{"SQ_MinLapTime": None, "SQ_MinLapTime_rank": None}),
        ],
        [_archive_row(2024, 2, "HAM@MER"), _archive_row(2024, 2, "VER@RED")],
    )
    assert set(frame["format"]) == {"sprint"}


def test_normal_format_is_also_set_by_the_race_not_by_one_driver():
    frame = _frame(
        [
            _metrics_row(2024, 2, "HAM"),
            _metrics_row(2024, 2, "VER", FP2_MinLapTime=None, FP2_MinLapTime_rank=None),
        ],
        [_archive_row(2024, 2, "HAM@MER"), _archive_row(2024, 2, "VER@RED")],
    )
    assert set(frame["format"]) == {"normal"}


def test_race_with_no_practice_sessions_is_an_error():
    with pytest.raises(ValueError, match="2024 race 2"):
        _frame(
            [_metrics_row(2024, 2, "HAM", FP2_MinLapTime_rank=None, FP3_MinLapTime_rank=None)],
            [_archive_row(2024, 2, "HAM@MER")],
        )


def test_no_late_session_on_a_2023_sprint_does_not_count_as_no_time():
    frame = _frame(
        [_sprint_row(2023, 2, "HAM", SQ_MinLapTime=None, SQ_MinLapTime_rank=None)],
        [_archive_row(2023, 2, "HAM@MER")],
    )
    assert frame["no_time"].tolist() == [False]


def test_no_time_flag_marks_a_driver_with_no_lap_in_a_slot_session():
    frame = _frame(
        [
            _metrics_row(2024, 2, "HAM"),
            _metrics_row(2024, 2, "VER", FP3_MinLapTime=None, FP3_MinLapTime_rank=0.0),
        ],
        [_archive_row(2024, 2, "HAM@MER"), _archive_row(2024, 2, "VER@RED")],
    )
    assert frame.set_index("Driver")["no_time"].to_dict() == {"HAM": False, "VER": True}


def test_grid_signal_is_negated_and_a_pit_lane_start_counts_as_last():
    frame = _frame(
        [
            _metrics_row(2024, 2, "HAM", GridPosition=2.0),
            _metrics_row(2024, 2, "VER", GridPosition=0.0),
        ],
        [_archive_row(2024, 2, "HAM@MER"), _archive_row(2024, 2, "VER@RED")],
    )
    grid = frame.set_index("Driver")["grid"].to_dict()
    assert grid["HAM"] == -2.0
    assert grid["VER"] < grid["HAM"]
