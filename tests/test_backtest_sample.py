import pandas as pd
import pytest

import backtest.sample as sample_module
from backtest.sample import DEFAULT_BAND_EDGES, sample_starting_teams


# Ten teams per band, plus one team sitting exactly on each band edge
_BAND_VALUES = {
    "(90, 95]": [90.5 + 0.4 * i for i in range(10)],
    "(95, 99.5]": [95.2 + 0.4 * i for i in range(10)],
    "(99.5, 100]": [99.55 + 0.04 * i for i in range(10)],
}
_EDGE_VALUES = [90.0, 95.0, 99.5, 100.0]


def _combinations(season: int) -> pd.DataFrame:
    """A stand-in for a season's priced combinations, indexed like the real one.

    The index is offset by season so each season's teams are distinguishable.
    """
    values = [v for band in _BAND_VALUES.values() for v in band] + _EDGE_VALUES
    index = [season * 1000 + i for i in range(len(values))]
    return pd.DataFrame({"total_value": values}, index=index)


@pytest.fixture
def calls(monkeypatch):
    """Serve synthetic combinations, filtered the way the real function filters."""
    recorded = []

    def fake(season, race_num, min_total_value, max_total_value):
        recorded.append((season, race_num, min_total_value, max_total_value))
        df = _combinations(season)
        keep = (df["total_value"] > min_total_value) & (df["total_value"] <= max_total_value)
        return df[keep]

    monkeypatch.setattr(sample_module, "get_starting_combinations", fake)
    return recorded


def test_one_enumeration_over_the_full_band_range_from_race_one(calls):
    sample_starting_teams(2023, 3, seed=1)
    assert calls == [(2023, 1, 90.0, 100.0)]


def test_n_rows_per_band(calls):
    out = sample_starting_teams(2023, 3, seed=1)
    assert len(out) == 9
    assert out["band"].value_counts().to_dict() == {band: 3 for band in _BAND_VALUES}


def test_every_row_is_inside_its_labelled_band(calls):
    out = sample_starting_teams(2023, 100, seed=1)
    bounds = {"(90, 95]": (90.0, 95.0), "(95, 99.5]": (95.0, 99.5), "(99.5, 100]": (99.5, 100.0)}
    for value, band in zip(out["total_value"], out["band"]):
        low, high = bounds[band]
        assert low < value <= high


def test_band_edges_exclude_the_minimum_and_include_the_maximum(calls):
    out = sample_starting_teams(2023, 100, seed=1)
    band_of = dict(zip(out["total_value"], out["band"]))
    assert 90.0 not in band_of
    assert band_of[95.0] == "(90, 95]"
    assert band_of[99.5] == "(95, 99.5]"
    assert band_of[100.0] == "(99.5, 100]"


def test_same_seed_gives_same_teams(calls):
    first = sample_starting_teams(2023, 3, seed=7)
    second = sample_starting_teams(2023, 3, seed=7)
    assert list(first.index) == list(second.index)


def test_different_seed_gives_different_teams(calls):
    first = sample_starting_teams(2023, 3, seed=7)
    second = sample_starting_teams(2023, 3, seed=8)
    assert list(first.index) != list(second.index)


def test_n_at_least_a_bands_population_gives_the_whole_band(calls):
    out = sample_starting_teams(2023, 50, seed=1)
    # Each band holds its ten interior teams plus the edge team at its maximum
    assert out["band"].value_counts().to_dict() == {band: 11 for band in _BAND_VALUES}
    assert set(out.index) == set(_combinations(2023).index) - {2023 * 1000 + 30}


def test_index_is_each_teams_position_in_the_full_combination_set(calls):
    out = sample_starting_teams(2023, 3, seed=1)
    source = _combinations(2023)
    assert (out["total_value"] == source.loc[out.index, "total_value"]).all()


def test_each_season_draws_from_its_own_combinations(calls):
    out_2023 = sample_starting_teams(2023, 3, seed=1)
    out_2024 = sample_starting_teams(2024, 3, seed=1)
    assert [c[0] for c in calls] == [2023, 2024]
    assert set(out_2023.index) <= set(_combinations(2023).index)
    assert set(out_2024.index) <= set(_combinations(2024).index)


def test_custom_band_edges_are_honoured(calls):
    out = sample_starting_teams(2023, 100, seed=1, band_edges=(95.0, 100.0))
    assert calls == [(2023, 1, 95.0, 100.0)]
    assert set(out["band"]) == {"(95, 100]"}
    # Twenty interior teams, plus the edge teams at 99.5 and 100.0; 95.0 is excluded
    assert len(out) == 22


@pytest.mark.parametrize("edges", [(90.0, 99.5, 95.0, 100.0), (90.0, 95.0, 95.0, 100.0), (100.0,), ()])
def test_edges_not_strictly_increasing_or_too_few_raise(calls, edges):
    with pytest.raises(ValueError):
        sample_starting_teams(2023, 3, seed=1, band_edges=edges)
    assert calls == []


def test_default_band_edges():
    assert DEFAULT_BAND_EDGES == (90.0, 95.0, 99.5, 100.0)


def test_real_season_sample_is_banded():
    # Unpatched: the real 2023 enumeration, so the banding meets real prices
    out = sample_starting_teams(2023, 5, seed=1)
    assert out["band"].value_counts().to_dict() == {"(90, 95]": 5, "(95, 99.5]": 5, "(99.5, 100]": 5}
    assert out["total_value"].between(90.0, 100.0, inclusive="right").all()
