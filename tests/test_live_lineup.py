import pytest

from common import AssetType
from import_data.derivations import DerivationType, get_derivation_name
from linear.strategy_fastf1 import StrategyFastF1RuleRise
from linear.strategy_p2pm import StrategyMaxP2PM
from linear.strategy_p2pm_no_reset import StrategyMaxP2PMNoReset
from live.display import default_drs
from live.lineup import add_to_lineup, fastf1_strategy, has_signal, implied_chip, run_lineup, strategies_for
from races.team import Team
from tests.live_fixtures import make_race

P2PM = get_derivation_name(DerivationType.P2PM_CUMULATIVE, 3)
POINTS = get_derivation_name(DerivationType.POINTS_CUMULATIVE, 3)

HELD_DRIVERS = ["HUL@AUD", "LAW@VRB", "LEC@FER", "PER@CAD", "VER@RED"]
HELD_CONSTRUCTORS = ["FER", "RED"]

# Held assets are worth a little, in a fixed order; HAM, RUS, ANT and MER are worth more
VALUES = {"HUL@AUD": 1.1, "LAW@VRB": 1.2, "LEC@FER": 1.3, "PER@CAD": 1.4, "VER@RED": 1.5, "FER": 1.6, "RED": 1.7,
          "HAM@FER": 5.0, "RUS@MER": 4.0, "ANT@MER": 3.0, "MER": 6.0}


def _team(unused_budget: float = 0.0) -> Team:
    team = Team(unused_budget=unused_budget)
    for d in HELD_DRIVERS:
        team.add_asset(AssetType.DRIVER, d)
    for c in HELD_CONSTRUCTORS:
        team.add_asset(AssetType.CONSTRUCTOR, c)
    return team


def _race(race: int, values: dict[str, float] = VALUES, prices: dict[str, float] | None = None):
    return make_race(race, prices=prices, derivs={P2PM: values, POINTS: {}})


def _picked(option) -> tuple[tuple[str, ...], tuple[str, ...]]:
    return option.pick.drivers, option.pick.constructors


def test_after_race_1_only_p2pm_runs():
    assert strategies_for(2, wildcard_used=False) == [StrategyMaxP2PM]
    assert strategies_for(5, wildcard_used=True) == [StrategyMaxP2PM]


def test_race_4_offers_p2pm_and_its_no_wildcard_twin_while_the_wildcard_is_unused():
    assert strategies_for(4, wildcard_used=False) == [StrategyMaxP2PMNoReset, StrategyMaxP2PM]


def test_race_4_offers_only_the_no_wildcard_twin_once_the_wildcard_is_used():
    assert strategies_for(4, wildcard_used=True) == [StrategyMaxP2PMNoReset]


def test_race_1_is_not_for_the_lineup():
    with pytest.raises(ValueError, match="race 1"):
        strategies_for(1, wildcard_used=False)


def test_p2pm_plays_the_wildcard_only_at_race_4():
    assert implied_chip("StrategyMaxP2PM", 4) == "Wildcard"
    assert implied_chip("StrategyMaxP2PM", 5) == ""
    assert implied_chip("StrategyMaxP2PMNoReset", 4) == ""
    assert implied_chip("Manual", 4) == ""


def test_a_pick_uses_the_free_moves():
    options = run_lineup([StrategyMaxP2PM], _team(), _race(10), _race(9), 2026, free_moves=2)

    assert [o.strategies for o in options] == [("StrategyMaxP2PM",)]
    assert _picked(options[0]) == (("HAM@FER", "LAW@VRB", "LEC@FER", "PER@CAD", "VER@RED"), ("MER", "RED"))
    assert (options[0].pick.moves_used, options[0].pick.cost) == (2, 70.0)


def test_the_wildcard_gives_unlimited_moves():
    options = run_lineup([StrategyMaxP2PM], _team(), _race(10), _race(9), 2026, free_moves=2, chip="Wildcard")

    assert _picked(options[0]) == (("ANT@MER", "HAM@FER", "PER@CAD", "RUS@MER", "VER@RED"), ("MER", "RED"))
    assert options[0].pick.moves_used == 4


def test_limitless_lifts_the_budget_to_every_assets_price():
    expensive = {"HAM@FER": 40.0}

    wildcard = run_lineup([StrategyMaxP2PM], _team(), _race(10, prices=expensive), _race(9), 2026, free_moves=2,
                          chip="Wildcard")
    limitless = run_lineup([StrategyMaxP2PM], _team(), _race(10, prices=expensive), _race(9), 2026, free_moves=2,
                           chip="Limitless")

    assert "HAM@FER" not in wildcard[0].pick.drivers
    assert "HAM@FER" in limitless[0].pick.drivers
    assert limitless[0].pick.cost == 100.0


