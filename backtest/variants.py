"""Build named, parameterised strategy variants for the back-test."""

import logging

from linear.strategy_base import StrategyBase

# The race StrategyMaxP2PM plays its unlimited-moves chip at: the first with a full
# three-race rolling window
CHIP_RACE = 4


def _check_label(label: str) -> None:
    """Raise if `label` cannot name a strategy class.

    PuLP names each problem after its class and rewrites whitespace, so none is allowed.

    Raises:
        ValueError: If the label is empty or contains whitespace.
    """
    if not label or any(char.isspace() for char in label):
        logging.error(f"Invalid variant label {label!r}")
        raise ValueError(f"Variant label must be non-empty with no whitespace, got {label!r}")


def make_variant(base: type[StrategyBase], label: str, **params) -> type[StrategyBase]:
    """Return a subclass of `base` named `label` that passes `params` to its constructor.

    `run_for_team` names a strategy's results by its `__name__`, which a
    `functools.partial` lacks, so a variant has to be a class of its own.

    The params are passed alongside the keywords `factory_strategy` supplies, so
    one that shares a name with any of them raises `TypeError` when the strategy
    is built, rather than silently overriding what the engine sets each race.

    Args:
        base: Strategy class to derive from.
        label: Name for the variant, used in results and keys. No whitespace is allowed.
        **params: Extra keyword arguments for `base`'s constructor.

    Raises:
        ValueError: If the label is empty or contains whitespace.
    """
    _check_label(label)

    def __init__(self, *args, **kwargs):
        base.__init__(self, *args, **kwargs, **params)

    return type(label, (base,), {"__init__": __init__})


def with_race4_chip(base: type[StrategyBase], label: str) -> type[StrategyBase]:
    """Return a subclass of `base` named `label` that plays the unlimited-moves chip at race 4.

    At `CHIP_RACE` the whole team may be moved, as `StrategyMaxP2PM.__init__` allows,
    and every other race keeps the moves `base` leaves. The moves are set after
    `base.__init__`, and `StrategyBase` reads them only when `execute()` builds the
    problem. Those lines are copied from P2PM, which is not edited while it picks the
    live team (R12 ledger, `docs/backtest_v1/requirements.md`).

    Args:
        base: Strategy class to derive from, which may itself be a variant.
        label: Name for the variant, used in results and keys. No whitespace is allowed.

    Raises:
        ValueError: If the label is empty or contains whitespace.
    """
    _check_label(label)

    def __init__(self, *args, **kwargs):
        base.__init__(self, *args, **kwargs)
        if self._race_num == CHIP_RACE:
            self._max_moves = len(self._team_drivers) + len(self._team_constructors)

    return type(label, (base,), {"__init__": __init__})
