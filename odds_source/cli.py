"""Capture race-winner odds from a saved Oddschecker page into the odds file.

Save the race's winner page from the browser into ``outputs/`` as ``.mhtml``,
then run::

    PYTHONPATH=. venv/bin/python -m odds_source.cli

FastF1 places the page in the weekend and names its drivers; the odds land in
``data/f1_betting_odds.csv`` in the column for the last session finished, and in
``Odds``. Review the file's git diff before committing it.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Callable
from pathlib import Path

import pandas as pd

from common import setup_logging
from fast_f1.api import get_event_schedule, get_session_drivers
from fast_f1.auth import F1CredentialsError, load_f1_credentials
from fast_f1.cache import setup_fastf1_cache
from fast_f1.output import DEFAULT_OUTPUT_DIRECTORY
from import_data.odds import _FILE_BETTING_ODDS
from odds_source.drivers import OddsEntry, load_entry_list, match_drivers
from odds_source.odds_file import write_race_odds
from odds_source.page import SavedOddsPage, read_saved_page
from odds_source.schedule import CapturePoint, find_capture_point

logger = logging.getLogger(__name__)

_SAVED_PAGE_SUFFIX = ".mhtml"


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture race-winner odds from a saved Oddschecker page")
    parser.add_argument("page", nargs="?", help=f"Saved page; defaults to the newest {_SAVED_PAGE_SUFFIX} in outputs/")
    parser.add_argument("--odds-file", default=_FILE_BETTING_ODDS, help="Odds file to write into")
    parser.add_argument("--cache-dir", type=str, help="FastF1 cache directory")
    return parser.parse_args()


def newest_saved_page(directory: Path) -> Path | None:
    """The most recently modified saved page in ``directory``, if any."""
    pages = sorted(directory.glob(f"*{_SAVED_PAGE_SUFFIX}"), key=lambda path: path.stat().st_mtime)
    return pages[-1] if pages else None


def _report(page_path: Path, page: SavedOddsPage, point: CapturePoint, entries: list[OddsEntry], odds_file: str) -> None:
    unmatched = [entry.driver for entry in entries if not entry.constructor]
    print(f"{page.race_name}: season {point.season} race {point.race}, column {point.column}")
    print(f"Read {page_path}, saved {page.saved_at:%Y-%m-%d %H:%M} UTC; wrote {len(entries)} drivers to {odds_file}")
    for entry in entries:
        print(f"  {entry.driver:<20} {entry.constructor:<4} {entry.odds}")
    if unmatched:
        print(f"Unmatched, constructor blank, fix by hand: {', '.join(unmatched)}")


def main() -> None:
    args = parse_arguments()
    try:
        load_f1_credentials()
    except F1CredentialsError:
        # already logged with the file path and what is wrong with it
        sys.exit(1)
    setup_fastf1_cache(cache_dir=args.cache_dir, interactive=args.cache_dir is None)

    page_path = Path(args.page) if args.page else newest_saved_page(DEFAULT_OUTPUT_DIRECTORY)
    if page_path is None:
        logger.error("No saved page (%s) in %s; save the race's winner page there first",
                     _SAVED_PAGE_SUFFIX, DEFAULT_OUTPUT_DIRECTORY)
        sys.exit(1)

    try:
        page, point = place_page(page_path)
        write_page_odds(page_path, page, point, args.odds_file)
    except ValueError:
        # already logged with what was wrong; the odds file has not been touched
        sys.exit(1)


def place_page(page_path: Path, schedule_fn: Callable[[int], pd.DataFrame] | None = None
               ) -> tuple[SavedOddsPage, CapturePoint]:
    """Read a saved page and place it in its race weekend.

    Args:
        page_path: The saved page.
        schedule_fn: Gives a season's event schedule; defaults to FastF1's.

    Raises:
        ValueError: If the page cannot be read or placed; already logged.
    """
    page = read_saved_page(page_path)
    return page, find_capture_point(page, (schedule_fn or get_event_schedule)(page.race_start.year))


def write_page_odds(page_path: Path, page: SavedOddsPage, point: CapturePoint, odds_file: str,
                    drivers_fn: Callable[[int, int, str], pd.DataFrame] | None = None) -> list[OddsEntry]:
    """Match a placed page's drivers and write its odds into the odds file, reporting what was written.

    Args:
        page_path: The saved page, for the report.
        page: The page as read.
        point: Where the page sits in its weekend.
        odds_file: The odds file to write into.
        drivers_fn: Gives a session's drivers; defaults to FastF1's.

    Raises:
        ValueError: If the drivers cannot be matched; already logged, and the file is untouched.
    """
    entries = match_drivers(page.prices, load_entry_list(point, fetch=drivers_fn or get_session_drivers))
    write_race_odds(odds_file, point, entries)
    _report(page_path, page, point, entries, odds_file)
    return entries


if __name__ == "__main__":
    setup_logging()
    main()
