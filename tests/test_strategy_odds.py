import pytest

from common import AssetType
from linear.strategy_odds import StrategyBettingOdds, load_odds, odds_to_pct
from linear.strategy_base import VarType

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

    dict_con = load_odds(ass_typ=AssetType.CONSTRUCTOR, season_year=1900, race_num=1, fn=_TEST_ODDS_FILE)
    assert len(dict_con) == 2

    dict_con_exp = {
        "CON_test_1": 0.05,
        "CON_test_2": 0.722,
    }
    for k in dict_con_exp.keys():
        assert pytest.approx(dict_con[k], 0.001) == dict_con_exp[k]


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
    assert strat._odds_assets["CON_test_1"] == 0.05


def test_strategy_odds_missing_assets():
    # Add extra constructor and extra driver which isn't in odds data, check that odds for these is set to 0.0
    strat = StrategyBettingOdds(
        fn_odds=_TEST_ODDS_FILE,
        team_drivers=["NewDrv1"],
        team_constructors=["NewCon1"],
        all_available_drivers=["NewDrv2"],
        all_available_constructors=["NewCon1", "NewCon2"],
        all_available_driver_pairs={"NewDrv2": "NewCon2"},
        prev_available_driver_pairs={},
        max_cost=0.0,
        max_moves=0,
        prices_assets={"NewDrv2": 10.0, "NewCon1": 11.0, "NewCon2": 12.0},
        derivs_assets={},
        race_num=1,
        season_year=1900,
    )
    assert len(strat._odds_assets) == 10
    assert strat._odds_assets["NewDrv1"] == 0.0
    assert strat._odds_assets["NewDrv2"] == 0.0
    assert strat._odds_assets["NewCon1"] == 0.0
    assert strat._odds_assets["NewCon2"] == 0.0


def test_strategy_odds_run():
    # Create a sub-optimal team with many possible moves, check best two moves are applied
    team_drivers = ["Drv1@Con1", "Drv2@Con1"]
    team_constructors = ["Con1", "Con2"]
    all_available_drivers = ["Drv1@Con1", "Drv2@Con1", "Drv3@Con2", "Drv4@Con2", "Drv5@Con3", "Drv6@Con3"]
    all_available_constructors = ["Con1", "Con2", "Con3"]
    all_available_driver_pairs = {
        "Drv1@Con1": "Con1",
        "Drv2@Con1": "Con1",
        "Drv3@Con2": "Con2",
        "Drv4@Con2": "Con2",
        "Drv5@Con3": "Con3",
        "Drv6@Con3": "Con3",
    }
    prices_assets = {
        "Drv1@Con1": 1.5,
        "Drv2@Con1": 2.5,
        "Drv3@Con2": 4.0,
        "Drv4@Con2": 5.5,
        "Drv5@Con3": 6.0,
        "Drv6@Con3": 7.5,
        "Con1": 6.0,
        "Con2": 8.0,
        "Con3": 12.0,
    }

    strat = StrategyBettingOdds(
        fn_odds=_TEST_ODDS_FILE,
        team_drivers=team_drivers,
        team_constructors=team_constructors,
        all_available_drivers=all_available_drivers,
        all_available_constructors=all_available_constructors,
        all_available_driver_pairs=all_available_driver_pairs,
        prev_available_driver_pairs={},
        max_cost=60.0,  # money is no object here
        max_moves=3,
        prices_assets=prices_assets,
        derivs_assets={},
        race_num=1,
        season_year=1900,
    )

    # Override the odds - we want cheaper options to be more appealing
    strat._odds_assets = {
        "Drv1@Con1": 0.2,
        "Drv2@Con1": 0.3,
        "Drv3@Con2": 0.9,
        "Drv4@Con2": 0.8,  # this is more expensive than Drv3, but Drv3 should get DRS
        "Drv5@Con3": 0.4,
        "Drv6@Con3": 0.5,
        "Con1": 0.4,
        "Con2": 0.5,
        "Con3": 0.6,  # Give slight preference to this one
    }

    # Execute and extract results
    problem = strat.execute()
    drivers = strat._lp_variables[VarType.TeamDrivers]
    constructors = strat._lp_variables[VarType.TeamConstructors]
    
    # Should select high P2PM drivers
    assert drivers["Drv1@Con1"].value() == 0.0
    assert drivers["Drv2@Con1"].value() == 0.0
    assert drivers["Drv3@Con2"].value() == 1.0
    assert drivers["Drv4@Con2"].value() == 1.0
    assert drivers["Drv5@Con3"].value() == 0.0
    assert drivers["Drv6@Con3"].value() == 0.0
    assert constructors["Con1"].value() == 0.0
    assert constructors["Con2"].value() == 1.0
    assert constructors["Con3"].value() == 1.0

    assert strat._lp_variables[VarType.Concentration].value() == 3.0

    # DRS driver should be highest odds, not highest price
    assert strat.get_drs_driver() == "Drv3@Con2"


