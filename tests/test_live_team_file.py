from dataclasses import replace

import pytest

from live.team_file import (
    COLUMNS,
    Held,
    TeamFileError,
    TeamRow,
    check_known,
    held_for,
    read_team_file,
    write_row,
)
from tests.live_fixtures import make_race

HEADER = ",".join(COLUMNS) + "\n"
ROW_20 = "2026,20,StrategyMaxP2PM,,HUL@AUD,LAW@VRB,LEC@FER,PER@CAD,VER@RED,FER,RED,VER@RED,2,1,135.3,1.0,329,329\n"
ROW_21 = "2026,21,Manual,Extra DRS,BOR@AUD,LAW@VRB,LEC@FER,PER@CAD,VER@RED,FER,RED,LEC@FER,3,1,138.5,1.0,,\n"
ROW_LIMITLESS = "2026,17,StrategyBettingOdds:1,Limitless,ANT@MER,HAM@FER,LEC@FER,NOR@MCL,VER@RED,MER,RED,VER@RED,2,6,160.2,,364,364\n"


def _file(tmp_path, body: str, header: str = HEADER):
    path = tmp_path / "live_team.csv"
    path.write_text(header + body)
    return path


def _swap(row: str, column: str, value: str) -> str:
    fields = row.rstrip("\n").split(",")
    fields[COLUMNS.index(column)] = value
    return ",".join(fields) + "\n"


def test_a_missing_file_holds_no_rows(tmp_path):
    assert read_team_file(tmp_path / "live_team.csv") == []


def test_reads_each_field_typed(tmp_path):
    path = _file(tmp_path, ROW_20 + ROW_21)

    rows = read_team_file(path)

    assert rows == [
        TeamRow(season=2026, race=20, strategy="StrategyMaxP2PM", chip="",
                drivers=("HUL@AUD", "LAW@VRB", "LEC@FER", "PER@CAD", "VER@RED"), constructors=("FER", "RED"),
                drs="VER@RED", free_moves=2, moves_used=1, team_value=135.3, unused_budget=1.0,
                points_predicted=329, points=329),
        TeamRow(season=2026, race=21, strategy="Manual", chip="Extra DRS",
                drivers=("BOR@AUD", "LAW@VRB", "LEC@FER", "PER@CAD", "VER@RED"), constructors=("FER", "RED"),
                drs="LEC@FER", free_moves=3, moves_used=1, team_value=138.5, unused_budget=1.0,
                points_predicted=None, points=None),
    ]


def test_a_limitless_row_has_no_unused_budget(tmp_path):
    assert read_team_file(_file(tmp_path, ROW_LIMITLESS))[0].unused_budget is None


def test_refuses_a_header_it_does_not_know(tmp_path):
    path = _file(tmp_path, ROW_20, header=HEADER.replace("DRS", "Boost"))

    with pytest.raises(TeamFileError, match="header"):
        read_team_file(path)


@pytest.mark.parametrize("column, value, match", [
    ("Race", "x", "Race"),
    ("FreeMoves", "", "FreeMoves"),
    ("TeamValue", "a lot", "TeamValue"),
    ("Strategy", "", "Strategy"),
    ("Chip", "Triple Boost", "chip"),
    ("D2", "HUL@AUD", "drivers"),
    ("D1", "ZZZ@AUD", "drivers"),
    ("D3", "", "drivers"),
    ("C1", "RED", "constructors"),
    ("C2", "AAA", "constructors"),
    ("DRS", "BOR@AUD", "DRS"),
    ("UnusedBudget", "", "UnusedBudget"),
])
def test_refuses_a_row_breaking_a_rule(tmp_path, column, value, match):
    path = _file(tmp_path, _swap(ROW_20, column, value))

    with pytest.raises(TeamFileError, match=match):
        read_team_file(path)


ROW_1 = "2026,1,StrategyBettingOdds:3,,HUL@AUD,LAW@VRB,LEC@FER,PER@CAD,VER@RED,FER,RED,VER@RED,,,98.4,1.6,,\n"


def test_race_1_has_no_moves(tmp_path):
    row = read_team_file(_file(tmp_path, ROW_1))[0]

    assert (row.race, row.strategy, row.free_moves, row.moves_used) == (1, "StrategyBettingOdds:3", None, None)


@pytest.mark.parametrize("row, column, value", [
    (ROW_1, "FreeMoves", "2"),
    (ROW_1, "MovesUsed", "7"),
    (ROW_20, "MovesUsed", ""),
], ids=["race 1 free moves", "race 1 moves used", "race 20 blank moves used"])
def test_moves_are_blank_at_race_1_and_only_there(tmp_path, row, column, value):
    with pytest.raises(TeamFileError, match="race 1"):
        read_team_file(_file(tmp_path, _swap(row, column, value)))


