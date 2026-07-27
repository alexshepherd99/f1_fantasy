from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from fast_f1.metrics import METRIC_WEIGHTS, get_rolling_window_races
from fast_f1.output import build_race_metrics, generate_historical_metrics


class DummySession:
    def __init__(self, laps: pd.DataFrame):
        self.laps = laps

    def load(self, **kwargs) -> None:
        pass


class DummyRaceSession:
    def __init__(self, results: pd.DataFrame):
        self.results = results

    def load(self, **kwargs) -> None:
        pass


class DummyEvent:
    def __init__(self, sessions: dict[str, DummySession | DummyRaceSession]):
        self._sessions = sessions

    def get_session(self, code: str):
        if code not in self._sessions:
            raise ValueError(f"Session {code} unavailable")
        return self._sessions[code]


def test_build_race_metrics_merges_driver_and_constructor_ranks(monkeypatch):
    season_year = 2025
    race_num = 4

    def fake_get_event_for_race(season: int, race: int):
        return DummyEvent({"FP2": DummySession(pd.DataFrame()), "FP3": DummySession(pd.DataFrame())})

    def fake_select_practice_sessions_from_event(event):
        return ("FP2", "FP3")

    fp2_laps = pd.DataFrame(
        {
            "Driver": ["HAM", "VER"],
            "LapTime": [80.0, 81.0],
            "LapNumber": [1, 1],
            "Stint": [1, 1],
            "PitOutTime": [0, 0],
            "PitInTime": [0, 0],
            "Compound": ["C1", "C1"],
            "TyreLife": [5, 5],
            "FreshTyre": [True, True],
            "Season": [season_year, season_year],
            "Race": [race_num, race_num],
            "SessionType": ["FP2", "FP2"],
        }
    )
    fp3_laps = pd.DataFrame(
        {
            "Driver": ["HAM", "VER"],
            "LapTime": [79.0, 82.0],
            "LapNumber": [1, 1],
            "Stint": [1, 1],
            "PitOutTime": [0, 0],
            "PitInTime": [0, 0],
            "Compound": ["C1", "C1"],
            "TyreLife": [4, 4],
            "FreshTyre": [True, True],
            "Season": [season_year, season_year],
            "Race": [race_num, race_num],
            "SessionType": ["FP3", "FP3"],
        }
    )
    current_results = pd.DataFrame(
        {
            "Abbreviation": ["HAM", "VER"],
            "Status": ["Finished", "Finished"],
            "Position": [1, 2],
            "ClassifiedPosition": [1, 2],
            "GridPosition": [2, 1],
            "Points": [25, 18],
            "Constructor": ["Mercedes", "Red Bull"],
            "Season": [season_year, season_year],
            "Race": [race_num, race_num],
        }
    )

    prior_results = pd.concat(
        [
            pd.DataFrame(
                {
                    "Abbreviation": ["HAM", "VER"],
                    "Points": [18, 25],
                    "Constructor": ["Mercedes", "Red Bull"],
                    "Season": [season_year, season_year],
                    "Race": [race_num - 1, race_num - 1],
                }
            ),
            pd.DataFrame(
                {
                    "Abbreviation": ["HAM", "VER"],
                    "Points": [12, 15],
                    "Constructor": ["Mercedes", "Red Bull"],
                    "Season": [season_year, season_year],
                    "Race": [race_num - 2, race_num - 2],
                }
            ),
            pd.DataFrame(
                {
                    "Abbreviation": ["HAM", "VER"],
                    "Points": [15, 18],
                    "Constructor": ["Mercedes", "Red Bull"],
                    "Season": [season_year, season_year],
                    "Race": [race_num - 3, race_num - 3],
                }
            ),
        ],
        ignore_index=True,
    )

    def fake_get_session_laps(season, race, session_type):
        if session_type == "FP2":
            return fp2_laps
        if session_type == "FP3":
            return fp3_laps
        raise ValueError("Unexpected session type")

    def fake_get_race_results(season, race):
        if race == race_num:
            return current_results
        return prior_results[prior_results["Race"] == race].reset_index(drop=True)

    monkeypatch.setattr("fast_f1.output.get_event_for_race", fake_get_event_for_race)
    monkeypatch.setattr("fast_f1.output.select_practice_sessions_from_event", fake_select_practice_sessions_from_event)
    monkeypatch.setattr("fast_f1.output.get_session_laps", fake_get_session_laps)
    monkeypatch.setattr("fast_f1.output.get_race_results", fake_get_race_results)

    metrics = build_race_metrics(season_year, race_num)

    assert "AggregateRank" in metrics.columns
    assert "RollingPointsRank" in metrics.columns
    assert "ConstructorRollingPointsRank" in metrics.columns
    assert "FP2_MinLapTime_rank" in metrics.columns
    assert "FP3_MinLapTime_rank" in metrics.columns
    assert metrics.loc[metrics["Driver"] == "HAM", "AggregateRank"].iloc[0] >= 0
    assert metrics.loc[metrics["Driver"] == "VER", "AggregateRank"].iloc[0] >= 0


