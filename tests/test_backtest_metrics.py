import pandas as pd
import pytest

from backtest.metrics import pair_with_baseline, rank_challengers, season_summary, verdict

_BASE = "Base"
_EDGES = (90.0, 95.0, 99.5, 100.0)


def _results(rows: list[tuple]) -> pd.DataFrame:
    """Result rows as (label, season, team, sampled_value, total_points), with a stale band."""
    return pd.DataFrame(
        [
            {
                "label": label,
                "season": season,
                "team": team,
                "sampled_value": value,
                "band": "stale",
                "total_points": points,
                "race": 22,
            }
            for label, season, team, value, points in rows
        ]
    )


def _by_key(paired: pd.DataFrame) -> dict:
    return {(r.label, r.season, r.team): r for r in paired.itertuples()}


def test_deltas_and_percent_deltas_per_team():
    paired = pair_with_baseline(
        _results([
            (_BASE, 2023, "t1", 99.7, 2000),
            (_BASE, 2023, "t2", 96.0, 1600),
            ("Chal", 2023, "t1", 99.7, 2100),
            ("Chal", 2023, "t2", 96.0, 1200),
        ]),
        _BASE,
        _EDGES,
    )

    rows = _by_key(paired)
    assert (rows["Chal", 2023, "t1"].baseline_points, rows["Chal", 2023, "t1"].delta) == (2000, 100)
    assert rows["Chal", 2023, "t1"].delta_pct == pytest.approx(5.0)
    assert (rows["Chal", 2023, "t2"].baseline_points, rows["Chal", 2023, "t2"].delta) == (1600, -400)
    assert rows["Chal", 2023, "t2"].delta_pct == pytest.approx(-25.0)


def test_baseline_is_paired_with_itself_at_zero_delta():
    paired = pair_with_baseline(
        _results([(_BASE, 2023, "t1", 99.7, 2000), ("Chal", 2023, "t1", 99.7, 2100)]),
        _BASE,
        _EDGES,
    )

    row = _by_key(paired)[_BASE, 2023, "t1"]
    assert (row.total_points, row.baseline_points, row.delta, row.delta_pct) == (2000, 2000, 0, 0.0)


def test_pairs_within_a_season_only():
    paired = pair_with_baseline(
        _results([
            (_BASE, 2023, "t1", 99.7, 2000),
            (_BASE, 2024, "t1", 99.7, 3000),
            ("Chal", 2023, "t1", 99.7, 2100),
            ("Chal", 2024, "t1", 99.7, 2900),
        ]),
        _BASE,
        _EDGES,
    )

    rows = _by_key(paired)
    assert rows["Chal", 2023, "t1"].delta == 100
    assert rows["Chal", 2024, "t1"].delta == -100


def test_teams_missing_from_either_side_are_dropped():
    paired = pair_with_baseline(
        _results([
            (_BASE, 2023, "t1", 99.7, 2000),
            (_BASE, 2023, "only_base", 99.7, 2000),
            ("Chal", 2023, "t1", 99.7, 2100),
            ("Chal", 2023, "only_chal", 99.7, 2100),
        ]),
        _BASE,
        _EDGES,
    )

    assert set(_by_key(paired)) == {(_BASE, 2023, "t1"), (_BASE, 2023, "only_base"), ("Chal", 2023, "t1")}


def test_band_is_derived_from_sampled_value_not_the_stored_band():
    paired = pair_with_baseline(
        _results([
            (_BASE, 2023, "a", 99.7, 2000),
            (_BASE, 2023, "edge", 95.0, 2000),
            (_BASE, 2023, "c", 90.1, 2000),
        ]),
        _BASE,
        _EDGES,
    )

    bands = {r.team: r.band for r in paired.itertuples()}
    assert bands == {"a": "(99.5, 100]", "edge": "(90, 95]", "c": "(90, 95]"}


def test_band_follows_the_edges_given():
    paired = pair_with_baseline(_results([(_BASE, 2023, "a", 99.7, 2000)]), _BASE, (95.0, 100.0))
    assert list(paired["band"]) == ["(95, 100]"]


