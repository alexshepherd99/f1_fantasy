import pandas as pd
import pytest

from backtest.metrics import pair_with_baseline

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
