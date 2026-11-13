"""The live team file, `data/live_team.csv`: one row per race played (live_picks_v1 D9).

The file is read and written as text with the `csv` module, never through pandas,
so a row a run does not touch is written back exactly as it was.
"""

from __future__ import annotations

import csv
import logging
import os
from dataclasses import dataclass
from pathlib import Path

from races.season import Race
from simulate.pick import next_free_moves

logger = logging.getLogger(__name__)

TEAM_FILE = "data/live_team.csv"

WILDCARD = "Wildcard"
LIMITLESS = "Limitless"
EXTRA_DRS = "Extra DRS"
NO_NEGATIVE = "No Negative"
AUTOPILOT = "Autopilot"
FINAL_FIX = "Final Fix"
CHIPS = (WILDCARD, LIMITLESS, EXTRA_DRS, NO_NEGATIVE, AUTOPILOT, FINAL_FIX)

NUM_DRIVERS = 5
NUM_CONSTRUCTORS = 2
# Race 1 picks the whole team, so race 2 starts on the game's free moves, with none carried
RACE_2_FREE_MOVES = 2
DRIVER_COLUMNS = [f"D{i}" for i in range(1, NUM_DRIVERS + 1)]
CONSTRUCTOR_COLUMNS = [f"C{i}" for i in range(1, NUM_CONSTRUCTORS + 1)]
COLUMNS = ["Season", "Race", "Strategy", "Chip", *DRIVER_COLUMNS, *CONSTRUCTOR_COLUMNS, "DRS", "FreeMoves",
           "MovesUsed", "TeamValue", "UnusedBudget", "PointsPredicted", "Points"]


class TeamFileError(ValueError):
    """The team file, or a row for it, breaks one of its rules."""


@dataclass(frozen=True)
class TeamRow:
    """One race played.

    Attributes:
        season: The season.
        race: The race number.
        strategy: The strategy's class name, `StrategyBettingOdds:<limit>` at race 1, or `Manual`.
        chip: The chip played, one of `CHIPS`, or "" for none.
        drivers: The drivers, sorted.
        constructors: The constructors, sorted.
        drs: The DRS driver, one of `drivers`.
        free_moves: The free moves available this race; None at race 1, where the whole team is picked.
        moves_used: The moves made from the team held into this one; None at race 1.
        team_value: The team's value at this race's prices.
        unused_budget: The budget left after the pick; None after Limitless, whose budget never carries.
        points_predicted: The points the archive gives the team, once scored.
        points: The app's points, which count; once filled the row is final.
    """
    season: int
    race: int
    strategy: str
    chip: str
    drivers: tuple[str, ...]
    constructors: tuple[str, ...]
    drs: str
    free_moves: int | None
    moves_used: int | None
    team_value: float
    unused_budget: float | None
    points_predicted: int | None
    points: int | None


@dataclass(frozen=True)
class Held:
    """The team going into a race, as the file gives it; Alex confirms or corrects each figure (D12).

    Attributes:
        drivers: The drivers held, sorted.
        constructors: The constructors held, sorted.
        unused_budget: The budget left over.
        free_moves: The free moves for the race.
        team_race: The race whose row the team and budget come from.
        last_race: The last race with a row, which the free moves come from.
    """
    drivers: tuple[str, ...]
    constructors: tuple[str, ...]
    unused_budget: float
    free_moves: int
    team_race: int
    last_race: int