def test_value_outside_every_band_raises():
    with pytest.raises(ValueError):
        pair_with_baseline(_results([(_BASE, 2023, "t1", 90.0, 2000)]), _BASE, _EDGES)


def test_missing_baseline_raises():
    with pytest.raises(ValueError):
        pair_with_baseline(_results([("Chal", 2023, "t1", 99.7, 2100)]), _BASE, _EDGES)


def test_columns():
    paired = pair_with_baseline(_results([(_BASE, 2023, "t1", 99.7, 2000)]), _BASE, _EDGES)
    assert list(paired.columns) == [
        "label", "season", "team", "band", "sampled_value",
        "total_points", "baseline_points", "delta", "delta_pct",
    ]


_BAND_A = "(99.5, 100]"
_BAND_C = "(90, 95]"


def _paired(rows: list[tuple]) -> pd.DataFrame:
    """Paired rows as (label, season, team, band, total_points, baseline_points)."""
    df = pd.DataFrame(rows, columns=["label", "season", "team", "band", "total_points", "baseline_points"])
    df["delta"] = df["total_points"] - df["baseline_points"]
    df["delta_pct"] = df["delta"] / df["baseline_points"] * 100
    return df


def _summary_fixture() -> pd.DataFrame:
    # Band A: four teams, the challenger scoring +100, -100, a tie and +400.
    # Band C: one team, the challenger scoring -150. Band B holds no teams.
    base = [(_BASE, 2023, t, band, pts, pts) for t, band, pts in [
        ("t1", _BAND_A, 1000), ("t2", _BAND_A, 2000), ("t3", _BAND_A, 3000), ("t4", _BAND_A, 4000), ("t5", _BAND_C, 1000),
    ]]
    chal = [("Chal", 2023, t, band, pts, base_pts) for t, band, pts, base_pts in [
        ("t1", _BAND_A, 1100, 1000), ("t2", _BAND_A, 1900, 2000), ("t3", _BAND_A, 3000, 3000),
        ("t4", _BAND_A, 4400, 4000), ("t5", _BAND_C, 850, 1000),
    ]]
    return _paired(base + chal)


def _summary_row(summary: pd.DataFrame, label: str, band: str) -> dict:
    rows = summary[(summary["label"] == label) & (summary["band"] == band)]
    assert len(rows) == 1
    return rows.iloc[0].to_dict()


def _assert_metrics(row: dict, expected: dict):
    assert {k: row[k] for k in expected} == pytest.approx(expected)


def test_summary_metrics_for_a_band():
    # P10 interpolates linearly: position 0.3 of the way through four sorted values
    row = _summary_row(season_summary(_summary_fixture(), _EDGES), "Chal", _BAND_A)
    _assert_metrics(row, {
        "teams": 4,
        "mean_points": 2600, "median_points": 2450, "p10_points": 1340, "max_points": 4400,
        "mean_delta": 100, "mean_delta_pct": 3.75, "median_delta": 50, "p10_delta": -70,
        "win_rate": 0.5,  # the tie is not a win
    })


def test_summary_metrics_for_a_single_team_band():
    row = _summary_row(season_summary(_summary_fixture(), _EDGES), "Chal", _BAND_C)
    _assert_metrics(row, {
        "teams": 1,
        "mean_points": 850, "median_points": 850, "p10_points": 850, "max_points": 850,
        "mean_delta": -150, "mean_delta_pct": -15, "median_delta": -150, "p10_delta": -150,
        "win_rate": 0,
    })


def test_baseline_rows_have_zero_deltas_and_no_wins():
    row = _summary_row(season_summary(_summary_fixture(), _EDGES), _BASE, _BAND_A)
    _assert_metrics(row, {
        "teams": 4,
        "mean_points": 2500, "median_points": 2500, "p10_points": 1300, "max_points": 4000,
        "mean_delta": 0, "mean_delta_pct": 0, "median_delta": 0, "p10_delta": 0,
        "win_rate": 0,
    })


