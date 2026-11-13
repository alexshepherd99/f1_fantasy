"""Pick the live team for the next race (live_picks_v1).

Run before each race, after saving any Oddschecker winner pages into ``outputs/``::

    PYTHONPATH=. venv/bin/python -m live.cli [--chip wildcard|limitless] [--skip-collection]

It first captures BoxBox's points and prices into the archive, every saved odds
page for the next race into the odds file, and the season's FastF1 metrics up to
the next race, once its sessions have run, into the metrics file. It then scores
the last race played once the archive has its points, asks Alex to confirm the
team held, its unused budget and free moves, runs the race's strategies (the
FastF1 strategy only when the metrics file has the race), shows their picks side
by side with prices, and records the pick he chooses in ``data/live_team.csv``.
At race 1 nothing is held or scored: the odds strategy picks the whole team at
each concentration limit, budget 100, and the race's odds are required. Once every
race of the season has points, the run scores the last races played and ends: the
season is over, which is not a refusal. Its prompts need a terminal: if input ends
first, nothing is recorded and the pick is refused, though any picks made are saved.
It ends with a summary of each step, and exits 1 if any was refused or failed.
Review the git diff of every data file it wrote and commit them.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from datetime import datetime, timezone

from boxbox.source import DEFAULT_COPY_DIR
from common import AssetType, setup_logging
from fast_f1.output import DEFAULT_HISTORICAL_OUTPUT, DEFAULT_OUTPUT_DIRECTORY
from helpers import load_with_derivations
from import_data.import_history import _DIR_ARCHIVE_INPUTS, read_archive_file
from import_data.odds import _FILE_BETTING_ODDS
from live.archive import SeasonOver, next_race, race_scored
from live.collect import (
    DONE,
    FAILED,
    REFUSED,
    SKIPPED,
    FastF1Api,
    OddsApi,
    StepOutcome,
    collect_boxbox,
    collect_fastf1,
    collect_odds,
    odds_present,
)
from live.display import default_drs, format_prices, format_table, manual_pick, parse_team
from live.lineup import (
    RACE_1_BUDGET,
    Option,
    add_to_lineup,
    fastf1_strategy,
    has_signal,
    implied_chip,
    run_lineup,
    run_race1_lineup,
    strategies_for,
)
from live.points import predict_points
from live.record import race_metrics_rows, write_record
from live.team_file import (
    AUTOPILOT,
    EXTRA_DRS,
    FINAL_FIX,
    LIMITLESS,
    NO_NEGATIVE,
    NUM_CONSTRUCTORS,
    NUM_DRIVERS,
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
    parser.add_argument("--copy-dir", default=DEFAULT_COPY_DIR, help="where each BoxBox download is saved")
    parser.add_argument("--pages-dir", default=str(DEFAULT_OUTPUT_DIRECTORY), help="where saved odds pages are")
    parser.add_argument("--odds-file", default=_FILE_BETTING_ODDS, help="the odds file to write into")
    parser.add_argument("--metrics-file", default=str(DEFAULT_HISTORICAL_OUTPUT),
                        help="the FastF1 metrics file to write into, which the FastF1 strategy reads")
    parser.add_argument("--skip-collection", action="store_true",
                        help="pick from the data already captured, without BoxBox or the odds pages")
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


def _held_pick(confirmed: Confirmed) -> Pick | None:
    """The team held as a pick to show beside the options, or None when nothing is held, as at race 1."""
    team = confirmed.team
    if not confirmed.assets:
        return None
    return Pick(drivers=tuple(sorted(team.assets[AssetType.DRIVER])),
                constructors=tuple(sorted(team.assets[AssetType.CONSTRUCTOR])), drs_driver="", moves_used=0,
                cost=confirmed.value, unused_budget=team.unused_budget)


def pick_race(args: argparse.Namespace, input_fn: InputFn, season_year: int, race_num: int, drivers_raw,
              run_at: datetime, outcomes: list[StepOutcome]) -> TeamRow | None:
    """Pick for the next race, from scoring the last race to recording the pick; returns the row written, if any.

    How the FastF1 pick went is added to `outcomes`.
    """
    if race_num == 1:
        return pick_race_1(args, input_fn, season_year, run_at)
    chip = CHIP_ARGUMENTS.get(args.chip, "")

    season = factory_season(*load_with_derivations(season_year, args.archive_dir), season_year)
    race, race_prev = season.races[race_num], season.races[race_num - 1]
    print(f"Season {season_year}, race {race_num}")

    rows = _read_rows(args.team_file, season_year, season)
    rows = score_rows(rows, season_year, race_num, season, drivers_raw, args.team_file, input_fn)

    chips_used = {r.chip for r in rows if r.season == season_year and r.race < race_num and r.chip}
    if chip in chips_used:
        raise RunStopped(f"The {chip} is already played in season {season_year}")

    confirmed = confirm_held(rows, season_year, race_num, race, race_prev, input_fn)
    budget = limitless_cap(race) if chip == LIMITLESS else confirmed.budget
    options = run_lineup(strategies_for(race_num, WILDCARD in chips_used), confirmed.team, race, race_prev,
                         season_year, confirmed.free_moves, chip)
    options, fastf1_outcome = _add_fastf1(args.metrics_file, options, confirmed, season_year, race, race_prev, chip)
    outcomes.append(_report(fastf1_outcome))
    print(f"Team value {confirmed.value:.1f}, budget {budget:.1f}, free moves "
          f"{'unlimited' if chip else confirmed.free_moves}{f', {chip}' if chip else ''}")
    print("\n".join(format_table(_held_pick(confirmed),
                                 [(f"{i} {' = '.join(o.strategies)}", o.pick) for i, o in enumerate(options, start=1)],
                                 race, race_prev)))

    held = {"drivers": sorted(confirmed.team.assets[AssetType.DRIVER]),
            "constructors": sorted(confirmed.team.assets[AssetType.CONSTRUCTOR]),
            "unused_budget": confirmed.team.unused_budget, "free_moves": confirmed.free_moves,
            "value": confirmed.value}
    return _choose_and_record(args, run_at, season_year, race, chip, held, options, lambda: choose_row(
        rows, options, confirmed, season_year, race, race_prev, budget, chip, chips_used, input_fn))


def end_season(args: argparse.Namespace, input_fn: InputFn, season_year: int, drivers_raw) -> str:
    """Score the season's rows still without points, once the archive has every race's (D24); returns the outcome.

    No race is left to pick for, which is the season's normal end.
    """
    season = factory_season(*load_with_derivations(season_year, args.archive_dir), season_year)
    rows = _read_rows(args.team_file, season_year, season)
    score_rows(rows, season_year, max(season.races) + 1, season, drivers_raw, args.team_file, input_fn)
    print(f"Season {season_year} is over: every race has points.")
    return f"season {season_year} over, no race left to pick for"


def _read_rows(team_file: str, season_year: int, season: Season) -> list[TeamRow]:
    """The team file's rows, each of `season_year`'s checked against the archive's race."""
    rows = read_team_file(team_file)
    for row in rows:
        if row.season == season_year:
            if row.race not in season.races:
                raise RunStopped(f"The team file has season {season_year} race {row.race}, which the archive lacks")
            check_known(row, season.races[row.race])
    return rows


