import itertools
import logging
import math
from pathlib import Path

import pandas as pd
import pytest

from common import AssetType
from fast_f1.output import DEFAULT_HISTORICAL_OUTPUT, load_existing_metrics
from helpers import load_with_derivations
from races.asset import Constructor, Driver
from races.season import Race, Season, factory_season

from fast_f1.indicator_analysis import bootstrap_interval

from backtest.race_one import (
    choose_default,
    compare_with_even_split,
    draw_random_teams,
    eligible_races,
    main,
    placeholder_team,
    race_cap,
    random_teams_points,
    run_race,
    score_team,
)


def _race(
    race_num: int,
    drivers: dict[str, tuple[float, int]],
    constructors: dict[str, tuple[float, int]],
) -> Race:
    """A race from `identifier -> (price, points)`, each driver's constructor taken from their identifier."""
    return Race(
        race_num,
        {d: Driver(d, d.split("@")[1], price, points, {}) for d, (price, points) in drivers.items()},
        {c: Constructor(c, price, points, {}) for c, (price, points) in constructors.items()},
    )


# Seven drivers and three constructors, the fewest that leave a choice of team
_DRIVERS = {
    "A1@CA": (20.0, 30),
    "A2@CA": (15.0, 10),
    "B1@CB": (10.0, 25),
    "B2@CB": (8.0, 4),
    "C1@CC": (6.0, 12),
    "C2@CC": (5.0, -3),
    "C3@CC": (5.0, 7),
}
_CONSTRUCTORS = {"CA": (25.0, 40), "CB": (15.0, 20), "CC": (10.0, 5)}


def test_race_cap_is_the_starting_budget_at_the_first_race():
    race = _race(1, _DRIVERS, _CONSTRUCTORS)

    assert race_cap(race, race) == pytest.approx(100.0)


def test_race_cap_scales_with_the_whole_grid_price():
    """A grid 10% dearer than at race 1 buys the same share of it with a cap of 110m."""
    first = _race(1, _DRIVERS, _CONSTRUCTORS)
    later = _race(
        5,
        {d: (price * 1.1, points) for d, (price, points) in _DRIVERS.items()},
        {c: (price * 1.1, points) for c, (price, points) in _CONSTRUCTORS.items()},
    )

    assert race_cap(later, first) == pytest.approx(110.0)


def test_race_cap_counts_constructors_as_well_as_drivers():
    """Only the constructors moved, by +11m on a grid of 69m + 50m."""
    first = _race(1, _DRIVERS, _CONSTRUCTORS)
    later = _race(5, _DRIVERS, {"CA": (36.0, 0), "CB": (15.0, 0), "CC": (10.0, 0)})

    assert race_cap(later, first) == pytest.approx(100.0 * 130.0 / 119.0)


def test_placeholder_team_holds_the_cheapest_assets():
    """C2 and C3 tie on price, so both are in; the constructor tie order is by name."""
    team = placeholder_team(_race(1, _DRIVERS, _CONSTRUCTORS | {"CD": (10.0, 0)}))

    assert sorted(team.assets[AssetType.DRIVER]) == ["B1@CB", "B2@CB", "C1@CC", "C2@CC", "C3@CC"]
    assert sorted(team.assets[AssetType.CONSTRUCTOR]) == ["CC", "CD"]
    team.check_asset_counts()


def test_placeholder_team_breaks_a_price_tie_by_name():
    """Six drivers and three constructors at one price, listed in reverse: the first by name are held."""
    drivers = {f"D{i}@CA": (5.0, 0) for i in range(6, 0, -1)}
    constructors = {"CC": (5.0, 0), "CB": (5.0, 0), "CA": (5.0, 0)}

    team = placeholder_team(_race(1, drivers, constructors))

    assert sorted(team.assets[AssetType.DRIVER]) == [f"D{i}@CA" for i in range(1, 6)]
    assert sorted(team.assets[AssetType.CONSTRUCTOR]) == ["CA", "CB"]


_TEAM_DRIVERS = ("A1@CA", "B1@CB", "B2@CB", "C1@CC", "C2@CC")
_TEAM_CONSTRUCTORS = ("CB", "CC")
# 30 + 25 + 4 + 12 - 3 for the drivers, 20 + 5 for the constructors
_TEAM_POINTS = 93


