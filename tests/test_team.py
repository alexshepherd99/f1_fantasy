import pytest

from common import AssetType
from import_data.import_history import load_archive_data_season
from races.team import Team, factory_team_row, factory_team_lists
from races.season import Race, factory_race
import numpy as np
from import_data.derivations import (
    derivation_cum_tot_constructor,
    derivation_cum_tot_driver,
    get_race_driver_constructor_pairs,
)


def test_add_asset_success_duplicate_and_limit():
    team = Team(num_drivers=2, num_constructors=1)

    # successful add
    team.add_asset(AssetType.DRIVER, "Hamilton")
    assert "Hamilton" in team.assets[AssetType.DRIVER]

    # duplicate add raises
    with pytest.raises(ValueError, match="already present"):
        team.add_asset(AssetType.DRIVER, "Hamilton")

    # add second driver ok
    team.add_asset(AssetType.DRIVER, "Verstappen")
    assert team.assets[AssetType.DRIVER] == ["Hamilton", "Verstappen"]

    # exceeding driver limit raises
    with pytest.raises(ValueError, match="limit already reached"):
        team.add_asset(AssetType.DRIVER, "Alonso")

    # remove all assets
    team.remove_all_assets()
    assert team.assets[AssetType.DRIVER] == []
    assert team.assets[AssetType.CONSTRUCTOR] == []
    assert len(team.assets.keys()) == 2

    # constructor limit check
    team_c = Team(num_drivers=1, num_constructors=1)
    team_c.add_asset(AssetType.CONSTRUCTOR, "Ferrari")
    with pytest.raises(ValueError, match="limit already reached"):
        team_c.add_asset(AssetType.CONSTRUCTOR, "Mercedes")


def test_remove_asset_success_and_missing():
    team = Team(num_drivers=2, num_constructors=1)

    team.add_asset(AssetType.DRIVER, "Sainz")
    team.add_asset(AssetType.CONSTRUCTOR, "Ferrari")

    # successful remove
    team.remove_asset(AssetType.DRIVER, "Sainz")
    assert "Sainz" not in team.assets[AssetType.DRIVER]

    # removing non-existent driver raises
    with pytest.raises(ValueError, match="asset is not present"):
        team.remove_asset(AssetType.DRIVER, "Nonexistent")

    # constructor removal
    team.remove_asset(AssetType.CONSTRUCTOR, "Ferrari")
    assert "Ferrari" not in team.assets[AssetType.CONSTRUCTOR]

    with pytest.raises(ValueError, match="asset is not present"):
        team.remove_asset(AssetType.CONSTRUCTOR, "Ferrari")


def race_n(race_num) -> Race:
    df_driver_2023 = load_archive_data_season(AssetType.DRIVER, 2023)
    df_constructor_2023 = load_archive_data_season(AssetType.CONSTRUCTOR, 2023)
    df_driver_pairs_2023 = get_race_driver_constructor_pairs(df_driver_2023)
    df_driver_ppm_2023 = derivation_cum_tot_driver(df_driver_2023, rolling_window=3)
    df_constructor_ppm_2023 = derivation_cum_tot_constructor(df_constructor_2023, rolling_window=3)

    return factory_race(
        df_driver_ppm_2023,
        df_constructor_ppm_2023,
        df_driver_pairs_2023,
        race_num,
        "PPM Cumulative (3)"
    )


@pytest.fixture
def race_1() -> Race:
    return race_n(1)


@pytest.fixture
def race_13() -> Race:
    return race_n(13)


def test_team_valuation(race_1, race_13):
    team = Team(num_drivers=2, num_constructors=2, unused_budget=3.1)
    team.add_asset(asset_type=AssetType.DRIVER, asset="NOR")
    team.add_asset(asset_type=AssetType.DRIVER, asset="VER")
    team.add_asset(asset_type=AssetType.CONSTRUCTOR, asset="FER")
    team.add_asset(asset_type=AssetType.CONSTRUCTOR, asset="RED")

    price = team.total_value(race_1, race_13)    
    assert price == 11.2 + 26.9 + 22.1 + 27.2
    assert team.total_budget(race_1, race_13) == price + 3.1

    # When driver is not available in race, use price from previous race
    team2 = Team(num_drivers=2, num_constructors=2, unused_budget=3.1)
    team2.add_asset(asset_type=AssetType.DRIVER, asset="LAW")
    team2.add_asset(asset_type=AssetType.DRIVER, asset="VER")
    team2.add_asset(asset_type=AssetType.CONSTRUCTOR, asset="FER")
    team2.add_asset(asset_type=AssetType.CONSTRUCTOR, asset="RED")

    price2 = team2.total_value(race_1, race_13)    
    assert price2 == 4.5 + 26.9 + 22.1 + 27.2
    assert team2.total_budget(race_1, race_13) == price2 + 3.1


