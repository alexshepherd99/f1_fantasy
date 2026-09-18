import pytest

import backtest.cli as cli
from backtest.cli import COMPLETED_SEASONS, STRATEGIES, main, parse_arguments
from backtest.sample import DEFAULT_BAND_EDGES
from linear.strategy_budget import StrategyMaxBudget
from linear.strategy_p2pm import StrategyMaxP2PM
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
    assert STRATEGIES == {
        "StrategyMaxP2PM": StrategyMaxP2PM,
        "StrategyZeroStop": StrategyZeroStop,
        "StrategyMaxBudget": StrategyMaxBudget,
    }


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