def test_score_team_counts_the_drs_driver_twice():
    race = _race(1, _DRIVERS, _CONSTRUCTORS)

    assert score_team(_TEAM_DRIVERS, _TEAM_CONSTRUCTORS, "B1@CB", race) == _TEAM_POINTS + 25


def test_score_team_with_no_drs_driver_doubles_the_dearest():
    """The game's default, as `Team` applies it: A1 is the dearest driver."""
    race = _race(1, _DRIVERS, _CONSTRUCTORS)

    assert score_team(_TEAM_DRIVERS, _TEAM_CONSTRUCTORS, "", race) == _TEAM_POINTS + 30


# The cheapest team: C2, C3, C1, B2 and B1 for 34m, then CC and CB for 25m. Any other team
# costs at least 5m more
_CHEAPEST_DRIVERS = ("B1@CB", "B2@CB", "C1@CC", "C2@CC", "C3@CC")
_CHEAPEST_CONSTRUCTORS = ("CB", "CC")
_CHEAPEST_COST = 59.0


def test_draw_random_teams_draws_valid_teams_under_the_cap():
    race = _race(1, _DRIVERS, _CONSTRUCTORS)

    teams = draw_random_teams(race, cap=80.0, count=200, seed=3)

    assert len(teams) == 200
    for drivers, constructors in teams:
        assert len(set(drivers)) == 5 and set(drivers) <= set(_DRIVERS)
        assert len(set(constructors)) == 2 and set(constructors) <= set(_CONSTRUCTORS)
        cost = sum(_DRIVERS[d][0] for d in drivers) + sum(_CONSTRUCTORS[c][0] for c in constructors)
        assert cost <= 80.0


def test_draw_random_teams_keeps_only_teams_within_the_cap():
    """At exactly the cheapest team's cost, it is the only team that fits, so every draw is it."""
    race = _race(1, _DRIVERS, _CONSTRUCTORS)

    teams = draw_random_teams(race, cap=_CHEAPEST_COST, count=20, seed=3)

    assert teams == [(_CHEAPEST_DRIVERS, _CHEAPEST_CONSTRUCTORS)] * 20


def test_draw_random_teams_can_draw_every_valid_team():
    """With a cap every team fits, all 21 x 3 driver and constructor choices turn up."""
    race = _race(1, _DRIVERS, _CONSTRUCTORS)

    teams = draw_random_teams(race, cap=1000.0, count=2000, seed=3)

    assert len(set(teams)) == 63


def test_draw_random_teams_repeats_for_a_seed_and_differs_by_race():
    """The draw is seeded by seed and race number together, so adding races leaves each race's draw alone."""
    race = _race(1, _DRIVERS, _CONSTRUCTORS)
    other_race = _race(2, _DRIVERS, _CONSTRUCTORS)

    first = draw_random_teams(race, cap=1000.0, count=50, seed=3)

    assert draw_random_teams(race, cap=1000.0, count=50, seed=3) == first
    assert draw_random_teams(race, cap=1000.0, count=50, seed=4) != first
    assert draw_random_teams(other_race, cap=1000.0, count=50, seed=3) != first


def test_draw_random_teams_raises_when_no_team_fits():
    race = _race(1, _DRIVERS, _CONSTRUCTORS)

    with pytest.raises(ValueError, match="No team"):
        draw_random_teams(race, cap=_CHEAPEST_COST - 0.1, count=5, seed=3)


def test_draw_random_teams_raises_rather_than_drawing_forever():
    """A cap so tight that almost no draw fits gives up after `MAX_DRAWS_PER_TEAM` draws a team."""
    race = _race(1, _DRIVERS, _CONSTRUCTORS)

    # One team in 63 fits, so 20 of them need about 1,260 draws, far more than 20 x 2
    with pytest.raises(RuntimeError, match="draws"):
        draw_random_teams(race, cap=_CHEAPEST_COST, count=20, seed=3, max_draws_per_team=2)


def test_random_teams_points_is_the_mean_with_drs_on_the_dearest_driver():
    """Only the cheapest team fits: 101 for its drivers, 2 for its constructors, and C's 30 again for DRS.

    C is the dearest driver but neither first nor last by name, so DRS is not landing on either by accident.
    """
    drivers = {
        "A@CA": (2.0, 10),
        "B@CA": (3.0, 20),
        "C@CB": (9.0, 30),
        "D@CB": (4.0, 40),
        "E@CB": (5.0, 1),
        "F@CB": (50.0, 0),
    }
    race = _race(1, drivers, {"CA": (1.0, 1), "CB": (1.0, 1), "CC": (50.0, 0)})

    assert random_teams_points(race, cap=25.0, count=10, seed=3) == pytest.approx(133.0)