def test_build_race_metrics_adds_final_position_from_aggregate_rank(monkeypatch):
    season_year = 2025
    race_num = 4

    def fake_get_event_for_race(season: int, race: int):
        return DummyEvent({"FP2": DummySession(pd.DataFrame()), "FP3": DummySession(pd.DataFrame())})

    def fake_select_practice_sessions_from_event(event):
        return ("FP2", "FP3")

    fp2_laps = pd.DataFrame(
        {
            "Driver": ["HAM", "VER"],
            "LapTime": [80.0, 81.0],
            "LapNumber": [1, 1],
            "Stint": [1, 1],
            "PitOutTime": [0, 0],
            "PitInTime": [0, 0],
            "Compound": ["C1", "C1"],
            "TyreLife": [5, 5],
            "FreshTyre": [True, True],
            "Season": [season_year, season_year],
            "Race": [race_num, race_num],
            "SessionType": ["FP2", "FP2"],
        }
    )
    fp3_laps = pd.DataFrame(
        {
            "Driver": ["HAM", "VER"],
            "LapTime": [79.0, 82.0],
            "LapNumber": [1, 1],
            "Stint": [1, 1],
            "PitOutTime": [0, 0],
            "PitInTime": [0, 0],
            "Compound": ["C1", "C1"],
            "TyreLife": [4, 4],
            "FreshTyre": [True, True],
            "Season": [season_year, season_year],
            "Race": [race_num, race_num],
            "SessionType": ["FP3", "FP3"],
        }
    )
    current_results = pd.DataFrame(
        {
            "Abbreviation": ["HAM", "VER"],
            "Status": ["Finished", "Finished"],
            "Position": [1, 2],
            "ClassifiedPosition": [1, 2],
            "GridPosition": [2, 1],
            "Points": [25, 18],
            "Constructor": ["Mercedes", "Red Bull"],
            "Season": [season_year, season_year],
            "Race": [race_num, race_num],
        }
    )

    prior_results = pd.concat(
        [
            pd.DataFrame(
                {
                    "Abbreviation": ["HAM", "VER"],
                    "Points": [18, 25],
                    "Constructor": ["Mercedes", "Red Bull"],
                    "Season": [season_year, season_year],
                    "Race": [race_num - 1, race_num - 1],
                }
            ),
            pd.DataFrame(
                {
                    "Abbreviation": ["HAM", "VER"],
                    "Points": [12, 15],
                    "Constructor": ["Mercedes", "Red Bull"],
                    "Season": [season_year, season_year],
                    "Race": [race_num - 2, race_num - 2],
                }
            ),
            pd.DataFrame(
                {
                    "Abbreviation": ["HAM", "VER"],
                    "Points": [15, 18],
                    "Constructor": ["Mercedes", "Red Bull"],
                    "Season": [season_year, season_year],
                    "Race": [race_num - 3, race_num - 3],
                }
            ),
        ],
        ignore_index=True,
    )

    def fake_get_session_laps(season, race, session_type):
        if session_type == "FP2":
            return fp2_laps
        if session_type == "FP3":
            return fp3_laps
        raise ValueError("Unexpected session type")

    def fake_get_race_results(season, race):
        if race == race_num:
            return current_results
        return prior_results[prior_results["Race"] == race].reset_index(drop=True)

    monkeypatch.setattr("fast_f1.output.get_event_for_race", fake_get_event_for_race)
    monkeypatch.setattr("fast_f1.output.select_practice_sessions_from_event", fake_select_practice_sessions_from_event)
    monkeypatch.setattr("fast_f1.output.get_session_laps", fake_get_session_laps)
    monkeypatch.setattr("fast_f1.output.get_race_results", fake_get_race_results)

    metrics = build_race_metrics(season_year, race_num)

    assert "RankPosition" in metrics.columns
    sorted_metrics = metrics.sort_values("AggregateRank", ascending=False).reset_index(drop=True)
    assert sorted_metrics["RankPosition"].tolist() == [1, 2]


