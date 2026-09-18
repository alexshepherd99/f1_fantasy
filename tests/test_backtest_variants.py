import pytest

from backtest.variants import make_variant
from helpers import load_with_derivations
from linear.strategy_factory import factory_strategy
from linear.strategy_p2pm import StrategyMaxP2PM
from linear.strategy_zero_stop import StrategyZeroStop
from races.season import Season, factory_season
from races.team import Team, factory_team_lists
from scripts.run_single_team import run_for_team

_SEASON = 2025


class _StrategyWithExtra(StrategyZeroStop):
    """A strategy taking a keyword no existing strategy has, to see params arrive."""

    def __init__(self, *args, extra=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.extra = extra


@pytest.fixture(scope="module")
def season() -> Season:
    return factory_season(*load_with_derivations(season=_SEASON), _SEASON)


def _team(season: Season) -> Team:
    # A fresh team per use, since run_for_team mutates the team it is given
    return factory_team_lists(
        drivers=["TSU@VRB", "SAI@WIL", "BEA@HAA", "HAD@VRB", "DOO@ALP"],
        constructors=["MCL", "FER"],
        race=season.races[1],
    )


def _build(strategy, season: Season):
    return factory_strategy(season.races[2], season.races[1], _team(season), strategy, max_moves=2, season_year=_SEASON)


def test_name_is_the_label():
    variant = make_variant(StrategyMaxP2PM, "StrategyMaxP2PM:test=1")
    assert variant.__name__ == "StrategyMaxP2PM:test=1"
    assert issubclass(variant, StrategyMaxP2PM)


def test_params_reach_init(season):
    variant = make_variant(_StrategyWithExtra, "Extra:7", extra=7)
    assert _build(variant, season).extra == 7


def test_base_class_is_left_unchanged(season):
    make_variant(_StrategyWithExtra, "Extra:7", extra=7)
    assert _build(_StrategyWithExtra, season).extra is None


@pytest.mark.parametrize("label", ["", "has space", "has\ttab", "trailing\n"])
def test_label_empty_or_with_whitespace_raises(label):
    with pytest.raises(ValueError):
        make_variant(StrategyMaxP2PM, label)


def test_param_clashing_with_a_factory_keyword_raises(season):
    variant = make_variant(StrategyZeroStop, "ZeroStop:moves=5", max_moves=5)
    with pytest.raises(TypeError):
        _build(variant, season)


def test_variant_run_for_team_labels_rows_and_matches_the_base(season):
    variant = make_variant(StrategyMaxP2PM, "StrategyMaxP2PM:variant")

    variant_rows = run_for_team(variant, _team(season), season, _SEASON, 1)
    base_rows = run_for_team(StrategyMaxP2PM, _team(season), season, _SEASON, 1)

    assert {row["strategy"] for row in variant_rows} == {"StrategyMaxP2PM:variant"}
    assert [row["total_points"] for row in variant_rows] == [row["total_points"] for row in base_rows]