def test_random_teams_points_averages_over_the_draw():
    race = _race(1, _DRIVERS, _CONSTRUCTORS)
    teams = draw_random_teams(race, cap=80.0, count=30, seed=3)
    expected = sum(score_team(d, c, "", race) for d, c in teams) / 30

    assert random_teams_points(race, cap=80.0, count=30, seed=3) == pytest.approx(expected)


_SEASON = 2026
# Each fixture driver's OddsRank and FP3 rank, in `_DRIVERS`' order: odds favour A1 down to C3,
# FP3 the reverse. Unevenly spaced, so no two teams tie on value
_ODDS_RANKS = [1.0, 0.9, 0.55, 0.4, 0.33, 0.12, 0.0]
_FP3_RANKS = [0.0, 0.2, 0.31, 0.47, 0.8, 0.93, 1.0]


def _write_metrics(path: Path, races: dict[int, str], season: int = _SEASON) -> Path:
    """Metrics rows for each race's drivers, in the shape of ``data/fastf1_practice_rolling_metrics.csv``.

    Each race is one of: ``normal``; ``sprint`` (FP1 and SQ, no FP2 or FP3); ``no_fp3`` (FP2 but
    no FP3); ``odds_zero`` (a normal weekend whose odds all scored zero when the file was built).
    """
    records = []
    for race_num, kind in races.items():
        sprint = kind == "sprint"
        for i, driver in enumerate(d.split("@")[0] for d in _DRIVERS):
            records.append({
                "Driver": driver,
                "Season": season,
                "Race": race_num,
                "RollingPointsRank": 0.5,
                "ConstructorRollingPointsRank": 0.5,
                "FP2_MinLapTime_rank": math.nan if sprint else 0.5,
                "FP3_MinLapTime_rank": math.nan if sprint or kind == "no_fp3" else _FP3_RANKS[i],
                "OddsImpliedProbability": 0.1,
                "OddsRank": 0.0 if kind == "odds_zero" else _ODDS_RANKS[i],
                "FP1_MinLapTime_rank": 0.5 if sprint else math.nan,
                "SQ_MinLapTime_rank": 0.5 if sprint else math.nan,
            })
    pd.DataFrame(records).to_csv(path, index=False)
    return path


def _write_odds(path: Path, races: list[int]) -> Path:
    """An odds file pricing every fixture driver at each of `races`."""
    records = [
        {"Driver": d.split("@")[0], "Constructor": d.split("@")[1], "Season": _SEASON, "Race": r, "Odds": f"{i + 2}/1"}
        for r in races
        for i, d in enumerate(_DRIVERS)
    ]
    pd.DataFrame(records).to_csv(path, index=False)
    return path


def _season(unscored: tuple[int, ...] = ()) -> Season:
    """Races 1 and 2 of the fixture, with the races in `unscored` not yet run (every point 0)."""
    races = {}
    for race_num in (1, 2):
        if race_num in unscored:
            drivers = {d: (price, 0) for d, (price, _) in _DRIVERS.items()}
            constructors = {c: (price, 0) for c, (price, _) in _CONSTRUCTORS.items()}
        else:
            drivers, constructors = _DRIVERS, _CONSTRUCTORS
        races[race_num] = _race(race_num, drivers, constructors)
    return Season(_SEASON, races)


def test_eligible_races_takes_scored_normal_weekends_with_odds_and_fp3(tmp_path):
    metrics = _write_metrics(tmp_path / "metrics.csv", {1: "normal", 2: "normal"})
    odds = _write_odds(tmp_path / "odds.csv", [1, 2])

    assert eligible_races(_season(), metrics, odds) == [1, 2]


@pytest.mark.parametrize("race_2_metrics, odds_races, unscored, why", [
    ({2: "sprint"}, [1, 2], (), "a sprint weekend has no FP3"),
    ({2: "no_fp3"}, [1, 2], (), "a normal weekend whose FP3 is missing"),
    ({}, [1, 2], (), "no metrics rows"),
    ({2: "normal"}, [1], (), "no odds in the odds file"),
    ({2: "normal"}, [1, 2], (2,), "not yet run, so nothing to score"),
])
def test_eligible_races_leaves_out_a_race(tmp_path, race_2_metrics, odds_races, unscored, why):
    metrics = _write_metrics(tmp_path / "metrics.csv", {1: "normal"} | race_2_metrics)
    odds = _write_odds(tmp_path / "odds.csv", odds_races)

    assert eligible_races(_season(unscored), metrics, odds) == [1], why


