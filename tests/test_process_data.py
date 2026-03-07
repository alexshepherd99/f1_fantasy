import pandas as pd

from external_data.process_data import get_practice_and_rolling_metrics


def test_practice_and_rolling_metrics_end_to_end():
    # exercise the new aggregation function with real fastf1 data
    season = 2025
    race = 5

    df = get_practice_and_rolling_metrics(season, race)

    assert isinstance(df, pd.DataFrame)

    # minimum expected columns should exist
    expected = {
        "Driver",
        "RollingPoints",
        "RollingPointsRank",
        "FP2_TotalLapCount",
        "FP3_TotalLapCount",
        "FP2_MinLapTime_rank",
        "FP3_MinLapTime_rank",
        "Season",
        "Race",
        "AggregageRank",
    }
    assert expected.issubset(set(df.columns)), f"Missing cols: {expected - set(df.columns)}"

    # No additional columns added
    assert "Season_x" not in df.columns
    assert "Season_y" not in df.columns
    assert "Race_x" not in df.columns
    assert "Race_y" not in df.columns

    # season/race columns are consistent with the arguments
    assert df["Season"].nunique() <= 1
    if not df.empty:
        assert df["Season"].iloc[0] == season
        assert df["Race"].iloc[0] == race

    # some basic sanity on the data
    # rolling points ranks should be integer type
    assert pd.api.types.is_integer_dtype(df["RollingPointsRank"])

    # there should be at least one driver with a non-null rolling points rank
    assert df["RollingPointsRank"].notna().any()

    # Run again for first race of the season
    df = get_practice_and_rolling_metrics(2025, 1)
