import pytest

from common import AssetType
from linear.strategy_odds import load_odds, odds_to_pct


def test_odds_to_pct():
    assert odds_to_pct("100/1") == pytest.approx(0.01, abs=0.001)
    assert odds_to_pct("100:1") == pytest.approx(0.01, abs=0.001)
    assert odds_to_pct("100-1") == pytest.approx(0.01, abs=0.001)
    assert odds_to_pct("10/2") == pytest.approx(0.2, abs=0.001)
    assert odds_to_pct("9/4") == pytest.approx(0.4444, abs=0.0001)

    with pytest.raises(ValueError):
        odds_to_pct(None)
    with pytest.raises(ValueError):
        odds_to_pct("")
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
    assert not load_odds(ass_typ=AssetType.CONSTRUCTOR, season_year=9999, race_num=1)
    assert not load_odds(ass_typ=AssetType.CONSTRUCTOR, season_year=1900, race_num=99)
    assert not load_odds(ass_typ=AssetType.DRIVER, season_year=9999, race_num=1)
    assert not load_odds(ass_typ=AssetType.DRIVER, season_year=1900, race_num=99)

    dict_con = load_odds(ass_typ=AssetType.CONSTRUCTOR, season_year=1900, race_num=1)
    assert len(dict_con) == 2

    dict_con_exp = {
        "CON_test_1": 0.1,
        "CON_test_2": 0.2,
    }
    assert dict_con == dict_con_exp

    dict_drv = load_odds(ass_typ=AssetType.DRIVER, season_year=1900, race_num=1)
    assert len(dict_drv) == 4

    dict_drv_exp = {
        "DRV_test_A@CON_test_1": 0.01,
        "DRV_test_B@CON_test_1": 0.04,
        "DRV_test_C@CON_test_2": 0.222,
        "DRV_test_D@CON_test_2": 0.5,
    }
    for k in dict_drv_exp.keys():
        assert pytest.approx(dict_drv[k], 0.001) == dict_drv_exp[k]
