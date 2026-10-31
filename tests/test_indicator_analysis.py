import pandas as pd
import pytest

from fast_f1.indicator_analysis import (
    build_analysis_frame,
    combination_signal,
    race_scores,
)


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


def _race(season: int, race: int, **columns: list[float]) -> pd.DataFrame:
    """A small race with drivers D0, D1, ... and the given columns."""
    size = len(next(iter(columns.values())))
    return pd.DataFrame({
        "Season": season,
        "Race": race,
        "Driver": [f"D{i}" for i in range(size)],
        **columns,
    })


def test_race_scores_spearman_is_one_race_at_a_time_and_ignores_scale():
    frame = pd.concat([
        _race(2024, 2, target=[3.0, 2.0, 1.0], signal=[100.0, 2.0, 1.0]),
        _race(2024, 3, target=[3.0, 2.0, 1.0], signal=[1.0, 2.0, 3.0]),
    ], ignore_index=True)
    scores = race_scores(frame, frame["signal"], "target")
    assert scores["Season"].tolist() == [2024, 2024]
    assert scores["Race"].tolist() == [2, 3]
    assert scores["spearman"].tolist() == pytest.approx([1.0, -1.0])


def test_race_scores_top_k_is_the_share_of_the_actual_top_k_also_picked():
    target = [9.0, 8.0, 7.0, 6.0, 5.0, 4.0, 3.0]
    # The signal's top 3 is D0, D1, D5 and its top 5 adds D3 and D6.
    signal = [9.0, 8.0, 3.0, 6.0, 2.0, 7.0, 5.0]
    frame = _race(2024, 2, target=target, signal=signal)
    row = race_scores(frame, frame["signal"], "target").iloc[0]
    assert row["top3"] == pytest.approx(2 / 3)
    assert row["top5"] == pytest.approx(3 / 5)


def test_race_scores_rejects_a_missing_signal_rather_than_scoring_around_it():
    frame = _race(2024, 2, target=[3.0, 2.0, 1.0], signal=[1.0, None, 3.0])
    with pytest.raises(ValueError, match="2024 race 2"):
        race_scores(frame, frame["signal"], "target")


def test_race_scores_rejects_a_constant_signal_which_has_no_rank_correlation():
    frame = _race(2024, 2, target=[3.0, 2.0, 1.0], signal=[0.0, 0.0, 0.0])
    with pytest.raises(ValueError, match="2024 race 2"):
        race_scores(frame, frame["signal"], "target")


def test_combination_signal_is_an_equal_weight_sum_of_the_stored_values():
    frame = _race(2024, 2, a=[1.0, 0.5], b=[0.25, 0.75], c=[9.0, 9.0])
    assert combination_signal(frame, ("a", "b")).tolist() == [1.25, 1.25]


def test_combination_signal_rank_scale_removes_the_effect_of_one_outlier():
    # Min-max style values where one slow lap squeezes the rest towards the top.
    frame = _race(2024, 2, pace=[1.0, 0.99, 0.98, 0.0], rolling=[0.0, 0.5, 1.0, 0.25])
    stored = combination_signal(frame, ("pace", "rolling"))
    ranked = combination_signal(frame, ("pace", "rolling"), scale="rank")
    assert stored.idxmax() == 2  # rolling decides it, because pace barely varies
    assert ranked.tolist() == pytest.approx([1.25, 1.5, 1.5, 0.75])


def test_combination_signal_ranks_within_each_race():
    frame = pd.concat([
        _race(2024, 2, a=[1.0, 2.0]),
        _race(2024, 3, a=[30.0, 40.0]),
    ], ignore_index=True)
    assert combination_signal(frame, ("a",), scale="rank").tolist() == [0.5, 1.0, 0.5, 1.0]


def test_combination_signal_does_not_treat_a_missing_slot_as_zero():
    frame = _race(2024, 2, a=[1.0, 0.5], b=[None, 0.75])
    assert combination_signal(frame, ("a", "b")).isna().tolist() == [True, False]
