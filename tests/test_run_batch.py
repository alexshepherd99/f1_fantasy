import pandas as pd
import pandas.testing as pdt
from pathlib import Path

from scripts.run_multiple_teams import open_batch_results_file


def test_load_nonexistent_returns_empty(tmp_path: Path):
    path = tmp_path / "does_not_exist.xlsx"
    # ensure it really doesn't exist
    assert not path.exists()

    df = open_batch_results_file(str(path))

    assert isinstance(df, pd.DataFrame)
    assert df.empty


def test_load_existing_reads_file(tmp_path: Path):
    data = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    file = tmp_path / "data.xlsx"
    data.to_parquet(file)

    loaded = open_batch_results_file(str(file))

    # DataFrame equality check
    pdt.assert_frame_equal(loaded.reset_index(drop=True), data.reset_index(drop=True))