def held_for(rows: list[TeamRow], season: int, race: int) -> Held:
    """Work out the team held going into `race` from the season's rows before it (D21).

    The team and unused budget come from the last row without Limitless, as the app puts the
    team back after it. The free moves come from the last row: after race 1, where the whole
    team was picked, `RACE_2_FREE_MOVES`; a chip race passes on the free moves it had; and
    otherwise fewer than 2 moves used gives 3, else 2. A row for `race` itself, from an
    earlier run before the race, is ignored.

    Raises:
        TeamFileError: If the season has a row after `race`, or no row before it without Limitless.
    """
    season_rows = [r for r in rows if r.season == season]
    after = [r.race for r in season_rows if r.race > race]
    if after:
        _fail(f"Season {season} has rows for races {after}, after race {race}")
    before = [r for r in season_rows if r.race < race]
    team_rows = [r for r in before if r.chip != LIMITLESS]
    if not team_rows:
        _fail(f"Season {season} has no row before race {race} without Limitless to take the team from")

    last, team = before[-1], team_rows[-1]
    if last.race == 1:
        free_moves = RACE_2_FREE_MOVES
    elif last.chip in (WILDCARD, LIMITLESS):
        free_moves = last.free_moves
    else:
        free_moves = next_free_moves(last.moves_used)
    return Held(drivers=team.drivers, constructors=team.constructors, unused_budget=team.unused_budget,
                free_moves=free_moves, team_race=team.race, last_race=last.race)


def read_team_file(path: Path | str) -> list[TeamRow]:
    """Read and check the team file.

    Args:
        path: The file. A file that does not exist yet holds no rows.

    Returns:
        The rows, in file order.

    Raises:
        TeamFileError: If the file breaks one of its rules.
    """
    path = Path(path)
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        lines = list(csv.reader(handle))
    if not lines or lines[0] != COLUMNS:
        _fail(f"{path}: header is not {','.join(COLUMNS)}")
    rows = [_parse(fields, f"{path} line {i}") for i, fields in enumerate(lines[1:], start=2)]
    _check_rows(rows, str(path))
    return rows