def test_writes_race_1_with_blank_moves(tmp_path):
    path = tmp_path / "live_team.csv"
    race_1 = replace(ROW, race=1, strategy="StrategyBettingOdds:3", free_moves=None, moves_used=None)

    write_row(path, race_1)

    assert read_team_file(path) == [race_1]
    assert ",VER@RED,,,135.3," in path.read_text()


def test_refuses_a_short_row(tmp_path):
    path = _file(tmp_path, ROW_20.replace(",329,329\n", ",329\n"))

    with pytest.raises(TeamFileError, match="fields"):
        read_team_file(path)


def test_refuses_a_race_twice(tmp_path):
    with pytest.raises(TeamFileError, match="order"):
        read_team_file(_file(tmp_path, ROW_20 + ROW_20))


def test_refuses_races_out_of_order(tmp_path):
    with pytest.raises(TeamFileError, match="order"):
        read_team_file(_file(tmp_path, ROW_21 + ROW_20))


def test_refuses_a_chip_played_twice_in_a_season(tmp_path):
    row_22 = _swap(ROW_21, "Race", "22")

    with pytest.raises(TeamFileError, match="Extra DRS"):
        read_team_file(_file(tmp_path, ROW_21 + row_22))


def test_allows_a_chip_once_in_each_season(tmp_path):
    row_2027 = _swap(ROW_21, "Season", "2027")

    assert [r.season for r in read_team_file(_file(tmp_path, ROW_21 + row_2027))] == [2026, 2027]


ROW = TeamRow(season=2026, race=20, strategy="StrategyMaxP2PM", chip="",
              drivers=("HUL@AUD", "LAW@VRB", "LEC@FER", "PER@CAD", "VER@RED"), constructors=("FER", "RED"),
              drs="VER@RED", free_moves=2, moves_used=1, team_value=135.3, unused_budget=1.0,
              points_predicted=None, points=None)


def test_a_row_of_the_race_is_known():
    check_known(ROW, make_race(20))


def test_refuses_a_driver_not_in_the_race():
    with pytest.raises(TeamFileError, match="PER@CAD"):
        check_known(ROW, make_race(20, drop=("PER@CAD",)))


def test_refuses_a_constructor_not_in_the_race():
    row = replace(ROW, constructors=("FER", "XXX"))

    with pytest.raises(TeamFileError, match="XXX"):
        check_known(row, make_race(20))


# Race 19 written by hand with more decimal places than the writer uses, so a rewrite would show
ROW_19_BY_HAND = "2026,19,StrategyMaxP2PM,,HAD@RED,HUL@AUD,LAW@VRB,LIN@VRB,VER@RED,FER,RED,VER@RED,3,1,134.00,0.50,283,283\n"


def test_writes_a_new_file_with_its_header(tmp_path):
    path = tmp_path / "live_team.csv"

    write_row(path, ROW)

    assert path.read_text() == HEADER + "2026,20,StrategyMaxP2PM,,HUL@AUD,LAW@VRB,LEC@FER,PER@CAD,VER@RED,FER,RED,VER@RED,2,1,135.3,1.0,,\n"


def test_adds_a_race_after_the_others_keeping_their_bytes(tmp_path):
    path = _file(tmp_path, ROW_19_BY_HAND)

    write_row(path, ROW)

    assert path.read_text().startswith(HEADER + ROW_19_BY_HAND)
    assert read_team_file(path)[1] == ROW


def test_adds_a_race_in_race_order(tmp_path):
    path = _file(tmp_path, ROW_19_BY_HAND + ROW_21)

    write_row(path, ROW)

    assert [r.race for r in read_team_file(path)] == [19, 20, 21]
    assert path.read_text().startswith(HEADER + ROW_19_BY_HAND)
    assert path.read_text().endswith(ROW_21)


def test_replaces_the_race_row_keeping_the_others_bytes(tmp_path):
    path = _file(tmp_path, ROW_19_BY_HAND + ROW_20.replace(",329,329\n", ",,\n"))
    rerun = replace(ROW, drs="LEC@FER", moves_used=2)

    write_row(path, rerun)

    assert path.read_text().startswith(HEADER + ROW_19_BY_HAND)
    assert read_team_file(path) == [read_team_file(path)[0], rerun]


def test_fills_the_points_of_the_race_row(tmp_path):
    path = _file(tmp_path, ROW_20.replace(",329,329\n", ",,\n"))
    scored = replace(read_team_file(path)[0], points_predicted=330, points=329)

    write_row(path, scored)

    assert read_team_file(path) == [scored]


def test_refuses_to_rewrite_a_final_row(tmp_path):
    path = _file(tmp_path, ROW_20)

    with pytest.raises(TeamFileError, match="final"):
        write_row(path, replace(ROW, points=300))

    assert path.read_text() == HEADER + ROW_20


