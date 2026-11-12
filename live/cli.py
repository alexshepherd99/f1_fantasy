"""Pick the live team for the next race (live_picks_v1).

Run before each race, once the race's prices are in the archive::

    PYTHONPATH=. venv/bin/python -m live.cli [--chip wildcard|limitless]

It scores the last race played once the archive has its points, asks Alex to
confirm the team held, its unused budget and free moves, runs the race's
strategies, shows their picks side by side with prices, and records the pick
he chooses in ``data/live_team.csv``. Review that file's git diff and commit it.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from datetime import datetime, timezone

from common import AssetType, setup_logging
from helpers import load_with_derivations
from import_data.import_history import _DIR_ARCHIVE_INPUTS, read_archive_file
from live.archive import next_race, race_scored
from live.display import default_drs, format_prices, format_table, manual_pick, parse_team
from live.lineup import Option, implied_chip, run_lineup, strategies_for
from live.points import predict_points
from live.record import write_record
from live.team_file import (
    AUTOPILOT,
    EXTRA_DRS,
    FINAL_FIX,
    LIMITLESS,
    NO_NEGATIVE,
    TEAM_FILE,
    WILDCARD,
    TeamFileError,
    TeamRow,
    check_known,
    held_for,
    read_team_file,
    write_row,
)
from races.season import Race, Season, factory_season
from races.team import Team
from simulate.pick import Pick, limitless_cap

logger = logging.getLogger(__name__)

DEFAULT_RECORD_DIR = "outputs/live_picks"
CHIP_ARGUMENTS = {"wildcard": WILDCARD, "limitless": LIMITLESS}
# The chips chosen at the prompt; Wildcard and Limitless change the picks, so come from --chip
PROMPT_CHIPS = (EXTRA_DRS, NO_NEGATIVE, AUTOPILOT, FINAL_FIX)
MANUAL = "Manual"

InputFn = Callable[[str], str]


class RunStopped(Exception):
    """The run cannot go on; the message says why."""


@dataclass(frozen=True)
class Confirmed:
    """The team held going into the race, as Alex confirmed it (D12)."""
    team: Team
    free_moves: int
    value: float

    @property
    def assets(self) -> tuple[str, ...]:
        return tuple(self.team.assets[AssetType.DRIVER]) + tuple(self.team.assets[AssetType.CONSTRUCTOR])

    @property
    def budget(self) -> float:
        return self.value + self.team.unused_budget


def parse_arguments(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pick the live team for the next race")
    parser.add_argument("--chip", choices=sorted(CHIP_ARGUMENTS), help="play the Wildcard or Limitless")
    parser.add_argument("--team-file", default=TEAM_FILE, help="the team file")
    parser.add_argument("--archive-dir", default=_DIR_ARCHIVE_INPUTS, help="directory holding the archive CSVs")
    parser.add_argument("--record-dir", default=DEFAULT_RECORD_DIR, help="where each run's record is saved")
    return parser.parse_args(argv)


def ask(input_fn: InputFn, prompt: str, default: str | None, parse: Callable[[str], object]):
    """Ask until `parse` accepts the answer; Enter gives `default`, when there is one."""
    shown = f"{prompt}: " if default is None else f"{prompt} [{default}]: "
    while True:
        answer = input_fn(shown).strip()
        if not answer and default is not None:
            answer = default
        try:
            return parse(answer)
        except ValueError as exc:
            print(f"  {exc}")


def _one_of(answer: str, allowed) -> str:
    if answer not in allowed:
        raise ValueError(f"{answer or 'Nothing'} is not one of {', '.join(sorted(allowed))}")
    return answer


def _whole(answer: str) -> int:
    value = int(answer)
    if value < 0:
        raise ValueError(f"{value} is below 0")
    return value


def ask_team(input_fn: InputFn, label: str, defaults: tuple[tuple[str, ...], tuple[str, ...]] | None,
             known_drivers: set[str], known_constructors: set[str]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Ask for drivers and constructors until they make a team of known identifiers."""
    while True:
        drivers = ask(input_fn, f"{label} drivers", ",".join(defaults[0]) if defaults else None, str)
        constructors = ask(input_fn, f"{label} constructors", ",".join(defaults[1]) if defaults else None, str)
        try:
            return parse_team(drivers, constructors, known_drivers, known_constructors)
        except ValueError as exc:
            print(f"  {exc}")


