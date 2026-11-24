import pytest

from common import AssetType
from races.asset import Constructor, Driver
from races.season import Race

from backtest.race_one import placeholder_team, race_cap, score_team


def _race(
    race_num: int,
    drivers: dict[str, tuple[float, int]],
    constructors: dict[str, tuple[float, int]],
) -> Race:
    """A race from `identifier -> (price, points)`, each driver's constructor taken from their identifier."""
    return Race(
        race_num,
        {d: Driver(d, d.split("@")[1], price, points, {}) for d, (price, points) in drivers.items()},
        {c: Constructor(c, price, points, {}) for c, (price, points) in constructors.items()},
    )


# Seven drivers and three constructors, the fewest that leave a choice of team
_DRIVERS = {
    "A1@CA": (20.0, 30),
    "A2@CA": (15.0, 10),
    "B1@CB": (10.0, 25),
    "B2@CB": (8.0, 4),
    "C1@CC": (6.0, 12),
    "C2@CC": (5.0, -3),
    "C3@CC": (5.0, 7),
}
_CONSTRUCTORS = {"CA": (25.0, 40), "CB": (15.0, 20), "CC": (10.0, 5)}


def test_race_cap_is_the_starting_budget_at_the_first_race():
    race = _race(1, _DRIVERS, _CONSTRUCTORS)

    assert race_cap(race, race) == pytest.approx(100.0)


def test_race_cap_scales_with_the_whole_grid_price():
    """A grid 10% dearer than at race 1 buys the same share of it with a cap of 110m."""
    first = _race(1, _DRIVERS, _CONSTRUCTORS)
    later = _race(
        5,
        {d: (price * 1.1, points) for d, (price, points) in _DRIVERS.items()},
        {c: (price * 1.1, points) for c, (price, points) in _CONSTRUCTORS.items()},
    )

    assert race_cap(later, first) == pytest.approx(110.0)


def test_race_cap_counts_constructors_as_well_as_drivers():
    """Only the constructors moved, by +11m on a grid of 69m + 50m."""
    first = _race(1, _DRIVERS, _CONSTRUCTORS)
    later = _race(5, _DRIVERS, {"CA": (36.0, 0), "CB": (15.0, 0), "CC": (10.0, 0)})

    assert race_cap(later, first) == pytest.approx(100.0 * 130.0 / 119.0)


def test_placeholder_team_holds_the_cheapest_assets():
    """C2 and C3 tie on price, so both are in; the constructor tie order is by name."""
    team = placeholder_team(_race(1, _DRIVERS, _CONSTRUCTORS | {"CD": (10.0, 0)}))

    assert sorted(team.assets[AssetType.DRIVER]) == ["B1@CB", "B2@CB", "C1@CC", "C2@CC", "C3@CC"]
    assert sorted(team.assets[AssetType.CONSTRUCTOR]) == ["CC", "CD"]
    team.check_asset_counts()


def test_placeholder_team_breaks_a_price_tie_by_name():
    """Six drivers and three constructors at one price, listed in reverse: the first by name are held."""
    drivers = {f"D{i}@CA": (5.0, 0) for i in range(6, 0, -1)}
    constructors = {"CC": (5.0, 0), "CB": (5.0, 0), "CA": (5.0, 0)}

    team = placeholder_team(_race(1, drivers, constructors))

    assert sorted(team.assets[AssetType.DRIVER]) == [f"D{i}@CA" for i in range(1, 6)]
    assert sorted(team.assets[AssetType.CONSTRUCTOR]) == ["CA", "CB"]


_TEAM_DRIVERS = ("A1@CA", "B1@CB", "B2@CB", "C1@CC", "C2@CC")
_TEAM_CONSTRUCTORS = ("CB", "CC")
# 30 + 25 + 4 + 12 - 3 for the drivers, 20 + 5 for the constructors
_TEAM_POINTS = 93


def test_score_team_counts_the_drs_driver_twice():
    race = _race(1, _DRIVERS, _CONSTRUCTORS)

    assert score_team(_TEAM_DRIVERS, _TEAM_CONSTRUCTORS, "B1@CB", race) == _TEAM_POINTS + 25


def test_score_team_with_no_drs_driver_doubles_the_dearest():
    """The game's default, as `Team` applies it: A1 is the dearest driver."""
    race = _race(1, _DRIVERS, _CONSTRUCTORS)

    assert score_team(_TEAM_DRIVERS, _TEAM_CONSTRUCTORS, "", race) == _TEAM_POINTS + 30
