from __future__ import annotations

import argparse
import datetime
import logging
import sys
from pathlib import Path

from fast_f1.cache import setup_fastf1_cache
from fast_f1.output import (
    DEFAULT_HISTORICAL_OUTPUT,
    generate_historical_metrics,
    generate_single_race_prediction,
)

logger = logging.getLogger(__name__)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="FastF1 data collection and metric generation")
    parser.add_argument("--season", type=int, help="Season year to process")
    parser.add_argument("--race", type=int, help="Race number to process")
    parser.add_argument("--historical", action="store_true", help="Generate historical metrics for a range of races")
    parser.add_argument("--cache-dir", type=str, help="FastF1 cache directory")
    parser.add_argument("--output", type=str, help="Output file path")
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()
    setup_fastf1_cache(cache_dir=args.cache_dir, interactive=args.cache_dir is None)

    if args.historical:
        current_year = datetime.datetime.now().year
        season_years = list(range(2023, current_year + 1))
        race_numbers = list(range(1, 23))
        output_path = Path(args.output) if args.output else DEFAULT_HISTORICAL_OUTPUT
        output_arg = str(output_path)

        logger.info("Generating historical metrics for %s seasons", len(season_years))
        generate_historical_metrics(season_years, race_numbers, output_path=output_arg)
        logger.info("Historical metrics generation complete: %s", output_arg)
        return

    if args.season is None or args.race is None:
        if not sys.stdin.isatty():
            raise ValueError("Both --season and --race are required for single-race mode")
        args.season = int(input("Enter season year: ").strip())
        args.race = int(input("Enter race number: ").strip())

    output_path = Path(args.output) if args.output else None
    output_arg = str(output_path) if output_path is not None else None
    path, dataframe = generate_single_race_prediction(args.season, args.race, output_path=output_arg)
    logger.info(
        "Single-race metrics generated for season %s race %s and saved to %s",
        args.season,
        args.race,
        path,
    )
    print(dataframe.head(10).to_string(index=False))
