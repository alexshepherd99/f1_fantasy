import pytest

from races.team import Team
from common import AssetType


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

