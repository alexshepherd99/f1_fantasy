"""FastF1 production package skeleton.

The current implementation is intentionally minimal: it preserves the
new package boundary while keeping the legacy ``external_data`` package
untouched. Actual FastF1 wrappers and metric computations will be added
in later steps.
"""

from fast_f1.api import (
    get_available_sessions_from_event,
    get_event_for_race,
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
    "get_race_results",
    "get_session_laps",
    "generate_single_race_prediction",
    "generate_historical_metrics",
    "DEFAULT_HISTORICAL_OUTPUT",
]
