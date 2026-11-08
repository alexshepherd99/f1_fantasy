from __future__ import annotations

import math

import pandas as pd
import pytest

from fast_f1.metrics import (
    aggregate_metrics,
    calculate_constructor_rolling_points,
    calculate_odds_rank,
    calculate_practice_performance,
    calculate_rolling_points,
    get_rolling_window_races,
)


def test_get_rolling_window_races_returns_prior_races():
    assert get_rolling_window_races(1, 3) == []
    assert get_rolling_window_races(2, 3) == [1]
    assert get_rolling_window_races(4, 3) == [1, 2, 3]
    assert get_rolling_window_races(5, 4) == [1, 2, 3, 4]


def test_calculate_rolling_points_sums_and_ranks():
    df_data = pd.DataFrame({
        "Race": [1, 1, 2, 2, 3, 3],
        "Abbreviation": ["VER", "HAM", "VER", "HAM", "VER", "HAM"],
        "Points": [25, 18, 20, 15, 25, 10],
    })

    result = calculate_rolling_points(df_data, season_year=2025, race_num=3, rolling_window=3)

    assert set(result["Driver"]) == {"VER", "HAM"}
    ver = result[result["Driver"] == "VER"].iloc[0]
    ham = result[result["Driver"] == "HAM"].iloc[0]
    assert ver["RollingPoints"] == 45
    assert ham["RollingPoints"] == 33
    assert ver["RollingPointsRank"] == pytest.approx(1.0, 1e-4)
    assert ham["RollingPointsRank"] == pytest.approx(0.0, 1e-4)
    assert all(result["Season"] == 2025)
    assert all(result["Race"] == 3)


def test_calculate_rolling_points_supports_constructor_column():
    df_data = pd.DataFrame({
        "Race": [1, 1, 2, 2],
        "Constructor": ["RED", "MER", "RED", "MER"],
        "Points": [18, 25, 20, 15],
    })

    result = calculate_rolling_points(df_data, season_year=2025, race_num=3, rolling_window=3)

    assert set(result["Driver"]) == {"RED", "MER"}
    red = result[result["Driver"] == "RED"].iloc[0]
    mer = result[result["Driver"] == "MER"].iloc[0]
    assert red["RollingPoints"] == 38
    assert mer["RollingPoints"] == 40
    assert mer["RollingPointsRank"] == pytest.approx(1.0, 1e-4)
    assert red["RollingPointsRank"] == pytest.approx(0.0, 1e-4)


def test_calculate_rolling_points_returns_empty_when_no_previous_races():
    df_data = pd.DataFrame({
        "Race": [1, 1],
        "Abbreviation": ["VER", "HAM"],
        "Points": [25, 18],
    })

    result = calculate_rolling_points(df_data, season_year=2025, race_num=1, rolling_window=3)
    assert result.empty
    assert list(result.columns) == ["Driver", "RollingPoints", "RollingPointsRank", "Season", "Race"]


def test_calculate_rolling_points_handles_empty_input_frame():
    result = calculate_rolling_points(pd.DataFrame(), season_year=2025, race_num=1, rolling_window=3)
    assert result.empty
    assert list(result.columns) == ["Driver", "RollingPoints", "RollingPointsRank", "Season", "Race"]


def test_calculate_constructor_rolling_points_handles_empty_input_frame():
    result = calculate_constructor_rolling_points(pd.DataFrame(), season_year=2025, race_num=1, rolling_window=3)
    assert result.empty
    assert list(result.columns) == [
        "Constructor",
        "ConstructorRollingPoints",
        "ConstructorRollingPointsRank",
        "Season",
        "Race",
    ]


def test_calculate_practice_performance_creates_ranked_columns():
    df_session_laps = pd.DataFrame({
        "Season": [2025, 2025, 2025, 2025],
        "Race": [5, 5, 5, 5],
        "SessionType": ["FP2", "FP2", "FP2", "FP2"],
        "Driver": ["PER", "ALO", "PER", "ALO"],
        "LapTime": [80.0, 82.0, 83.0, 79.0],
        "Stint": [1, 1, 2, 2],
    })

    result = calculate_practice_performance(df_session_laps)
    assert set(result.columns) >= {
        "Driver",
        "FP2_TotalLapCount",
        "FP2_MinLapTime",
        "FP2_MaxLapsInStint",
        "FP2_MinLapTime_rank",
        "Season",
        "Race",
    }
    assert result.loc[result["Driver"] == "PER", "FP2_TotalLapCount"].iloc[0] == 2
    assert result.loc[result["Driver"] == "ALO", "FP2_TotalLapCount"].iloc[0] == 2
    assert result.loc[result["Driver"] == "ALO", "FP2_MinLapTime_rank"].iloc[0] == pytest.approx(1.0, 1e-4)
    assert result.loc[result["Driver"] == "PER", "FP2_MinLapTime_rank"].iloc[0] == pytest.approx(0.0, 1e-4)