def score_rows(rows: list[TeamRow], season_year: int, race_num: int, season: Season, drivers_raw,
               team_file: str, input_fn: InputFn) -> list[TeamRow]:
    """Score each row of the season before `race_num` with no points, once the archive has its race's (D24)."""
    for row in rows:
        if row.season != season_year or row.race >= race_num or row.points is not None:
            continue
        if not race_scored(drivers_raw, season_year, row.race):
            continue
        race = season.races[row.race]
        final_fix = None
        if row.chip == FINAL_FIX:
            out = ask(input_fn, f"Race {row.race} Final Fix: driver swapped out", None,
                      lambda a: _one_of(a, set(row.drivers)))
            swapped_in = ask(input_fn, f"Race {row.race} Final Fix: driver swapped in", None,
                             lambda a: _one_of(a, set(race.drivers) - set(row.drivers)))
            final_fix = (out, swapped_in)
        predicted = predict_points(row, race, final_fix)
        default = str(predicted)
        if row.chip == NO_NEGATIVE:
            print(f"Race {row.race} played No Negative, which the prediction leaves out: type the app's figure.")
            default = None
        points = ask(input_fn, f"Race {row.race} points: the archive gives {predicted}; the app's figure", default, int)
        write_row(team_file, replace(row, points_predicted=predicted, points=points))
    return read_team_file(team_file)


def confirm_held(rows: list[TeamRow], season_year: int, race_num: int, race: Race, race_prev: Race,
                 input_fn: InputFn) -> Confirmed:
    """Ask Alex to confirm the team held, its unused budget and its free moves (D12, D21)."""
    before = [r for r in rows if r.season == season_year and r.race < race_num]
    if before:
        held = held_for(rows, season_year, race_num)
        defaults = (held.drivers, held.constructors)
        unused, free_moves = f"{held.unused_budget:.1f}", str(held.free_moves)
        if held.last_race < race_num - 1:
            print(f"No row for races {held.last_race + 1} to {race_num - 1}: "
                  f"the defaults come from race {held.last_race}.")
    else:
        print(f"Season {season_year} has no row before race {race_num}: enter the team held.")
        defaults, unused, free_moves = None, None, None

    drivers, constructors = ask_team(input_fn, "Held", defaults, set(race.drivers) | set(race_prev.drivers),
                                     set(race.constructors))
    team = Team(unused_budget=ask(input_fn, "Unused budget", unused, float))
    for d in drivers:
        team.add_asset(AssetType.DRIVER, d)
    for c in constructors:
        team.add_asset(AssetType.CONSTRUCTOR, c)
    moves = ask(input_fn, "Free moves", free_moves, _whole)
    return Confirmed(team=team, free_moves=moves, value=team.total_value(race, race_prev))


def choose(options: list[Option], confirmed: Confirmed, race: Race, race_prev: Race, budget: float, chip: str,
           input_fn: InputFn) -> tuple[str, Pick] | None:
    """Ask Alex to choose an option or type a team (D23). None records nothing."""
    choices = {str(i): option for i, option in enumerate(options, start=1)}
    answer = ask(input_fn, f"Pick 1-{len(options)}, m to type a team, x to record nothing", "1",
                 lambda a: _one_of(a.lower(), set(choices) | {"m", "x"}))
    if answer == "x":
        return None
    if answer in choices:
        return choices[answer].strategies[0], choices[answer].pick

    print("\n".join(["Prices:", *format_prices(race)]))
    while True:
        drivers, constructors = ask_team(input_fn, "Your", None, set(race.drivers), set(race.constructors))
        pick = manual_pick(drivers, constructors, default_drs(drivers, race), confirmed.assets, race, budget)
        print("\n".join(format_table(_held_pick(confirmed), [(MANUAL, pick)], race, race_prev)))
        if pick.unused_budget < -1e-6:
            print(f"  That team costs {pick.cost:.1f}, over the budget of {budget:.1f}.")
            continue
        if not chip and pick.moves_used > confirmed.free_moves:
            print(f"  {pick.moves_used} moves with {confirmed.free_moves} free: the app takes points for the rest.")
        return MANUAL, pick


def choose_chip(strategy: str, race_num: int, chip: str, chips_used: set[str], input_fn: InputFn) -> str:
    """The chip played: `--chip`'s, the one the strategy plays itself, or one asked for (D19)."""
    if chip:
        return chip
    if implied_chip(strategy, race_num):
        print(f"{strategy} plays the {implied_chip(strategy, race_num)} at race {race_num}.")
        return implied_chip(strategy, race_num)
    offered = [c for c in PROMPT_CHIPS if c not in chips_used]
    by_name = {c.lower(): c for c in offered} | {"none": ""}
    return by_name[ask(input_fn, f"Chip ({', '.join(offered)}, or none)", "none",
                       lambda a: _one_of(a.lower(), set(by_name)))]


def _held_pick(confirmed: Confirmed) -> Pick:
    team = confirmed.team
    return Pick(drivers=tuple(sorted(team.assets[AssetType.DRIVER])),
                constructors=tuple(sorted(team.assets[AssetType.CONSTRUCTOR])), drs_driver="", moves_used=0,
                cost=confirmed.value, unused_budget=team.unused_budget)