def test_pooled_row_is_computed_from_the_paired_rows_not_the_band_means():
    # Averaging the two band means gives (100 - 150) / 2 = -25; pooling the five
    # teams gives +50, the opposite sign
    row = _summary_row(season_summary(_summary_fixture(), _EDGES), "Chal", "pooled")
    _assert_metrics(row, {
        "teams": 5,
        "mean_points": 2250, "median_points": 1900, "p10_points": 950, "max_points": 4400,
        "mean_delta": 50, "mean_delta_pct": 0, "median_delta": 0, "p10_delta": -130,
        "win_rate": 0.4,
    })


def test_one_row_per_label_season_and_populated_band_plus_pooled():
    summary = season_summary(_summary_fixture(), _EDGES)
    assert sorted(zip(summary["label"], summary["season"], summary["band"])) == sorted(
        (label, 2023, band) for label in [_BASE, "Chal"] for band in [_BAND_A, _BAND_C, "pooled"]
    )


def test_summary_columns():
    assert list(season_summary(_summary_fixture(), _EDGES).columns) == [
        "label", "season", "band", "teams",
        "mean_points", "median_points", "p10_points", "max_points",
        "mean_delta", "mean_delta_pct", "median_delta", "p10_delta", "win_rate",
    ]


def test_summary_rows_ordered_by_season_label_then_band_edges_then_pooled():
    band_b = "(95, 99.5]"
    paired = _paired([
        ("Chal", 2024, "t", _BAND_A, 1, 1),
        (_BASE, 2024, "t", _BAND_A, 1, 1),
        ("Chal", 2023, "t", _BAND_A, 1, 1),
        ("Chal", 2023, "u", band_b, 1, 1),
        ("Chal", 2023, "v", _BAND_C, 1, 1),
    ])

    summary = season_summary(paired, _EDGES)

    assert list(zip(summary["season"], summary["label"], summary["band"])) == [
        (2023, "Chal", _BAND_C), (2023, "Chal", band_b), (2023, "Chal", _BAND_A), (2023, "Chal", "pooled"),
        (2024, _BASE, _BAND_A), (2024, _BASE, "pooled"),
        (2024, "Chal", _BAND_A), (2024, "Chal", "pooled"),
    ]
    assert list(summary.index) == list(range(len(summary)))


def test_bands_are_ordered_by_edge_not_by_label_text():
    # The default labels happen to sort correctly as text; "(10, 100]" sorts before "(5, 10]"
    paired = _paired([(_BASE, 2023, "hi", "(10, 100]", 1, 1), (_BASE, 2023, "lo", "(5, 10]", 1, 1)])

    summary = season_summary(paired, (5.0, 10.0, 100.0))

    assert list(summary["band"]) == ["(5, 10]", "(10, 100]", "pooled"]


def _summary(rows: list[tuple]) -> pd.DataFrame:
    """Summary rows as (label, season, band, mean_delta, mean_delta_pct)."""
    return pd.DataFrame(rows, columns=["label", "season", "band", "mean_delta", "mean_delta_pct"])


def _ranks(ranked: pd.DataFrame) -> dict:
    return {(r.label, r.season, r.band): r.rank for r in ranked.itertuples()}


def test_challengers_ranked_by_mean_percent_delta_within_each_season_and_band():
    # A wins band A but loses band C and the pooled row; in 2024 it wins the pooled row
    ranked = rank_challengers(_summary([
        ("A", 2023, _BAND_A, 50, 5.0), ("B", 2023, _BAND_A, 30, 3.0),
        ("A", 2023, _BAND_C, -20, -2.0), ("B", 2023, _BAND_C, 40, 4.0),
        ("A", 2023, "pooled", 10, 1.0), ("B", 2023, "pooled", 20, 2.0),
        ("A", 2024, "pooled", 30, 3.0), ("B", 2024, "pooled", 20, 2.0),
    ]), _BASE)

    assert _ranks(ranked) == {
        ("A", 2023, _BAND_A): 1, ("B", 2023, _BAND_A): 2,
        ("A", 2023, _BAND_C): 2, ("B", 2023, _BAND_C): 1,
        ("A", 2023, "pooled"): 2, ("B", 2023, "pooled"): 1,
        ("A", 2024, "pooled"): 1, ("B", 2024, "pooled"): 2,
    }


