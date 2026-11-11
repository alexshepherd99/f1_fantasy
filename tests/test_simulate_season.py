import json

import pytest

from helpers import load_with_derivations
from linear.strategy_fastf1 import StrategyFastF1RuleRise
from linear.strategy_p2pm import StrategyMaxP2PM
from races.season import factory_season
from races.team import factory_team_lists
from simulate.season import run_for_team

# Every per-race row of a 2025 season for two strategies, recorded from the code
# before live_picks_v1 moved run_for_team (its D3): the back-test must not change
_FILE_PINNED_ROWS = "data/test_run_for_team_2025.json"


@pytest.fixture(scope="module")
def season_2025():
    return factory_season(*load_with_derivations(season=2025), 2025)


@pytest.mark.parametrize("strategy", [StrategyMaxP2PM, StrategyFastF1RuleRise])
def test_run_for_team_matches_the_pinned_rows(season_2025, strategy):
    with open(_FILE_PINNED_ROWS) as f:
        pinned = json.load(f)[strategy.__name__]
    team = factory_team_lists(
        drivers=["TSU@VRB", "SAI@WIL", "BEA@HAA", "HAD@VRB", "DOO@ALP"],
        constructors=["MCL", "FER"],
        race=season_2025.races[1],
    )

    rows = run_for_team(strategy, team, season_2025, 2025, 1)

    assert len(rows) == 24
    for row, pinned_row in zip(rows, pinned):
        assert row == pinned_row, f"race {pinned_row['race']}"