def run(args: argparse.Namespace, input_fn: InputFn) -> None:
    """One run, from scoring the last race to recording the pick."""
    run_at = datetime.now(timezone.utc)
    drivers_raw = read_archive_file(AssetType.DRIVER, args.archive_dir)
    season_year, race_num = next_race(drivers_raw)
    if race_num == 1:
        raise RunStopped(f"Season {season_year}'s next race is race 1, which race-1 mode picks; it is not built yet")
    chip = CHIP_ARGUMENTS.get(args.chip, "")

    season = factory_season(*load_with_derivations(season_year, args.archive_dir), season_year)
    race, race_prev = season.races[race_num], season.races[race_num - 1]
    print(f"Season {season_year}, race {race_num}")

    rows = read_team_file(args.team_file)
    for row in rows:
        if row.season == season_year:
            if row.race not in season.races:
                raise RunStopped(f"The team file has season {season_year} race {row.race}, which the archive lacks")
            check_known(row, season.races[row.race])
    rows = score_rows(rows, season_year, race_num, season, drivers_raw, args.team_file, input_fn)

    chips_used = {r.chip for r in rows if r.season == season_year and r.race < race_num and r.chip}
    if chip in chips_used:
        raise RunStopped(f"The {chip} is already played in season {season_year}")

    confirmed = confirm_held(rows, season_year, race_num, race, race_prev, input_fn)
    budget = limitless_cap(race) if chip == LIMITLESS else confirmed.budget
    options = run_lineup(strategies_for(race_num, WILDCARD in chips_used), confirmed.team, race, race_prev,
                         season_year, confirmed.free_moves, chip)
    options = [Option(o.strategies, replace(o.pick, drs_driver=o.pick.drs_driver or default_drs(o.pick.drivers, race)))
               for o in options]
    print(f"Team value {confirmed.value:.1f}, budget {budget:.1f}, free moves "
          f"{'unlimited' if chip else confirmed.free_moves}{f', {chip}' if chip else ''}")
    print("\n".join(format_table(_held_pick(confirmed),
                                 [(f"{i} {' = '.join(o.strategies)}", o.pick) for i, o in enumerate(options, start=1)],
                                 race, race_prev)))

    row = choose_row(rows, options, confirmed, season_year, race, race_prev, budget, chip, chips_used, input_fn)
    written = None
    try:
        if row is None:
            print("Nothing recorded.")
        else:
            write_row(args.team_file, row)
            written = row
            print(f"Recorded race {race_num} in {args.team_file}. Review its git diff and commit it.")
    finally:
        held = {"drivers": sorted(confirmed.team.assets[AssetType.DRIVER]),
                "constructors": sorted(confirmed.team.assets[AssetType.CONSTRUCTOR]),
                "unused_budget": confirmed.team.unused_budget, "free_moves": confirmed.free_moves,
                "value": confirmed.value}
        path = write_record(args.record_dir, run_at, season_year, race, chip, held, options, written)
        print(f"Saved this run's picks to {path}")


def choose_row(rows: list[TeamRow], options: list[Option], confirmed: Confirmed, season_year: int, race: Race,
               race_prev: Race, budget: float, chip: str, chips_used: set[str], input_fn: InputFn) -> TeamRow | None:
    """The row Alex chooses to record, with its DRS driver and chip, or None to record nothing."""
    race_num = int(race.race)
    chosen = choose(options, confirmed, race, race_prev, budget, chip, input_fn)
    if chosen is None:
        return None
    strategy, pick = chosen
    drs = ask(input_fn, "DRS driver", pick.drs_driver, lambda a: _one_of(a, set(pick.drivers)))
    chip_played = choose_chip(strategy, race_num, chip, chips_used, input_fn)
    row = TeamRow(season=season_year, race=race_num, strategy=strategy, chip=chip_played, drivers=pick.drivers,
                  constructors=pick.constructors, drs=drs, free_moves=confirmed.free_moves,
                  moves_used=pick.moves_used, team_value=pick.cost,
                  unused_budget=None if chip == LIMITLESS else confirmed.budget - pick.cost,
                  points_predicted=None, points=None)

    existing = [r for r in rows if (r.season, r.race) == (season_year, race_num)]
    if existing and ask(input_fn, f"Race {race_num} already has a row ({existing[0].strategy}); replace it? y/n",
                        "n", lambda a: _one_of(a.lower(), {"y", "n"})) == "n":
        return None
    return row


def main(argv: Sequence[str] | None = None, input_fn: InputFn = input) -> int:
    """Run once. Returns the exit code: 0 done, 1 refused or failed."""
    args = parse_arguments(argv)
    try:
        run(args, input_fn)
    except (RunStopped, TeamFileError, ValueError, OSError) as exc:
        logger.error(f"Stopped: {exc}")
        print(f"Stopped: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    setup_logging()
    sys.exit(main())
