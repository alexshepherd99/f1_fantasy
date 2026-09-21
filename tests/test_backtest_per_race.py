import pandas as pd
import pandas.testing as pdt
import pytest

import backtest.per_race as per_race_module
from backtest.per_race import (
    add_full_stacks,
    concentration,
    full_stack_count,
    race_driver_pairs,
    row_assets,
    run_per_race,
    simulate_per_race,
)
from backtest.sample import DEFAULT_BAND_EDGES, sample_starting_teams
from helpers import load_with_derivations
from linear.strategy_max_points import StrategyMaxPoints
from linear.strategy_p2pm import StrategyMaxP2PM
from races.season import factory_season
from races.team import factory_team_row
from scripts.run_multiple_teams import get_starting_key, open_batch_results_file
from scripts.run_single_team import run_for_team

_SEASON = 2023
_STRATEGIES = [StrategyMaxP2PM, StrategyMaxPoints]

# One constructor's two drivers, a second constructor's two, and a lone third
_PAIRS = {
    "VER@RED": "RED",
    "PER@RED": "RED",
    "HAM@MER": "MER",
    "RUS@MER": "MER",
    "NOR@MCL": "MCL",
}


def test_a_team_sharing_no_constructor_is_unconcentrated():
    assert concentration(["VER@RED", "HAM@MER", "NOR@MCL"], ["FER"], _PAIRS) == 0


def test_two_drivers_from_one_constructor_count_once():
    assert concentration(["VER@RED", "PER@RED", "NOR@MCL"], ["FER"], _PAIRS) == 1


def test_a_driver_held_with_their_own_constructor_counts_once():
    assert concentration(["VER@RED", "HAM@MER"], ["RED"], _PAIRS) == 1


def test_a_constructor_pairs_with_each_of_its_held_drivers():
    # One driver-driver pair, plus a driver-constructor pair for each of the two
    assert concentration(["VER@RED", "PER@RED"], ["RED"], _PAIRS) == 3


def test_a_constructor_with_none_of_its_drivers_is_unconcentrated():
    assert concentration(["HAM@MER"], ["RED"], _PAIRS) == 0


def test_drivers_from_one_constructor_count_every_pair_between_them():
    # Three is impossible in F1, but it fixes the metric as pair-counting rather
    # than counting the constructors that are doubled up on
    pairs = _PAIRS | {"LAW@RED": "RED"}
    assert concentration(["VER@RED", "PER@RED", "LAW@RED"], [], pairs) == 3


def test_a_driver_missing_from_the_pairings_raises():
    with pytest.raises(ValueError, match="SAI@FER"):
        concentration(["VER@RED", "SAI@FER"], [], _PAIRS)


@pytest.fixture(scope="module")
def season():
    return factory_season(*load_with_derivations(season=_SEASON), _SEASON)


def test_race_driver_pairs_covers_every_driver_in_the_race(season):
    race = season.races[1]

    pairs = race_driver_pairs(race)

    assert set(pairs) == set(race.drivers)
    assert pairs["VER@RED"] == "RED"


def test_a_constructor_held_with_both_its_drivers_is_one_full_stack():
    assert full_stack_count(["VER@RED", "PER@RED"], ["RED"], _PAIRS) == 1


def test_a_constructor_held_with_only_one_of_its_drivers_is_no_stack():
    assert full_stack_count(["VER@RED"], ["RED"], _PAIRS) == 0


def test_each_fully_held_constructor_counts_separately():
    drivers = ["VER@RED", "PER@RED", "HAM@MER", "RUS@MER"]
    assert full_stack_count(drivers, ["RED", "MER"], _PAIRS) == 2


def test_a_constructor_whose_drivers_are_not_held_is_no_stack():
    assert full_stack_count(["VER@RED", "PER@RED"], ["MCL"], _PAIRS) == 0


def test_drivers_held_without_their_constructor_are_no_stack():
    assert full_stack_count(["VER@RED", "PER@RED"], [], _PAIRS) == 0


def test_row_assets_reads_the_numbered_columns_and_not_their_companions():
    row = {
        "season": 2023, "race": 4,
        "D1": "VER@RED", "D1_val": 27.5, "D1_pts": 41,
        "D2": "NOR@MCL", "D2_val": 12.0, "D2_pts": 18,
        "C1": "RED", "C1_val": 25.9, "C1_pts": 60,
        "C2": "MCL", "C2_val": 14.4, "C2_pts": 22,
    }

    assert row_assets(row) == (["VER@RED", "NOR@MCL"], ["RED", "MCL"])


@pytest.fixture(scope="module")
def sample():
    # One team per band, three in all
    return sample_starting_teams(_SEASON, 1, seed=1)