def test_calculate_practice_performance_raises_when_multiple_session_types():
    df_session_laps = pd.DataFrame({
        "Season": [2025, 2025],
        "Race": [5, 5],
        "SessionType": ["FP2", "FP3"],
        "Driver": ["PER", "ALO"],
        "LapTime": [80.0, 81.0],
        "Stint": [1, 1],
    })

    with pytest.raises(ValueError):
        calculate_practice_performance(df_session_laps)


def _race_ranks(race: int, **columns: list[float]) -> pd.DataFrame:
    """Drivers A and B's rank columns in one 2026 race, each given as [A, B].

    Driver rolling, constructor rolling and odds default to zero; a session column is
    present only when given, as in a race that held that session.
    """
    frame = {
        "Season": [2026, 2026],
        "Race": [race, race],
        "Driver": ["A", "B"],
        "RollingPointsRank": [0.0, 0.0],
        "ConstructorRollingPointsRank": [0.0, 0.0],
        "OddsRank": [0.0, 0.0],
    }
    frame.update(columns)
    return pd.DataFrame(frame)


def _aggregates(result: pd.DataFrame) -> dict[str, float]:
    return dict(zip(result["Driver"], result["AggregateRank"]))


def test_aggregate_metrics_adds_driver_constructor_and_fp3_on_a_normal_weekend():
    # B leads only on the inputs a normal weekend leaves out: FP2 and odds.
    df = _race_ranks(
        5,
        RollingPointsRank=[0.5, 0.0],
        ConstructorRollingPointsRank=[0.25, 0.0],
        FP2_MinLapTime_rank=[0.0, 1.0],
        FP3_MinLapTime_rank=[0.125, 0.0],
        OddsRank=[0.0, 1.0],
    )

    result = aggregate_metrics(df)

    assert _aggregates(result) == pytest.approx({"A": 0.875, "B": 0.0})
    assert list(result["Driver"]) == ["A", "B"]


def test_aggregate_metrics_adds_driver_and_constructor_on_a_sprint_weekend():
    # B leads only on practice and odds, which a sprint weekend leaves out.
    df = _race_ranks(
        5,
        RollingPointsRank=[0.5, 0.0],
        ConstructorRollingPointsRank=[0.25, 0.0],
        FP1_MinLapTime_rank=[0.0, 1.0],
        SQ_MinLapTime_rank=[0.0, 1.0],
        OddsRank=[0.0, 1.0],
    )

    assert _aggregates(aggregate_metrics(df)) == pytest.approx({"A": 0.75, "B": 0.0})


def test_aggregate_metrics_adds_driver_and_constructor_on_a_2023_fp1_only_sprint():
    df = _race_ranks(
        5,
        RollingPointsRank=[0.5, 0.0],
        ConstructorRollingPointsRank=[0.25, 0.0],
        FP1_MinLapTime_rank=[0.0, 1.0],
        OddsRank=[0.0, 1.0],
    )

    assert _aggregates(aggregate_metrics(df)) == pytest.approx({"A": 0.75, "B": 0.0})


def test_aggregate_metrics_ranks_race_one_on_odds_alone():
    # B leads on every input but odds.
    df = _race_ranks(
        1,
        RollingPointsRank=[0.0, 1.0],
        ConstructorRollingPointsRank=[0.0, 1.0],
        FP2_MinLapTime_rank=[0.0, 1.0],
        FP3_MinLapTime_rank=[0.0, 1.0],
        OddsRank=[0.25, 0.0],
    )

    assert _aggregates(aggregate_metrics(df)) == pytest.approx({"A": 0.25, "B": 0.0})


def test_aggregate_metrics_counts_a_missing_input_as_zero():
    df = _race_ranks(
        5,
        RollingPointsRank=[0.5, 0.25],
        ConstructorRollingPointsRank=[0.25, 0.25],
        FP2_MinLapTime_rank=[1.0, 0.0],
        FP3_MinLapTime_rank=[float("nan"), 1.0],
    )

    assert _aggregates(aggregate_metrics(df)) == pytest.approx({"A": 0.75, "B": 1.5})


