from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from fast_f1.metrics import get_rolling_window_races
from fast_f1.output import (
    HistoricalRunIncomplete,
    build_race_metrics,
    generate_historical_metrics,
    load_existing_metrics,
)


def _write_odds_file(path: Path, season_year: int, race_num: int, odds_by_driver: dict[str, str]) -> Path:
    """Write a betting odds file holding one race, in the layout `load_odds` reads."""
    pd.DataFrame(
        {
            "Driver": list(odds_by_driver),
            "Constructor": ["CON"] * len(odds_by_driver),
            "Season": [season_year] * len(odds_by_driver),
            "Race": [race_num] * len(odds_by_driver),
            "Odds": list(odds_by_driver.values()),
        }
    ).to_csv(path, index=False)
    return path


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
    using practice session drivers and the teams the sessions name for them."""
    season_year = 2026
    race_num = 6

    def fake_get_event_for_race(season: int, race: int):
        return DummyEvent({"FP2": DummySession(pd.DataFrame()), "FP3": DummySession(pd.DataFrame())})

    def fake_select_practice_sessions_from_event(event):
        return ("FP2", "FP3")

    fp2_laps = pd.DataFrame(
        {
            "Driver": ["ALO", "PER"],
            # PER tops FP2 alone, so leaving FP2 out moves the aggregate
            "LapTime": [86.0, 85.0],
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
    monkeypatch.setattr(
        "fast_f1.output.get_session_drivers",
        lambda season, race, session_type: pd.DataFrame(
            {"Abbreviation": ["ALO", "PER"], "TeamName": ["Alfa", "Perse"]}
        ),
    )

    metrics = build_race_metrics(season_year, race_num)

    # Drivers derived from practice should be present
    assert set(metrics["Driver"]) >= {"ALO", "PER"}
    # Constructor ranks should be present
    assert "ConstructorRollingPointsRank" in metrics.columns
    assert "AggregateRank" in metrics.columns

    # A normal weekend after race 1 adds driver rolling, constructor rolling and FP3.
    for driver in ["ALO", "PER"]:
        driver_row = metrics[metrics["Driver"] == driver].iloc[0]
        expected_aggregate = (
            driver_row["RollingPointsRank"]
            + driver_row["ConstructorRollingPointsRank"]
            + driver_row["FP3_MinLapTime_rank"]
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
    generate_historical_metrics treats as a failure rather than missing data -
    one washed-out practice session would end a whole historical run as
    incomplete instead of skipping one race.
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
    monkeypatch.setattr(
        "fast_f1.output.get_session_laps",
        lambda season, race, session_type: laps.assign(SessionType=session_type),
    )
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


def test_build_race_metrics_ranks_race_one_on_odds_alone(monkeypatch, tmp_path):
    season_year, race_num = 2025, 1
    _patch_minimal_race(monkeypatch, season_year, race_num, ["HAM", "VER"])
    # 3/2 and 24/1 imply probabilities of 0.4 and 0.04
    odds_file = _write_odds_file(
        tmp_path / "odds.csv", season_year, race_num, {"HAM": "3/2", "VER": "24/1"}
    )

    metrics = build_race_metrics(season_year, race_num, odds_file=odds_file).set_index("Driver")

    assert metrics.loc["HAM", "OddsRank"] == pytest.approx(1.0)
    assert metrics.loc["VER", "OddsRank"] == pytest.approx(0.0)
    # The raw probability is carried through for auditability
    assert metrics.loc["HAM", "OddsImpliedProbability"] == pytest.approx(0.4)

    # HAM also tops both practice sessions, which race 1 leaves out
    assert metrics.loc["HAM", "FP2_MinLapTime_rank"] == pytest.approx(1.0)
    assert metrics.loc["HAM", "FP3_MinLapTime_rank"] == pytest.approx(1.0)
    assert metrics.loc["HAM", "AggregateRank"] == pytest.approx(1.0)
    assert metrics.loc["VER", "AggregateRank"] == pytest.approx(0.0)


def test_build_race_metrics_zeroes_odds_when_lookup_fails(monkeypatch, tmp_path, caplog):
    season_year, race_num = 2025, 1
    _patch_minimal_race(monkeypatch, season_year, race_num, ["HAM", "VER"])
    # `odds_to_pct` raises ValueError on a price it cannot parse
    odds_file = _write_odds_file(
        tmp_path / "odds.csv", season_year, race_num, {"HAM": "nonsense", "VER": "24/1"}
    )

    caplog.set_level("WARNING", logger="fast_f1.output")
    metrics = build_race_metrics(season_year, race_num, odds_file=odds_file)

    assert list(metrics["OddsRank"]) == [0.0, 0.0]
    assert "odds" in caplog.text.lower()


def test_build_race_metrics_does_not_multiply_rows_for_repeated_drivers(monkeypatch, tmp_path):
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
    odds_file = _write_odds_file(
        tmp_path / "odds.csv", season_year, race_num, {"HAM": "3/2", "VER": "24/1"}
    )

    metrics = build_race_metrics(season_year, race_num, odds_file=odds_file)

    assert len(metrics) == len(repeated)


def _patch_race_with_history(monkeypatch, season_year, results_by_race):
    """Wire build_race_metrics to per-race results given as (driver, constructor, points).

    The last race in ``results_by_race`` is the one being built, and its
    drivers are the ones given practice laps.
    """
    race_num = max(results_by_race)
    drivers = [driver for driver, _, _ in results_by_race[race_num]]
    laps = pd.DataFrame(
        {
            "Driver": drivers,
            "LapTime": [80.0 + i for i in range(len(drivers))],
            "Stint": [1] * len(drivers),
            "Season": [season_year] * len(drivers),
            "Race": [race_num] * len(drivers),
            "SessionType": ["FP2"] * len(drivers),
        }
    )

    def fake_get_race_results(season, race):
        rows = results_by_race[race]
        return pd.DataFrame(
            {
                "Abbreviation": [driver for driver, _, _ in rows],
                "Constructor": [constructor for _, constructor, _ in rows],
                "Points": [points for _, _, points in rows],
                "Season": [season] * len(rows),
                "Race": [race] * len(rows),
            }
        )

    monkeypatch.setattr(
        "fast_f1.output.get_event_for_race",
        lambda season, race: DummyEvent({"FP2": DummySession(pd.DataFrame()), "FP3": DummySession(pd.DataFrame())}),
    )
    monkeypatch.setattr("fast_f1.output.select_practice_sessions_from_event", lambda event: ("FP2", "FP3"))
    monkeypatch.setattr(
        "fast_f1.output.get_session_laps",
        lambda season, race, session_type: laps.assign(SessionType=session_type),
    )
    monkeypatch.setattr("fast_f1.output.get_race_results", fake_get_race_results)
    return race_num


def _constructor_points(metrics: pd.DataFrame) -> dict[str, float]:
    return metrics.set_index("Driver")["ConstructorRollingPoints"].to_dict()


def test_build_race_metrics_keeps_rolling_points_for_a_renamed_team(monkeypatch):
    """2024 race 24: a team renamed in the race being built keeps its history."""
    season_year = 2024
    before = [("VER", "Red Bull Racing", 25), ("PER", "Red Bull Racing", 10),
              ("HAM", "Mercedes", 18), ("RUS", "Mercedes", 12)]
    after = [("VER", "Red Bull", 25), ("PER", "Red Bull", 10),
             ("HAM", "Mercedes", 18), ("RUS", "Mercedes", 12)]
    race_num = _patch_race_with_history(monkeypatch, season_year, {1: before, 2: before, 3: before, 4: after})

    metrics = build_race_metrics(season_year, race_num)

    assert _constructor_points(metrics) == {"VER": 105, "PER": 105, "HAM": 90, "RUS": 90}
    by_driver = metrics.set_index("Driver")
    assert by_driver.loc["VER", "ConstructorRollingPointsRank"] == pytest.approx(1.0)
    # The stored name stays as FastF1 gave it for the race
    assert by_driver.loc["VER", "Constructor"] == "Red Bull"


def test_build_race_metrics_keeps_rolling_points_when_a_name_flips_back_and_forth(monkeypatch):
    """The current name having some history must not drop the races under the other name."""
    season_year = 2024

    def race(red_bull_name):
        return [("VER", red_bull_name, 25), ("PER", red_bull_name, 10),
                ("HAM", "Mercedes", 18), ("RUS", "Mercedes", 12)]

    race_num = _patch_race_with_history(
        monkeypatch,
        season_year,
        {1: race("Red Bull Racing"), 2: race("Red Bull"), 3: race("Red Bull Racing"), 4: race("Red Bull")},
    )

    metrics = build_race_metrics(season_year, race_num)

    assert _constructor_points(metrics) == {"VER": 105, "PER": 105, "HAM": 90, "RUS": 90}


def test_build_race_metrics_does_not_move_points_when_drivers_swap_teams(monkeypatch, caplog):
    """2025's Tsunoda/Lawson swap: both names race on, so neither takes the other's history."""
    season_year = 2025
    before_swap = [("VER", "Red Bull Racing", 25), ("LAW", "Red Bull Racing", 1),
                   ("TSU", "Racing Bulls", 6), ("HAD", "Racing Bulls", 4)]
    after_swap = [("VER", "Red Bull Racing", 18), ("TSU", "Red Bull Racing", 2),
                  ("LAW", "Racing Bulls", 0), ("HAD", "Racing Bulls", 8)]
    race_num = _patch_race_with_history(
        monkeypatch, season_year, {1: before_swap, 2: before_swap, 3: after_swap, 4: after_swap}
    )

    caplog.set_level("WARNING", logger="fast_f1")
    metrics = build_race_metrics(season_year, race_num)

    # Both teams still race, so there is nothing to link and nothing to warn about
    assert "Constructor" not in caplog.text

    red_bull = 2 * (25 + 1) + (18 + 2)
    racing_bulls = 2 * (6 + 4) + (0 + 8)
    assert _constructor_points(metrics) == {
        "VER": red_bull, "TSU": red_bull, "LAW": racing_bulls, "HAD": racing_bulls,
    }


def test_build_race_metrics_warns_when_a_vanished_name_cannot_be_linked(monkeypatch, caplog):
    """A missing name whose drivers now race for two teams is not guessed at."""
    season_year = 2024
    before = [("HUL", "Kick Sauber", 4), ("BOT", "Kick Sauber", 2),
              ("HAM", "Mercedes", 18), ("RUS", "Mercedes", 12)]
    after = [("HUL", "Sauber", 4), ("BOT", "Mercedes", 2),
             ("HAM", "Mercedes", 18), ("RUS", "Sauber", 12)]
    race_num = _patch_race_with_history(monkeypatch, season_year, {1: before, 2: before, 3: before, 4: after})

    caplog.set_level("WARNING", logger="fast_f1")
    metrics = build_race_metrics(season_year, race_num)

    assert "Kick Sauber" in caplog.text
    # Neither current team takes Kick Sauber's history, so Sauber has none
    points = _constructor_points(metrics)
    assert pd.isna(points["HUL"]) and pd.isna(points["RUS"])
    assert points["HAM"] == points["BOT"] == 90


def _patch_race_before_results(monkeypatch, season_year, race_num, prior_by_race, session_teams):
    """Wire build_race_metrics to a race with no results yet.

    ``prior_by_race`` gives earlier races as (driver, constructor, points), and
    ``session_teams`` the driver list both practice sessions report.
    """
    drivers = list(session_teams)
    laps = pd.DataFrame(
        {
            "Driver": drivers,
            "LapTime": [80.0 + i for i in range(len(drivers))],
            "Stint": [1] * len(drivers),
            "Season": [season_year] * len(drivers),
            "Race": [race_num] * len(drivers),
            "SessionType": ["FP2"] * len(drivers),
        }
    )

    def fake_get_race_results(season, race):
        if race == race_num:
            return pd.DataFrame()
        rows = prior_by_race[race]
        return pd.DataFrame(
            {
                "Abbreviation": [driver for driver, _, _ in rows],
                "Constructor": [constructor for _, constructor, _ in rows],
                "Points": [points for _, _, points in rows],
                "Season": [season] * len(rows),
                "Race": [race] * len(rows),
            }
        )

    monkeypatch.setattr(
        "fast_f1.output.get_event_for_race",
        lambda season, race: DummyEvent({"FP2": DummySession(pd.DataFrame()), "FP3": DummySession(pd.DataFrame())}),
    )
    monkeypatch.setattr("fast_f1.output.select_practice_sessions_from_event", lambda event: ("FP2", "FP3"))
    monkeypatch.setattr(
        "fast_f1.output.get_session_laps",
        lambda season, race, session_type: laps.assign(SessionType=session_type),
    )
    monkeypatch.setattr("fast_f1.output.get_race_results", fake_get_race_results)
    monkeypatch.setattr(
        "fast_f1.output.get_session_drivers",
        lambda season, race, session_type: pd.DataFrame(
            {"Abbreviation": drivers, "TeamName": [session_teams[d] for d in drivers]}
        ),
    )


def test_build_race_metrics_before_results_uses_the_team_a_driver_moved_to(monkeypatch):
    """A team change inside the rolling window must not leave a driver on the old team."""
    before_swap = [("VER", "Red Bull Racing", 25), ("LAW", "Red Bull Racing", 1),
                   ("TSU", "Racing Bulls", 6), ("HAD", "Racing Bulls", 4)]
    after_swap = [("VER", "Red Bull Racing", 18), ("TSU", "Red Bull Racing", 2),
                  ("LAW", "Racing Bulls", 0), ("HAD", "Racing Bulls", 8)]
    _patch_race_before_results(
        monkeypatch, 2025, 4, {1: before_swap, 2: before_swap, 3: after_swap},
        {"VER": "Red Bull Racing", "TSU": "Red Bull Racing", "LAW": "Racing Bulls", "HAD": "Racing Bulls"},
    )

    metrics = build_race_metrics(2025, 4)

    assert metrics.set_index("Driver").loc["TSU", "Constructor"] == "Red Bull Racing"
    red_bull = 2 * (25 + 1) + (18 + 2)
    assert _constructor_points(metrics)["TSU"] == red_bull


def test_build_race_metrics_before_results_gives_a_new_driver_a_team(monkeypatch):
    """CAM at Haas in 2026 race 20: a driver with no recent results still gets a team."""
    prior = [("OCO", "Haas F1 Team", 4), ("BEA", "Haas F1 Team", 2),
             ("HAM", "Ferrari", 18), ("LEC", "Ferrari", 12)]
    _patch_race_before_results(
        monkeypatch, 2026, 20, {17: prior, 18: prior, 19: prior},
        {"CAM": "Haas F1 Team", "BEA": "Haas F1 Team", "HAM": "Ferrari", "LEC": "Ferrari"},
    )

    metrics = build_race_metrics(2026, 20)

    assert metrics.set_index("Driver").loc["CAM", "Constructor"] == "Haas F1 Team"
    assert _constructor_points(metrics)["CAM"] == 3 * (4 + 2)


def test_build_race_metrics_before_results_takes_the_latest_session_team(monkeypatch):
    """Where practice sessions disagree on a driver's team, the later session wins."""
    prior = [("OCO", "Haas F1 Team", 4), ("BEA", "Haas F1 Team", 2),
             ("HAM", "Ferrari", 18), ("LEC", "Ferrari", 12)]
    _patch_race_before_results(
        monkeypatch, 2026, 20, {17: prior, 18: prior, 19: prior},
        {"CAM": "Haas F1 Team", "BEA": "Haas F1 Team", "HAM": "Ferrari", "LEC": "Ferrari"},
    )
    cam_team_by_session = {"FP2": "Ferrari", "FP3": "Haas F1 Team"}
    monkeypatch.setattr(
        "fast_f1.output.get_session_drivers",
        lambda season, race, session_type: pd.DataFrame(
            {
                "Abbreviation": ["CAM", "BEA", "HAM", "LEC"],
                "TeamName": [cam_team_by_session[session_type], "Haas F1 Team", "Ferrari", "Ferrari"],
            }
        ),
    )

    metrics = build_race_metrics(2026, 20)

    assert metrics.set_index("Driver").loc["CAM", "Constructor"] == "Haas F1 Team"


