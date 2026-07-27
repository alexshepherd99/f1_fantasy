"""FastF1 signal package.

Pulls forward-looking race signal from the FastF1 API: practice-session
lap-time ranks combined with rolling driver points and driver betting odds,
normalised to 0-1 and summed into an ``AggregateRank``. Rolling constructor
points are computed and reported alongside them but carry zero weight in the
aggregate — see ``metrics.METRIC_WEIGHTS``.
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
