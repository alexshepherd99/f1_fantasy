import pytest

from linear.strategy import StrategyBase, COST_PROHIBITIVE


@pytest.fixture
def fixture_asset_prices() -> dict[str, float]:
    return {
        # Drivers
        "VER": 1.0,
        "LEC": 2.0,
        "HAM": 3.0,
        "ALO": 4.0,
        "HUL": 6.5,
        "MAG": 7.0,
        "BOT": 8.0,
        "NOR": 9.0,
        "PIA": 10.0,
        "TSU": 9.5,
        # Constructors
        "MCL": 4.0,
        "FER": 6.0,
        "RED": 5.0,
        "MER": 7.0,
        "AST": 12.0,
    }


@pytest.fixture
def fixture_all_available_drivers() -> list[str]:
    return ["VER", "LEC", "HAM", "ALO", "HUL", "MAG", "BOT", "NOR", "PIA", "TSU"]


@pytest.fixture
def fixture_all_available_constructors() -> list[str]:
    return ["MCL", "FER", "RED", "MER", "AST"]


def test_construct(
        fixture_all_available_drivers,
        fixture_all_available_constructors,
        fixture_asset_prices,
    ):
    # Team constructors all present in all available constructors
    with pytest.raises(ValueError) as excinfo:
        StrategyBase(
            team_drivers=[],
            team_constructors=["???"],
            all_available_drivers=[],
            all_available_constructors=fixture_all_available_constructors,
            all_available_driver_pairs={},
            max_cost=0.0,
            max_moves=2,
            prices_assets={}
        );
    assert str(excinfo.value) == "Cannot find team constructor ??? in all available constructors"

    # Team count drivers greater than count of available drivers
    with pytest.raises(ValueError) as excinfo:
        StrategyBase(
            team_drivers=["A", "A", "A", "A", "A", "A", "A", "A", "A", "A", "A",],
            team_constructors=[],
            all_available_drivers=fixture_all_available_drivers,
            all_available_constructors=[],
            all_available_driver_pairs={},
            max_cost=0.0,
            max_moves=2,
            prices_assets={}
        )
    assert str(excinfo.value) == "Team count of 11 is greater than 10 available drivers"

    # Team count constructors greater than count of available constructors
    with pytest.raises(ValueError) as excinfo:
        StrategyBase(
            team_drivers=[],
            team_constructors=["MCL", "MCL", "MCL", "MCL", "MCL", "MCL",],
            all_available_drivers=[],
            all_available_constructors=fixture_all_available_constructors,
            all_available_driver_pairs={},
            max_cost=0.0,
            max_moves=2,
            prices_assets={}
        )
    assert str(excinfo.value) == "Team count of 6 is greater than 5 available constructors"

    # All available drivers have a price
    with pytest.raises(ValueError) as excinfo:
        StrategyBase(
            team_drivers=[],
            team_constructors=[],
            all_available_drivers=fixture_all_available_drivers + ["XXX"],
            all_available_constructors=[],
            all_available_driver_pairs={},
            max_cost=0.0,
            max_moves=2,
            prices_assets=fixture_asset_prices
        )
    assert str(excinfo.value) == "Driver XXX does not have a price"

    # All available constructors have a price
    with pytest.raises(ValueError) as excinfo:
        StrategyBase(
            team_drivers=[],
            team_constructors=[],
            all_available_drivers=[],
            all_available_constructors=fixture_all_available_constructors + ["XXX"],
            all_available_driver_pairs={},
            max_cost=0.0,
            max_moves=2,
            prices_assets=fixture_asset_prices
        )
    assert str(excinfo.value) == "Constructor XXX does not have a price"

    # Team drivers not available in all available drivers have a high price
    sb = StrategyBase(
            team_drivers=["VER", "RUS"],
            team_constructors=["MCL"],
            all_available_drivers=fixture_all_available_drivers,
            all_available_constructors=fixture_all_available_constructors,
            all_available_driver_pairs={},
            max_cost=0.0,
            max_moves=2,
            prices_assets=fixture_asset_prices
        )
    assert len(sb._prices_assets) == len(fixture_asset_prices) + 1
    assert sb._prices_assets["RUS"] == COST_PROHIBITIVE

    # Everything in price assets is available in either all drivers or all constructors (check both)
    # All driver pairs keys are in all available drivers
    # All driver pairs values are in all available constructors
    assert False
