"""A hand-built world for the live tests: twelve drivers in six constructors, teams of five and two."""

from races.asset import Constructor, Driver
from races.season import Race

PAIRS = {
    "HUL@AUD": "AUD", "BOR@AUD": "AUD",
    "LAW@VRB": "VRB", "LIN@VRB": "VRB",
    "LEC@FER": "FER", "HAM@FER": "FER",
    "PER@CAD": "CAD", "BOT@CAD": "CAD",
    "VER@RED": "RED", "HAD@RED": "RED",
    "RUS@MER": "MER", "ANT@MER": "MER",
}
CONSTRUCTORS = sorted(set(PAIRS.values()))


def make_race(race: int, prices: dict[str, float] | None = None, points: dict[str, int] | None = None,
              drop: tuple[str, ...] = (), derivs: dict[str, dict[str, float]] | None = None) -> Race:
    """A race of the hand-built world.

    Args:
        race: The race number.
        prices: Prices by asset; the rest are 10.
        points: Points by asset; the rest are 0, as the loader gives a race not yet held.
        drop: Drivers not in this race.
        derivs: Each deriv's value by asset; an asset without one gets 0.
    """
    prices = prices or {}
    points = points or {}
    derivs = derivs or {}

    def _args(asset):
        return {"price": prices.get(asset, 10.0), "points": points.get(asset, 0),
                "derivs": {name: values.get(asset, 0.0) for name, values in derivs.items()}}

    drivers = {d: Driver(driver=d, constructor=c, **_args(d)) for d, c in PAIRS.items() if d not in drop}
    constructors = {c: Constructor(constructor=c, **_args(c)) for c in CONSTRUCTORS}
    return Race(race=race, drivers=drivers, constructors=constructors)