def test_aggregate_metrics_runs_on_a_normal_weekend_before_fp3():
    df = _race_ranks(
        5,
        RollingPointsRank=[0.5, 0.0],
        ConstructorRollingPointsRank=[0.25, 0.0],
        FP2_MinLapTime_rank=[0.0, 1.0],
    )

    assert _aggregates(aggregate_metrics(df)) == pytest.approx({"A": 0.75, "B": 0.0})


def test_aggregate_metrics_handles_several_races_at_once():
    # Together the two races hold every session column, so the sprint race's rows
    # have FP2 and FP3 missing, as in the stored metrics file. Reading the sprint as a
    # normal weekend would not change its sum today, as its FP3 counts zero, so this
    # does not pin the format to each race.
    normal = _race_ranks(
        5,
        RollingPointsRank=[0.5, 0.0],
        FP2_MinLapTime_rank=[0.0, 1.0],
        FP3_MinLapTime_rank=[0.25, 0.0],
    )
    sprint = _race_ranks(
        6,
        RollingPointsRank=[0.5, 0.0],
        FP1_MinLapTime_rank=[0.0, 1.0],
        SQ_MinLapTime_rank=[1.0, 0.0],
    )

    result = aggregate_metrics(pd.concat([normal, sprint], ignore_index=True))

    by_race = {race: _aggregates(rows) for race, rows in result.groupby("Race")}
    assert by_race == {
        5: pytest.approx({"A": 0.75, "B": 0.0}),
        6: pytest.approx({"A": 0.5, "B": 0.0}),
    }


def test_calculate_odds_rank_normalises_on_a_log_scale():
    # Implied probabilities a decade apart should land evenly spaced, which is
    # the point of normalising on log rather than on the raw probability
    driver_odds = {"A": 0.5, "B": 0.1, "C": 0.01}

    result = calculate_odds_rank(driver_odds, ["A", "B", "C"], season_year=2026, race_num=9)

    ranks = result.set_index("Driver")["OddsRank"]
    span = math.log(0.5) - math.log(0.01)
    assert ranks["A"] == pytest.approx(1.0, abs=1e-6)
    assert ranks["B"] == pytest.approx((math.log(0.1) - math.log(0.01)) / span, abs=1e-6)
    assert ranks["C"] == pytest.approx(0.0, abs=1e-6)

    # The raw probability is carried through alongside the normalised rank
    assert result.set_index("Driver")["OddsImpliedProbability"]["B"] == pytest.approx(0.1)
    assert set(result["Season"]) == {2026}
    assert set(result["Race"]) == {9}


def test_calculate_odds_rank_scores_drivers_without_odds_as_zero():
    driver_odds = {"A": 0.5, "B": 0.05}

    result = calculate_odds_rank(driver_odds, ["A", "B", "NOODDS"], season_year=2026, race_num=9)

    ranks = result.set_index("Driver")["OddsRank"]
    assert list(result["Driver"]) == ["A", "B", "NOODDS"]
    assert ranks["NOODDS"] == 0.0
    assert result.set_index("Driver")["OddsImpliedProbability"]["NOODDS"] == 0.0
    # The drivers that do have odds still normalise across their own range
    assert ranks["A"] == pytest.approx(1.0, abs=1e-6)
    assert ranks["B"] == pytest.approx(0.0, abs=1e-6)


def test_calculate_odds_rank_returns_zeros_when_no_odds_available():
    result = calculate_odds_rank({}, ["A", "B"], season_year=2026, race_num=9)

    assert list(result["Driver"]) == ["A", "B"]
    assert list(result["OddsRank"]) == [0.0, 0.0]
    assert list(result["OddsImpliedProbability"]) == [0.0, 0.0]


def test_calculate_odds_rank_returns_zeros_when_every_price_is_equal():
    result = calculate_odds_rank({"A": 0.2, "B": 0.2}, ["A", "B"], season_year=2026, race_num=9)

    assert list(result["OddsRank"]) == [0.0, 0.0]


def test_calculate_odds_rank_handles_no_drivers():
    result = calculate_odds_rank({"A": 0.5}, [], season_year=2026, race_num=9)

    assert result.empty
    assert list(result.columns) == [
        "Driver", "OddsImpliedProbability", "OddsRank", "Season", "Race"
    ]


def test_calculate_odds_rank_returns_one_row_per_distinct_driver():
    # The result is merged on Driver, so a repeated driver would fan the merge
    # out into a cartesian product rather than annotating the existing rows
    result = calculate_odds_rank(
        {"A": 0.5, "B": 0.1}, ["A", "A", "B"], season_year=2026, race_num=9
    )

    assert list(result["Driver"]) == ["A", "B"]
    assert result["Driver"].is_unique
