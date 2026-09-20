"""Command line entry point for the backtest: `python -m backtest.cli`."""

import argparse
from collections.abc import Sequence

from backtest.runner import run_backtest
from backtest.sample import DEFAULT_BAND_EDGES, validate_band_edges
from common import F1_SEASON_CONSTRUCTORS, setup_logging
from linear.strategy_budget import StrategyMaxBudget
from linear.strategy_max_points import StrategyMaxPoints
from linear.strategy_p2pm import StrategyMaxP2PM
from linear.strategy_zero_stop import StrategyZeroStop

# Seasons run by default. Add a season here once it has finished; one in
# progress is left out unless named with --seasons (R6)
COMPLETED_SEASONS = [2023, 2024, 2025]

# Strategies that can be named with --strategies, by label
STRATEGIES = {s.__name__: s for s in [StrategyMaxP2PM, StrategyZeroStop, StrategyMaxBudget, StrategyMaxPoints]}

DEFAULT_SAMPLE_SIZE = 500
DEFAULT_SEED = 1
DEFAULT_OUTPUT = "outputs/backtest_v1_results.parquet"
DEFAULT_SUMMARY = "outputs/backtest_v1_summary.csv"


def parse_arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse the command line, rejecting unknown strategies and invalid band edges."""
    parser = argparse.ArgumentParser(
        description="Back-test strategies against StrategyMaxP2PM on a sample of starting teams per value band",
    )
    parser.add_argument(
        "--seasons", type=int, nargs="+", default=COMPLETED_SEASONS, choices=sorted(F1_SEASON_CONSTRUCTORS),
        help="seasons to run (default: completed seasons only)",
    )
    parser.add_argument(
        "--sample-size", type=int, default=DEFAULT_SAMPLE_SIZE,
        help="starting teams to sample per band, not per season: 500 over three bands is 1,500 a season",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="sampling seed")
    parser.add_argument(
        "--strategies", nargs="+", required=True, choices=sorted(STRATEGIES),
        help="challengers to compare with StrategyMaxP2PM, which always runs as the baseline",
    )
    parser.add_argument(
        "--bands", type=float, nargs="+", default=list(DEFAULT_BAND_EDGES),
        help="value band edges, each band (min, max] between consecutive edges (default: 90 95 99.5 100)",
    )
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="per-team results parquet, resumed from if present")
    parser.add_argument("--summary", default=DEFAULT_SUMMARY, help="summary CSV; the verdict is written beside it")

    args = parser.parse_args(argv)
    try:
        validate_band_edges(args.bands)
    except ValueError as exc:
        parser.error(str(exc))
    return args


def main(argv: Sequence[str] | None = None) -> None:
    """Parse the command line and run the backtest."""
    args = parse_arguments(argv)
    run_backtest(
        args.seasons,
        args.sample_size,
        args.seed,
        [STRATEGIES[name] for name in args.strategies],
        args.bands,
        args.output,
        args.summary,
    )


if __name__ == "__main__":
    setup_logging()
    main()
