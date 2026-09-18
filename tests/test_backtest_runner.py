import pandas as pd
import pandas.testing as pdt
import pytest

import backtest.runner as runner_module
from backtest.runner import append_results, run_backtest, simulate_sample
from backtest.sample import DEFAULT_BAND_EDGES, sample_starting_teams
from helpers import load_with_derivations
from linear.strategy_p2pm import StrategyMaxP2PM
from linear.strategy_zero_stop import StrategyZeroStop
from races.season import factory_season
from races.team import factory_team_row
from scripts.run_multiple_teams import get_starting_key, open_batch_results_file
from scripts.run_single_team import run_for_team

_SEASON = 2023
_STRATEGIES = [StrategyMaxP2PM, StrategyZeroStop]


def _rows(labels: list[str]) -> list[dict]:
    return [
        {
            "sim_key": f"({label})(2023)team",
            "label": label,
            "team": "team",
            "total_value": 99.7,
            "band": "(99.5, 100]",
            "total_points": 3000,
        }
        for label in labels
    ]


def test_append_writes_to_the_given_path_and_nowhere_else(tmp_path, monkeypatch):
    # From tmp_path, a relative write such as the old hardcoded outputs/ path lands here too
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "results.parquet"

    append_results(open_batch_results_file(str(path)), _rows(["A"]), str(path))

    assert list(tmp_path.rglob("*")) == [path]


def test_round_trip_preserves_rows(tmp_path):
    path = str(tmp_path / "results.parquet")
    rows = _rows(["A", "B"])

    returned = append_results(open_batch_results_file(path), rows, path)

    pdt.assert_frame_equal(returned, pd.DataFrame(rows))
    pdt.assert_frame_equal(open_batch_results_file(path), pd.DataFrame(rows))


def test_appends_accumulate_with_an_unrepeated_index(tmp_path):
    path = str(tmp_path / "results.parquet")

    store = append_results(open_batch_results_file(path), _rows(["A", "B"]), path)
    store = append_results(store, _rows(["C", "D"]), path)

    stored = open_batch_results_file(path)
    assert list(stored["label"]) == ["A", "B", "C", "D"]
    assert list(stored.index) == [0, 1, 2, 3]
    pdt.assert_frame_equal(stored, store)


def test_appending_no_rows_writes_nothing(tmp_path):
    path = tmp_path / "results.parquet"
    store = append_results(open_batch_results_file(str(path)), _rows(["A"]), str(path))
    written_at = path.stat().st_mtime_ns

    returned = append_results(store, [], str(path))

    assert path.stat().st_mtime_ns == written_at
    pdt.assert_frame_equal(returned, store)


def test_appending_no_rows_to_a_missing_file_creates_nothing(tmp_path):
    path = tmp_path / "results.parquet"

    append_results(open_batch_results_file(str(path)), [], str(path))

    assert not path.exists()


@pytest.fixture(scope="module")
def season():
    return factory_season(*load_with_derivations(season=_SEASON), _SEASON)


@pytest.fixture(scope="module")
def sample():
    # Two teams per band, six in all
    return sample_starting_teams(_SEASON, 2, seed=1)


@pytest.fixture(scope="module")
def simulated(sample, tmp_path_factory):
    """Simulate the sample once for the tests that only read the outcome."""
    path = str(tmp_path_factory.mktemp("simulated") / "results.parquet")
    store = simulate_sample(_SEASON, sample, _STRATEGIES, path, flush_every=100)
    return path, store


def _team(row, season):
    return factory_team_row(row.drop(["total_value", "band"]).to_dict(), season.races[1])


def test_one_row_per_label_and_team_carrying_the_sample(simulated, sample, season):
    path, store = simulated

    expected = {}
    for strategy in _STRATEGIES:
        for _, row in sample.iterrows():
            team = _team(row, season)
            key = get_starting_key(strategy.__name__, _SEASON, team)
            expected[key] = (strategy.__name__, str(team), row["total_value"], row["band"])

    assert len(store) == len(expected) == 12
    actual = {
        r.sim_key: (r.label, r.team, r.sampled_value, r.band)
        for r in store.itertuples()
    }
    assert actual == expected
    pdt.assert_frame_equal(open_batch_results_file(path), store)


def test_rows_keep_the_engines_own_values(simulated):
    _, store = simulated
    # total_value stays the engine's end-of-season valuation, not the sampled one
    assert (store["total_value"] != store["sampled_value"]).any()
    assert (store["race"] == store["race"].max()).all()


def test_matches_a_direct_run_for_team(simulated, sample, season):
    _, store = simulated
    row = sample.iloc[0]

    direct = run_for_team(StrategyZeroStop, _team(row, season), season, _SEASON, 1)[-1]

    key = get_starting_key("StrategyZeroStop", _SEASON, _team(row, season))
    stored = store.set_index("sim_key").loc[key]
    assert stored["total_points"] == direct["total_points"]
    assert stored["D1"] == direct["D1"]


def test_rerun_simulates_nothing(simulated, sample, monkeypatch):
    path, store = simulated

    def fail(*args, **kwargs):
        raise AssertionError("run_for_team called on a re-run")

    monkeypatch.setattr(runner_module, "run_for_team", fail)
    rerun = simulate_sample(_SEASON, sample, _STRATEGIES, path, flush_every=100)

    pdt.assert_frame_equal(rerun, store)


