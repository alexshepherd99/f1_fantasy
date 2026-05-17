"""FastF1 production package skeleton.

The current implementation is intentionally minimal: it preserves the
new package boundary while keeping the legacy ``external_data`` package
untouched. Actual FastF1 wrappers and metric computations will be added
in later steps.
"""

from fast_f1.cache import setup_fastf1_cache
from fast_f1.cli import main as main_cli

__all__ = ["setup_fastf1_cache", "main_cli"]
