import csv

from odds_source.drivers import OddsEntry
from odds_source.odds_file import write_race_odds
from odds_source.schedule import SNAPSHOT_COLUMNS, CapturePoint

_LEGACY_HEADER = "Driver,Constructor,Season,Race,Odds,Odds_Pre_Weekend,Odds_Pre_Quali,Odds_Post_FP2,Odds_Post_Quali\n"
_RACE_19 = "NOR,MCL,2026,19,14-1,14:1,,,\nVER,RED,2026,19,5-4,5:4,,,\n"
_RACE_20 = "NOR,MCL,2026,20,14-1,14-1,,,\nVER,RED,2026,20,5-4,5-4,,,\nHAD,RED,2026,20,28-1,28-1,,,\n"
_RACE_21 = "NOR,MCL,2026,21,3-1,3-1,,,\n"


def _odds_file(tmp_path, body: str):
    path = tmp_path / "odds.csv"
    path.write_text(_LEGACY_HEADER + body)
    return path


def _rows(path) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _race(path, race: int) -> list[dict[str, str]]:
    return [row for row in _rows(path) if row["Race"] == str(race)]


_RACE_20_Q = CapturePoint(2026, 20, "Odds_Q")
_ENTRIES = [OddsEntry("VER", "RED", "5/1"), OddsEntry("NOR", "MCL", "9/5"), OddsEntry("CAM", "HAA", "500/1")]


def test_adds_every_snapshot_column_once_after_the_legacy_ones(tmp_path):
    path = _odds_file(tmp_path, _RACE_19 + _RACE_20)

    write_race_odds(path, _RACE_20_Q, _ENTRIES)

    assert path.read_text().splitlines()[0] == _LEGACY_HEADER.strip() + "," + ",".join(SNAPSHOT_COLUMNS)


def test_fills_the_column_and_odds_for_each_priced_driver(tmp_path):
    path = _odds_file(tmp_path, _RACE_19 + _RACE_20)

    write_race_odds(path, _RACE_20_Q, _ENTRIES)

    norris = _race(path, 20)[0]
    assert (norris["Driver"], norris["Odds"], norris["Odds_Q"]) == ("NOR", "9/5", "9/5")
    # Legacy snapshots and the other new columns are left alone
    assert norris["Odds_Pre_Weekend"] == "14-1"
    assert norris["Odds_FP3"] == ""


def test_blanks_the_column_and_odds_for_a_driver_this_run_did_not_price(tmp_path):
    path = _odds_file(tmp_path, _RACE_19 + _RACE_20)

    write_race_odds(path, _RACE_20_Q, _ENTRIES)

    hadjar = _race(path, 20)[2]
    assert (hadjar["Driver"], hadjar["Odds"], hadjar["Odds_Q"], hadjar["Odds_Pre_Weekend"]) == ("HAD", "", "", "28-1")


def test_appends_a_new_driver_after_the_races_rows(tmp_path):
    path = _odds_file(tmp_path, _RACE_19 + _RACE_20 + _RACE_21)

    write_race_odds(path, _RACE_20_Q, _ENTRIES + [OddsEntry("Esteban Ocon", "", "500/1")])

    assert [(row["Race"], row["Driver"], row["Constructor"]) for row in _rows(path)][2:] == [
        ("20", "NOR", "MCL"), ("20", "VER", "RED"), ("20", "HAD", "RED"),
        ("20", "CAM", "HAA"), ("20", "Esteban Ocon", ""),
        ("21", "NOR", "MCL"),
    ]


def test_a_race_with_no_rows_goes_between_the_races_either_side(tmp_path):
    path = _odds_file(tmp_path, _RACE_19 + _RACE_21)

    write_race_odds(path, _RACE_20_Q, _ENTRIES)

    assert [(row["Race"], row["Driver"]) for row in _rows(path)] == [
        ("19", "NOR"), ("19", "VER"), ("20", "VER"), ("20", "NOR"), ("20", "CAM"), ("21", "NOR"),
    ]


def test_a_rerun_overwrites_and_earlier_snapshots_stay(tmp_path):
    path = _odds_file(tmp_path, _RACE_19 + _RACE_20)

    write_race_odds(path, CapturePoint(2026, 20, "Odds_FP3"), [OddsEntry("NOR", "MCL", "2/1")])
    write_race_odds(path, _RACE_20_Q, [OddsEntry("NOR", "MCL", "7/4")])
    write_race_odds(path, _RACE_20_Q, [OddsEntry("NOR", "MCL", "9/5")])

    norris = _race(path, 20)[0]
    assert (norris["Odds"], norris["Odds_FP3"], norris["Odds_Q"]) == ("9/5", "2/1", "9/5")


def test_other_races_keep_their_values_and_then_their_bytes(tmp_path):
    path = _odds_file(tmp_path, _RACE_19 + _RACE_20 + _RACE_21)
    before = [row for row in _rows(path) if row["Race"] != "20"]

    write_race_odds(path, _RACE_20_Q, _ENTRIES)

    # The first write adds the new columns, so only the values can be compared
    after = [row for row in _rows(path) if row["Race"] != "20"]
    assert [{key: row[key] for key in before[0]} for row in after] == before
    assert all(row[column] == "" for row in after for column in SNAPSHOT_COLUMNS)

    other_lines = [line for line in path.read_text().splitlines() if ",2026,20," not in line]
    write_race_odds(path, _RACE_20_Q, [OddsEntry("NOR", "MCL", "2/1")])
    assert [line for line in path.read_text().splitlines() if ",2026,20," not in line] == other_lines


def test_leaves_no_temporary_file_behind(tmp_path):
    path = _odds_file(tmp_path, _RACE_20)

    write_race_odds(path, _RACE_20_Q, _ENTRIES)

    assert [p.name for p in tmp_path.iterdir()] == ["odds.csv"]
