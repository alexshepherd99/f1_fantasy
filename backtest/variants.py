"""Build named, parameterised strategy variants for the back-test."""

import logging

from linear.strategy_base import StrategyBase


def make_variant(base: type[StrategyBase], label: str, **params) -> type[StrategyBase]:
    """Return a subclass of `base` named `label` that passes `params` to its constructor.

    `run_for_team` names a strategy's results by its `__name__`, which a
    `functools.partial` lacks, so a variant has to be a class of its own.

    The params are passed alongside the keywords `factory_strategy` supplies, so
    one that shares a name with any of them raises `TypeError` when the strategy
    is built, rather than silently overriding what the engine sets each race.

    Args:
        base: Strategy class to derive from.
        label: Name for the variant, used in results and keys. PuLP names each
            problem after its class and rewrites whitespace, so none is allowed.
        **params: Extra keyword arguments for `base`'s constructor.

    Raises:
        ValueError: If the label is empty or contains whitespace.
    """
    if not label or any(char.isspace() for char in label):
        logging.error(f"Invalid variant label {label!r}")
        raise ValueError(f"Variant label must be non-empty with no whitespace, got {label!r}")

    def __init__(self, *args, **kwargs):
        base.__init__(self, *args, **kwargs, **params)

    return type(label, (base,), {"__init__": __init__})