def test_build_race_metrics_before_results_raises_when_no_session_names_a_drivers_team(monkeypatch, caplog):
    """A driver left without a team would silently drop out of the constructor signal."""
    prior = [("HAM", "Ferrari", 18), ("LEC", "Ferrari", 12)]
    _patch_race_before_results(
        monkeypatch, 2026, 20, {17: prior, 18: prior, 19: prior},
        {"HAM": "Ferrari", "LEC": "Ferrari"},
    )
    monkeypatch.setattr(
        "fast_f1.output.get_session_drivers",
        lambda season, race, session_type: pd.DataFrame(
            {"Abbreviation": ["HAM"], "TeamName": ["Ferrari"]}
        ),
    )

    caplog.set_level("ERROR", logger="fast_f1.output")
    with pytest.raises(RuntimeError, match="LEC"):
        build_race_metrics(2026, 20)

    assert "LEC" in caplog.text


def test_build_race_metrics_survives_a_damaged_odds_file(monkeypatch, tmp_path, caplog):
    """A damaged odds file must degrade the odds indicator, not abort the run."""
    season_year, race_num = 2025, 1
    _patch_minimal_race(monkeypatch, season_year, race_num, ["HAM", "VER"])

    # A file that has lost its Odds column reads without error and then raises
    # KeyError, which derives from neither OSError nor ValueError
    damaged = tmp_path / "f1_betting_odds.csv"
    damaged.write_text("Driver,Constructor,Season,Race\nHAM,CON,2025,1\n")

    caplog.set_level("WARNING", logger="fast_f1.output")
    metrics = build_race_metrics(season_year, race_num, odds_file=damaged)

    assert list(metrics["OddsRank"]) == [0.0, 0.0]
    assert "odds" in caplog.text.lower()