def pick_race_1(args: argparse.Namespace, input_fn: InputFn, season_year: int, run_at: datetime) -> TeamRow | None:
    """Pick race 1 on betting odds alone, at each concentration limit (D29); returns the row written, if any.

    Nothing is held, so there is no team to confirm and no race to score; the budget is
    `RACE_1_BUDGET` and every move is free.
    """
    if args.chip:
        raise RunStopped(f"Race 1 picks the whole team with every move free, so --chip {args.chip} does nothing there")
    if not odds_present(args.odds_file, season_year, 1):
        raise RunStopped(f"No odds for season {season_year} race 1 in {args.odds_file}: race 1 is picked on them. "
                         f"Save the race's Oddschecker page into {args.pages_dir} and run again.")

    season = factory_season(*load_with_derivations(season_year, args.archive_dir), season_year)
    race = season.races[1]
    print(f"Season {season_year}, race 1: picked on betting odds, budget {RACE_1_BUDGET:.1f}")
    rows = read_team_file(args.team_file)
    for row in rows:
        if row.season == season_year:
            check_known(row, season.races[row.race])

    options = run_race1_lineup(race, season_year, args.odds_file)
    print("\n".join(format_table(None, [(f"{i} {' = '.join(o.strategies)}", o.pick)
                                        for i, o in enumerate(options, start=1)], race, race)))

    nothing_held = Confirmed(team=Team(unused_budget=RACE_1_BUDGET), free_moves=NUM_DRIVERS + NUM_CONSTRUCTORS,
                             value=0.0)
    return _choose_and_record(args, run_at, season_year, race, "", None, options, lambda: choose_row(
        rows, options, nothing_held, season_year, race, race, RACE_1_BUDGET, "", set(), input_fn))