def test_concentration_variable():
    """Test that concentration variable correctly tracks driver-constructor pairing.
    
    Concentration measures how many drivers are paired with their selected constructor.
    """
    
    # Scenario 1: Two drivers from same constructor, constructor selected
    # Expected: concentration = 3 (1 driver-driver pair + 2 driver-constructor pairs)
    strat1 = StrategyBettingOdds(
        fn_odds=_TEST_ODDS_FILE,
        team_drivers=["Drv1@Con1", "Drv2@Con1"],
        team_constructors=["Con1"],
        all_available_drivers=["Drv1@Con1", "Drv2@Con1", "Drv3@Con2", "Drv4@Con3"],
        all_available_constructors=["Con1", "Con2", "Con3"],
        all_available_driver_pairs={
            "Drv1@Con1": "Con1",
            "Drv2@Con1": "Con1",
            "Drv3@Con2": "Con2",
            "Drv4@Con3": "Con3",
        },
        prev_available_driver_pairs={},
        max_cost=1000.0,
        max_moves=10,
        prices_assets={
            "Drv1@Con1": 1.0, "Drv2@Con1": 1.0, "Drv3@Con2": 1.0, "Drv4@Con3": 1.0,
            "Con1": 1.0, "Con2": 1.0, "Con3": 1.0,
        },
        derivs_assets={},
        race_num=1,
        season_year=1900,
    )
    # Make both Con1 drivers attractive (keep existing team)
    strat1._odds_assets = {
        "Drv1@Con1": 10.0, "Drv2@Con1": 10.0, "Drv3@Con2": 0.0, "Drv4@Con3": 0.0,
        "Con1": 10.0, "Con2": 0.0, "Con3": 0.0,
    }
    strat1.execute()
    conc1 = strat1._lp_variables[VarType.Concentration].value()
    assert conc1 == pytest.approx(3.0, abs=0.01), f"Scenario 1: Expected concentration 3.0, got {conc1}"

    # Scenario 2: One driver from selected constructor
    # Expected: concentration = 1
    strat2 = StrategyBettingOdds(
        fn_odds=_TEST_ODDS_FILE,
        team_drivers=["Drv1@Con1"],
        team_constructors=["Con1"],
        all_available_drivers=["Drv1@Con1", "Drv2@Con2", "Drv3@Con3"],
        all_available_constructors=["Con1", "Con2", "Con3"],
        all_available_driver_pairs={
            "Drv1@Con1": "Con1",
            "Drv2@Con2": "Con2",
            "Drv3@Con3": "Con3",
        },
        prev_available_driver_pairs={},
        max_cost=1000.0,
        max_moves=10,
        prices_assets={
            "Drv1@Con1": 1.0, "Drv2@Con2": 1.0, "Drv3@Con3": 1.0,
            "Con1": 1.0, "Con2": 1.0, "Con3": 1.0,
        },
        derivs_assets={},
        race_num=1,
        season_year=1900,
    )
    strat2._odds_assets = {
        "Drv1@Con1": 10.0, "Drv2@Con2": 0.0, "Drv3@Con3": 0.0,
        "Con1": 10.0, "Con2": 0.0, "Con3": 0.0,
    }
    strat2.execute()
    conc2 = strat2._lp_variables[VarType.Concentration].value()
    assert conc2 == pytest.approx(1.0, abs=0.01), f"Scenario 2: Expected concentration 1.0, got {conc2}"

    # Scenario 3: No drivers from selected constructors
    # Expected: concentration = 0
    strat3 = StrategyBettingOdds(
        fn_odds=_TEST_ODDS_FILE,
        team_drivers=["Drv1@Con1"],
        team_constructors=["Con1"],
        all_available_drivers=["Drv1@Con1", "Drv2@Con2", "Drv3@Con3"],
        all_available_constructors=["Con1", "Con2", "Con3"],
        all_available_driver_pairs={
            "Drv1@Con1": "Con1",
            "Drv2@Con2": "Con2",
            "Drv3@Con3": "Con3",
        },
        prev_available_driver_pairs={},
        max_cost=1000.0,
        max_moves=10,
        prices_assets={
            "Drv1@Con1": 1.0, "Drv2@Con2": 1.0, "Drv3@Con3": 1.0,
            "Con1": 1.0, "Con2": 1.0, "Con3": 1.0,
        },
        derivs_assets={},
        race_num=1,
        season_year=1900,
    )
    # Only selected constructor is attractive for value
    strat3._odds_assets = {
        "Drv1@Con1": 0.0, "Drv2@Con2": 10.0, "Drv3@Con3": 10.0,
        "Con1": 10.0, "Con2": 0.0, "Con3": 0.0,
    }
    strat3.execute()
    conc3 = strat3._lp_variables[VarType.Concentration].value()
    assert conc3 == pytest.approx(0.0, abs=0.01), f"Scenario 3: Expected concentration 0.0, got {conc3}"

    # Scenario 4: Multiple selected constructors, each with paired driver
    # Expected: concentration = 2 (1 driver from Con1 + 1 driver from Con2)
    strat4 = StrategyBettingOdds(
        fn_odds=_TEST_ODDS_FILE,
        team_drivers=["Drv1@Con1", "Drv2@Con2"],
        team_constructors=["Con1", "Con2"],
        all_available_drivers=["Drv1@Con1", "Drv2@Con2", "Drv3@Con3"],
        all_available_constructors=["Con1", "Con2", "Con3"],
        all_available_driver_pairs={
            "Drv1@Con1": "Con1",
            "Drv2@Con2": "Con2",
            "Drv3@Con3": "Con3",
        },
        prev_available_driver_pairs={},
        max_cost=1000.0,
        max_moves=10,
        prices_assets={
            "Drv1@Con1": 1.0, "Drv2@Con2": 1.0, "Drv3@Con3": 1.0,
            "Con1": 1.0, "Con2": 1.0, "Con3": 1.0,
        },
        derivs_assets={},
        race_num=1,
        season_year=1900,
    )
    # Make both selected constructors' drivers attractive (keep existing team)
    strat4._odds_assets = {
        "Drv1@Con1": 10.0, "Drv2@Con2": 10.0, "Drv3@Con3": 0.0,
        "Con1": 10.0, "Con2": 10.0, "Con3": 0.0,
    }
    strat4.execute()
    conc4 = strat4._lp_variables[VarType.Concentration].value()
    assert conc4 == pytest.approx(2.0, abs=0.01), f"Scenario 4: Expected concentration 2.0, got {conc4}"

    # Scenario 5: Constructor selected but no drivers from it
    # Expected: concentration = 0
    strat5 = StrategyBettingOdds(
        fn_odds=_TEST_ODDS_FILE,
        team_drivers=["Drv1@Con1"],
        team_constructors=["Con1"],
        all_available_drivers=["Drv1@Con1", "Drv2@Con2", "Drv3@Con3"],
        all_available_constructors=["Con1", "Con2", "Con3"],
        all_available_driver_pairs={
            "Drv1@Con1": "Con1",
            "Drv2@Con2": "Con2",
            "Drv3@Con3": "Con3",
        },
        prev_available_driver_pairs={},
        max_cost=1000.0,
        max_moves=10,
        prices_assets={
            "Drv1@Con1": 1.0, "Drv2@Con2": 1.0, "Drv3@Con3": 1.0,
            "Con1": 10.0, "Con2": 0.0, "Con3": 0.0,
        },
        derivs_assets={},
        race_num=1,
        season_year=1900,
    )
    # Constructor is expensive, drivers are cheap
    strat5._odds_assets = {
        "Drv1@Con1": 0.0, "Drv2@Con2": 10.0, "Drv3@Con3": 10.0,
        "Con1": 10.0, "Con2": 0.0, "Con3": 0.0,
    }
    strat5.execute()
    conc5 = strat5._lp_variables[VarType.Concentration].value()
    assert conc5 == pytest.approx(0.0, abs=0.01), f"Scenario 5: Expected concentration 0.0, got {conc5}"
