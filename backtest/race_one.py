"""odds_fp3_v1's single-race back-test: each weekend scored as if it were a season's first race.

See ``docs/odds_fp3_v1/requirements.md``, R7-R9.
"""
from collections.abc import Iterable

from common import DEFAULT_STARTING_BUDGET, AssetType
from races.season import Race
from races.team import Team
from simulate.pick import limitless_cap

NUM_DRIVERS = 5
NUM_CONSTRUCTORS = 2


def race_cap(race: Race, first_race: Race) -> float:
    """The budget cap for a team picked from scratch at `race` (R8).

    The starting budget scaled by the whole grid's price at `race` against `first_race`, so a
    later race buys the same share of the field as race 1 does.
    """
    return DEFAULT_STARTING_BUDGET * limitless_cap(race) / limitless_cap(first_race)


def placeholder_team(race: Race) -> Team:
    """The race's cheapest drivers and constructors, ties by name, as a team to pick from.

    `StrategyBase` sizes the team from the team it is given, so a pick from scratch needs a
    team held. With every move allowed and the cap given, which team it is cannot change the
    pick. The same rule as `live.lineup`'s race-1 options.
    """
    team = Team(num_drivers=NUM_DRIVERS, num_constructors=NUM_CONSTRUCTORS, unused_budget=0.0)
    for driver in sorted(race.drivers, key=lambda d: (race.drivers[d].price, d))[:NUM_DRIVERS]:
        team.add_asset(AssetType.DRIVER, driver)
    for constructor in sorted(race.constructors, key=lambda c: (race.constructors[c].price, c))[:NUM_CONSTRUCTORS]:
        team.add_asset(AssetType.CONSTRUCTOR, constructor)
    return team


def score_team(drivers: Iterable[str], constructors: Iterable[str], drs_driver: str, race: Race) -> int:
    """The team's fantasy points at `race`, with the DRS driver counted twice.

    An empty `drs_driver` leaves DRS to the game's default, the dearest driver, as `Team` applies it.

    Raises:
        ValueError: The team is not 5 drivers and 2 constructors.
    """
    team = Team(num_drivers=NUM_DRIVERS, num_constructors=NUM_CONSTRUCTORS)
    for driver in drivers:
        team.add_asset(AssetType.DRIVER, driver)
    for constructor in constructors:
        team.add_asset(AssetType.CONSTRUCTOR, constructor)
    team.drs_driver = drs_driver
    return team.update_points(race)
