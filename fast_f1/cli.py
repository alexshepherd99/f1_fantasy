from __future__ import annotations

import argparse


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="FastF1 data collection and metric generation")
    parser.add_argument("--season", type=int, help="Season year to process")
    parser.add_argument("--race", type=int, help="Race number to process")
    parser.add_argument("--historical", action="store_true", help="Generate historical metrics for a range of races")
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()
    if args.historical:
        raise NotImplementedError("Historical generation is not implemented yet")
    if args.season is None or args.race is None:
        raise ValueError("Both --season and --race are required for single-race mode")
    raise NotImplementedError("Single-race prediction is not implemented yet")