def test_build_race_metrics_works_when_race_results_missing(monkeypatch):
    """If official Race results are not yet published, metrics should still be computed
    using practice session drivers and prior-results constructor mapping."""
    season_year = 2026
    race_num = 6

    def fake_get_event_for_race(season: int, race: int):
        return DummyEvent({"FP2": DummySession(pd.DataFrame()), "FP3": DummySession(pd.DataFrame())})

    def fake_select_practice_sessions_from_event(event):
        return ("FP2", "FP3")

    fp2_laps = pd.DataFrame(
        {
            "Driver": ["ALO", "PER"],
            "LapTime": [85.0, 86.0],
            "LapNumber": [1, 1],
            "Stint": [1, 1],
            "PitOutTime": [0, 0],
            "PitInTime": [0, 0],
            "Compound": ["C1", "C1"],
            "TyreLife": [3, 3],
            "FreshTyre": [True, True],
            "Season": [season_year, season_year],
            "Race": [race_num, race_num],
            "SessionType": ["FP2", "FP2"],
        }
    )
    fp3_laps = pd.DataFrame(
        {
            "Driver": ["ALO", "PER"],
            "LapTime": [84.0, 87.0],
            "LapNumber": [1, 1],
            "Stint": [1, 1],
            "PitOutTime": [0, 0],
            "PitInTime": [0, 0],
            "Compound": ["C1", "C1"],
            "TyreLife": [2, 2],
            "FreshTyre": [True, True],
            "Season": [season_year, season_year],
            "Race": [race_num, race_num],
            "SessionType": ["FP3", "FP3"],
        }
    )

    # Prior results include constructor mapping for drivers
    prior_results = pd.concat(
        [
            pd.DataFrame(
                {
                    "Abbreviation": ["ALO", "PER"],
                    "Points": [10, 8],
                    "Constructor": ["Alfa", "Perse"],
                    "Season": [season_year, season_year],
                    "Race": [race_num - 1, race_num - 1],
                }
            ),
            pd.DataFrame(
                {
                    "Abbreviation": ["ALO", "PER"],
                    "Points": [12, 6],
                    "Constructor": ["Alfa", "Perse"],
                    "Season": [season_year, season_year],
                    "Race": [race_num - 2, race_num - 2],
                }
            ),
            pd.DataFrame(
                {
                    "Abbreviation": ["ALO", "PER"],
                    "Points": [9, 10],
                    "Constructor": ["Alfa", "Perse"],
                    "Season": [season_year, season_year],
                    "Race": [race_num - 3, race_num - 3],
                }
            ),
        ],
        ignore_index=True,
    )

    def fake_get_session_laps(season, race, session_type):
        if session_type == "FP2":
            return fp2_laps
        if session_type == "FP3":
            return fp3_laps
        raise ValueError("Unexpected session type")

    def fake_get_race_results(season, race):
        # Return empty for current race to simulate unpublished results
        if race == race_num:
            return pd.DataFrame()
        return prior_results[prior_results["Race"] == race].reset_index(drop=True)

    monkeypatch.setattr("fast_f1.output.get_event_for_race", fake_get_event_for_race)
    monkeypatch.setattr("fast_f1.output.select_practice_sessions_from_event", fake_select_practice_sessions_from_event)
    monkeypatch.setattr("fast_f1.output.get_session_laps", fake_get_session_laps)
    monkeypatch.setattr("fast_f1.output.get_race_results", fake_get_race_results)

    metrics = build_race_metrics(season_year, race_num)

    # Drivers derived from practice should be present
    assert set(metrics["Driver"]) >= {"ALO", "PER"}
    # Constructor mapping from prior results should be present
    assert "ConstructorRollingPointsRank" in metrics.columns
    assert "AggregateRank" in metrics.columns

    rank_columns = [
        col for col in metrics.columns
        if col != "AggregateRank" and (col.endswith("Rank") or col.endswith("_rank"))
    ]
    assert "ConstructorRollingPointsRank" in rank_columns

    for driver in ["ALO", "PER"]:
        driver_row = metrics[metrics["Driver"] == driver].iloc[0]
        expected_aggregate = sum(
            METRIC_WEIGHTS.get(col, 1.0) * driver_row[col] for col in rank_columns
        )
        assert driver_row["AggregateRank"] == pytest.approx(expected_aggregate)