def test_ranked_by_percent_delta_not_points_delta():
    # A gains more points, B more per cent, as against a lower-scoring baseline
    ranked = rank_challengers(_summary([("A", 2023, "pooled", 100, 1.0), ("B", 2023, "pooled", 50, 2.0)]), _BASE)
    assert _ranks(ranked) == {("A", 2023, "pooled"): 2, ("B", 2023, "pooled"): 1}


def test_ties_share_a_rank_and_the_baseline_is_unranked():
    ranked = rank_challengers(_summary([
        (_BASE, 2023, "pooled", 0, 0.0),
        ("A", 2023, "pooled", 10, 1.0), ("B", 2023, "pooled", 10, 1.0), ("C", 2023, "pooled", -10, -1.0),
    ]), _BASE)

    ranks = _ranks(ranked)
    assert pd.isna(ranks[_BASE, 2023, "pooled"])
    assert {k: v for k, v in ranks.items() if k[0] != _BASE} == {
        ("A", 2023, "pooled"): 1, ("B", 2023, "pooled"): 1, ("C", 2023, "pooled"): 3,
    }


def test_ranking_keeps_the_summary_rows_and_order():
    summary = _summary([("B", 2023, "pooled", 10, 1.0), (_BASE, 2023, "pooled", 0, 0.0), ("A", 2023, "pooled", 20, 2.0)])

    ranked = rank_challengers(summary, _BASE)

    pd.testing.assert_frame_equal(ranked.drop(columns="rank"), summary)


def _verdicts(summary: pd.DataFrame) -> dict:
    return {r.label: r for r in verdict(summary, _BASE).itertuples()}


def test_verdict_needs_a_positive_pooled_delta_in_every_season():
    verdicts = _verdicts(_summary([
        (_BASE, 2023, "pooled", 0, 0.0), (_BASE, 2024, "pooled", 0, 0.0),
        # A band row below zero does not count against a positive pooled row
        ("Always", 2023, _BAND_A, -100, -5.0),
        ("Always", 2023, "pooled", 10, 1.0), ("Always", 2024, "pooled", 5, 0.5),
        ("OneBad", 2023, "pooled", 10, 1.0), ("OneBad", 2024, "pooled", -5, -0.5),
        ("Zero", 2023, "pooled", 10, 1.0), ("Zero", 2024, "pooled", 0, 0.0),
        ("AllNeg", 2023, "pooled", -10, -1.0), ("AllNeg", 2024, "pooled", -5, -0.5),
        ("NegZero", 2023, "pooled", -10, -1.0), ("NegZero", 2024, "pooled", 0, 0.0),
        ("Missing", 2023, "pooled", 10, 1.0),
    ]))

    assert set(verdicts) == {"Always", "OneBad", "Zero", "AllNeg", "NegZero", "Missing"}
    got = {label: (v.seasons, v.seasons_positive, v.beats_baseline, v.consistent_sign) for label, v in verdicts.items()}
    assert got == {
        "Always": (2, 2, True, True),
        "OneBad": (2, 1, False, False),
        "Zero": (2, 1, False, False),
        "AllNeg": (2, 0, False, True),
        "NegZero": (2, 0, False, False),  # zero has no sign
        "Missing": (1, 1, False, False),
    }


def test_verdict_follows_the_pooled_mean_not_the_average_of_band_means():
    # Step 6's fixture: pooled mean delta +50, average of the band means -25
    summary = season_summary(_summary_fixture(), _EDGES)

    assert _verdicts(summary)["Chal"].beats_baseline


def test_verdict_columns():
    summary = _summary([(_BASE, 2023, "pooled", 0, 0.0), ("A", 2023, "pooled", 10, 1.0)])
    assert list(verdict(summary, _BASE).columns) == [
        "label", "seasons", "seasons_positive", "beats_baseline", "consistent_sign",
    ]
