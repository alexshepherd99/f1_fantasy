import pytest

from common import AssetType
from import_data.odds import load_odds, odds_to_pct

_TEST_ODDS_FILE = "data/test_betting_odds.xlsx"


def test_odds_to_pct():
    # Implied probability of fractional odds a/b is b / (a + b)
    assert odds_to_pct("100/1") == pytest.approx(1 / 101, abs=0.0001)
    assert odds_to_pct("100:1") == pytest.approx(1 / 101, abs=0.0001)
    assert odds_to_pct("100-1") == pytest.approx(1 / 101, abs=0.0001)
    assert odds_to_pct("10/2") == pytest.approx(2 / 12, abs=0.0001)
    assert odds_to_pct("9/4") == pytest.approx(4 / 13, abs=0.0001)
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

    dict_drv = load_odds(ass_typ=AssetType.DRIVER, season_year=1900, race_num=1, fn=_TEST_ODDS_FILE)
    assert len(dict_drv) == 4

    dict_drv_exp = {
        "DRV_test_A@CON_test_1": 1 / 101,   # 100/1
        "DRV_test_B@CON_test_1": 2 / 52,    # 50/2
        "DRV_test_C@CON_test_2": 2 / 11,    # 9/2
        "DRV_test_D@CON_test_2": 4 / 12,    # 8/4
    }
    for k in dict_drv_exp.keys():
        assert pytest.approx(dict_drv[k], 0.001) == dict_drv_exp[k]

    dict_con = load_odds(ass_typ=AssetType.CONSTRUCTOR, season_year=1900, race_num=1, fn=_TEST_ODDS_FILE)
    assert len(dict_con) == 2

    dict_con_exp = {
        "CON_test_1": 1 / 101 + 2 / 52,
        "CON_test_2": 2 / 11 + 4 / 12,
    }
    for k in dict_con_exp.keys():
        assert pytest.approx(dict_con[k], 0.001) == dict_con_exp[k]