def test_build_race_metrics_handles_first_race_with_no_prior_points(monkeypatch, caplog):
    season_year = 2025
    race_num = 1

    def fake_get_event_for_race(season: int, race: int):
        return DummyEvent({"FP2": DummySession(pd.DataFrame()), "FP3": DummySession(pd.DataFrame())})

    def fake_select_practice_sessions_from_event(event):
        return ("FP2", "FP3")

    fp2_laps = pd.DataFrame(
        {
            "Driver": ["HAM", "VER"],
            "LapTime": [80.0, 81.0],
            "LapNumber": [1, 1],
            "Stint": [1, 1],
            "PitOutTime": [0, 0],
            "PitInTime": [0, 0],
            "Compound": ["C1", "C1"],
            "TyreLife": [5, 5],
            "FreshTyre": [True, True],
            "Season": [season_year, season_year],
            "Race": [race_num, race_num],
            "SessionType": ["FP2", "FP2"],
        }
    )
    fp3_laps = pd.DataFrame(
        {
            "Driver": ["HAM", "VER"],
            "LapTime": [79.0, 82.0],
            "LapNumber": [1, 1],
            "Stint": [1, 1],
            "PitOutTime": [0, 0],
            "PitInTime": [0, 0],
            "Compound": ["C1", "C1"],
            "TyreLife": [4, 4],
            "FreshTyre": [True, True],
            "Season": [season_year, season_year],
            "Race": [race_num, race_num],
            "SessionType": ["FP3", "FP3"],
        }
    )
    current_results = pd.DataFrame(
        {
            "Abbreviation": ["HAM", "VER"],
            "Status": ["Finished", "Finished"],
            "Position": [1, 2],
            "ClassifiedPosition": [1, 2],
            "GridPosition": [2, 1],
            "Points": [25, 18],
            "Constructor": ["Mercedes", "Red Bull"],
            "Season": [season_year, season_year],
            "Race": [race_num, race_num],
        }
    )

    def fake_get_session_laps(season, race, session_type):
        if session_type == "FP2":
            return fp2_laps
        if session_type == "FP3":
            return fp3_laps
        raise ValueError("Unexpected session type")

    def fake_get_race_results(season, race):
        assert season == season_year
        assert race == race_num
        return current_results

    monkeypatch.setattr("fast_f1.output.get_event_for_race", fake_get_event_for_race)
    monkeypatch.setattr("fast_f1.output.select_practice_sessions_from_event", fake_select_practice_sessions_from_event)
    monkeypatch.setattr("fast_f1.output.get_session_laps", fake_get_session_laps)
    monkeypatch.setattr("fast_f1.output.get_race_results", fake_get_race_results)

    caplog.set_level("INFO", logger="fast_f1.output")
    metrics = build_race_metrics(season_year, race_num)

    assert "No prior races available to compute rolling points" in caplog.text
    assert "Assuming zero historical points" in caplog.text
    assert not metrics.empty
    assert all(metrics["RollingPointsRank"].fillna(0.0) == 0.0)
    assert all(metrics["ConstructorRollingPointsRank"].fillna(0.0) == 0.0)


