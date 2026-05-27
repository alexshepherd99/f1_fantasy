from __future__ import annotations

import logging
from pathlib import Path

from fast_f1.cache import setup_fastf1_cache
from fast_f1.output import generate_historical_metrics
from common import setup_logging


_FILE_FASTF1_METRICS = Path("data/fastf1_practice_rolling_metrics.xlsx")


def load_existing_metrics(file_path: Path) -> None:
    # Legacy script now delegates to fast_f1.output.generate_historical_metrics.
    raise NotImplementedError("Use fast_f1.output.generate_historical_metrics instead")


if __name__ == "__main__":
    setup_logging()
    setup_fastf1_cache()
    generate_historical_metrics(
        season_years=[2023, 2024, 2025],
        race_numbers=[x for x in range(1, 23)],
        output_path=_FILE_FASTF1_METRICS,
    )
