from helpers import load_with_derivations
from races.season import factory_season


def test_strategy_factory():
    (df_driver_ppm, df_constructor_ppm, df_driver_pairs) = load_with_derivations(season=2023)
    
    season = factory_season(
        df_driver_ppm,
        df_constructor_ppm,
        df_driver_pairs,
        2023,
        "PPM Cumulative (3)"
    )

    race = season.races[1]

    assert False
