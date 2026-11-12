"""The data a live run collects before picking: BoxBox's prices and points, and saved odds pages (D25, D26).

Each step ends done, not yet, refused or failed. A step never stops the run: the
run carries on and its summary reports each outcome.
"""

from __future__ import annotations

import csv
import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from boxbox.change import CaptureNotYet, CaptureRefused
from boxbox.cli import capture
from boxbox.source import BoxBoxDataError
from fast_f1.api import get_event_schedule, get_session_drivers
from fast_f1.auth import load_f1_credentials
from fast_f1.cache import setup_fastf1_cache
from odds_source.cli import place_page, write_page_odds

logger = logging.getLogger(__name__)

DONE = "done"
NOT_YET = "not yet"
REFUSED = "refused"
FAILED = "failed"
# A step the run was told to leave out
SKIPPED = "skipped"

SAVED_PAGE_SUFFIX = ".mhtml"


@dataclass(frozen=True)
class StepOutcome:
    """How one step ended, and why."""
    step: str
    status: str
    detail: str


@dataclass(frozen=True)
class OddsApi:
    """The FastF1 calls the odds step makes: a season's schedule, and a session's drivers."""
    schedule: Callable[[int], pd.DataFrame]
    drivers: Callable[[int, int, str], pd.DataFrame]


def collect_boxbox(archive_dir: str, copy_dir: str, fetch: Callable[[str], bytes] | None = None,
                   season_constructors: dict[int, int] | None = None) -> StepOutcome:
    """Capture BoxBox's latest points and prices into the archive, as `boxbox.cli` does.

    Returns:
        Done with the change written; not yet when BoxBox is not updated; refused when the
        change is doubtful or BoxBox's files are not understood; failed on a download or file error.
    """
    step = "BoxBox"
    try:
        change = capture(archive_dir, copy_dir, fetch, season_constructors)
    except CaptureNotYet as exc:
        return StepOutcome(step, NOT_YET, str(exc))
    except (CaptureRefused, BoxBoxDataError) as exc:
        return StepOutcome(step, REFUSED, str(exc))
    except OSError as exc:
        logger.error(f"BoxBox capture failed: {exc}")
        return StepOutcome(step, FAILED, str(exc))
    return StepOutcome(step, DONE, f"{change.mode} season {change.season} race {change.target_race}")


def collect_odds(pages_dir: Path | str, odds_file: str, season: int, race: int,
                 api: OddsApi | None = None) -> StepOutcome:
    """Capture every saved odds page for the race into the odds file, oldest first.

    Pages for other races are skipped with a note. The FastF1 account and cache are set up
    only when there is a page to place, and only when `api` is not given.

    Returns:
        Done with the pages written; not yet when no saved page is for the race; failed when
        a page could not be read, placed or matched, or FastF1 could not be reached.
    """
    step = "Odds"
    paths = sorted(Path(pages_dir).glob(f"*{SAVED_PAGE_SUFFIX}"))
    if not paths:
        return StepOutcome(step, NOT_YET, f"no saved page in {pages_dir}")

    failures, placed = [], []
    try:
        api = api or _fastf1_api()
        for path in paths:
            try:
                page, point = place_page(path, api.schedule)
            except ValueError as exc:
                failures.append(f"{path.name}: {exc}")
                continue
            if (point.season, point.race) != (season, race):
                print(f"Skipped {path.name}: season {point.season} race {point.race}, not the next race")
                continue
            placed.append((page.saved_at, path, page, point))

        written = 0
        for _, path, page, point in sorted(placed, key=lambda item: item[0]):
            try:
                write_page_odds(path, page, point, odds_file, api.drivers)
                written += 1
            except ValueError as exc:
                failures.append(f"{path.name}: {exc}")
    # FastF1 raises its own errors as well as network ones; any of them fails this step, not the run
    except Exception as exc:
        logger.exception("Odds capture failed")
        return StepOutcome(step, FAILED, f"FastF1 could not place the pages: {exc}")

    pages = f"{written} page{'' if written == 1 else 's'} for season {season} race {race} written"
    if failures:
        return StepOutcome(step, FAILED, f"{pages}; could not capture {'; '.join(failures)}")
    if not written:
        return StepOutcome(step, NOT_YET, f"no saved page for season {season} race {race} in {pages_dir}")
    return StepOutcome(step, DONE, pages)


def _fastf1_api() -> OddsApi:
    """FastF1's calls, after signing in and setting up its cache as `odds_source.cli` does."""
    load_f1_credentials()
    setup_fastf1_cache(cache_dir=None, interactive=True)
    return OddsApi(schedule=get_event_schedule, drivers=get_session_drivers)


def odds_present(odds_file: str, season: int, race: int) -> bool:
    """Whether the odds file holds any `Odds` for the race."""
    with open(odds_file, newline="", encoding="utf-8") as handle:
        return any(row["Season"] == str(season) and row["Race"] == str(race) and row["Odds"]
                   for row in csv.DictReader(handle))