def test_refuses_a_row_that_breaks_the_file_rules(tmp_path):
    path = _file(tmp_path, ROW_21)

    with pytest.raises(TeamFileError, match="Extra DRS"):
        write_row(path, replace(ROW, race=22, chip="Extra DRS"))

    assert path.read_text() == HEADER + ROW_21


def test_refuses_a_row_that_breaks_a_row_rule(tmp_path):
    path = _file(tmp_path, ROW_19_BY_HAND)

    with pytest.raises(TeamFileError, match="DRS"):
        write_row(path, replace(ROW, drs="BOR@AUD"))

    assert path.read_text() == HEADER + ROW_19_BY_HAND


def test_writes_money_to_one_decimal_place(tmp_path):
    path = tmp_path / "live_team.csv"

    write_row(path, replace(ROW, team_value=135.29999999, unused_budget=0.30000000004))

    assert ",135.3,0.3,," in path.read_text()


def test_writes_a_limitless_row_with_no_unused_budget(tmp_path):
    path = tmp_path / "live_team.csv"
    limitless = replace(ROW, chip="Limitless", unused_budget=None)

    write_row(path, limitless)

    assert read_team_file(path) == [limitless]


TEAM_A = ("HUL@AUD", "LAW@VRB", "LEC@FER", "PER@CAD", "VER@RED")
TEAM_B = ("ANT@MER", "HAM@FER", "LEC@FER", "RUS@MER", "VER@RED")


def _row(race: int, moves_used: int = 1, free_moves: int = 2, chip: str = "", drivers=TEAM_A,
         unused_budget: float | None = 1.0, season: int = 2026) -> TeamRow:
    return replace(ROW, season=season, race=race, chip=chip, drivers=drivers, drs=drivers[0],
                   moves_used=moves_used, free_moves=free_moves, unused_budget=unused_budget)


@pytest.mark.parametrize("moves_used, free_moves", [(0, 3), (1, 3), (2, 2), (3, 2)])
def test_free_moves_follow_the_moves_used(moves_used, free_moves):
    rows = [_row(19), _row(20, moves_used=moves_used, free_moves=3)]

    assert held_for(rows, 2026, 21).free_moves == free_moves


@pytest.mark.parametrize("chip", ["", "Extra DRS"])
def test_race_2_starts_on_2_free_moves(chip):
    rows = [replace(_row(1, chip=chip, unused_budget=1.6), free_moves=None, moves_used=None)]

    assert held_for(rows, 2026, 2) == Held(drivers=TEAM_A, constructors=("FER", "RED"), unused_budget=1.6,
                                           free_moves=2, team_race=1, last_race=1)


def test_the_team_and_budget_come_from_the_last_row():
    rows = [_row(19, unused_budget=4.0), _row(20, drivers=TEAM_B, unused_budget=0.7)]

    assert held_for(rows, 2026, 21) == Held(drivers=TEAM_B, constructors=("FER", "RED"), unused_budget=0.7,
                                            free_moves=3, team_race=20, last_race=20)


def test_a_wildcard_race_passes_on_its_free_moves():
    rows = [_row(19), _row(20, chip="Wildcard", drivers=TEAM_B, moves_used=5, free_moves=3)]

    held = held_for(rows, 2026, 21)

    assert (held.drivers, held.free_moves) == (TEAM_B, 3)


def test_after_limitless_the_team_and_budget_come_from_the_row_before():
    rows = [_row(19, unused_budget=0.4),
            _row(20, chip="Limitless", drivers=TEAM_B, moves_used=5, free_moves=3, unused_budget=None)]

    assert held_for(rows, 2026, 21) == Held(drivers=TEAM_A, constructors=("FER", "RED"), unused_budget=0.4,
                                            free_moves=3, team_race=19, last_race=20)


def test_a_row_for_the_race_itself_is_ignored():
    rows = [_row(19, moves_used=2), _row(20, drivers=TEAM_B, moves_used=0)]

    assert held_for(rows, 2026, 20) == Held(drivers=TEAM_A, constructors=("FER", "RED"), unused_budget=1.0,
                                            free_moves=2, team_race=19, last_race=19)


def test_other_seasons_are_ignored():
    rows = [_row(19, season=2025, moves_used=0), _row(3, drivers=TEAM_B, moves_used=2, season=2026)]

    held = held_for(rows, 2026, 4)

    assert (held.drivers, held.free_moves, held.team_race) == (TEAM_B, 2, 3)


def test_refuses_a_season_without_a_row_before_the_race():
    with pytest.raises(TeamFileError, match="no row"):
        held_for([_row(19, season=2025), _row(5)], 2026, 5)


def test_refuses_a_season_with_only_limitless_before_the_race():
    with pytest.raises(TeamFileError, match="no row"):
        held_for([_row(5, chip="Limitless", unused_budget=None)], 2026, 6)


def test_refuses_a_row_after_the_race():
    with pytest.raises(TeamFileError, match="after"):
        held_for([_row(5), _row(7)], 2026, 6)