def test_eligible_races_ignores_another_seasons_metrics(tmp_path):
    metrics = _write_metrics(tmp_path / "metrics.csv", {1: "normal", 2: "normal"}, season=_SEASON - 1)
    odds = _write_odds(tmp_path / "odds.csv", [1, 2])

    assert eligible_races(_season(), metrics, odds) == []


def test_eligible_races_warns_when_the_metrics_predate_the_odds(tmp_path, caplog):
    """The odds file has race 2's odds, but the metrics scored them all zero, so were built before they were added.

    The strategy reads odds from the metrics, so the race is left out, with a warning to rebuild them.
    """
    metrics = _write_metrics(tmp_path / "metrics.csv", {1: "normal", 2: "odds_zero"})
    odds = _write_odds(tmp_path / "odds.csv", [1, 2])

    with caplog.at_level(logging.WARNING):
        assert eligible_races(_season(), metrics, odds) == [1]

    assert "2026 race 2" in caplog.text


_LABELS = [
    "OddsFP3_w0",
    "OddsFP3_w0p25",
    "OddsFP3_w0p5",
    "OddsFP3_w0p75",
    "OddsFP3_w1",
    "MaxBudget",
    "BettingOdds",
    "RandomTeams",
]
_STRATEGY_LABELS = _LABELS[:-1]


@pytest.fixture
def race_one_rows(tmp_path) -> tuple[Race, float, list[dict]]:
    """`run_race` on the fixture race, whose whole grid is 5% cheaper than at race 1, so the cap is 95m.

    At 95m, max budget's team and the odds-alone team are each 3 moves from the placeholder, so a
    pick held to fewer moves would show.
    """
    race = _race(3, _DRIVERS, _CONSTRUCTORS)
    first_race = _race(
        1,
        {d: (price * 100 / 95, points) for d, (price, points) in _DRIVERS.items()},
        {c: (price * 100 / 95, points) for c, (price, points) in _CONSTRUCTORS.items()},
    )
    metrics = _write_metrics(tmp_path / "metrics.csv", {3: "normal"})
    odds = _write_odds(tmp_path / "odds.csv", [3])
    return race, 95.0, run_race(_SEASON, race, first_race, metrics, odds)


def _cost(drivers, constructors) -> float:
    return sum(_DRIVERS[d][0] for d in drivers) + sum(_CONSTRUCTORS[c][0] for c in constructors)


def _teams_within(cap: float) -> list[tuple[tuple[str, ...], tuple[str, ...]]]:
    """Every team of the fixture within `cap`, found by listing all 63."""
    return [
        (drivers, constructors)
        for drivers in itertools.combinations(sorted(_DRIVERS), 5)
        for constructors in itertools.combinations(sorted(_CONSTRUCTORS), 2)
        if _cost(drivers, constructors) <= cap
    ]


def test_run_race_gives_a_row_per_mix_and_control(race_one_rows):
    _, cap, rows = race_one_rows

    assert [row["label"] for row in rows] == _LABELS
    for row in rows:
        assert row["season"] == _SEASON
        assert row["race"] == 3
        assert row["cap"] == pytest.approx(cap)


def test_run_race_picks_valid_teams_within_the_cap_and_scores_them(race_one_rows):
    race, cap, rows = race_one_rows

    for row in rows[:-1]:
        drivers, constructors = row["drivers"].split(","), row["constructors"].split(",")
        assert len(set(drivers)) == 5 and len(set(constructors)) == 2, row["label"]
        assert row["cost"] == pytest.approx(_cost(drivers, constructors)), row["label"]
        assert row["cost"] <= cap + 1e-6, row["label"]
        assert row["points"] == score_team(drivers, constructors, row["drs_driver"], race), row["label"]


def test_run_race_gives_the_strategies_the_cap(race_one_rows):
    """Max budget spends as much of the 95m as any team can."""
    _, cap, rows = race_one_rows
    best_spend = max(_cost(d, c) for d, c in _teams_within(cap))

    assert rows[_LABELS.index("MaxBudget")]["cost"] == pytest.approx(best_spend)


