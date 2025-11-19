import pytest

from common import AssetType
from import_data.import_history import load_archive_data_season
from races.team import Team
from races.season import factory_race
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


def test_team_valuation():
    df_driver_2023 = load_archive_data_season(AssetType.DRIVER, 2023)
    df_constructor_2023 = load_archive_data_season(AssetType.CONSTRUCTOR, 2023)
    df_driver_pairs_2023 = get_race_driver_constructor_pairs(df_driver_2023)
    df_driver_ppm_2023 = derivation_cum_tot_driver(df_driver_2023, rolling_window=3)
    df_constructor_ppm_2023 = derivation_cum_tot_constructor(df_constructor_2023, rolling_window=3)

    race_1 = factory_race(
        df_driver_ppm_2023,
        df_constructor_ppm_2023,
        df_driver_pairs_2023,
        1,
        "PPM Cumulative (3)"
    )
	
    team = Team(num_drivers=2, num_constructors=2)
    team.add_asset(asset_type=AssetType.DRIVER, asset="NOR")
    team.add_asset(asset_type=AssetType.DRIVER, asset="VER")
    team.add_asset(asset_type=AssetType.CONSTRUCTOR, asset="FER")
    team.add_asset(asset_type=AssetType.CONSTRUCTOR, asset="RED")

    price = team.total_value(race_1)
    price_old = team.total_value_old(race_1)
	
    assert price == 11.1 + 27.0 + 22.1 + 27.3
    assert price_old == 11.2 + 26.9 + 22.1 + 27.2
