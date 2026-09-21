import pandas as pd
import pandas.testing as pdt
import pytest

import backtest.per_race as per_race_module
from backtest.per_race import (
    add_full_stacks,
    concentration,
    concentration_summary,
    full_stack_count,
    race_driver_pairs,
    race_summary,
    row_assets,
    run_per_race,
    simulate_per_race,
    team_summary,
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
_BASELINE = "StrategyMaxP2PM"


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    """One team per band over two seasons, so season keying has something to get wrong."""
    path = str(tmp_path_factory.mktemp("run") / "results.parquet")
    return path, run_per_race(_RUN_SEASONS, 1, 1, _STRATEGIES, DEFAULT_BAND_EDGES, path)


@pytest.fixture(scope="module")
def stacked(run):
    _, rows = run
    return add_full_stacks(rows)


def test_a_run_puts_every_season_in_one_store(run):
    path, rows = run

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


@pytest.mark.parametrize(
    "summarise",
    [
        concentration_summary,
        lambda rows: team_summary(rows, _BASELINE),
        lambda rows: race_summary(rows, _BASELINE),
    ],
    ids=["concentration_summary", "team_summary", "race_summary"],
)
def test_a_summary_without_full_stacks_says_which_call_is_missing(run, summarise):
    _, rows = run

    with pytest.raises(ValueError, match="add_full_stacks"):
        summarise(rows)


def test_concentration_is_summarised_per_label_and_season(stacked):
    summary = concentration_summary(stacked)

    assert list(zip(summary["label"], summary["season"])) == [
        (label, season) for season in _RUN_SEASONS for label in sorted({s.__name__ for s in _STRATEGIES})
    ]
    # 3 teams x every race of the season
    races = stacked.groupby("season")["race"].nunique().to_dict()
    assert dict(zip(zip(summary["label"], summary["season"]), summary["team_races"])) == {
        (strategy.__name__, season): 3 * races[season] for season in _RUN_SEASONS for strategy in _STRATEGIES
    }
    assert summary["share_concentrated"].between(0, 1).all()
    assert summary["share_full_stacked"].between(0, 1).all()


@pytest.fixture
def shared_team():
    """The same starting team in two seasons, which a real sample never produces.

    Driver identifiers carry their constructor, so no two seasons draw the same
    team string and no real fixture can catch a pairing that ignores the season.
    """
    rows = []
    for season, scores in [(2023, [10, 20]), (2024, [100, 200])]:
        for label, bonus in [(_BASELINE, 0), ("StrategyMaxPoints", 5)]:
            total = 0
            for race, points in enumerate(scores, start=1):
                total += points + bonus
                rows.append({
                    "label": label, "season": season, "race": race, "team": "(A,B)(C)",
                    "sim_key": f"({label})({season})(A,B)(C)", "band": "(99.5, 100]",
                    "points": points + bonus, "total_points": total,
                    "concentration": 1, "full_stacks": 0,
                })
    return pd.DataFrame(rows)


def test_teams_are_paired_within_their_own_season(shared_team):
    summary = team_summary(shared_team, _BASELINE)

    # Four rows, not eight: neither season's team pairs with the other's baseline
    assert len(summary) == 4
    assert summary[summary["label"] != _BASELINE].set_index("season")["delta"].to_dict() == {2023: 10, 2024: 10}


def test_races_are_paired_within_their_own_season(shared_team):
    summary = race_summary(shared_team, _BASELINE)

    assert (summary["teams"] == 1).all()
    assert summary.loc[summary["label"] != _BASELINE, "mean_cumulative_delta"].tolist() == [5.0, 10.0, 5.0, 10.0]


def test_each_team_is_summarised_once_with_its_final_delta(stacked):
    summary = team_summary(stacked, _BASELINE)

    assert len(summary) == len(stacked.groupby(["label", "season", "team"]))
    assert (summary.loc[summary["label"] == _BASELINE, "delta"] == 0).all()

    # The delta is against the baseline's final race for the same season and team
    finals = stacked.loc[stacked.groupby("sim_key")["race"].idxmax()]
    row = summary[summary["label"] != _BASELINE].iloc[0]
    paired = finals[(finals["season"] == row["season"]) & (finals["team"] == row["team"])]
    assert row["delta"] == (
        paired.loc[paired["label"] == row["label"], "total_points"].item()
        - paired.loc[paired["label"] == _BASELINE, "total_points"].item()
    )


def test_every_race_of_every_season_gets_a_paired_row(stacked):
    summary = race_summary(stacked, _BASELINE)

    expected = stacked.groupby(["label", "season"])["race"].nunique().sum()
    assert len(summary) == expected
    assert (summary.loc[summary["label"] == _BASELINE, "mean_cumulative_delta"] == 0).all()
    # The cumulative delta at the final race is the season delta
    teams = team_summary(stacked, _BASELINE)
    final = summary.loc[summary.groupby(["label", "season"])["race"].idxmax()]
    expected_final = teams.groupby(["label", "season"])["delta"].mean().reset_index()
    assert final["mean_cumulative_delta"].round(6).tolist() == expected_final["delta"].round(6).tolist()