@pytest.mark.parametrize("label, odds_weight", [("OddsFP3_w0", 0.0), ("OddsFP3_w1", 1.0)])
def test_run_race_mixes_pick_by_their_weight(race_one_rows, label, odds_weight):
    """Each mix's team is the best within the cap on its weight, its best driver counted twice for DRS.

    The fixture's odds favour A1 down to C3 and its FP3 the reverse, so the two weights disagree.
    """
    _, cap, rows = race_one_rows
    value = {
        d: odds_weight * _ODDS_RANKS[i] + (1 - odds_weight) * _FP3_RANKS[i] for i, d in enumerate(_DRIVERS)
    }
    for constructor in _CONSTRUCTORS:
        value[constructor] = sum(v for d, v in value.items() if d.endswith("@" + constructor))

    def objective(team):
        drivers, constructors = team
        return sum(value[a] for a in drivers + constructors) + max(value[d] for d in drivers)

    ranked = sorted(_teams_within(cap), key=objective, reverse=True)
    assert objective(ranked[0]) > objective(ranked[1]) + 1e-9, "the fixture needs a single best team"
    best_drivers, best_constructors = ranked[0]
    row = rows[_LABELS.index(label)]

    assert row["drivers"] == ",".join(best_drivers)
    assert row["constructors"] == ",".join(best_constructors)
    assert row["drs_driver"] == max(best_drivers, key=lambda d: value[d])


def test_run_race_random_row_is_the_random_control(race_one_rows):
    race, cap, rows = race_one_rows
    row = rows[-1]

    assert row["points"] == pytest.approx(random_teams_points(race, cap))
    assert row["drivers"] == "" and row["drs_driver"] == ""


def _real_metrics(path: Path, races: list[int]) -> Path:
    """The committed metrics file's 2026 rows for `races` only, so a run covers just those."""
    metrics = load_existing_metrics(DEFAULT_HISTORICAL_OUTPUT)
    metrics[(metrics["Season"] == _SEASON) & metrics["Race"].isin(races)].to_csv(path, index=False)
    return path


def test_main_writes_every_eligible_race(tmp_path):
    """Run on the real 2026 archive and odds, with metrics for races 1, 2 (a sprint) and 3."""
    output = tmp_path / "races.csv"

    exit_code = main([
        "--metrics", str(_real_metrics(tmp_path / "m.csv", [1, 2, 3])),
        "--output", str(output),
        "--comparison", str(tmp_path / "comparison.csv"),
    ])

    assert exit_code == 0
    results = pd.read_csv(output)
    assert results["race"].tolist() == [1] * len(_LABELS) + [3] * len(_LABELS)
    assert results["label"].tolist() == _LABELS * 2
    assert (results["season"] == _SEASON).all()
    assert results.loc[results["race"] == 1, "cap"].tolist() == pytest.approx([100.0] * len(_LABELS))
    season = factory_season(*load_with_derivations(season=_SEASON), _SEASON)
    race_3_cap = race_cap(season.races[3], season.races[1])
    assert race_3_cap != pytest.approx(100.0), "race 3's grid price must differ from race 1's for this check"
    assert results.loc[results["race"] == 3, "cap"].tolist() == pytest.approx([race_3_cap] * len(_LABELS))


def test_main_writes_the_comparison_and_logs_the_default(tmp_path, caplog):
    output, comparison = tmp_path / "races.csv", tmp_path / "comparison.csv"

    with caplog.at_level(logging.INFO):
        main([
            "--metrics", str(_real_metrics(tmp_path / "m.csv", [1, 3])),
            "--output", str(output),
            "--comparison", str(comparison),
        ])

    expected = compare_with_even_split(pd.read_csv(output))
    pd.testing.assert_frame_equal(pd.read_csv(comparison), expected)
    assert f"Default: {choose_default(expected)}" in caplog.text


def test_main_fails_when_no_race_is_eligible(tmp_path):
    """Race 2 alone is a sprint, so there is nothing to run, and no results or comparison file is written."""
    output, comparison = tmp_path / "races.csv", tmp_path / "comparison.csv"

    exit_code = main([
        "--metrics", str(_real_metrics(tmp_path / "m.csv", [2])),
        "--output", str(output),
        "--comparison", str(comparison),
    ])

    assert exit_code == 1
    assert not output.exists()
    assert not comparison.exists()


