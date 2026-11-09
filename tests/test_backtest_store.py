from pathlib import Path

import pandas as pd
import pandas.testing as pdt

from backtest.store import get_starting_key, open_batch_results_file
from helpers import load_with_derivations
from races.season import factory_race
from races.team import factory_team_lists


def test_load_nonexistent_returns_empty(tmp_path: Path):
    path = tmp_path / "does_not_exist.parquet"
    assert not path.exists()

    df = open_batch_results_file(str(path))

    assert isinstance(df, pd.DataFrame)
    assert df.empty


def test_load_existing_reads_file(tmp_path: Path):
    data = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    file = tmp_path / "data.parquet"
    data.to_parquet(file)

    loaded = open_batch_results_file(str(file))

    pdt.assert_frame_equal(loaded.reset_index(drop=True), data.reset_index(drop=True))


def test_starting_key_format_is_unchanged():
    # Existing stores resume by this exact key, so its format must never drift
    (df_driver_ppm, df_constructor_ppm, df_driver_pairs) = load_with_derivations(season=2025)
    race = factory_race(df_driver_ppm, df_constructor_ppm, df_driver_pairs, 1)
    team = factory_team_lists(
        drivers=["TSU@VRB", "SAI@WIL", "BEA@HAA", "HAD@VRB", "DOO@ALP"],
        constructors=["MCL", "FER"],
        race=race,
    )

    key = get_starting_key("StrategyZeroStop", 2025, team)

    assert key == "(StrategyZeroStop)(2025)(BEA@HAA,DOO@ALP,HAD@VRB,SAI@WIL,TSU@VRB)(FER,MCL)"
