import pytest

from common import AssetType
from linear.strategy_odds import StrategyBettingOdds, load_odds, odds_to_pct

_TEST_ODDS_FILE = "data/test_betting_odds.xlsx"


def test_odds_to_pct():
    assert odds_to_pct("100/1") == pytest.approx(0.01, abs=0.001)
    assert odds_to_pct("100:1") == pytest.approx(0.01, abs=0.001)
    assert odds_to_pct("100-1") == pytest.approx(0.01, abs=0.001)
    assert odds_to_pct("10/2") == pytest.approx(0.2, abs=0.001)
    assert odds_to_pct("9/4") == pytest.approx(0.4444, abs=0.0001)
    assert odds_to_pct("") == 0.0
    assert odds_to_pct(None) == 0.0

    with pytest.raises(ValueError):
        odds_to_pct("0/100")
    with pytest.raises(ValueError):
        odds_to_pct("100/0")
    with pytest.raises(ValueError):
        odds_to_pct("1/100")
    with pytest.raises(ValueError):
        odds_to_pct("100")
    with pytest.raises(ValueError):
        odds_to_pct("/")
    with pytest.raises(ValueError):
        odds_to_pct("/1")
    with pytest.raises(ValueError):
        odds_to_pct("100/")
    with pytest.raises(ValueError):
        odds_to_pct("100/100/100")
    with pytest.raises(ValueError):
        odds_to_pct("string")


def test_load_odds():
    assert not load_odds(ass_typ=AssetType.CONSTRUCTOR, season_year=9999, race_num=1, fn=_TEST_ODDS_FILE)
    assert not load_odds(ass_typ=AssetType.CONSTRUCTOR, season_year=1900, race_num=99, fn=_TEST_ODDS_FILE)
    assert not load_odds(ass_typ=AssetType.DRIVER, season_year=9999, race_num=1, fn=_TEST_ODDS_FILE)
    assert not load_odds(ass_typ=AssetType.DRIVER, season_year=1900, race_num=99, fn=_TEST_ODDS_FILE)

    dict_con = load_odds(ass_typ=AssetType.CONSTRUCTOR, season_year=1900, race_num=1, fn=_TEST_ODDS_FILE)
    assert len(dict_con) == 2

    dict_con_exp = {
        "CON_test_1": 0.1,
        "CON_test_2": 0.2,
    }
    assert dict_con == dict_con_exp

    dict_drv = load_odds(ass_typ=AssetType.DRIVER, season_year=1900, race_num=1, fn=_TEST_ODDS_FILE)
    assert len(dict_drv) == 4

    dict_drv_exp = {
        "DRV_test_A@CON_test_1": 0.01,
        "DRV_test_B@CON_test_1": 0.04,
        "DRV_test_C@CON_test_2": 0.222,
        "DRV_test_D@CON_test_2": 0.5,
    }
    for k in dict_drv_exp.keys():
        assert pytest.approx(dict_drv[k], 0.001) == dict_drv_exp[k]


def test_strategy_odds_load_data():
    # Basic check to ensure that odds data file is loaded, just check size of data set and one of the keys
    strat = StrategyBettingOdds(
        fn_odds=_TEST_ODDS_FILE,
        team_drivers=[],
        team_constructors=[],
        all_available_drivers=[],
        all_available_constructors=[],
        all_available_driver_pairs={},
        prev_available_driver_pairs={},
        max_cost=0.0,
        max_moves=0,
        prices_assets={},
        derivs_assets={},
        race_num=1,
        season_year=1900,
    )
    assert len(strat._odds_assets) == 6
    assert strat._odds_assets["DRV_test_A@CON_test_1"] == 0.01
    assert strat._odds_assets["CON_test_1"] == 0.1


def test_strategy_odds_missing_assets():
    # Add extra constructor and extra driver which isn't in odds data, check that odds for these is set to 0.0
    assert False


def test_strategy_odds_check_assets():
    # Check that driver odds are directly taken from file, and constructor odds are doubled to reflect extra value
    assert False


def test_strategy_odds_run():
    # Create a sub-optimal team with many possible moves, check best two moves are applied
    assert False


def test_strategy_odds_select_drs():
    # DRS selection should pick the driver with the best odds, not the highest value
    assert False
