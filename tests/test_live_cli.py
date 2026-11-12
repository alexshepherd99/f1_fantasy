"""The live script end to end, on an archive cut from 2023 and a team file in a temporary folder."""

import json
from dataclasses import replace

import pytest

from common import AssetType
from helpers import load_with_derivations
from linear.strategy_p2pm import StrategyMaxP2PM
from live.cli import main
from live.lineup import run_lineup
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


@pytest.fixture
def world(tmp_path):
    """Paths for a run whose next race is 2023 race 6."""
    return _world(tmp_path, next_race=6)


ODDS_HEADER = "Driver,Constructor,Season,Race,Odds\n"


def _world(tmp_path, next_race: int, odds: str = f"VER,RED,{SEASON},6,5-4\n") -> dict:
    archive = tmp_path / "archive"
    archive.mkdir()
    write_archive(archive, last_race=next_race, unscored=(next_race,))
    (tmp_path / "pages").mkdir()
    (tmp_path / "odds.csv").write_text(ODDS_HEADER + odds)
    return {"archive": archive, "team_file": tmp_path / "live_team.csv", "records": tmp_path / "records",
            "pages": tmp_path / "pages", "odds": tmp_path / "odds.csv", "copies": tmp_path / "copies"}


def _run(world, inputs: Inputs, *extra: str, collect: bool = False, **injected) -> int:
    return main(["--team-file", str(world["team_file"]), "--archive-dir", str(world["archive"]),
                 "--record-dir", str(world["records"]), "--pages-dir", str(world["pages"]),
                 "--odds-file", str(world["odds"]), "--copy-dir", str(world["copies"]),
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


def _record(world) -> dict:
    files = list(world["records"].glob(f"{SEASON}_6_*.json"))
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


def test_race_1_is_refused(tmp_path):
    world = _world(tmp_path, next_race=1)

    assert _run(world, Inputs()) == 1


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


def test_a_refused_pick_is_in_the_summary(tmp_path, capsys):
    world = _world(tmp_path, next_race=1)

    _run(world, Inputs())

    assert "Pick: refused - " in capsys.readouterr().out.split("Summary:")[1]
