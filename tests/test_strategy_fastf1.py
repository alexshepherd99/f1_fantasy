import functools

import pytest
from pulp import LpStatusOptimal

from common import AssetType
from helpers import load_with_derivations
from linear.strategy_base import VarType
from linear.strategy_factory import factory_strategy
from backtest.variants import make_variant
from linear.strategy_fastf1 import StrategyFastF1, StrategyFastF1RuleRise
from races.season import factory_season
from races.team import Team, factory_team_lists
from scripts.run_single_team import run_for_team

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
_VALUES = {
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
    """Stands in for ``SignalTables``, returning set values and recording what was asked."""

    def __init__(self, values: dict[str, float]):
        self._values = values
        self._negative_chance = {asset: 0.0 for asset in _PRICES}
        # Only assets with a value have a rise, so tests name the ones they need
        self._price_rise: dict[str, float] = {}
        self.requested: list[tuple[int, int]] = []
        self.negatives_requested: list[tuple[int, int]] = []
        self.rises_requested: list[tuple[int, int]] = []

    def values(self, season: int, race: int) -> dict[str, float]:
        self.requested.append((season, race))
        return dict(self._values)

    def negative_chance(self, season: int, race: int) -> dict[str, float]:
        self.negatives_requested.append((season, race))
        return dict(self._negative_chance)

    def price_rise(self, season: int, race: int) -> dict[str, float]:
        self.rises_requested.append((season, race))
        return dict(self._price_rise)


@pytest.fixture
def stub_tables(monkeypatch) -> tuple[_StubTables, list]:
    """Replace ``load_signal_tables`` as the strategy sees it, recording the file asked for.

    The real tables need 2023-25 metrics rows matched to the real archive, which no
    small fixture file can give, so the unit tests set the values directly.
    """
    tables = _StubTables(_VALUES)
    files_loaded = []

    def _load(fn_metrics):
        files_loaded.append(fn_metrics)
        return tables

    monkeypatch.setattr("linear.strategy_fastf1.load_signal_tables", _load)
    return tables, files_loaded


def _strategy(
    max_cost: float, max_moves: int, race_num: int = 5, cls: type[StrategyFastF1] = StrategyFastF1, **kwargs
) -> StrategyFastF1:
    """The fixture race and team as a ``cls``, with any argument overridden by ``kwargs``."""
    arguments = dict(
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
    )
    return cls(**(arguments | kwargs))


def _selected(strat: StrategyFastF1) -> set[str]:
    chosen = set()
    for var_type in (VarType.TeamDrivers, VarType.TeamConstructors):
        chosen |= {a for a, var in strat._lp_variables[var_type].items() if var.value() > 0.5}
    return chosen


def test_strategy_fastf1_reads_the_tables_for_its_race(stub_tables):
    """The metrics file given is loaded, and the values asked for are this season and race's."""
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
    tables._values = _VALUES | {unknown: 1.0}

    with pytest.raises(ValueError, match=unknown):
        _strategy(max_cost=25.0, max_moves=2)


def test_strategy_fastf1_maximises_values_within_budget_and_moves(stub_tables):
    """The best team on values that the budget and two moves allow.

    With the budget lifted, or with four moves and the budget lifted, the best team
    differs, so both limits bind. D1 has no signal and scores zero. DRS is left out.
    """
    strat = _strategy(max_cost=25.0, max_moves=2, drs_coefficient=0.0)

    strat.execute()

    assert _selected(strat) == {"D1@C1", "D5@C3", "C1", "C3"}
    assert strat._lp_variables[VarType.OptimiseMax].value() == pytest.approx(70.0)


@pytest.mark.parametrize(
    "drs_coefficient, team, objective",
    [
        (0.0, {"D1@C1", "D3@C2", "C1", "C3"}, 54.0),
        (0.5, {"D1@C1", "D6@C3", "C1", "C2"}, 60.0),
        (1.0, {"D1@C1", "D6@C3", "C1", "C2"}, 75.0),
    ],
)
def test_strategy_fastf1_scales_the_drs_term_by_its_coefficient(
    stub_tables, drs_coefficient, team, objective
):
    """The DRS driver's value counts again, times the coefficient.

    At a budget of 23 the best team without DRS differs from the best with it, and
    each is the only best team, found by brute force.
    """
    strat = _strategy(max_cost=23.0, max_moves=2, drs_coefficient=drs_coefficient)

    strat.execute()

    assert _selected(strat) == team
    assert strat._lp_variables[VarType.OptimiseMax].value() == pytest.approx(objective)


def test_strategy_fastf1_leaves_the_drs_term_out_at_zero(stub_tables):
    """A coefficient of zero adds no DRS variables or constraints to the problem."""
    strat = _strategy(max_cost=23.0, max_moves=2, drs_coefficient=0.0)

    problem = strat.execute()

    assert VarType.DrsDriver not in strat._lp_variables
    assert not any(name.startswith("drs") for name in problem.constraints)


@pytest.mark.parametrize(
    "drs_coefficient, drs_driver",
    [
        # D6 has the best value of any driver, but is not selected at zero
        (0.0, "D3@C2"),
        (1.0, "D6@C3"),
    ],
)
def test_strategy_fastf1_gives_drs_to_the_selected_driver_with_the_best_value(
    stub_tables, drs_coefficient, drs_driver
):
    """The same rule at any coefficient: the best value on the selected team."""
    strat = _strategy(max_cost=23.0, max_moves=2, drs_coefficient=drs_coefficient)

    strat.execute()

    assert strat.get_drs_driver() == drs_driver


@pytest.mark.parametrize("drs_coefficient", [0.0, 1.0])
def test_strategy_fastf1_leaves_drs_to_the_default_with_no_signal(stub_tables, drs_coefficient):
    """With no selected driver worth anything, an empty string lets the default pick.

    At a coefficient of 1 the DRS binaries still nominate someone, arbitrarily.
    """
    tables, _ = stub_tables
    tables._values = {}
    strat = _strategy(max_cost=23.0, max_moves=2, drs_coefficient=drs_coefficient)

    strat.execute()

    assert strat.get_drs_driver() == ""


def test_strategy_fastf1_breaks_a_drs_tie_on_the_identifier(stub_tables):
    """Two selected drivers on equal values: the first identifier wins, whatever the race's order."""
    tables, _ = stub_tables
    tables._values = {"D3@C2": 10.0, "D4@C2": 10.0}
    strat = _strategy(
        max_cost=999.0,
        max_moves=2,
        drs_coefficient=0.0,
        all_available_drivers=list(reversed(_DRIVER_PAIRS)),
    )

    strat.execute()

    assert _selected(strat) >= {"D3@C2", "D4@C2"}
    assert strat.get_drs_driver() == "D3@C2"


@pytest.mark.parametrize(
    "budget_reward, team, objective",
    [
        (0.0, {"D2@C1", "D3@C2", "C1", "C2"}, 20.0),
        (0.25, {"D2@C1", "D3@C2", "C1", "C2"}, 25.0),
        (1.0, {"D2@C1", "D6@C3", "C1", "C2"}, 42.5),
    ],
)
def test_strategy_fastf1_rewards_each_1m_spent(stub_tables, budget_reward, team, objective):
    """The reward adds points per 1m of the team's cost, and at zero changes nothing.

    One move: D3 (price 4) on 10 points is best without a reward, and D6 (price 7.5)
    on 9 points is best at a reward of 1, found by brute force.
    """
    tables, _ = stub_tables
    tables._values = {"D2@C1": 10.0, "D3@C2": 10.0, "D6@C3": 9.0}
    strat = _strategy(max_cost=999.0, max_moves=1, drs_coefficient=0.0, budget_reward=budget_reward)

    strat.execute()

    assert _selected(strat) == team
    assert strat._lp_variables[VarType.OptimiseMax].value() == pytest.approx(objective)


@pytest.mark.parametrize(
    "negative_penalty, team, objective",
    [
        (0.0, {"D2@C1", "D3@C2", "C1", "C2"}, 20.0),
        (1.0, {"D2@C1", "D3@C2", "C1", "C2"}, 19.0),
        (6.0, {"D2@C1", "D6@C3", "C1", "C2"}, 15.4),
    ],
)
def test_strategy_fastf1_penalises_each_selected_assets_chance_of_going_negative(
    stub_tables, negative_penalty, team, objective
):
    """The penalty takes points per unit of chance, for drivers and constructors alike.

    One move: D3 on 10 points with a 50% chance is best below a penalty of 2.5, and D6
    on 9 points with a 10% chance above it. C1's 50% chance counts on every team.
    """
    tables, _ = stub_tables
    tables._values = {"D2@C1": 10.0, "D3@C2": 10.0, "D6@C3": 9.0}
    tables._negative_chance |= {"D3@C2": 0.5, "D6@C3": 0.1, "C1": 0.5}
    strat = _strategy(max_cost=999.0, max_moves=1, drs_coefficient=0.0, negative_penalty=negative_penalty)

    strat.execute()

    assert _selected(strat) == team
    assert strat._lp_variables[VarType.OptimiseMax].value() == pytest.approx(objective)


def test_strategy_fastf1_does_not_double_the_drs_drivers_chance(stub_tables):
    """DRS doubles a driver's value, but their chance of going negative counts once.

    One move: D3 joins D2 and C1, each with a chance, and D2 or D3 takes DRS on 10.
    Values 20, DRS 10 and chances 0.2 + 0.5 + 0.5 give 28.8, found by brute force. A
    doubled chance would give DRS to D2, the lower chance, and 28.6.
    """
    tables, _ = stub_tables
    tables._values = {"D2@C1": 10.0, "D3@C2": 10.0, "D6@C3": 9.0}
    tables._negative_chance |= {"D2@C1": 0.2, "D3@C2": 0.5, "D6@C3": 0.1, "C1": 0.5}
    strat = _strategy(max_cost=999.0, max_moves=1, drs_coefficient=1.0, negative_penalty=1.0)

    strat.execute()

    assert _selected(strat) == {"D2@C1", "D3@C2", "C1", "C2"}
    assert strat._lp_variables[VarType.OptimiseMax].value() == pytest.approx(28.8)


@pytest.mark.parametrize("negative_penalty, requested", [(0.0, []), (6.0, [(2025, 7)])])
def test_strategy_fastf1_reads_the_chances_only_with_a_penalty(stub_tables, negative_penalty, requested):
    """At zero the chances are never read. Otherwise they are this season and race's."""
    tables, _ = stub_tables

    _strategy(max_cost=25.0, max_moves=2, race_num=7, negative_penalty=negative_penalty)

    assert tables.negatives_requested == requested


@pytest.mark.parametrize("unknown", ["D7@C9", "C9"])
def test_strategy_fastf1_raises_on_a_chance_for_an_asset_not_in_the_race(stub_tables, unknown):
    """As for values, a chance naming an asset the race does not have raises."""
    tables, _ = stub_tables
    tables._negative_chance[unknown] = 0.1

    with pytest.raises(ValueError, match=unknown):
        _strategy(max_cost=25.0, max_moves=2, negative_penalty=6.0)


@pytest.mark.parametrize("missing", ["D1@C1", "C3"])
def test_strategy_fastf1_raises_on_an_available_asset_with_no_chance(stub_tables, missing):
    """Every priced asset has a chance, so one missing is a defect rather than a zero."""
    tables, _ = stub_tables
    del tables._negative_chance[missing]

    with pytest.raises(ValueError, match=missing):
        _strategy(max_cost=25.0, max_moves=2, negative_penalty=6.0)


@pytest.mark.parametrize(
    "price_rise_reward, team, objective",
    [
        (0.0, {"D2@C1", "D3@C2", "C1", "C2"}, 20.0),
        (1.0, {"D2@C1", "D3@C2", "C1", "C2"}, 20.3),
        (5.0, {"D2@C1", "D6@C3", "C1", "C2"}, 22.5),
    ],
)
def test_strategy_fastf1_rewards_each_selected_assets_expected_price_rise(
    stub_tables, price_rise_reward, team, objective
):
    """The reward adds points per 1m of expected rise, for drivers and constructors alike.

    One move: D3 on 10 points rising 0.1 is best below a reward of 2.5, and D6 on 9
    points rising 0.5 above it. C1's 0.2 counts on every team. D2 has no rise and
    scores zero for it, as an asset with no value has none.
    """
    tables, _ = stub_tables
    tables._values = {"D2@C1": 10.0, "D3@C2": 10.0, "D6@C3": 9.0}
    tables._price_rise = {"D3@C2": 0.1, "D6@C3": 0.5, "C1": 0.2}
    strat = _strategy(max_cost=999.0, max_moves=1, drs_coefficient=0.0, price_rise_reward=price_rise_reward)

    strat.execute()

    assert _selected(strat) == team
    assert strat._lp_variables[VarType.OptimiseMax].value() == pytest.approx(objective)


def test_strategy_fastf1_does_not_double_the_drs_drivers_rise(stub_tables):
    """DRS doubles a driver's value, but not their price change, so their rise counts once.

    One move: D3 joins D2 and C1, each with a rise, and D2 or D3 takes DRS on 10.
    Values 20, DRS 10 and rises 0.2 + 0.5 + 0.5 give 31.2, found by brute force. A
    doubled rise would give DRS to D3, the higher rise, and 31.7.
    """
    tables, _ = stub_tables
    tables._values = {"D2@C1": 10.0, "D3@C2": 10.0, "D6@C3": 9.0}
    tables._price_rise = {"D2@C1": 0.2, "D3@C2": 0.5, "D6@C3": 0.1, "C1": 0.5}
    strat = _strategy(max_cost=999.0, max_moves=1, drs_coefficient=1.0, price_rise_reward=1.0)

    strat.execute()

    assert _selected(strat) == {"D2@C1", "D3@C2", "C1", "C2"}
    assert strat._lp_variables[VarType.OptimiseMax].value() == pytest.approx(31.2)


@pytest.mark.parametrize("price_rise_reward, requested", [(0.0, []), (5.0, [(2025, 7)])])
def test_strategy_fastf1_reads_the_rises_only_with_a_reward(stub_tables, price_rise_reward, requested):
    """At zero the rises are never read. Otherwise they are this season and race's."""
    tables, _ = stub_tables

    _strategy(max_cost=25.0, max_moves=2, race_num=7, price_rise_reward=price_rise_reward)

    assert tables.rises_requested == requested


@pytest.mark.parametrize("unknown", ["D7@C9", "C9"])
def test_strategy_fastf1_raises_on_a_rise_for_an_asset_not_in_the_race(stub_tables, unknown):
    """As for values, a rise naming an asset the race does not have raises."""
    tables, _ = stub_tables
    tables._price_rise[unknown] = 0.1

    with pytest.raises(ValueError, match=unknown):
        _strategy(max_cost=25.0, max_moves=2, price_rise_reward=5.0)


@pytest.mark.parametrize(
    "settings",
    [{}, {"negative_penalty": 6.0}, {"budget_reward": 1.0}, {"price_rise_reward": 5.0}],
)
def test_strategy_fastf1_solves_a_race_with_no_signal(stub_tables, settings):
    """As 2026 race 19, priced but with no metrics: every asset's value is zero and it solves.

    DRS falls to the default pick. A race with no signal has no rises, as the stub gives
    by default, but chances and cost come from prices, so the penalty and the budget
    reward still count. The objective's value is not checked: with every coefficient
    zero, PuLP swaps in a ``__dummy`` variable that CBC never sets, so ``value()`` gives
    None rather than 0.
    """
    tables, _ = stub_tables
    tables._values = {}
    strat = _strategy(max_cost=25.0, max_moves=2, **settings)

    problem = strat.execute()

    assert problem.status == LpStatusOptimal
    assert len(_selected(strat)) == 4
    assert strat.get_drs_driver() == ""


def test_strategy_fastf1_keeps_the_move_limit_at_race_four(stub_tables):
    """No race-4 unlimited-moves chip: two moves stay two, where four would pick another team."""
    strat = _strategy(max_cost=999.0, max_moves=2, race_num=4, drs_coefficient=0.0)

    strat.execute()

    assert strat._max_moves == 2
    assert strat._lp_variables[VarType.TeamMoves].value() == pytest.approx(2.0)
    assert _selected(strat) == {"D2@C1", "D6@C3", "C2", "C3"}


@pytest.mark.parametrize(
    "settings", [{}, {"negative_penalty": 6.0}, {"price_rise_reward": 5.0}]
)
def test_strategy_fastf1_solves_a_real_race(settings):
    """Built by the factory on the real metrics file and archive, for 2025 race 5.

    The signal's identifiers match the race's, every selected asset has a positive
    value, and the LP solves with a full team. With a penalty, every
    available asset has a chance of going negative. With a reward, every rise names
    an asset in the race, and every selected asset has a value but not always a
    positive one: the reward rightly holds BOR, at 0 and expected to hold, over HUL,
    at 0.70 and expected to fall 0.6m.
    """
    season = factory_season(*load_with_derivations(season=2025), 2025)
    team = Team(num_drivers=5, num_constructors=2, unused_budget=50.0)
    for driver in ["BOR@KCK", "HAD@VRB", "DOO@ALP", "ALO@AST", "HUL@KCK"]:
        team.add_asset(AssetType.DRIVER, driver)
    for constructor in ["KCK", "AST"]:
        team.add_asset(AssetType.CONSTRUCTOR, constructor)

    strategy = functools.partial(StrategyFastF1, **settings)
    strat = factory_strategy(season.races[5], season.races[4], team, strategy, max_moves=2, season_year=2025)
    problem = strat.execute()

    selected = _selected(strat)
    assert problem.status == LpStatusOptimal
    assert len(selected) == 7
    assert strat._lp_variables[VarType.TeamMoves].value() == pytest.approx(2.0)
    if "price_rise_reward" in settings:
        assert all(a in strat._values for a in selected)
    else:
        assert all(strat._values.get(a, 0.0) > 0.0 for a in selected)


def test_strategy_fastf1_rule_rise_is_the_chosen_setting(stub_tables):
    """fastf1_v2's chosen setting: a price-rise reward of 2.5, every other default kept."""
    tables, _ = stub_tables

    strat = _strategy(max_cost=25.0, max_moves=2, race_num=7, cls=StrategyFastF1RuleRise)

    assert StrategyFastF1RuleRise.__name__ == "StrategyFastF1RuleRise"
    assert isinstance(strat, StrategyFastF1)
    assert strat._price_rise_reward == 2.5
    assert strat._drs_coefficient == 1.0
    assert strat._budget_reward == 0.0
    assert strat._negative_penalty == 0.0
    assert tables.rises_requested == [(2025, 7)]


def test_strategy_fastf1_rule_rise_will_not_take_another_reward(stub_tables):
    """The reward is fixed, so the name always means the setting that was back-tested."""
    with pytest.raises(TypeError, match="price_rise_reward"):
        _strategy(max_cost=25.0, max_moves=2, cls=StrategyFastF1RuleRise, price_rise_reward=5.0)


def test_strategy_fastf1_rule_rise_plays_as_the_backtested_variant():
    """A 2025 season, race for race, as step 17's ``FastF1_RuleRise2p5`` built by ``make_variant``."""
    season = factory_season(*load_with_derivations(season=2025), 2025)

    def _run(strategy) -> list[dict]:
        # A fresh team per run, since run_for_team mutates the team it is given
        team = factory_team_lists(
            drivers=["BOR@KCK", "HAD@VRB", "ALB@WIL", "ALO@AST", "HUL@KCK"],
            constructors=["KCK", "AST"],
            race=season.races[1],
        )
        rows = run_for_team(strategy, team, season, 2025, 1)
        return [{key: value for key, value in row.items() if key != "strategy"} for row in rows]

    variant_rows = _run(make_variant(StrategyFastF1, "FastF1_RuleRise2p5", price_rise_reward=2.5))

    assert _run(StrategyFastF1RuleRise) == variant_rows
    # Without this, the test could pass with the reward doing nothing
    assert _run(StrategyFastF1) != variant_rows
