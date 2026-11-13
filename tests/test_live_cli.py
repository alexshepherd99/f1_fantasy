"""The live script end to end, on an archive cut from 2023 and a team file in a temporary folder."""

import json
from dataclasses import replace

import pandas as pd
import pytest

from common import AssetType
from helpers import load_with_derivations
from linear.strategy_p2pm import StrategyMaxP2PM
from live.cli import main
from live.collect import FastF1Api
from live.lineup import fastf1_strategy, run_lineup, run_race1_lineup
from live.points import predict_points
from live.team_file import TeamRow, read_team_file, write_row
from races.season import factory_season
from races.team import Team
from simulate.pick import limitless_cap, next_free_moves, solve_race
from tests.live_archive import SEASON, write_archive

HELD_DRIVERS = ("ALO@AST", "HUL@HAA", "NOR@MCL", "PIA@MCL", "TSU@ALT")
HELD_CONSTRUCTORS = ("AST", "HAA")
HELD_TEXT = ("ALO@AST, HUL@HAA,NOR@MCL,PIA@MCL,TSU@ALT", "HAA,AST")
UNUSED = 50.0


class Inputs:
    """Answers each prompt in turn, keeping the prompts asked."""

    def __init__(self, *answers: str):
        self.answers = list(answers)
        self.prompts: list[str] = []

    def __call__(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.answers.pop(0)


class EndingInputs(Inputs):
    """Answers each prompt in turn, then ends input as a closed stdin does."""

    def __call__(self, prompt: str) -> str:
        if not self.answers:
            self.prompts.append(prompt)
            raise EOFError
        return super().__call__(prompt)


@pytest.fixture
def world(tmp_path):
    """Paths for a run whose next race is 2023 race 6."""
    return _world(tmp_path, next_race=6)


ODDS_HEADER = "Driver,Constructor,Season,Race,Odds\n"


METRICS_HEADER = ("Season,Race,Driver,Points,RollingPoints,RollingPointsRank,ConstructorRollingPointsRank,"
                  "FP2_MinLapTime_rank,FP3_MinLapTime_rank,SQ_MinLapTime_rank,FP1_MinLapTime_rank,OddsRank,"
                  "AggregateRank\n")
RACE_6_METRICS = f"{SEASON},6,VER,,60.0,1.0,1.0,0.9,0.8,,,0.0,2.7\n"


def _world(tmp_path, next_race: int, odds: str = f"VER,RED,{SEASON},6,5-4\n", metrics: str = "") -> dict:
    archive = tmp_path / "archive"
    archive.mkdir()
    write_archive(archive, last_race=next_race, unscored=(next_race,))
    (tmp_path / "pages").mkdir()
    (tmp_path / "odds.csv").write_text(ODDS_HEADER + odds)
    (tmp_path / "metrics.csv").write_text(METRICS_HEADER + metrics)
    return {"archive": archive, "team_file": tmp_path / "live_team.csv", "records": tmp_path / "records",
            "pages": tmp_path / "pages", "odds": tmp_path / "odds.csv", "copies": tmp_path / "copies",
            "metrics": tmp_path / "metrics.csv"}


def _unreachable(season):
    raise ConnectionError("no network")


def _run(world, inputs: Inputs, *extra: str, collect: bool = False, **injected) -> int:
    injected.setdefault("fastf1_api", FastF1Api(schedule=_unreachable, build=None))
    return main(["--team-file", str(world["team_file"]), "--archive-dir", str(world["archive"]),
                 "--record-dir", str(world["records"]), "--pages-dir", str(world["pages"]),
                 "--odds-file", str(world["odds"]), "--copy-dir", str(world["copies"]),
                 "--metrics-file", str(world["metrics"]),
                 *([] if collect else ["--skip-collection"]), *extra], input_fn=inputs, **injected)


def _season(world):
    return factory_season(*load_with_derivations(SEASON, str(world["archive"])), SEASON)


def _team(drivers=HELD_DRIVERS, constructors=HELD_CONSTRUCTORS, unused_budget=UNUSED) -> Team:
    team = Team(unused_budget=unused_budget)
    for d in drivers:
        team.add_asset(AssetType.DRIVER, d)
    for c in constructors:
        team.add_asset(AssetType.CONSTRUCTOR, c)
    return team


def _row(race: int, chip: str = "", points: int | None = None, moves_used: int = 1) -> TeamRow:
    return TeamRow(season=SEASON, race=race, strategy="StrategyMaxP2PM", chip=chip, drivers=HELD_DRIVERS,
                   constructors=HELD_CONSTRUCTORS, drs="NOR@MCL", free_moves=2, moves_used=moves_used,
                   team_value=47.9, unused_budget=UNUSED, points_predicted=points, points=points)


def test_a_season_with_no_row_asks_for_the_team_and_records_p2pms_pick(world):
    inputs = Inputs(*HELD_TEXT, "50.0", "2", "", "", "")

    assert _run(world, inputs) == 0

    season = _season(world)
    race, race_prev = season.races[6], season.races[5]
    pick = solve_race(StrategyMaxP2PM, _team(), race, race_prev, SEASON, max_moves=2)
    budget = _team().total_budget(race, race_prev)
    assert read_team_file(world["team_file"]) == [TeamRow(
        season=SEASON, race=6, strategy="StrategyMaxP2PM", chip="", drivers=pick.drivers,
        constructors=pick.constructors, drs=pick.drs_driver or max(pick.drivers, key=lambda d: race.drivers[d].price),
        free_moves=2, moves_used=pick.moves_used, team_value=round(pick.cost, 1),
        unused_budget=round(budget - pick.cost, 1), points_predicted=None, points=None)]
    assert inputs.prompts[0] == "Held drivers: "


def test_scores_the_last_race_and_offers_the_files_figures_as_defaults(world):
    write_row(world["team_file"], _row(5, moves_used=2))
    inputs = Inputs("", "", "", "", "", "x")

    assert _run(world, inputs) == 0

    predicted = predict_points(_row(5), _season(world).races[5])
    assert read_team_file(world["team_file"]) == [_row(5, moves_used=2, points=predicted)]
    assert inputs.prompts[0] == f"Race 5 points: the archive gives {predicted}; the app's figure [{predicted}]: "
    assert inputs.prompts[1:5] == ["Held drivers [ALO@AST,HUL@HAA,NOR@MCL,PIA@MCL,TSU@ALT]: ",
                                   "Held constructors [AST,HAA]: ", "Unused budget [50.0]: ",
                                   f"Free moves [{next_free_moves(2)}]: "]


def test_the_apps_figure_is_recorded_beside_the_prediction(world):
    write_row(world["team_file"], _row(5))
    inputs = Inputs("250", "", "", "", "", "x")

    _run(world, inputs)

    row = read_team_file(world["team_file"])[0]
    assert (row.points_predicted, row.points) == (predict_points(_row(5), _season(world).races[5]), 250)


def test_final_fix_is_scored_with_the_swap(world):
    write_row(world["team_file"], _row(5, chip="Final Fix"))
    inputs = Inputs("TSU@ALT", "SAR@WIL", "", "", "", "", "", "x")

    _run(world, inputs)

    expected = predict_points(_row(5, chip="Final Fix"), _season(world).races[5], final_fix=("TSU@ALT", "SAR@WIL"))
    assert read_team_file(world["team_file"])[0].points_predicted == expected


def test_no_negative_needs_the_apps_figure(world):
    write_row(world["team_file"], _row(5, chip="No Negative"))
    inputs = Inputs("", "200", "", "", "", "", "x")

    _run(world, inputs)

    assert read_team_file(world["team_file"])[0].points == 200
    assert inputs.prompts[0] == inputs.prompts[1]


def test_recording_nothing_leaves_the_file_alone(world):
    inputs = Inputs(*HELD_TEXT, "50.0", "2", "x")

    assert _run(world, inputs) == 0

    assert not world["team_file"].exists()


def test_a_manual_team_over_budget_is_asked_again(world):
    expensive = ("VER@RED,HAM@MER,PER@RED,LEC@FER,SAI@FER", "RED,MER")
    cheap = ("ALO@AST,HUL@HAA,NOR@MCL,SAR@WIL,TSU@ALT", "AST,HAA")
    inputs = Inputs(*HELD_TEXT, "50.0", "2", "m", *expensive, *cheap, "SAR@WIL", "")

    assert _run(world, inputs) == 0

    row = read_team_file(world["team_file"])[0]
    assert (row.strategy, row.drivers, row.drs, row.moves_used) == (
        "Manual", ("ALO@AST", "HUL@HAA", "NOR@MCL", "SAR@WIL", "TSU@ALT"), "SAR@WIL", 1)


def test_the_wildcard_gives_unlimited_moves_and_is_recorded(world):
    inputs = Inputs(*HELD_TEXT, "50.0", "2", "", "")

    assert _run(world, inputs, "--chip", "wildcard") == 0

    season = _season(world)
    pick = solve_race(StrategyMaxP2PM, _team(), season.races[6], season.races[5], SEASON, max_moves=7)
    row = read_team_file(world["team_file"])[0]
    assert (row.chip, row.drivers, row.constructors, row.free_moves) == ("Wildcard", pick.drivers,
                                                                         pick.constructors, 2)


def test_limitless_picks_under_its_cap_and_leaves_the_budget_blank(world):
    inputs = Inputs(*HELD_TEXT, "50.0", "2", "", "")

    assert _run(world, inputs, "--chip", "limitless") == 0

    season = _season(world)
    pick = solve_race(StrategyMaxP2PM, _team(), season.races[6], season.races[5], SEASON, max_moves=7,
                      max_cost=limitless_cap(season.races[6]))
    row = read_team_file(world["team_file"])[0]
    assert (row.chip, row.drivers, row.unused_budget, row.team_value) == ("Limitless", pick.drivers, None,
                                                                          round(pick.cost, 1))
    assert row.team_value > _team().total_budget(season.races[6], season.races[5])


def test_refuses_a_chip_already_played(world):
    write_row(world["team_file"], _row(3, chip="Wildcard", points=100))
    before = world["team_file"].read_text()

    assert _run(world, Inputs(), "--chip", "wildcard") == 1

    assert world["team_file"].read_text() == before


def test_offers_only_the_chips_not_yet_played(world):
    write_row(world["team_file"], _row(5, chip="Extra DRS", points=100))
    inputs = Inputs("", "", "", "", "", "", "extra drs", "autopilot")

    assert _run(world, inputs) == 0

    assert read_team_file(world["team_file"])[1].chip == "Autopilot"
    assert inputs.prompts[-1] == "Chip (No Negative, Autopilot, Final Fix, or none) [none]: "


def test_asks_before_replacing_the_races_row(world):
    write_row(world["team_file"], replace(_row(6), strategy="Manual"))
    before = world["team_file"].read_text()
    inputs = Inputs(*HELD_TEXT, "50.0", "2", "", "", "", "n")

    assert _run(world, inputs) == 0

    assert world["team_file"].read_text() == before


def test_p2pms_race_4_pick_plays_the_wildcard(tmp_path):
    world = _world(tmp_path, next_race=4)
    season = _season(world)
    options = run_lineup([StrategyMaxP2PM], _team(), season.races[4], season.races[3], SEASON, free_moves=2)
    write_row(world["team_file"], _row(3, points=100))
    inputs = Inputs("", "", "", "", "2", "")

    assert _run(world, inputs) == 0

    row = read_team_file(world["team_file"])[1]
    assert (row.strategy, row.chip, row.drivers) == ("StrategyMaxP2PM", "Wildcard", options[0].pick.drivers)


def _record(world, race: int = 6) -> dict:
    files = list(world["records"].glob(f"{SEASON}_{race}_*.json"))
    assert len(files) == 1
    return json.loads(files[0].read_text())


def test_each_run_saves_every_pick_with_prices(world):
    inputs = Inputs(*HELD_TEXT, "50.0", "2", "", "", "")

    _run(world, inputs)

    season = _season(world)
    race = season.races[6]
    pick = solve_race(StrategyMaxP2PM, _team(), race, season.races[5], SEASON, max_moves=2)
    record = _record(world)
    assert (record["season"], record["race"], record["chip"]) == (SEASON, 6, "")
    assert record["held"] == {"drivers": list(HELD_DRIVERS), "constructors": list(HELD_CONSTRUCTORS),
                              "unused_budget": UNUSED, "free_moves": 2,
                              "value": pytest.approx(_team().total_value(race, season.races[5]))}
    assert [(o["strategies"], o["drivers"], o["constructors"], o["moves_used"]) for o in record["options"]] == [
        (["StrategyMaxP2PM"], list(pick.drivers), list(pick.constructors), pick.moves_used)]
    assert record["prices"]["VER@RED"] == race.drivers["VER@RED"].price
    assert record["prices"]["RED"] == race.constructors["RED"].price
    assert record["recorded"]["drivers"] == list(read_team_file(world["team_file"])[0].drivers)


def test_a_run_recording_nothing_still_saves_its_picks(world):
    _run(world, Inputs(*HELD_TEXT, "50.0", "2", "x"))

    record = _record(world)
    assert record["recorded"] is None
    assert len(record["options"]) == 1


RACE_1_ODDS = "".join(f"{driver},{team},{SEASON},1,{price}\n" for driver, team, price in [
    ("VER", "RED", "1-1"), ("PER", "RED", "3-1"), ("ALO", "AST", "6-1"), ("HAM", "MER", "8-1"),
    ("LEC", "FER", "8-1"), ("SAI", "FER", "12-1"), ("RUS", "MER", "14-1")])


def test_race_1_without_odds_is_refused(tmp_path, capsys):
    world = _world(tmp_path, next_race=1)

    assert _run(world, Inputs()) == 1

    assert not world["team_file"].exists()
    summary = capsys.readouterr().out.split("Summary:")[1]
    assert f"Pick: refused - No odds for season {SEASON} race 1 in {world['odds']}" in summary


def test_race_1_records_the_odds_pick_with_blank_moves(tmp_path):
    world = _world(tmp_path, next_race=1, odds=RACE_1_ODDS)
    inputs = Inputs("", "", "")

    assert _run(world, inputs) == 0

    expected = run_race1_lineup(_season(world).races[1], SEASON, str(world["odds"]))[0]
    row = read_team_file(world["team_file"])[0]
    assert row == TeamRow(season=SEASON, race=1, strategy=expected.strategies[0], chip="",
                          drivers=expected.pick.drivers, constructors=expected.pick.constructors,
                          drs=expected.pick.drs_driver, free_moves=None, moves_used=None,
                          team_value=round(expected.pick.cost, 1), unused_budget=round(100.0 - expected.pick.cost, 1),
                          points_predicted=None, points=None)
    assert row.strategy == "StrategyBettingOdds:999.9"
    assert not any(prompt.startswith("Held") for prompt in inputs.prompts)


def test_race_1_offers_each_concentration_limit_and_saves_them(tmp_path, capsys):
    world = _world(tmp_path, next_race=1, odds=RACE_1_ODDS)

    _run(world, Inputs("x"))

    record = _record(world, race=1)
    labels = [label for option in record["options"] for label in option["strategies"]]
    assert labels == [f"StrategyBettingOdds:{limit}" for limit in ("999.9", "4", "3", "2", "1", "0")]
    assert record["held"] is None
    assert "Held" not in capsys.readouterr().out


def test_race_1_takes_a_manual_team_against_a_budget_of_100(tmp_path):
    world = _world(tmp_path, next_race=1, odds=RACE_1_ODDS)
    team = ("ALO@AST,HUL@HAA,NOR@MCL,SAR@WIL,TSU@ALT", "AST,HAA")

    assert _run(world, Inputs("m", *team, "", "")) == 0

    race = _season(world).races[1]
    cost = sum(race.drivers[d].price for d in team[0].split(",")) + sum(race.constructors[c].price for c in ("AST", "HAA"))
    row = read_team_file(world["team_file"])[0]
    assert (row.strategy, row.free_moves, row.moves_used, row.unused_budget) == ("Manual", None, None,
                                                                                round(100.0 - cost, 1))


def test_race_1_refuses_a_chip_argument(tmp_path):
    world = _world(tmp_path, next_race=1, odds=RACE_1_ODDS)

    assert _run(world, Inputs(), "--chip", "wildcard") == 1

    assert not world["team_file"].exists()


def test_race_2_starts_from_race_1s_row_on_2_free_moves(tmp_path):
    world = _world(tmp_path, next_race=2)
    race_1 = replace(_row(1), strategy="StrategyBettingOdds:3", free_moves=None, moves_used=None)
    write_row(world["team_file"], race_1)
    inputs = Inputs("", "", "", "", "", "x")

    assert _run(world, inputs) == 0

    assert inputs.prompts[1:5] == ["Held drivers [ALO@AST,HUL@HAA,NOR@MCL,PIA@MCL,TSU@ALT]: ",
                                   "Held constructors [AST,HAA]: ", "Unused budget [50.0]: ", "Free moves [2]: "]


def _no_network(url):
    raise ConnectionError("no network")


def test_a_failed_step_still_picks_then_exits_1_naming_it(world, capsys):
    inputs = Inputs(*HELD_TEXT, "50.0", "2", "", "", "")

    assert _run(world, inputs, collect=True, boxbox_fetch=_no_network) == 1

    assert read_team_file(world["team_file"])[0].race == 6
    summary = capsys.readouterr().out.split("Summary:")[1]
    assert "BoxBox: failed - no network" in summary
    assert f"Odds: not yet - no saved page in {world['pages']}" in summary
    assert "Pick: done - recorded race 6" in summary


def test_collection_runs_before_the_pick(world, capsys):
    inputs = Inputs(*HELD_TEXT, "50.0", "2", "x")

    _run(world, inputs, collect=True, boxbox_fetch=_no_network)

    out = capsys.readouterr().out
    assert out.index("BoxBox: failed") < out.index("Held") < out.index("Summary:")


def test_skipping_collection_is_reported(world, capsys):
    assert _run(world, Inputs(*HELD_TEXT, "50.0", "2", "x")) == 0

    summary = capsys.readouterr().out.split("Summary:")[1]
    assert "BoxBox: skipped" in summary
    assert "Pick: done - nothing recorded" in summary


def test_missing_odds_warn_at_the_top_and_in_the_summary_without_failing(tmp_path, capsys):
    world = _world(tmp_path, next_race=6, odds=f"VER,RED,{SEASON},5,5-4\n")

    assert _run(world, Inputs(*HELD_TEXT, "50.0", "2", "x")) == 0

    out = capsys.readouterr().out
    warning = f"No odds for season {SEASON} race 6"
    assert out.index(warning) < out.index("Held")
    assert warning in out.split("Summary:")[1]


def test_odds_present_give_no_warning(world, capsys):
    _run(world, Inputs(*HELD_TEXT, "50.0", "2", "x"))

    assert "No odds" not in capsys.readouterr().out


def _season_over_world(tmp_path) -> dict:
    """Paths for a run once every race of the archive's season, 2023 races 1 to 6, has points."""
    world = _world(tmp_path, next_race=6)
    write_archive(world["archive"], last_race=6)
    return world


def test_the_final_race_is_scored_and_the_season_ends(tmp_path, capsys):
    world = _season_over_world(tmp_path)
    write_row(world["team_file"], _row(6))
    inputs = Inputs("")

    assert _run(world, inputs) == 0

    predicted = predict_points(_row(6), _season(world).races[6])
    assert read_team_file(world["team_file"]) == [_row(6, points=predicted)]
    assert inputs.prompts == [f"Race 6 points: the archive gives {predicted}; the app's figure [{predicted}]: "]
    assert f"Pick: done - season {SEASON} over, no race left to pick for" in capsys.readouterr().out.split(
        "Summary:")[1]


def test_a_season_over_with_nothing_to_score_exits_0(tmp_path, capsys):
    world = _season_over_world(tmp_path)

    assert _run(world, Inputs()) == 0

    assert not world["team_file"].exists()
    assert f"season {SEASON} over" in capsys.readouterr().out.split("Summary:")[1]


def test_a_season_over_refuses_a_row_the_archive_lacks(tmp_path, capsys):
    world = _season_over_world(tmp_path)
    write_row(world["team_file"], _row(7))

    assert _run(world, Inputs()) == 1

    assert f"Pick: refused - The team file has season {SEASON} race 7" in capsys.readouterr().out.split(
        "Summary:")[1]


def test_input_ending_before_the_picks_refuses_and_saves_nothing(world, capsys):
    inputs = EndingInputs()

    assert _run(world, inputs) == 1

    assert inputs.prompts == ["Held drivers: "]
    assert not world["team_file"].exists()
    assert not world["records"].exists()
    assert "Pick: refused - no input" in capsys.readouterr().out.split("Summary:")[1]


def test_input_ending_at_the_choice_records_nothing_but_saves_the_picks(world, capsys):
    inputs = EndingInputs(*HELD_TEXT, "50.0", "2")

    assert _run(world, inputs) == 1

    assert inputs.prompts[-1].startswith("Pick 1-1")
    assert not world["team_file"].exists()
    record = _record(world)
    assert (record["recorded"], len(record["options"])) == (None, 1)
    assert "Pick: refused - no input" in capsys.readouterr().out.split("Summary:")[1]


def test_input_ending_at_race_1s_choice_saves_the_picks(tmp_path):
    world = _world(tmp_path, next_race=1, odds=RACE_1_ODDS)

    assert _run(world, EndingInputs()) == 1

    assert not world["team_file"].exists()
    assert _record(world, race=1)["recorded"] is None


def test_a_refused_pick_is_in_the_summary(tmp_path, capsys):
    world = _world(tmp_path, next_race=1)

    _run(world, Inputs())

    assert "Pick: refused - " in capsys.readouterr().out.split("Summary:")[1]


class _StubTables:
    """Stands in for the FastF1 strategy's ``SignalTables``: set values, and no price rises."""

    def values(self, season: int, race: int) -> dict[str, float]:
        return {"VER@RED": 30.0, "PER@RED": 20.0, "RED": 40.0}

    def price_rise(self, season: int, race: int) -> dict[str, float]:
        return {}


@pytest.fixture
def signal(monkeypatch) -> list:
    """Give the FastF1 strategy set values in place of the real tables, recording each file it reads.

    The real tables need the 2023-25 metrics rows matched to the real archive, as in
    ``tests/test_strategy_fastf1.py``.
    """
    read = []

    def _load(fn_metrics):
        read.append(fn_metrics)
        return _StubTables()

    monkeypatch.setattr("linear.strategy_fastf1.load_signal_tables", _load)
    return read


def test_the_fastf1_pick_is_offered_when_the_race_has_signal(tmp_path, signal, capsys):
    world = _world(tmp_path, next_race=6, metrics=RACE_6_METRICS)

    assert _run(world, Inputs(*HELD_TEXT, "50.0", "2", "x")) == 0

    season = _season(world)
    pick = solve_race(fastf1_strategy(str(world["metrics"])), _team(), season.races[6], season.races[5], SEASON,
                      max_moves=2)
    options = _record(world)["options"]
    assert [o["drivers"] for o in options if "StrategyFastF1RuleRise" in o["strategies"]] == [list(pick.drivers)]
    assert signal[-1] == str(world["metrics"])
    assert "FastF1 pick: done" in capsys.readouterr().out.split("Summary:")[1]


def test_the_fastf1_pick_is_skipped_without_signal(world, signal, capsys):
    assert _run(world, Inputs(*HELD_TEXT, "50.0", "2", "x")) == 0

    assert [o["strategies"] for o in _record(world)["options"]] == [["StrategyMaxP2PM"]]
    assert signal == []
    summary = capsys.readouterr().out.split("Summary:")[1]
    assert f"FastF1 pick: skipped - no FastF1 signal for season {SEASON} race 6 in {world['metrics']}" in summary


def test_a_fastf1_pick_that_fails_still_records_then_exits_1(tmp_path, monkeypatch, capsys):
    def _load(fn_metrics):
        raise ValueError("No single fantasy pair for 2023 race 6: DOO")

    monkeypatch.setattr("linear.strategy_fastf1.load_signal_tables", _load)
    world = _world(tmp_path, next_race=6, metrics=RACE_6_METRICS)

    assert _run(world, Inputs(*HELD_TEXT, "50.0", "2", "", "", "")) == 1

    assert read_team_file(world["team_file"])[0].strategy == "StrategyMaxP2PM"
    summary = capsys.readouterr().out.split("Summary:")[1]
    assert "FastF1 pick: failed - No single fantasy pair for 2023 race 6: DOO" in summary
    assert "Pick: done - recorded race 6" in summary


def test_the_record_keeps_the_races_metrics_rows(tmp_path, signal):
    world = _world(tmp_path, next_race=6, metrics=RACE_6_METRICS)

    _run(world, Inputs(*HELD_TEXT, "50.0", "2", "x"))

    rows = _record(world)["fastf1_metrics"]
    assert [(r["Driver"], r["FP3_MinLapTime_rank"], r["Points"]) for r in rows] == [("VER", 0.8, None)]


def _schedule_after_the_race(season):
    """A schedule whose race 6 ran long ago, so its sessions have all run."""
    start = pd.Timestamp("2023-05-26 11:30")
    return pd.DataFrame({
        "RoundNumber": [6],
        **{f"Session{i}": [name] for i, name in enumerate(
            ["Practice 1", "Practice 2", "Practice 3", "Qualifying", "Race"], start=1)},
        **{f"Session{i}DateUtc": [start + pd.Timedelta(days=i)] for i in range(1, 6)},
    })


def _build(season, race):
    return pd.DataFrame({
        "Season": [season], "Race": [race], "Driver": ["VER"], "Points": [None if race == 6 else 25],
        "RollingPoints": [60.0], "RollingPointsRank": [1.0], "ConstructorRollingPointsRank": [1.0],
        "FP2_MinLapTime_rank": [0.9], "FP3_MinLapTime_rank": [0.8], "OddsRank": [0.0], "AggregateRank": [2.7],
    })


def test_collection_builds_the_metrics_before_the_fastf1_pick(world, signal, capsys):
    api = FastF1Api(schedule=_schedule_after_the_race, build=_build)

    _run(world, Inputs(*HELD_TEXT, "50.0", "2", "x"), collect=True, boxbox_fetch=_no_network, fastf1_api=api)

    out = capsys.readouterr().out
    assert out.index("Odds: not yet") < out.index("FastF1: done - built races 1, 2, 3, 4, 5, 6") < out.index("Held")
    assert any("StrategyFastF1RuleRise" in o["strategies"] for o in _record(world)["options"])


def test_skipping_collection_skips_the_fastf1_step(world, capsys):
    _run(world, Inputs(*HELD_TEXT, "50.0", "2", "x"))

    assert "FastF1: skipped - --skip-collection" in capsys.readouterr().out.split("Summary:")[1]
