import pytest

from live.team_file import COLUMNS, TeamFileError, TeamRow, read_team_file

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
