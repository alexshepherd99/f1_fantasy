"""The data a live run collects before picking: BoxBox's prices and points, and saved odds pages (D25, D26).

Each step ends done, not yet, refused or failed. A step never stops the run: the
run carries on and its summary reports each outcome.
"""

from __future__ import annotations

import csv
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from boxbox.change import CaptureNotYet, CaptureRefused
from boxbox.cli import capture
from boxbox.source import BoxBoxDataError
from fast_f1.api import get_event_schedule, get_session_drivers
from fast_f1.auth import load_f1_credentials
from fast_f1.cache import setup_fastf1_cache
from fast_f1.metrics import SIGNAL_SLOTS, add_signal_inputs
from fast_f1.output import build_race_metrics, load_existing_metrics, write_race_metrics
from fast_f1.weekend import unrun_sessions
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
    _sign_in()
    return OddsApi(schedule=get_event_schedule, drivers=get_session_drivers)


def _sign_in() -> None:
    """Load the F1 account and set up FastF1's cache, as `fast_f1.cli` does."""
    load_f1_credentials()
    setup_fastf1_cache(cache_dir=None, interactive=True)


@dataclass(frozen=True)
class FastF1Api:
    """The FastF1 calls the metrics step makes: a season's schedule, and a race's metrics rows."""
    schedule: Callable[[int], pd.DataFrame]
    build: Callable[[int, int], pd.DataFrame]


def collect_fastf1(metrics_file: str, season: int, race: int, now: datetime, api: FastF1Api | None = None,
                   odds_file: str | None = None) -> StepOutcome:
    """Bring the season's FastF1 metrics rows up to the next race (D17, D28).

    Each race before `race` that the file lacks, or holds as built before its results,
    is built whole, as a historical run would build it, and any signal input the rebuild
    changed is printed. Then the next race is built, once the sessions its weekend needs
    have run by the schedule; it is rebuilt every run until it has results. Each race is
    written as soon as it is built, keeping every other line's bytes, and a race that
    fails is stepped over.

    Args:
        metrics_file: The metrics file the strategy reads.
        season: The season.
        race: The next race.
        now: The time to judge the next race's sessions by, timezone-aware.
        api: The FastF1 calls; by default FastF1's own, after signing in.
        odds_file: The odds file the metrics read, when `api` is not given.

    Returns:
        Done with every race built; not yet when the next race's sessions have not all
        run; failed when FastF1 could not be reached or a race could not be built or written.
    """
    step = "FastF1"
    try:
        api = api or _fastf1_metrics_api(odds_file)
        stored = load_existing_metrics(metrics_file)
        events = api.schedule(season)
        event = events[events["RoundNumber"] == race]
        if event.empty:
            return StepOutcome(step, FAILED, f"FastF1's schedule for {season} has no race {race}")
        unrun = unrun_sessions(event.iloc[0], now)
    # FastF1 raises its own errors as well as network ones; any of them fails this step, not the run
    except Exception as exc:
        logger.exception("FastF1 metrics step failed")
        return StepOutcome(step, FAILED, f"FastF1 could not be reached: {exc}")

    season_rows = stored[stored["Season"] == season] if not stored.empty else stored
    to_build = [r for r in range(1, race) if _needs_build(season_rows, r)]
    if not unrun:
        to_build.append(race)

    built, changes, failures = [], [], []
    for r in to_build:
        try:
            rows = api.build(season, r)
            write_race_metrics(rows, metrics_file, season, r)
        # As above: a race that cannot be built is reported and stepped over
        except Exception as exc:
            logger.exception(f"FastF1 metrics for season {season} race {r} failed")
            failures.append(f"race {r}: {exc}")
            continue
        built.append(r)
        old = season_rows[season_rows["Race"] == r] if not season_rows.empty else season_rows
        if not old.empty:
            changed = _signal_changes(old, rows, r)
            for line in changed:
                print(line)
            changes.append(f"race {r}: {len(changed)} signal input{'' if len(changed) == 1 else 's'} changed")

    parts = [f"built race{'' if len(built) == 1 else 's'} {', '.join(map(str, built))}" if built else "built nothing"]
    parts += changes
    if failures:
        return StepOutcome(step, FAILED, "; ".join(parts + [f"could not build {'; '.join(failures)}"]))
    if unrun:
        waiting = ", ".join(f"{code} starts {start:%Y-%m-%d %H:%M} UTC" for code, start in unrun.items())
        return StepOutcome(step, NOT_YET, "; ".join(parts + [f"race {race} waits: {waiting}"]))
    return StepOutcome(step, DONE, "; ".join(parts))


def _needs_build(season_rows: pd.DataFrame, race: int) -> bool:
    """Whether a race of the season is missing from the stored rows, or was stored before its results."""
    if season_rows.empty:
        return True
    rows = season_rows[season_rows["Race"] == race]
    return rows.empty or rows["Points"].isna().all()


# Signal inputs differing by less than this are taken as equal, so a rebuild's float noise is not reported
_CHANGE_TOLERANCE = 1e-12


def _signal_changes(old: pd.DataFrame, new: pd.DataFrame, race: int) -> list[str]:
    """One line per driver added or dropped, and per signal input a rebuild changed.

    The inputs are ``RollingPoints``, which scales the signal, and the slots
    ``SIGNAL_SLOTS`` sums for the race's weekend format.
    """
    columns = old.columns.union(new.columns)
    old_inputs = add_signal_inputs(old.reindex(columns=columns)).set_index("Driver")
    new_inputs = add_signal_inputs(new.reindex(columns=columns)).set_index("Driver")

    lines = [f"Race {race} {driver} dropped" for driver in sorted(set(old_inputs.index) - set(new_inputs.index))]
    lines += [f"Race {race} {driver} added" for driver in sorted(set(new_inputs.index) - set(old_inputs.index))]
    old_format, new_format = old_inputs["format"].iloc[0], new_inputs["format"].iloc[0]
    if old_format != new_format:
        lines.append(f"Race {race} weekend format: {old_format} -> {new_format}")
    inputs = ["RollingPoints", *SIGNAL_SLOTS[new_format]]
    for driver in sorted(set(old_inputs.index) & set(new_inputs.index)):
        for column in inputs:
            before, after = old_inputs.at[driver, column], new_inputs.at[driver, column]
            if pd.isna(before) and pd.isna(after):
                continue
            if pd.isna(before) or pd.isna(after) or abs(float(before) - float(after)) > _CHANGE_TOLERANCE:
                lines.append(f"Race {race} {driver} {column}: {before} -> {after}")
    return lines


def _fastf1_metrics_api(odds_file: str | None) -> FastF1Api:
    """FastF1's calls for the metrics step, after signing in and setting up its cache."""
    _sign_in()
    return FastF1Api(schedule=get_event_schedule,
                     build=lambda season, race: build_race_metrics(season, race, odds_file=odds_file))


def odds_present(odds_file: str, season: int, race: int) -> bool:
    """Whether the odds file holds any `Odds` for the race."""
    with open(odds_file, newline="", encoding="utf-8") as handle:
        return any(row["Season"] == str(season) and row["Race"] == str(race) and row["Odds"]
                   for row in csv.DictReader(handle))