_BASELINE = "OddsFP3_w0p5"
_BASELINE_POINTS = [100.0, 150.0, 80.0, 200.0, 120.0, 90.0]


def _results(gains: dict[str, list[float]], races: list[int] | None = None) -> pd.DataFrame:
    """Per-race results: every label at the baseline's points plus its gain at that race (0 if not given)."""
    races = races or list(range(1, len(_BASELINE_POINTS) + 1))
    rows = []
    for i, race_num in enumerate(races):
        for label in _LABELS:
            gain = gains.get(label, [0.0] * len(races))[i]
            rows.append({"season": _SEASON, "race": race_num, "label": label, "points": _BASELINE_POINTS[i] + gain})
    return pd.DataFrame(rows)


def _row(comparison: pd.DataFrame, label: str) -> pd.Series:
    return comparison.set_index("label").loc[label]


def test_compare_gives_a_row_per_label_but_the_even_split():
    comparison = compare_with_even_split(_results({}))

    assert comparison["label"].tolist() == [label for label in _LABELS if label != _BASELINE]
    assert comparison["kind"].tolist() == ["mix"] * 4 + ["control"] * 3
    assert (comparison["races"] == len(_BASELINE_POINTS)).all()


def test_compare_passes_a_mix_ahead_at_every_race():
    """10 points ahead at every race: every pretend season averages 10, so the interval is above zero."""
    row = _row(compare_with_even_split(_results({"OddsFP3_w1": [10.0] * 6})), "OddsFP3_w1")

    assert row["mean_gain"] == pytest.approx(10.0)
    assert (row["low"], row["high"]) == pytest.approx((10.0, 10.0))
    assert row["passes"]


def test_compare_fails_a_mix_whose_interval_reaches_zero():
    """Ahead on average, but by too little against its spread for the interval to clear zero."""
    gains = [40.0, -30.0, 35.0, -25.0, 30.0, -20.0]
    row = _row(compare_with_even_split(_results({"OddsFP3_w0": gains})), "OddsFP3_w0")

    assert row["mean_gain"] == pytest.approx(5.0)
    assert row["low"] < 0 < row["high"]
    assert not row["passes"]


def test_compare_interval_is_the_bootstrap_on_the_per_race_gains():
    gains = [12.0, -3.0, 25.0, 4.0, 9.0, 1.0]
    row = _row(compare_with_even_split(_results({"MaxBudget": gains})), "MaxBudget")

    assert (row["low"], row["high"]) == pytest.approx(bootstrap_interval(gains))
    assert row["passes"] == (bootstrap_interval(gains)[0] > 0)


def test_compare_pairs_each_label_with_the_even_split_by_race():
    """Rows shuffled and races numbered out of order: each gain is still taken at its own race."""
    gains = [12.0, -3.0, 25.0, 4.0, 9.0, 1.0]
    results = _results({"OddsFP3_w0p25": gains}, races=[3, 1, 8, 6, 21, 10]).sample(frac=1, random_state=0)

    row = _row(compare_with_even_split(results), "OddsFP3_w0p25")

    assert (row["low"], row["high"]) == pytest.approx(bootstrap_interval([-3.0, 12.0, 4.0, 25.0, 1.0, 9.0]))


def test_compare_raises_when_a_label_misses_a_race():
    results = _results({})
    results = results[~((results["label"] == "BettingOdds") & (results["race"] == 4))]

    with pytest.raises(ValueError, match="BettingOdds"):
        compare_with_even_split(results)


def test_choose_default_keeps_the_even_split_when_no_mix_passes():
    comparison = compare_with_even_split(_results({"OddsFP3_w0": [40.0, -30.0, 35.0, -25.0, 30.0, -20.0]}))

    assert choose_default(comparison) == _BASELINE


def test_choose_default_takes_the_passing_mix_with_the_highest_gain():
    comparison = compare_with_even_split(_results({"OddsFP3_w1": [10.0] * 6, "OddsFP3_w0p75": [20.0] * 6}))

    assert choose_default(comparison) == "OddsFP3_w0p75"


def test_choose_default_ignores_a_passing_control():
    """A control ahead of the even split is reported, but never becomes the default."""
    comparison = compare_with_even_split(_results({"OddsFP3_w1": [5.0] * 6, "BettingOdds": [50.0] * 6}))

    assert _row(comparison, "BettingOdds")["passes"]
    assert choose_default(comparison) == "OddsFP3_w1"