def write_row(path: Path | str, row: TeamRow) -> None:
    """Put `row` into the team file, replacing the row for its race or adding it in race order.

    Every other line keeps its bytes. Money is written to one decimal place, as the app shows it.
    The file is created with its header if it does not exist yet.

    Raises:
        TeamFileError: If the race's row is final (its points are filled), or the file with
            `row` in it would break one of its rules. The file is then left as it was.
    """
    path = Path(path)
    body = []
    if path.exists():
        read_team_file(path)
        with path.open(newline="", encoding="utf-8") as handle:
            body = list(csv.reader(handle))[1:]

    key = (row.season, row.race)
    keys = [(int(fields[0]), int(fields[1])) for fields in body]
    fields = _fields(row)
    if key in keys:
        at = keys.index(key)
        if body[at][COLUMNS.index("Points")] != "":
            _fail(f"{path}: season {row.season} race {row.race} has its points, so its row is final")
        body[at] = fields
    else:
        at = next((i for i, k in enumerate(keys) if k > key), len(body))
        body.insert(at, fields)

    rows = [_parse(f, f"{path} line {i}") for i, f in enumerate(body, start=2)]
    _check_rows(rows, str(path))

    temporary = path.with_name(f".{path.name}.tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(COLUMNS)
        writer.writerows(body)
    os.replace(temporary, path)
    logger.info(f"Wrote season {row.season} race {row.race} into {path}")


def _money(value: float | None) -> str:
    return "" if value is None else f"{value:.1f}"


def _optional(value: int | None) -> str:
    return "" if value is None else str(value)


def _fields(row: TeamRow) -> list[str]:
    return [str(row.season), str(row.race), row.strategy, row.chip, *row.drivers, *row.constructors, row.drs,
            _optional(row.free_moves), _optional(row.moves_used), _money(row.team_value), _money(row.unused_budget),
            _optional(row.points_predicted), _optional(row.points)]


def _fail(message: str) -> None:
    logger.error(message)
    raise TeamFileError(message)


def _int(value: str, column: str, where: str) -> int:
    try:
        return int(value)
    except ValueError:
        _fail(f"{where}: {column} {value!r} is not a whole number")


def _float(value: str, column: str, where: str) -> float:
    try:
        return float(value)
    except ValueError:
        _fail(f"{where}: {column} {value!r} is not a number")


def _parse(fields: list[str], where: str) -> TeamRow:
    if len(fields) != len(COLUMNS):
        _fail(f"{where}: {len(fields)} fields, not {len(COLUMNS)}")
    value = dict(zip(COLUMNS, fields))
    row = TeamRow(
        season=_int(value["Season"], "Season", where),
        race=_int(value["Race"], "Race", where),
        strategy=value["Strategy"],
        chip=value["Chip"],
        drivers=tuple(value[c] for c in DRIVER_COLUMNS),
        constructors=tuple(value[c] for c in CONSTRUCTOR_COLUMNS),
        drs=value["DRS"],
        free_moves=None if value["FreeMoves"] == "" else _int(value["FreeMoves"], "FreeMoves", where),
        moves_used=None if value["MovesUsed"] == "" else _int(value["MovesUsed"], "MovesUsed", where),
        team_value=_float(value["TeamValue"], "TeamValue", where),
        unused_budget=None if value["UnusedBudget"] == "" else _float(value["UnusedBudget"], "UnusedBudget", where),
        points_predicted=None if value["PointsPredicted"] == "" else _int(value["PointsPredicted"], "PointsPredicted",
                                                                           where),
        points=None if value["Points"] == "" else _int(value["Points"], "Points", where),
    )
    check_row(row, where)
    return row


def check_row(row: TeamRow, where: str = "row") -> None:
    """Check the rules one row must keep on its own, raising `TeamFileError` if it breaks one."""
    if not row.strategy:
        _fail(f"{where}: Strategy is empty")
    if row.chip and row.chip not in CHIPS:
        _fail(f"{where}: chip {row.chip!r} is not one of {', '.join(CHIPS)}")
    _check_assets(row.drivers, NUM_DRIVERS, "drivers", where, lambda d: "@" in d)
    _check_assets(row.constructors, NUM_CONSTRUCTORS, "constructors", where, lambda c: "@" not in c)
    if row.drs not in row.drivers:
        _fail(f"{where}: DRS {row.drs!r} is not one of the drivers")
    if (row.unused_budget is None) != (row.chip == LIMITLESS):
        _fail(f"{where}: UnusedBudget must be blank after Limitless and only then")
    if (row.free_moves is None, row.moves_used is None) != (row.race == 1, row.race == 1):
        _fail(f"{where}: FreeMoves and MovesUsed must be blank at race 1, where the whole team is picked, "
              f"and only there")


def check_known(row: TeamRow, race: Race) -> None:
    """Check that every driver and constructor in `row` is in `race`, its race in the archive.

    Raises:
        TeamFileError: Naming the identifiers the race does not have.
    """
    unknown = [d for d in row.drivers if d not in race.drivers]
    unknown += [c for c in row.constructors if c not in race.constructors]
    if unknown:
        _fail(f"Season {row.season} race {row.race}: {', '.join(unknown)} not in the race")


def _check_assets(assets: tuple[str, ...], count: int, kind: str, where: str, well_formed) -> None:
    if len(assets) != count or not all(assets) or not all(well_formed(a) for a in assets):
        _fail(f"{where}: {kind} {assets} are not {count} identifiers")
    if list(assets) != sorted(set(assets)):
        _fail(f"{where}: {kind} {assets} are not sorted and distinct")


def _check_rows(rows: list[TeamRow], where: str) -> None:
    """Check the rules between rows: races in order, once each, and each chip once a season."""
    for before, after in zip(rows, rows[1:]):
        if (before.season, before.race) >= (after.season, after.race):
            _fail(f"{where}: season {after.season} race {after.race} is out of order or repeated")
    played = set()
    for row in rows:
        if row.chip:
            if (row.season, row.chip) in played:
                _fail(f"{where}: {row.chip} is played twice in season {row.season}")
            played.add((row.season, row.chip))