@pytest.fixture(scope="module")
def simulated(sample, tmp_path_factory):
    """Simulate the sample once for the tests that only read the outcome."""
    path = str(tmp_path_factory.mktemp("per_race") / "results.parquet")
    return path, simulate_per_race(_SEASON, sample, _STRATEGIES, path)


def _team(row, season):
    return factory_team_row(row.drop(["total_value", "band"]).to_dict(), season.races[1])


def test_every_race_of_the_season_is_kept(simulated, season):
    _, store = simulated

    # 2 labels x 3 teams, each simulated through every race
    assert store.groupby("sim_key").size().to_dict() == {key: len(season.races) for key in store["sim_key"].unique()}
    assert len(store) == 6 * len(season.races)


def test_every_row_carries_its_key_label_team_and_sample(simulated, sample, season):
    _, store = simulated

    expected = set()
    for strategy in _STRATEGIES:
        for _, row in sample.iterrows():
            team = _team(row, season)
            key = get_starting_key(strategy.__name__, _SEASON, team)
            expected.add((key, strategy.__name__, str(team), row["total_value"], row["band"]))

    actual = {(r.sim_key, r.label, r.team, r.sampled_value, r.band) for r in store.itertuples()}
    assert actual == expected


def test_every_race_matches_a_direct_run_for_team(simulated, sample, season):
    _, store = simulated
    row = sample.iloc[0]

    direct = pd.DataFrame(run_for_team(StrategyMaxPoints, _team(row, season), season, _SEASON, 1))

    key = get_starting_key("StrategyMaxPoints", _SEASON, _team(row, season))
    stored = store[store["sim_key"] == key].reset_index(drop=True)
    pdt.assert_frame_equal(stored[direct.columns], direct)


def test_concentration_is_recorded_against_the_right_races_pairings(simulated):
    _, store = simulated

    # Derived from the DRIVER@CONSTRUCTOR identifier rather than the race, so a
    # row scored against the wrong race's pairings disagrees
    expected = [
        concentration(drivers, constructors, {d: d.split("@")[1] for d in drivers})
        for drivers, constructors in (row_assets(row) for row in store.to_dict("records"))
    ]

    assert list(store["concentration"]) == expected
    assert store["concentration"].nunique() > 1


def test_rerun_simulates_nothing(simulated, sample, monkeypatch):
    path, store = simulated

    def fail(*args, **kwargs):
        raise AssertionError("run_for_team called on a re-run")

    monkeypatch.setattr(per_race_module, "run_for_team", fail)
    rerun = simulate_per_race(_SEASON, sample, _STRATEGIES, path)

    pdt.assert_frame_equal(rerun, store)


def test_flushing_counts_simulations_not_rows(sample, season, tmp_path, monkeypatch):
    path = str(tmp_path / "results.parquet")
    calls = []

    def crash_on_third(*args, **kwargs):
        calls.append(1)
        if len(calls) == 3:
            raise RuntimeError("simulated crash")
        return run_for_team(*args, **kwargs)

    monkeypatch.setattr(per_race_module, "run_for_team", crash_on_third)
    with pytest.raises(RuntimeError, match="simulated crash"):
        simulate_per_race(_SEASON, sample, _STRATEGIES, path, flush_every=2)

    # Two whole simulations were flushed, not the first two rows
    assert len(open_batch_results_file(path)) == 2 * len(season.races)


_RUN_SEASONS = [2023, 2024]


def test_a_run_puts_every_season_in_one_store(tmp_path):
    path = str(tmp_path / "results.parquet")

    rows = run_per_race(_RUN_SEASONS, 1, 1, _STRATEGIES, DEFAULT_BAND_EDGES, path)

    pdt.assert_frame_equal(rows, open_batch_results_file(path))
    # 2 labels x 3 teams in each season, each kept for every race
    assert rows.groupby("season")["sim_key"].nunique().to_dict() == {2023: 6, 2024: 6}
    assert (rows.groupby("season")["race"].nunique() == rows.groupby("season")["race"].max()).all()


def test_full_stacks_are_added_per_row_against_that_rows_race(simulated):
    _, store = simulated

    with_stacks = add_full_stacks(store)

    # Each full stack is a shared driver pair plus two held driver-constructor pairs
    stacked = with_stacks[with_stacks["full_stacks"] > 0]
    assert not stacked.empty
    assert (stacked["concentration"] >= 3 * stacked["full_stacks"]).all()
    assert (with_stacks.loc[with_stacks["concentration"] == 0, "full_stacks"] == 0).all()
    pdt.assert_frame_equal(with_stacks.drop(columns="full_stacks"), store)
