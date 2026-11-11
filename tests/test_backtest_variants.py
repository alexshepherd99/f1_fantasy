import pytest

from backtest.variants import make_variant, with_race4_chip
from helpers import load_with_derivations
from linear.strategy_budget import StrategyMaxBudget
from linear.strategy_factory import factory_strategy
from linear.strategy_p2pm import StrategyMaxP2PM
from linear.strategy_p2pm_no_reset import StrategyMaxP2PMNoReset
from linear.strategy_zero_stop import StrategyZeroStop
from races.season import Season, factory_season
from races.team import Team, factory_team_lists
from simulate.season import run_for_team

_SEASON = 2025


class _StrategyWithExtra(StrategyMaxBudget):
    """A strategy taking a keyword no existing strategy has, to see params arrive.

    It keeps the moves it is given, as the chip tests need, which StrategyZeroStop does not.
    """

    def __init__(self, *args, extra=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.extra = extra


@pytest.fixture(scope="module")
def season() -> Season:
    return factory_season(*load_with_derivations(season=_SEASON), _SEASON)


# A team whose race-4 chip changes P2PM's season, so a run can tell the chip played
_DRIVERS = ["TSU@VRB", "SAI@WIL", "BEA@HAA", "HAD@VRB", "DOO@ALP"]
# Every driver keeps one team to race 5, so a strategy builds at races 3-5, as TSU@VRB's does not
_DRIVERS_TO_RACE_5 = ["ALB@WIL", "SAI@WIL", "BEA@HAA", "HAD@VRB", "DOO@ALP"]


def _team(season: Season, drivers: list[str] = _DRIVERS) -> Team:
    # A fresh team per use, since run_for_team mutates the team it is given
    return factory_team_lists(drivers=drivers, constructors=["MCL", "FER"], race=season.races[1])


def _build(strategy, season: Season, race: int = 2):
    team = _team(season, _DRIVERS_TO_RACE_5)
    return factory_strategy(season.races[race], season.races[race - 1], team, strategy, max_moves=2, season_year=_SEASON)


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


def test_chip_gives_the_whole_team_as_moves_at_race_four(season):
    chip = with_race4_chip(StrategyMaxBudget, "MaxBudget_Chip")
    assert _build(chip, season, race=4)._max_moves == 7


@pytest.mark.parametrize("race", [3, 5])
def test_chip_leaves_the_moves_given_at_other_races(season, race):
    chip = with_race4_chip(StrategyMaxBudget, "MaxBudget_Chip")
    assert _build(chip, season, race=race)._max_moves == 2


def test_chip_name_is_the_label():
    chip = with_race4_chip(StrategyMaxBudget, "MaxBudget_Chip")
    assert chip.__name__ == "MaxBudget_Chip"
    assert issubclass(chip, StrategyMaxBudget)


def test_chip_keeps_the_params_of_a_variant_base(season):
    chip = with_race4_chip(make_variant(_StrategyWithExtra, "Extra:7", extra=7), "Extra:7_Chip")
    strat = _build(chip, season, race=4)
    assert (strat.extra, strat._max_moves) == (7, 7)


def test_chip_leaves_the_base_class_unchanged(season):
    with_race4_chip(StrategyMaxBudget, "MaxBudget_Chip")
    assert _build(StrategyMaxBudget, season, race=4)._max_moves == 2


@pytest.mark.parametrize("label", ["", "has space"])
def test_chip_label_empty_or_with_whitespace_raises(label):
    with pytest.raises(ValueError):
        with_race4_chip(StrategyMaxBudget, label)


def test_chip_on_p2pm_without_it_plays_as_p2pm(season):
    """P2PM's chip taken off and put back again gives P2PM's season, race for race."""
    chip = with_race4_chip(StrategyMaxP2PMNoReset, "NoReset_Chip")

    chip_rows = run_for_team(chip, _team(season), season, _SEASON, 1)
    p2pm_rows = run_for_team(StrategyMaxP2PM, _team(season), season, _SEASON, 1)
    no_reset_rows = run_for_team(StrategyMaxP2PMNoReset, _team(season), season, _SEASON, 1)

    assert [row["total_points"] for row in chip_rows] == [row["total_points"] for row in p2pm_rows]
    # Without this, the chip test could pass with the chip doing nothing
    assert [row["total_points"] for row in no_reset_rows] != [row["total_points"] for row in p2pm_rows]