def test_returns_only_this_runs_rows_and_keeps_the_rest_stored(simulated, sample, tmp_path, monkeypatch):
    _, store = simulated
    foreign_label = store.iloc[[0]].assign(sim_key="(OtherStrategy)(2023)team", label="OtherStrategy")
    foreign_team = store.iloc[[0]].assign(sim_key="(StrategyMaxP2PM)(2023)other_team", team="other_team")
    path = str(tmp_path / "results.parquet")
    pd.concat([foreign_label, store, foreign_team], ignore_index=True).to_parquet(path)

    def fail(*args, **kwargs):
        raise AssertionError("run_for_team called on a re-run")

    monkeypatch.setattr(runner_module, "run_for_team", fail)
    returned = simulate_sample(_SEASON, sample, _STRATEGIES, path, flush_every=100)

    pdt.assert_frame_equal(returned, store)
    assert len(open_batch_results_file(path)) == len(store) + 2


def test_work_flushed_before_a_crash_survives(sample, tmp_path, monkeypatch):
    path = str(tmp_path / "results.parquet")
    calls = []

    def crash_on_fifth(*args, **kwargs):
        calls.append(1)
        if len(calls) == 5:
            raise RuntimeError("simulated crash")
        return run_for_team(*args, **kwargs)

    monkeypatch.setattr(runner_module, "run_for_team", crash_on_fifth)
    with pytest.raises(RuntimeError, match="simulated crash"):
        simulate_sample(_SEASON, sample.head(3), _STRATEGIES, path, flush_every=2)

    assert len(open_batch_results_file(path)) == 4


_BACKTEST_SEASONS = [2023, 2024]


@pytest.fixture(scope="module")
def backtest_run(tmp_path_factory):
    """One team per band over two seasons, naming only the challenger."""
    directory = tmp_path_factory.mktemp("backtest")
    store_path = str(directory / "results.parquet")
    summary_path = str(directory / "summary.csv")
    summary, verdicts = run_backtest(
        _BACKTEST_SEASONS, 1, 1, [StrategyZeroStop], DEFAULT_BAND_EDGES, store_path, summary_path,
    )
    return directory, store_path, summary_path, summary, verdicts


def test_backtest_prepends_the_baseline_and_stores_every_simulation(backtest_run):
    _, store_path, _, _, _ = backtest_run
    store = open_batch_results_file(store_path)

    # 2 labels x 2 seasons x 3 teams
    assert len(store) == 12
    assert store.groupby(["label", "season"]).size().to_dict() == {
        (label, season): 3 for label in ["StrategyMaxP2PM", "StrategyZeroStop"] for season in _BACKTEST_SEASONS
    }
    # The baseline is simulated first within each season
    assert list(store.drop_duplicates("season")["label"]) == ["StrategyMaxP2PM", "StrategyMaxP2PM"]


def test_backtest_writes_the_ranked_summary(backtest_run):
    _, _, summary_path, summary, _ = backtest_run

    # 2 labels x 2 seasons x (3 bands + pooled)
    assert len(summary) == 16
    assert "rank" in summary.columns
    written = pd.read_csv(summary_path)
    assert list(written.columns) == list(summary.columns)
    assert list(zip(written["label"], written["season"], written["band"])) == list(
        zip(summary["label"], summary["season"], summary["band"])
    )


def test_backtest_writes_the_verdict_beside_the_summary(backtest_run):
    directory, _, _, _, verdicts = backtest_run

    assert list(verdicts["label"]) == ["StrategyZeroStop"]
    assert verdicts.iloc[0]["seasons"] == 2
    written = pd.read_csv(directory / "summary_verdict.csv")
    pdt.assert_frame_equal(written, verdicts)
    assert sorted(p.name for p in directory.iterdir()) == ["results.parquet", "summary.csv", "summary_verdict.csv"]


def test_backtest_rerun_with_the_baseline_named_simulates_nothing(backtest_run, tmp_path, monkeypatch):
    _, store_path, _, summary, verdicts = backtest_run

    def fail(*args, **kwargs):
        raise AssertionError("run_for_team called on a re-run")

    monkeypatch.setattr(runner_module, "run_for_team", fail)
    # Naming the baseline gives the same results as leaving it out
    rerun_summary, rerun_verdicts = run_backtest(
        _BACKTEST_SEASONS, 1, 1, [StrategyZeroStop, StrategyMaxP2PM], DEFAULT_BAND_EDGES,
        store_path, str(tmp_path / "summary.csv"),
    )

    pdt.assert_frame_equal(rerun_summary, summary)
    pdt.assert_frame_equal(rerun_verdicts, verdicts)


@pytest.mark.parametrize("given", [
    [StrategyZeroStop],
    [StrategyZeroStop, StrategyMaxP2PM],
    [StrategyMaxP2PM, StrategyZeroStop],
])
def test_baseline_runs_first_and_once(given):
    # simulate_sample does not track keys within a run, so a baseline listed
    # twice would be simulated twice
    ordered = runner_module._with_baseline_first(given)
    assert [s.__name__ for s in ordered] == ["StrategyMaxP2PM", "StrategyZeroStop"]


def test_backtest_duplicate_labels_raise_before_any_work(tmp_path, monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("work started")

    monkeypatch.setattr(runner_module, "sample_starting_teams", fail)
    with pytest.raises(ValueError):
        run_backtest(
            [2023], 1, 1, [StrategyZeroStop, StrategyZeroStop], DEFAULT_BAND_EDGES,
            str(tmp_path / "results.parquet"), str(tmp_path / "summary.csv"),
        )
