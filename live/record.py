"""Each run's record: every pick on offer with the race's prices, under `outputs/` (D8)."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import pandas as pd

from fast_f1.output import load_existing_metrics
from live.lineup import Option
from live.team_file import TeamRow
from races.season import Race

logger = logging.getLogger(__name__)


def race_metrics_rows(metrics_file: Path | str, season: int, race: int) -> list[dict]:
    """The race's FastF1 metrics rows, the FastF1 strategy's inputs, with missing values as None.

    A rebuild once the race has results replaces them in the metrics file, so the record
    keeps what the pick saw (D28). Empty when the file has no rows for the race.
    """
    metrics = load_existing_metrics(metrics_file)
    if metrics.empty:
        return []
    rows = metrics[(metrics["Season"] == season) & (metrics["Race"] == race)]
    return [{column: (None if pd.isna(value) else value) for column, value in row.items()}
            for row in rows.to_dict(orient="records")]


def write_record(record_dir: Path | str, run_at: datetime, season: int, race: Race, chip: str, held: dict,
                 options: list[Option], recorded: TeamRow | None, fastf1_metrics: list[dict]) -> Path:
    """Save one run's record as `<season>_<race>_<UTC time>.json` in `record_dir`.

    Args:
        record_dir: The folder, created if missing.
        run_at: When the run started, in UTC.
        season: The season.
        race: The race picked for, whose prices are saved.
        chip: The chip given with `--chip`, or "".
        held: The team held as confirmed: drivers, constructors, unused budget, free moves and value.
        options: Every pick on offer.
        recorded: The row recorded, or None.
        fastf1_metrics: The race's FastF1 metrics rows, from `race_metrics_rows`.

    Returns:
        The file written.
    """
    record = {
        "season": season,
        "race": int(race.race),
        "run_at": run_at.isoformat(),
        "chip": chip,
        "held": held,
        "prices": {**{d: a.price for d, a in race.drivers.items()}, **{c: a.price for c, a in race.constructors.items()}},
        "options": [{"strategies": list(o.strategies), **asdict(o.pick)} for o in options],
        "recorded": None if recorded is None else asdict(recorded),
        "fastf1_metrics": fastf1_metrics,
    }
    path = Path(record_dir) / f"{season}_{race.race}_{run_at:%Y%m%dT%H%M%SZ}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    logger.info(f"Saved this run's picks to {path}")
    return path