def test_team_size_check(race_1, race_13):
    team = Team(num_drivers=2, num_constructors=2, unused_budget=3.1)
    team.add_asset(asset_type=AssetType.DRIVER, asset="NOR")
    team.add_asset(asset_type=AssetType.DRIVER, asset="VER")
    team.add_asset(asset_type=AssetType.CONSTRUCTOR, asset="FER")
    team.add_asset(asset_type=AssetType.CONSTRUCTOR, asset="RED")
    
    team.asset_count[AssetType.DRIVER] = 3
    with pytest.raises(ValueError, match="Team has incorrect number of assets of type Driver, 2 vs 3"):
        team.total_value(race_1, race_13)

    team.asset_count[AssetType.DRIVER] = 1
    with pytest.raises(ValueError, match="Team has incorrect number of assets of type Driver, 2 vs 1"):
        team.total_value(race_1, race_13)

    team.asset_count[AssetType.DRIVER] = 2
    team.asset_count[AssetType.CONSTRUCTOR] = 3
    with pytest.raises(ValueError, match="Team has incorrect number of assets of type Constructor, 2 vs 3"):
        team.total_value(race_1, race_13)

    team.asset_count[AssetType.CONSTRUCTOR] = 1
    with pytest.raises(ValueError, match="Team has incorrect number of assets of type Constructor, 2 vs 1"):
        team.total_value(race_1, race_13)


def test_factory_team_row(race_1):
    # Build a row dict where exactly the expected number of drivers and constructors
    # are present (price_old values), and all others are NaN
    drivers = list(race_1.drivers.keys())
    constructors = list(race_1.constructors.keys())

    sel_drivers = drivers[:5]
    sel_constructors = constructors[:2]

    row_assets = {}
    total_value = 0.0
    for d in drivers:
        row_assets[d] = race_1.drivers[d].price if d in sel_drivers else np.nan
        total_value += row_assets[d] if not np.isnan(row_assets[d]) else 0.0
    for c in constructors:
        row_assets[c] = race_1.constructors[c].price if c in sel_constructors else np.nan
        total_value += row_assets[c] if not np.isnan(row_assets[c]) else 0.0

    team = factory_team_row(row_assets, race_1, total_budget=100.0)

    # Ensure drivers and constructors were added correctly
    assert set(team.assets[AssetType.DRIVER]) == set(sel_drivers)
    assert len(team.assets[AssetType.DRIVER]) == 5
    assert set(team.assets[AssetType.CONSTRUCTOR]) == set(sel_constructors)
    assert len(team.assets[AssetType.CONSTRUCTOR]) == 2

    row_assets["total_value"] = 9999.99  # should be ignored by factory_team_row

    # Check remaining budget
    assert team.unused_budget == 100.0 - total_value

    # Missing one driver should raise an informative ValueError
    row_missing = row_assets.copy()
    # remove the first selected driver
    row_missing[sel_drivers[0]] = np.nan
    with pytest.raises(ValueError, match="Incorrect number of drivers"):
        factory_team_row(row_missing, race_1)

    # Too many drivers should raise due to the Team driver limit being exceeded
    # Add an extra driver from the remaining pool
    extra_driver = drivers[5]
    row_extra = row_assets.copy()
    row_extra[extra_driver] = race_1.drivers[extra_driver].price
    with pytest.raises(ValueError, match="limit already reached"):
        factory_team_row(row_extra, race_1)


def test_factory_team_lists(race_1):
    drivers = [
         "SAR",  # 4.0
         "HUL",  # 4.3
         "DEV",  # 5.0
         "TSU",  # 4.8
         "ZHO",  # 4.9
    ]
    constructors = [
        "MCL",  # 9.1
        "FER",  # 22.1
    ]
    # total value of 54.2

    t = factory_team_lists(drivers, constructors, race_1, total_budget=90.0)
    assert set(t.assets[AssetType.DRIVER]) == set(drivers)
    assert set(t.assets[AssetType.CONSTRUCTOR]) == set(constructors)
    assert t.unused_budget == 90.0 - 54.2


def test_team_update_points(race_1):
    drivers = [
         "SAR",  # 11
         "HUL",  # -1
         "DEV",  # 8, highest value driver so gets x2 boost
         "TSU",  # 8
         "ZHO",  # 15
    ]
    constructors = [
        "MCL",  # -16   
        "FER",  # 31
    ]
    # total points 56 + 8 bonus = 64

    t = factory_team_lists(drivers, constructors, race_1, total_budget=90.0)
    assert t.total_points == 0

    assert t.update_points(race_1) == 64
    assert t.total_points == 64

    # Repeat update, should add points again
    assert t.update_points(race_1) == 64
    assert t.total_points == 128
