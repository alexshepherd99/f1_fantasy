import pytest
import pandas as pd
from pandas.testing import assert_frame_equal

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


def test_load_odds_no_extras():
    assert load_odds(ass_typ=AssetType.CONSTRUCTOR, season_year=9999, race_num=1).empty
    assert load_odds(ass_typ=AssetType.CONSTRUCTOR, season_year=1900, race_num=99).empty
    assert load_odds(ass_typ=AssetType.DRIVER, season_year=9999, race_num=1).empty
    assert load_odds(ass_typ=AssetType.DRIVER, season_year=1900, race_num=99).empty

    df_con_no_extras = load_odds(ass_typ=AssetType.CONSTRUCTOR, season_year=1900, race_num=1)
    assert len(df_con_no_extras) == 2

    df_con_no_extras_exp = pd.DataFrame(
        columns=["Constructor", "Season", "Race", "Odds"],
        data=[
            ["CON_test_1", 1900, 1, 0.1],
            ["CON_test_2", 1900, 1, 0.2],
        ],
    )
    assert_frame_equal(df_con_no_extras.reset_index(drop=True), df_con_no_extras_exp)

    df_drv_no_expected = load_odds(ass_typ=AssetType.DRIVER, season_year=1900, race_num=1)
    assert len(df_drv_no_expected) == 4

    df_drv_no_extras_exp = pd.DataFrame(
        columns=["Driver", "Constructor", "Season", "Race", "Odds"],
        data=[
            ["DRV_test_A@CON_test_1", "CON_test_1", 1900, 1, 0.01],
            ["DRV_test_B@CON_test_1", "CON_test_1", 1900, 1, 0.04],
            ["DRV_test_C@CON_test_2", "CON_test_2", 1900, 1, 0.222],
            ["DRV_test_D@CON_test_2", "CON_test_2", 1900, 1, 0.5],
        ],
    )
    assert_frame_equal(df_drv_no_expected.reset_index(drop=True), df_drv_no_extras_exp, atol=0.001)
