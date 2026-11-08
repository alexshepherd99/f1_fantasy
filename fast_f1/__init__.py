"""FastF1 signal package.

Pulls forward-looking race signal from the FastF1 API: practice-session
lap-time ranks, rolling driver and constructor points and driver betting odds,
each normalised to 0-1. ``AggregateRank`` sums the ones `indicator_analysis_v1`
chose for each weekend format, and odds alone at race 1 — see
``metrics.aggregate_metrics``.
"""

from fast_f1.api import (
    get_available_sessions_from_event,
    get_event_for_race,
    get_event_schedule,
    get_race_numbers_for_season,
    get_race_results,
    get_session_laps,
    select_practice_sessions_from_available,
    select_practice_sessions_from_event,
)
from fast_f1.cache import setup_fastf1_cache
from fast_f1.cli import main as main_cli
from fast_f1.output import (
    DEFAULT_HISTORICAL_OUTPUT,
    generate_historical_metrics,
    generate_single_race_prediction,
)

__all__ = [
    "setup_fastf1_cache",
    "main_cli",
    "get_available_sessions_from_event",
    "select_practice_sessions_from_event",
    "select_practice_sessions_from_available",
    "get_event_for_race",
    "get_event_schedule",
    "get_race_numbers_for_season",
    "get_race_results",
    "get_session_laps",
    "generate_single_race_prediction",
    "generate_historical_metrics",
    "DEFAULT_HISTORICAL_OUTPUT",
]