def test_build_race_metrics_treats_a_session_with_no_timed_laps_as_missing(monkeypatch, caplog):
    """Laps with no lap time are as unusable as no laps at all.

    A session red-flagged before anyone set a time still returns lap rows, so
    the empty-frame guard does not catch it. The 107% threshold is then derived
    from a NaT and the rank arithmetic raises TypeError, which
    generate_historical_metrics does not catch - one washed-out practice
    session would abort a whole historical run instead of skipping one race.
    """
    season_year, race_num = 2025, 4
    drivers = ["HAM", "VER"]
    untimed_laps = pd.DataFrame(
        {
            "Driver": drivers,
            "LapTime": [pd.NaT, pd.NaT],
            "Stint": [1, 1],
            "Season": [season_year] * 2,
            "Race": [race_num] * 2,
            "SessionType": ["FP2"] * 2,
        }
    )

    monkeypatch.setattr(
        "fast_f1.output.get_event_for_race",
        lambda season, race: DummyEvent({"FP2": DummySession(pd.DataFrame()), "FP3": DummySession(pd.DataFrame())}),
    )
    monkeypatch.setattr("fast_f1.output.select_practice_sessions_from_event", lambda event: ("FP2", "FP3"))
    monkeypatch.setattr("fast_f1.output.get_session_laps", lambda season, race, session_type: untimed_laps)
    monkeypatch.setattr("fast_f1.output.get_race_results", lambda season, race: pd.DataFrame())

    caplog.set_level("ERROR", logger="fast_f1.output")
    with pytest.raises(RuntimeError, match="Required practice session data missing"):
        build_race_metrics(season_year, race_num)

    assert "FP2" in caplog.text


def test_build_race_metrics_fetches_exactly_the_rolling_window_races(monkeypatch):
    """The races fetched must be the window metrics.py scores over.

    build_race_metrics chooses which prior races to fetch and
    _calculate_rolling_points chooses which to sum. They are only ever right
    together, so this pins the two to one definition.
    """
    season_year, race_num = 2025, 4
    requested: list[int] = []

    laps = pd.DataFrame(
        {
            "Driver": ["HAM", "VER"],
            "LapTime": [80.0, 81.0],
            "Stint": [1, 1],
            "Season": [season_year] * 2,
            "Race": [race_num] * 2,
            "SessionType": ["FP2"] * 2,
        }
    )

    def fake_get_race_results(season, race):
        requested.append(race)
        return pd.DataFrame(
            {
                "Abbreviation": ["HAM", "VER"],
                "Points": [25, 18],
                "Constructor": ["Mercedes", "Red Bull"],
                "Season": [season] * 2,
                "Race": [race] * 2,
            }
        )

    monkeypatch.setattr(
        "fast_f1.output.get_event_for_race",
        lambda season, race: DummyEvent({"FP2": DummySession(pd.DataFrame()), "FP3": DummySession(pd.DataFrame())}),
    )
    monkeypatch.setattr("fast_f1.output.select_practice_sessions_from_event", lambda event: ("FP2", "FP3"))
    monkeypatch.setattr("fast_f1.output.get_session_laps", lambda season, race, session_type: laps)
    monkeypatch.setattr("fast_f1.output.get_race_results", fake_get_race_results)

    build_race_metrics(season_year, race_num, rolling_window=3)

    prior_races = [race for race in requested if race != race_num]
    assert prior_races == get_rolling_window_races(race_num, 3) == [1, 2, 3]


