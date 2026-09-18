import pandas as pd
import pandas.testing as pdt

from backtest.runner import append_results
from scripts.run_multiple_teams import open_batch_results_file


def _rows(labels: list[str]) -> list[dict]:
    return [
        {
            "sim_key": f"({label})(2023)team",
            "label": label,
            "team": "team",
            "total_value": 99.7,
            "band": "(99.5, 100]",
            "total_points": 3000,
        }
        for label in labels
    ]


def test_append_writes_to_the_given_path_and_nowhere_else(tmp_path, monkeypatch):
    # From tmp_path, a relative write such as the old hardcoded outputs/ path lands here too
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "results.parquet"

    append_results(open_batch_results_file(str(path)), _rows(["A"]), str(path))

    assert list(tmp_path.rglob("*")) == [path]


def test_round_trip_preserves_rows(tmp_path):
    path = str(tmp_path / "results.parquet")
    rows = _rows(["A", "B"])

    returned = append_results(open_batch_results_file(path), rows, path)

    pdt.assert_frame_equal(returned, pd.DataFrame(rows))
    pdt.assert_frame_equal(open_batch_results_file(path), pd.DataFrame(rows))


def test_appends_accumulate_with_an_unrepeated_index(tmp_path):
    path = str(tmp_path / "results.parquet")

    store = append_results(open_batch_results_file(path), _rows(["A", "B"]), path)
    store = append_results(store, _rows(["C", "D"]), path)

    stored = open_batch_results_file(path)
    assert list(stored["label"]) == ["A", "B", "C", "D"]
    assert list(stored.index) == [0, 1, 2, 3]
    pdt.assert_frame_equal(stored, store)


def test_appending_no_rows_writes_nothing(tmp_path):
    path = tmp_path / "results.parquet"
    store = append_results(open_batch_results_file(str(path)), _rows(["A"]), str(path))
    written_at = path.stat().st_mtime_ns

    returned = append_results(store, [], str(path))

    assert path.stat().st_mtime_ns == written_at
    pdt.assert_frame_equal(returned, store)


def test_appending_no_rows_to_a_missing_file_creates_nothing(tmp_path):
    path = tmp_path / "results.parquet"

    append_results(open_batch_results_file(str(path)), [], str(path))

    assert not path.exists()