def _choose_and_record(args: argparse.Namespace, run_at: datetime, season_year: int, race: Race, chip: str,
                       held: dict | None, options: list[Option],
                       choose: Callable[[], TeamRow | None]) -> TeamRow | None:
    """Ask for the row to record and write it, if any, then save the run's record whatever happened.

    The record keeps the picks even when choosing ends without an answer, as when input runs out.

    Returns:
        The row written, or None.
    """
    written = None
    try:
        row = choose()
        if row is None:
            print("Nothing recorded.")
        else:
            write_row(args.team_file, row)
            written = row
            print(f"Recorded race {row.race} in {args.team_file}. Review its git diff and commit it.")
    finally:
        path = write_record(args.record_dir, run_at, season_year, race, chip, held, options, written,
                            race_metrics_rows(args.metrics_file, season_year, int(race.race)))
        print(f"Saved this run's picks to {path}")
    return written


def _add_fastf1(metrics_file: str, options: list[Option], confirmed: Confirmed, season_year: int, race: Race,
                race_prev: Race, chip: str) -> tuple[list[Option], StepOutcome]:
    """Add the FastF1 strategy's pick when the race has its signal (D16, D18).

    Returns:
        The line-up, and how the FastF1 pick went: done, skipped without the signal, or
        failed with the error, the other picks kept.
    """
    step = "FastF1 pick"
    race_num = int(race.race)
    try:
        if not has_signal(metrics_file, season_year, race_num):
            return options, StepOutcome(step, SKIPPED, f"no FastF1 signal for season {season_year} race {race_num} "
                                                       f"in {metrics_file}")
        added = add_to_lineup(options, fastf1_strategy(metrics_file), confirmed.team, race, race_prev, season_year,
                              confirmed.free_moves, chip)
    # The signal fails in types that share no useful base; any of them loses only this pick, not the run's
    except Exception as exc:
        logger.exception("FastF1 pick failed")
        return options, StepOutcome(step, FAILED, str(exc))
    return added, StepOutcome(step, DONE, "offered")


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
    # Race 1 picks the whole team, so has no moves to record
    first = race_num == 1
    row = TeamRow(season=season_year, race=race_num, strategy=strategy, chip=chip_played, drivers=pick.drivers,
                  constructors=pick.constructors, drs=drs, free_moves=None if first else confirmed.free_moves,
                  moves_used=None if first else pick.moves_used, team_value=pick.cost,
                  unused_budget=None if chip == LIMITLESS else confirmed.budget - pick.cost,
                  points_predicted=None, points=None)

    existing = [r for r in rows if (r.season, r.race) == (season_year, race_num)]
    if existing and ask(input_fn, f"Race {race_num} already has a row ({existing[0].strategy}); replace it? y/n",
                        "n", lambda a: _one_of(a.lower(), {"y", "n"})) == "n":
        return None
    return row