def _patch_minimal_race(monkeypatch, season_year, race_num, drivers):
    """Wire build_race_metrics to a two-driver race with no prior results."""
    laps = {
        session: pd.DataFrame(
            {
                "Driver": drivers,
                "LapTime": [80.0 + i for i in range(len(drivers))],
                "Stint": [1] * len(drivers),
                "Season": [season_year] * len(drivers),
                "Race": [race_num] * len(drivers),
                "SessionType": [session] * len(drivers),
            }
        )
        for session in ("FP2", "FP3")
    }
    current_results = pd.DataFrame(
        {
            "Abbreviation": drivers,
            "Points": [25, 18],
            "Constructor": ["Mercedes", "Red Bull"],
            "Season": [season_year] * len(drivers),
            "Race": [race_num] * len(drivers),
        }
    )

    monkeypatch.setattr(
        "fast_f1.output.get_event_for_race",
        lambda season, race: DummyEvent({"FP2": DummySession(pd.DataFrame()), "FP3": DummySession(pd.DataFrame())}),
    )
    monkeypatch.setattr(
        "fast_f1.output.select_practice_sessions_from_event", lambda event: ("FP2", "FP3")
    )
    monkeypatch.setattr(
        "fast_f1.output.get_session_laps", lambda season, race, session_type: laps[session_type]
    )
    monkeypatch.setattr("fast_f1.output.get_race_results", lambda season, race: current_results)


def test_build_race_metrics_includes_odds_rank_at_parity_weight(monkeypatch):
    season_year, race_num = 2025, 1
    _patch_minimal_race(monkeypatch, season_year, race_num, ["HAM", "VER"])
    monkeypatch.setattr(
        "fast_f1.output.load_odds", lambda *args, **kwargs: {"HAM": 0.4, "VER": 0.04}
    )

    metrics = build_race_metrics(season_year, race_num).set_index("Driver")

    assert metrics.loc["HAM", "OddsRank"] == pytest.approx(1.0)
    assert metrics.loc["VER", "OddsRank"] == pytest.approx(0.0)
    # The raw probability is carried through for auditability
    assert metrics.loc["HAM", "OddsImpliedProbability"] == pytest.approx(0.4)

    # HAM's odds advantage must reach AggregateRank at the same weight as every
    # other indicator
    other_ranks = sum(
        METRIC_WEIGHTS.get(col, 1.0) * metrics.loc["HAM", col]
        for col in metrics.columns
        if col not in ("AggregateRank", "OddsRank") and (col.endswith("Rank") or col.endswith("_rank"))
    )
    assert metrics.loc["HAM", "AggregateRank"] == pytest.approx(other_ranks + 1.0)


def test_build_race_metrics_zeroes_odds_when_lookup_fails(monkeypatch, caplog):
    season_year, race_num = 2025, 1
    _patch_minimal_race(monkeypatch, season_year, race_num, ["HAM", "VER"])

    def explode(*args, **kwargs):
        raise ValueError("odds_to_pct invalid input nonsense")

    monkeypatch.setattr("fast_f1.output.load_odds", explode)

    caplog.set_level("WARNING", logger="fast_f1.output")
    metrics = build_race_metrics(season_year, race_num)

    assert list(metrics["OddsRank"]) == [0.0, 0.0]
    assert "odds" in caplog.text.lower()


def test_build_race_metrics_does_not_multiply_rows_for_repeated_drivers(monkeypatch):
    """A driver appearing twice in results must not fan out through the odds merge."""
    season_year, race_num = 2025, 1
    _patch_minimal_race(monkeypatch, season_year, race_num, ["HAM", "VER"])

    repeated = pd.DataFrame(
        {
            "Abbreviation": ["HAM", "HAM", "VER"],
            "Points": [25, 25, 18],
            "Constructor": ["Mercedes", "Mercedes", "Red Bull"],
            "Season": [season_year] * 3,
            "Race": [race_num] * 3,
        }
    )
    monkeypatch.setattr("fast_f1.output.get_race_results", lambda season, race: repeated)
    monkeypatch.setattr(
        "fast_f1.output.load_odds", lambda *args, **kwargs: {"HAM": 0.4, "VER": 0.04}
    )

    metrics = build_race_metrics(season_year, race_num)

    assert len(metrics) == len(repeated)


