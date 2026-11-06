import pytest
from pulp import LpStatusOptimal

from common import AssetType
from helpers import load_with_derivations
from linear.strategy_base import VarType
from linear.strategy_factory import factory_strategy
from linear.strategy_fastf1 import StrategyFastF1
from races.season import factory_season
from races.team import Team

_DRIVER_PAIRS = {
    "D1@C1": "C1",
    "D2@C1": "C1",
    "D3@C2": "C2",
    "D4@C2": "C2",
    "D5@C3": "C3",
    "D6@C3": "C3",
}
_PRICES = {
    "D1@C1": 1.0,
    "D2@C1": 2.0,
    "D3@C2": 4.0,
    "D4@C2": 5.0,
    "D5@C3": 6.0,
    "D6@C3": 7.5,
    "C1": 6.0,
    "C2": 8.0,
    "C3": 12.0,
}
# D1 has no signal, as SAR in 2024 race 3, so scores zero
_EXPECTED_POINTS = {
    "D2@C1": 3.0,
    "D3@C2": 9.0,
    "D4@C2": 10.0,
    "D5@C3": 25.0,
    "D6@C3": 30.0,
    "C1": 5.0,
    "C2": 10.0,
    "C3": 40.0,
}


class _StubTables:
    """Stands in for ``SignalTables``, returning set points and recording what was asked."""

    def __init__(self, expected_points: dict[str, float]):
        self._expected_points = expected_points
        self.requested: list[tuple[int, int]] = []

    def expected_points(self, season: int, race: int) -> dict[str, float]:
        self.requested.append((season, race))
        return dict(self._expected_points)


@pytest.fixture
def stub_tables(monkeypatch) -> tuple[_StubTables, list]:
    """Replace ``load_signal_tables`` as the strategy sees it, recording the file asked for.

    The real tables need 2023-25 metrics rows matched to the real archive, which no
    small fixture file can give, so the unit tests set the expected points directly.
    """
    tables = _StubTables(_EXPECTED_POINTS)
    files_loaded = []

    def _load(fn_metrics):
        files_loaded.append(fn_metrics)
        return tables

    monkeypatch.setattr("linear.strategy_fastf1.load_signal_tables", _load)
    return tables, files_loaded


def _strategy(max_cost: float, max_moves: int, race_num: int = 5, **kwargs) -> StrategyFastF1:
    return StrategyFastF1(
        team_drivers=["D1@C1", "D2@C1"],
        team_constructors=["C1", "C2"],
        all_available_drivers=list(_DRIVER_PAIRS),
        all_available_constructors=["C1", "C2", "C3"],
        all_available_driver_pairs=_DRIVER_PAIRS,
        prev_available_driver_pairs=_DRIVER_PAIRS,
        max_cost=max_cost,
        max_moves=max_moves,
        prices_assets=_PRICES,
        derivs_assets={},
        race_num=race_num,
        season_year=2025,
        **kwargs,
    )


def _selected(strat: StrategyFastF1) -> set[str]:
    chosen = set()
    for var_type in (VarType.TeamDrivers, VarType.TeamConstructors):
        chosen |= {a for a, var in strat._lp_variables[var_type].items() if var.value() > 0.5}
    return chosen


def test_strategy_fastf1_reads_the_tables_for_its_race(stub_tables):
    """The metrics file given is loaded, and the points asked for are this season and race's."""
    tables, files_loaded = stub_tables

    _strategy(max_cost=25.0, max_moves=2, race_num=7, fn_metrics="some/metrics.xlsx")

    assert files_loaded == ["some/metrics.xlsx"]
    assert tables.requested == [(2025, 7)]


@pytest.mark.parametrize("unknown", ["D7@C9", "C9"])
def test_strategy_fastf1_raises_on_a_signal_for_an_asset_not_in_the_race(stub_tables, unknown):
    """A signal naming an asset the race does not have means the identifiers disagree.

    Left alone, a disagreement over every identifier would score each asset zero and
    still solve, so it raises instead.
    """
    tables, _ = stub_tables
    tables._expected_points = _EXPECTED_POINTS | {unknown: 1.0}

    with pytest.raises(ValueError, match=unknown):
        _strategy(max_cost=25.0, max_moves=2)


def test_strategy_fastf1_maximises_expected_points_within_budget_and_moves(stub_tables):
    """The best team on expected points that the budget and two moves allow.

    With the budget lifted, or with four moves and the budget lifted, the best team
    differs, so both limits bind. D1 has no signal and scores zero.
    """
    strat = _strategy(max_cost=25.0, max_moves=2)

    strat.execute()

    assert _selected(strat) == {"D1@C1", "D5@C3", "C1", "C3"}
    assert strat._lp_variables[VarType.OptimiseMax].value() == pytest.approx(70.0)


def test_strategy_fastf1_keeps_the_move_limit_at_race_four(stub_tables):
    """No race-4 unlimited-moves chip: two moves stay two, where four would pick another team."""
    strat = _strategy(max_cost=999.0, max_moves=2, race_num=4)

    strat.execute()

    assert strat._max_moves == 2
    assert strat._lp_variables[VarType.TeamMoves].value() == pytest.approx(2.0)
    assert _selected(strat) == {"D2@C1", "D6@C3", "C2", "C3"}


def test_strategy_fastf1_solves_a_real_race():
    """Built by the factory on the real metrics file and archive, for 2025 race 5.

    The signal's identifiers match the race's, every selected asset has positive
    expected points, and the LP solves with a full team.
    """
    season = factory_season(*load_with_derivations(season=2025), 2025)
    team = Team(num_drivers=5, num_constructors=2, unused_budget=50.0)
    for driver in ["BOR@KCK", "HAD@VRB", "DOO@ALP", "ALO@AST", "HUL@KCK"]:
        team.add_asset(AssetType.DRIVER, driver)
    for constructor in ["KCK", "AST"]:
        team.add_asset(AssetType.CONSTRUCTOR, constructor)

    strat = factory_strategy(
        season.races[5], season.races[4], team, StrategyFastF1, max_moves=2, season_year=2025
    )
    problem = strat.execute()

    selected = _selected(strat)
    assert problem.status == LpStatusOptimal
    assert len(selected) == 7
    assert strat._lp_variables[VarType.TeamMoves].value() == pytest.approx(2.0)
    assert all(strat._expected_points.get(a, 0.0) > 0.0 for a in selected)