def main(argv: Sequence[str] | None = None, input_fn: InputFn = input,
         boxbox_fetch: Callable[[str], bytes] | None = None, odds_api: OddsApi | None = None,
         season_constructors: dict[int, int] | None = None, fastf1_api: FastF1Api | None = None) -> int:
    """Run once: collect the week's data, then pick (D25, D26).

    Every step runs whatever the steps before it gave. Returns the exit code: 1 if any step
    was refused or failed, even when a pick was recorded, else 0.
    """
    args = parse_arguments(argv)
    run_at = datetime.now(timezone.utc)
    outcomes: list[StepOutcome] = []
    warnings: list[str] = []

    if args.skip_collection:
        outcomes.append(_report(StepOutcome("BoxBox", SKIPPED, "--skip-collection")))
    else:
        outcomes.append(_report(collect_boxbox(args.archive_dir, args.copy_dir, boxbox_fetch, season_constructors)))

    try:
        drivers_raw = read_archive_file(AssetType.DRIVER, args.archive_dir)
        season_year, race_num = next_race(drivers_raw)
    except SeasonOver as over:
        outcomes.append(_pick_step(lambda: end_season(args, input_fn, over.season, drivers_raw)))
        return _summarise(outcomes, warnings)
    except (ValueError, OSError) as exc:
        outcomes.append(_report(StepOutcome("Pick", REFUSED, f"no next race: {exc}")))
        return _summarise(outcomes, warnings)

    if args.skip_collection:
        outcomes.append(_report(StepOutcome("Odds", SKIPPED, "--skip-collection")))
    else:
        outcomes.append(_report(collect_odds(args.pages_dir, args.odds_file, season_year, race_num, odds_api)))
    if race_num > 1:
        warnings += _odds_warning(args, season_year, race_num)

    if args.skip_collection:
        outcomes.append(_report(StepOutcome("FastF1", SKIPPED, "--skip-collection")))
    elif race_num == 1:
        outcomes.append(_report(StepOutcome("FastF1", SKIPPED, "race 1 is picked on betting odds alone")))
    else:
        outcomes.append(_report(collect_fastf1(args.metrics_file, season_year, race_num, run_at, fastf1_api,
                                               args.odds_file)))

    def pick() -> str:
        written = pick_race(args, input_fn, season_year, race_num, drivers_raw, run_at, outcomes)
        return f"recorded race {race_num}" if written else "nothing recorded"

    outcomes.append(_pick_step(pick))
    return _summarise(outcomes, warnings)


def _pick_step(step: Callable[[], str]) -> StepOutcome:
    """Run the pick step, which returns how it went, as an outcome: refused or failed when it raises."""
    try:
        return StepOutcome("Pick", DONE, step())
    except (RunStopped, TeamFileError, ValueError) as exc:
        logger.error(f"Pick refused: {exc}")
        return StepOutcome("Pick", REFUSED, str(exc))
    except OSError as exc:
        logger.error(f"Pick failed: {exc}")
        return StepOutcome("Pick", FAILED, str(exc))
    # Input ends where stdin is closed, as under Claude Code's ``!``: no answer, so no pick
    except EOFError:
        logger.error("Pick refused: input ended before the prompts were answered")
        return StepOutcome("Pick", REFUSED, "no input")


def _report(outcome: StepOutcome) -> StepOutcome:
    print(_outcome_line(outcome))
    return outcome


def _outcome_line(outcome: StepOutcome) -> str:
    return f"{outcome.step}: {outcome.status} - {outcome.detail}"


def _odds_warning(args: argparse.Namespace, season_year: int, race_num: int) -> list[str]:
    """A loud warning, printed now and returned for the summary, when the race has no odds (D27)."""
    try:
        if odds_present(args.odds_file, season_year, race_num):
            return []
        warning = (f"No odds for season {season_year} race {race_num} in {args.odds_file}. The pick does not "
                   f"need them, but the record of this race's odds has a gap: save the race's Oddschecker page "
                   f"into {args.pages_dir} and run again.")
    except OSError as exc:
        warning = f"Could not read the odds file to check for race {race_num}'s odds: {exc}"
    logger.warning(warning)
    print("\n".join(["!" * 72, f"WARNING: {warning}", "!" * 72]))
    return [warning]


def _summarise(outcomes: list[StepOutcome], warnings: list[str]) -> int:
    print("\n".join(["", "Summary:", *[f"  {_outcome_line(o)}" for o in outcomes],
                     *[f"  WARNING: {w}" for w in warnings]]))
    return 1 if any(o.status in (REFUSED, FAILED) for o in outcomes) else 0


if __name__ == "__main__":
    setup_logging()
    sys.exit(main())