def test_strategies_picking_the_same_team_merge():
    only_mer = {**{a: v for a, v in VALUES.items() if a not in ("HAM@FER", "RUS@MER", "ANT@MER")}}
    strategies = [StrategyMaxP2PMNoReset, StrategyMaxP2PM]

    options = run_lineup(strategies, _team(), _race(4, only_mer), _race(3), 2026, free_moves=2)

    assert [o.strategies for o in options] == [("StrategyMaxP2PMNoReset", "StrategyMaxP2PM")]
    assert _picked(options[0]) == (tuple(HELD_DRIVERS), ("MER", "RED"))


def test_strategies_picking_different_teams_each_show():
    strategies = [StrategyMaxP2PMNoReset, StrategyMaxP2PM]

    options = run_lineup(strategies, _team(), _race(4), _race(3), 2026, free_moves=2)

    assert [o.strategies for o in options] == [("StrategyMaxP2PMNoReset",), ("StrategyMaxP2PM",)]
    assert [o.pick.moves_used for o in options] == [2, 4]


class _StubTables:
    """Stands in for the FastF1 strategy's ``SignalTables``: set values, and no price rises."""

    def __init__(self, values: dict[str, float]):
        self._values = values

    def values(self, season: int, race: int) -> dict[str, float]:
        return dict(self._values)

    def price_rise(self, season: int, race: int) -> dict[str, float]:
        return {}


@pytest.fixture
def signal_files(monkeypatch) -> dict[str, list]:
    """Give the FastF1 strategy set values in place of a metrics file, recording each file it reads.

    The real tables need the 2023-25 metrics rows matched to the real archive, which the
    hand-built world cannot give, as in ``tests/test_strategy_fastf1.py``.
    """
    files: dict[str, list] = {"read": [], "values": VALUES}

    def _load(fn_metrics):
        files["read"].append(fn_metrics)
        return _StubTables(files["values"])

    monkeypatch.setattr("linear.strategy_fastf1.load_signal_tables", _load)
    return files


def test_a_pick_leaving_drs_to_the_default_is_given_it_before_merging():
    race = _race(10, prices={"VER@RED": 11.0})

    options = run_lineup([StrategyMaxP2PM], _team(unused_budget=1.0), race, _race(9), 2026, free_moves=2)

    assert options[0].pick.drs_driver == default_drs(options[0].pick.drivers, race) == "VER@RED"


def test_the_fastf1_strategy_reads_the_metrics_file_given(signal_files):
    strategy = fastf1_strategy("scratch/metrics.csv")

    options = add_to_lineup([], strategy, _team(), _race(10), _race(9), 2026, free_moves=2)

    assert signal_files["read"] == ["scratch/metrics.csv"]
    assert issubclass(strategy, StrategyFastF1RuleRise)
    assert [o.strategies for o in options] == [("StrategyFastF1RuleRise",)]


def test_a_strategy_added_with_the_same_pick_merges(signal_files):
    options = run_lineup([StrategyMaxP2PM], _team(), _race(10), _race(9), 2026, free_moves=2)

    merged = add_to_lineup(options, fastf1_strategy("m.csv"), _team(), _race(10), _race(9), 2026, free_moves=2)

    assert [o.strategies for o in merged] == [("StrategyMaxP2PM", "StrategyFastF1RuleRise")]
    assert [o.strategies for o in options] == [("StrategyMaxP2PM",)]


def test_a_strategy_added_with_another_pick_shows_after(signal_files):
    signal_files["values"] = {**VALUES, "HAM@FER": 0.1, "HAD@RED": 9.0}
    options = run_lineup([StrategyMaxP2PM], _team(), _race(10), _race(9), 2026, free_moves=2)

    added = add_to_lineup(options, fastf1_strategy("m.csv"), _team(), _race(10), _race(9), 2026, free_moves=2)

    assert [o.strategies for o in added] == [("StrategyMaxP2PM",), ("StrategyFastF1RuleRise",)]
    assert "HAD@RED" in added[1].pick.drivers


def test_a_strategy_added_under_a_chip_gets_its_moves(signal_files):
    options = add_to_lineup([], fastf1_strategy("m.csv"), _team(), _race(10), _race(9), 2026, free_moves=2,
                            chip="Wildcard")

    assert options[0].pick.moves_used == 4


@pytest.mark.parametrize("race, present", [(21, True), (22, False)])
def test_has_signal_reads_the_races_metrics_rows(tmp_path, race, present):
    path = tmp_path / "metrics.csv"
    path.write_text("Season,Race,Driver\n2025,22,VER\n2026,21,VER\n", encoding="utf-8")

    assert has_signal(str(path), 2026, race) == present
