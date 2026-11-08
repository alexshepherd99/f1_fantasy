"""Command line entry point for the backtest: `python -m backtest.cli`."""

import argparse
from collections.abc import Sequence

from backtest.runner import run_backtest
from backtest.sample import DEFAULT_BAND_EDGES, validate_band_edges
from backtest.variants import make_variant
from common import F1_SEASON_CONSTRUCTORS, setup_logging
from linear.strategy_budget import StrategyMaxBudget
from linear.strategy_fastf1 import StrategyFastF1
from linear.strategy_max_points import StrategyMaxPoints
from linear.strategy_odds import StrategyBettingOdds
from linear.strategy_p2pm import StrategyMaxP2PM
from linear.strategy_p2pm_no_reset import StrategyMaxP2PMNoReset
from linear.strategy_zero_stop import StrategyZeroStop

# Seasons run by default. Add a season here once it has finished; one in
# progress is left out unless named with --seasons (R6)
COMPLETED_SEASONS = [2023, 2024, 2025]

# fastf1_v2's tuning variants, each one change from StrategyFastF1's defaults, at the values
# fixed in step 15.1 (docs/fastf1_v2/plan.md, step 15; log.md, *Step 15.1*)
FASTF1_VARIANTS = [
    make_variant(StrategyFastF1, "FastF1_Drs0", drs_coefficient=0.0),
    make_variant(StrategyFastF1, "FastF1_Neg6p5", negative_penalty=6.5),
    make_variant(StrategyFastF1, "FastF1_Neg13", negative_penalty=13.0),
    make_variant(StrategyFastF1, "FastF1_Neg26", negative_penalty=26.0),
    make_variant(StrategyFastF1, "FastF1_Bud01", budget_reward=0.1),
    make_variant(StrategyFastF1, "FastF1_Bud025", budget_reward=0.25),
    make_variant(StrategyFastF1, "FastF1_Bud05", budget_reward=0.5),
    # Named for the rules-based rise in step 21, so a resumed run cannot reuse step 16's rows
    # stored under the old table-based labels
    make_variant(StrategyFastF1, "FastF1_RuleRise5", price_rise_reward=5.0),
    make_variant(StrategyFastF1, "FastF1_RuleRise10", price_rise_reward=10.0),
    make_variant(StrategyFastF1, "FastF1_RuleRise20", price_rise_reward=20.0),
    # Lower rewards, continuing the halving from 5, tried on fresh teams in step 23
    make_variant(StrategyFastF1, "FastF1_RuleRise2p5", price_rise_reward=2.5),
    make_variant(StrategyFastF1, "FastF1_RuleRise1p25", price_rise_reward=1.25),
]

# Strategies that can be named with --strategies, by label
STRATEGIES = {
    s.__name__: s
    for s in [
        StrategyMaxP2PM, StrategyZeroStop, StrategyMaxBudget, StrategyMaxPoints, StrategyMaxP2PMNoReset,
        StrategyBettingOdds, StrategyFastF1, *FASTF1_VARIANTS,
    ]
}

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
    parser.add_argument(
        "--last-race", type=int, default=None,
        help="race to stop every season at (default: every priced race); give it a store of its own, "
             "as stored rows are keyed without it and a run to a different race would reuse them",
    )

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
        last_race=args.last_race,
    )


if __name__ == "__main__":
    setup_logging()
    main()
