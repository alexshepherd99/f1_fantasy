import pytest

import backtest.cli as cli
from backtest.cli import COMPLETED_SEASONS, STRATEGIES, main, parse_arguments
from backtest.sample import DEFAULT_BAND_EDGES
from linear.strategy_budget import StrategyMaxBudget
from linear.strategy_fastf1 import StrategyFastF1
from linear.strategy_max_points import StrategyMaxPoints
from linear.strategy_odds import StrategyBettingOdds
from linear.strategy_p2pm import StrategyMaxP2PM
from linear.strategy_p2pm_no_reset import StrategyMaxP2PMNoReset
from linear.strategy_zero_stop import StrategyZeroStop


def test_defaults():
    args = parse_arguments(["--strategies", "StrategyZeroStop"])

    assert args.seasons == [2023, 2024, 2025]
    assert args.sample_size == 500
    assert args.seed == 1
    assert args.bands == list(DEFAULT_BAND_EDGES)
    assert args.output == "outputs/backtest_v1_results.parquet"
    assert args.summary == "outputs/backtest_v1_summary.csv"


def test_completed_seasons_leave_out_the_season_in_progress():
    assert COMPLETED_SEASONS == [2023, 2024, 2025]


def test_registry_holds_the_existing_strategies_by_name():
    assert {name: s for name, s in STRATEGIES.items() if name not in _FASTF1_SETTINGS} == {
        "StrategyMaxP2PM": StrategyMaxP2PM,
        "StrategyZeroStop": StrategyZeroStop,
        "StrategyMaxBudget": StrategyMaxBudget,
        "StrategyMaxPoints": StrategyMaxPoints,
        "StrategyMaxP2PMNoReset": StrategyMaxP2PMNoReset,
        "StrategyBettingOdds": StrategyBettingOdds,
    }


# fastf1_v2's tuning variants, each one change from the base: (DRS coefficient, penalty, reward)
_FASTF1_SETTINGS = {
    "StrategyFastF1": (1.0, 0.0, 0.0),
    "FastF1_Drs0": (0.0, 0.0, 0.0),
    "FastF1_Neg6": (1.0, 6.0, 0.0),
    "FastF1_Neg12": (1.0, 12.0, 0.0),
    "FastF1_Bud025": (1.0, 0.0, 0.25),
    "FastF1_Bud05": (1.0, 0.0, 0.5),
    "FastF1_Bud1": (1.0, 0.0, 1.0),
}


class _EmptyTables:
    """Stands in for ``SignalTables`` for a race with no assets."""

    def expected_points(self, season: int, race: int) -> dict[str, float]:
        return {}

    def negative_chance(self, season: int, race: int) -> dict[str, float]:
        return {}


@pytest.mark.parametrize("label, settings", _FASTF1_SETTINGS.items())
def test_fastf1_variants_are_registered_with_their_settings(monkeypatch, label, settings):
    """Each fastf1_v2 variant is nameable, is a StrategyFastF1, and is built with its settings."""
    monkeypatch.setattr("linear.strategy_fastf1.load_signal_tables", lambda fn_metrics: _EmptyTables())

    args = parse_arguments(["--strategies", label])
    strategy = STRATEGIES[args.strategies[0]]
    strat = strategy(
        team_drivers=[],
        team_constructors=[],
        all_available_drivers=[],
        all_available_constructors=[],
        all_available_driver_pairs={},
        prev_available_driver_pairs={},
        max_cost=0.0,
        max_moves=0,
        prices_assets={},
        derivs_assets={},
        race_num=5,
        season_year=2025,
    )

    assert strategy.__name__ == label
    assert isinstance(strat, StrategyFastF1)
    assert (strat._drs_coefficient, strat._negative_penalty, strat._budget_reward) == settings


def test_max_points_is_selectable_as_a_challenger():
    """StrategyMaxPoints has to be nameable on the command line to be back-tested."""
    args = parse_arguments(["--strategies", "StrategyMaxPoints"])

    assert args.strategies == ["StrategyMaxPoints"]
    assert STRATEGIES[args.strategies[0]] is StrategyMaxPoints


def test_p2pm_no_reset_is_selectable_as_a_challenger():
    """StrategyMaxP2PMNoReset has to be nameable on the command line to be back-tested."""
    args = parse_arguments(["--strategies", "StrategyMaxP2PMNoReset"])

    assert args.strategies == ["StrategyMaxP2PMNoReset"]
    assert STRATEGIES[args.strategies[0]] is StrategyMaxP2PMNoReset


def test_betting_odds_is_selectable_as_a_challenger():
    """StrategyBettingOdds has to be nameable on the command line to be back-tested."""
    args = parse_arguments(["--strategies", "StrategyBettingOdds"])

    assert args.strategies == ["StrategyBettingOdds"]
    assert STRATEGIES[args.strategies[0]] is StrategyBettingOdds


def test_every_option_parses():
    args = parse_arguments([
        "--seasons", "2024", "2026",
        "--sample-size", "20",
        "--seed", "7",
        "--strategies", "StrategyMaxBudget", "StrategyZeroStop",
        "--bands", "95", "100",
        "--output", "out.parquet",
        "--summary", "out.csv",
    ])

    assert args.seasons == [2024, 2026]
    assert args.sample_size == 20
    assert args.seed == 7
    assert args.strategies == ["StrategyMaxBudget", "StrategyZeroStop"]
    assert args.bands == [95.0, 100.0]
    assert (args.output, args.summary) == ("out.parquet", "out.csv")


def test_sample_size_help_says_per_band(capsys):
    with pytest.raises(SystemExit):
        parse_arguments(["--help"])
    assert "per band" in " ".join(capsys.readouterr().out.split())


@pytest.mark.parametrize("argv", [
    [],
    ["--strategies"],
    ["--strategies", "StrategyNotReal"],
    ["--strategies", "StrategyZeroStop", "--seasons", "2019"],
    ["--strategies", "StrategyZeroStop", "--bands", "100", "95"],
    ["--strategies", "StrategyZeroStop", "--bands", "90", "95", "95", "100"],
    ["--strategies", "StrategyZeroStop", "--bands", "100"],
])
def test_invalid_arguments_are_rejected(argv):
    with pytest.raises(SystemExit) as exc:
        parse_arguments(argv)
    assert exc.value.code == 2


def test_main_calls_run_backtest_with_the_parsed_values(monkeypatch):
    calls = []
    monkeypatch.setattr(cli, "run_backtest", lambda *args: calls.append(args))

    main([
        "--seasons", "2024",
        "--sample-size", "20",
        "--seed", "7",
        "--strategies", "StrategyZeroStop", "StrategyMaxBudget",
        "--bands", "95", "99.5", "100",
        "--output", "out.parquet",
        "--summary", "out.csv",
    ])

    assert calls == [(
        [2024], 20, 7, [StrategyZeroStop, StrategyMaxBudget], [95.0, 99.5, 100.0], "out.parquet", "out.csv",
    )]
