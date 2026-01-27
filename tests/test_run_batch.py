import pandas as pd
import pandas.testing as pdt
from pathlib import Path

from helpers import load_with_derivations
from linear.strategy_p2pm import StrategyMaxP2PM
from races.season import factory_season
from races.team import factory_team_lists
from scripts.run_multiple_teams import open_batch_results_file
from scripts.run_single_team import run_for_team


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


def test_run_single_batch():
    # Basic test, if any of the function signatures have changed, this should pick it up
    
    (df_driver_ppm, df_constructor_ppm, df_driver_pairs) = load_with_derivations(season=2025)
    
    _season = factory_season(
        df_driver_ppm,
        df_constructor_ppm,
        df_driver_pairs,
        2025,
    )

    # This will calculate the unused budget based on starting prices
    _team = factory_team_lists(
        drivers=["TSU@VRB", "SAI@WIL", "BEA@HAA", "HAD@VRB", "DOO@ALP"],
        constructors=["MCL", "FER"],
        race=_season.races[1],
    )

    rows = run_for_team(StrategyMaxP2PM, _team, _season, 2025, 1)

    assert len(rows) == 24