def test_build_race_metrics_does_not_read_the_real_odds_file(monkeypatch):
    """Tests must not silently pick up live odds data.

    2026 race 9 with ANT and RUS is a real, populated row set in
    data/f1_betting_odds.csv, so without isolation this would score them from
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
    ValueError, failing the run over rounds that never existed.
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


def _patch_failing_middle_round(monkeypatch) -> list[tuple[int, int]]:
    """Schedule rounds 1-3 where round 2's fetch fails, as a refused download does."""
    monkeypatch.setattr(
        "fastf1.get_event_schedule",
        lambda season_year, include_testing=False: pd.DataFrame({"RoundNumber": [1, 2, 3]}),
    )

    attempted: list[tuple[int, int]] = []

    def fake_build_race_metrics(season_year, race_num, *args, **kwargs):
        attempted.append((season_year, race_num))
        if race_num == 2:
            raise ConnectionError("401 Unauthorized from livetiming")
        return pd.DataFrame({"Season": [season_year], "Race": [race_num], "AggregateRank": [1.0]})

    monkeypatch.setattr("fast_f1.output.build_race_metrics", fake_build_race_metrics)
    return attempted


def test_historical_metrics_carries_on_past_a_race_that_fails(monkeypatch, tmp_path, caplog):
    """One race that cannot be fetched must not block every race after it.

    The failed race is logged and left out of the file, so the next run retries
    it; the races either side of it are computed and saved.
    """
    attempted = _patch_failing_middle_round(monkeypatch)
    output_path = tmp_path / "historical.xlsx"

    caplog.set_level("ERROR", logger="fast_f1.output")
    with pytest.raises(Exception):
        generate_historical_metrics([2025], output_path=output_path)

    assert attempted == [(2025, 1), (2025, 2), (2025, 3)]
    assert sorted(load_existing_metrics(output_path)["Race"]) == [1, 3]
    assert "season 2025 race 2" in caplog.text
    assert "401 Unauthorized" in caplog.text


def test_historical_metrics_reports_failed_races_once_all_are_tried(monkeypatch, tmp_path):
    """A run with a failed race must not end looking like a clean one."""
    _patch_failing_middle_round(monkeypatch)

    with pytest.raises(HistoricalRunIncomplete, match="season 2025 race 2") as excinfo:
        generate_historical_metrics([2025], output_path=tmp_path / "historical.xlsx")

    assert excinfo.value.failed_races == [(2025, 2)]