def test_build_race_metrics_survives_a_corrupt_odds_workbook(monkeypatch, tmp_path, caplog):
    """A damaged spreadsheet must degrade the odds indicator, not abort the run."""
    season_year, race_num = 2025, 1
    _patch_minimal_race(monkeypatch, season_year, race_num, ["HAM", "VER"])

    # A truncated workbook is the realistic corruption: still recognisably an
    # xlsx, so pandas gets as far as unzipping it and raises BadZipFile, which
    # derives from Exception rather than OSError/ValueError
    corrupt = tmp_path / "f1_betting_odds.xlsx"
    source = Path("data/f1_betting_odds.xlsx").read_bytes()
    corrupt.write_bytes(source[: len(source) // 4])
    monkeypatch.setattr(
        "fast_f1.output.load_odds",
        lambda *args, **kwargs: pd.read_excel(corrupt),
    )

    caplog.set_level("WARNING", logger="fast_f1.output")
    metrics = build_race_metrics(season_year, race_num)

    assert list(metrics["OddsRank"]) == [0.0, 0.0]
    assert "odds" in caplog.text.lower()


def test_build_race_metrics_does_not_read_the_real_odds_spreadsheet(monkeypatch):
    """Tests must not silently pick up live odds data.

    2026 race 9 with ANT and RUS is a real, populated row set in
    data/f1_betting_odds.xlsx, so without isolation this would score them from
    the live file rather than from the test's own inputs.
    """
    season_year, race_num = 2026, 9
    _patch_minimal_race(monkeypatch, season_year, race_num, ["ANT", "RUS"])

    metrics = build_race_metrics(season_year, race_num)

    assert list(metrics["OddsRank"]) == [0.0, 0.0]
    assert list(metrics["OddsImpliedProbability"]) == [0.0, 0.0]


def test_historical_metrics_walks_the_rounds_each_season_actually_has(monkeypatch, tmp_path):
    """Seasons differ in length, so the race range cannot be one hardcoded list.

    2024 and 2025 ran 24 rounds where 2023 and 2026 ran 22; a shared range
    either misses real races or asks for rounds that never existed.
    """
    scheduled_rounds = {2024: [1, 2, 3], 2025: [1, 2]}
    monkeypatch.setattr(
        "fastf1.get_event_schedule",
        lambda season_year, include_testing=False: pd.DataFrame(
            {"RoundNumber": scheduled_rounds[season_year]}
        ),
    )

    attempted: list[tuple[int, int]] = []

    def fake_build_race_metrics(season_year, race_num, *args, **kwargs):
        attempted.append((season_year, race_num))
        raise RuntimeError("No data published for this race")

    monkeypatch.setattr("fast_f1.output.build_race_metrics", fake_build_race_metrics)

    generate_historical_metrics([2024, 2025], output_path=tmp_path / "historical.xlsx")

    assert attempted == [(2024, 1), (2024, 2), (2024, 3), (2025, 1), (2025, 2)]


def test_historical_metrics_walks_over_a_gap_in_the_round_numbers(monkeypatch, tmp_path):
    """A missing round is stepped over, not stopped at and not invented.

    Rounds are taken from the schedule as they are, so a season listing 1, 2, 5
    is walked as 1, 2, 5 - asking for the absent 3 and 4 would raise a
    ValueError that the historical loop does not catch.
    """
    monkeypatch.setattr(
        "fastf1.get_event_schedule",
        lambda season_year, include_testing=False: pd.DataFrame({"RoundNumber": [1, 2, 5]}),
    )

    attempted: list[tuple[int, int]] = []

    def fake_build_race_metrics(season_year, race_num, *args, **kwargs):
        attempted.append((season_year, race_num))
        raise RuntimeError("No data published for this race")

    monkeypatch.setattr("fast_f1.output.build_race_metrics", fake_build_race_metrics)

    generate_historical_metrics([2025], output_path=tmp_path / "historical.xlsx")

    assert attempted == [(2025, 1), (2025, 2), (2025, 5)]
