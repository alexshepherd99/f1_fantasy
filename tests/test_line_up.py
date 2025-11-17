import pytest
import pandas as pd
import numpy as np

from races.line_up import factory_driver, factory_constructor, factory_race


def test_factory_driver():
    with pytest.raises(ValueError) as excinfo:
        factory_driver(
            pd.DataFrame(
                columns=["Driver", "Race"],
            ),
            "VER",
            "RED",
            1,
            "col"
        )
    assert str(excinfo.value) == "Driver VER not found for race 1"

    with pytest.raises(ValueError) as excinfo:
        factory_driver(
            pd.DataFrame(
                columns=["Driver", "Race"],
                data=[["VER", 1], ["VER", 1]]
            ),
            "VER",
            "RED",
            1,
            "col"
        )
    assert str(excinfo.value) == "Multiple entries found for Driver VER in race 1"

    with pytest.raises(ValueError) as excinfo:
        factory_driver(
            pd.DataFrame(
                columns=["Driver", "Race", "col"],
                data=[["VER", 1, 3.3], ["VER", 2, 4.4], ["VER", 2, 5.5]]
            ),
            "VER",
            "RED",
            1,
            "col"
        )
    assert str(excinfo.value) == "Multiple price entries found for Driver VER in race 2"

    driver_1 = factory_driver(
        pd.DataFrame(
            columns=["Driver", "Race", "col", "Price"],
            data=[["VER", 1, 3.3, 33.33], ["VER", 2, 4.4, 44.44]]
        ),
        "VER",
        "RED",
        1,
        "col"
    )
    assert driver_1.constructor == "RED"
    assert driver_1.driver == "VER"
    assert driver_1.ppm == 3.3
    assert driver_1.price == 44.44

    driver_2 = factory_driver(
        pd.DataFrame(
            columns=["Driver", "Race", "col", "Price"],
            data=[["VER", 1, 3.3, 33.33]]
        ),
        "VER",
        "RED",
        1,
        "col"
    )
    assert driver_2.constructor == "RED"
    assert driver_2.driver == "VER"
    assert driver_2.ppm == 3.3
    assert driver_2.price is np.nan



def test_factory_constructor():
    with pytest.raises(ValueError) as excinfo:
        factory_constructor(
            pd.DataFrame(
                columns=["Constructor", "Race"],
            ),
            "RED",
            1,
            "col"
        )
    assert str(excinfo.value) == "Constructor RED not found for race 1"

    with pytest.raises(ValueError) as excinfo:
        factory_constructor(
            pd.DataFrame(
                columns=["Constructor", "Race"],
                data=[["RED", 1], ["RED", 1]]
            ),
            "RED",
            1,
            "col"
        )
    assert str(excinfo.value) == "Multiple entries found for Constructor RED in race 1"

    with pytest.raises(ValueError) as excinfo:
        factory_constructor(
            pd.DataFrame(
                columns=["Constructor", "Race", "col"],
                data=[["RED", 1, 3.3], ["RED", 2, 4.4], ["RED", 2, 5.5]]
            ),
            "RED",
            1,
            "col"
        )
    assert str(excinfo.value) == "Multiple price entries found for Constructor RED in race 2"

    constructor_1 = factory_constructor(
        pd.DataFrame(
            columns=["Constructor", "Race", "col", "Price"],
            data=[["RED", 1, 3.3, 33.33], ["RED", 2, 4.4, 44.44]]
        ),
        "RED",
        1,
        "col"
    )
    assert constructor_1.constructor == "RED"
    assert constructor_1.ppm == 3.3
    assert constructor_1.price == 44.44

    constructor_2 = factory_constructor(
        pd.DataFrame(
            columns=["Constructor", "Race", "col", "Price"],
            data=[["RED", 1, 3.3, 33.33]]
        ),
        "RED",
        1,
        "col"
    )
    assert constructor_2.constructor == "RED"
    assert constructor_2.ppm == 3.3
    assert constructor_2.price is np.nan


def test_factory_race():
    race_1 = factory_race(
        pd.DataFrame(
            columns=["Driver", "Race", "col", "Price"],
            data=[["VER", 1, 3.3, 33.33], ["VER", 2, 4.4, 44.44], ["VER", 3, np.nan, 55.55]]
        ),
        pd.DataFrame(
            columns=["Constructor", "Race", "col", "Price"],
            data=[["RED", 1, 6.6, 66.66], ["RED", 2, 7.7, 77.77], ["RED", 3, np.nan, 88.88]]
        ),
        pd.DataFrame(
            columns=["Race", "Constructor", "Driver"],
            data=[[1, "RED", "VER"], [2, "RED", "VER"]]
        ),
        1,
        "col"
    )
    assert race_1.race == 1
    assert len(race_1.drivers) == 1
    assert len(race_1.constructors) == 1
    assert race_1.drivers["VER"].constructor == "RED"
    assert race_1.drivers["VER"].driver == "VER"
    assert race_1.drivers["VER"].ppm == 3.3
    assert race_1.drivers["VER"].price == 44.44
    assert race_1.constructors["RED"].constructor == "RED"
    assert race_1.constructors["RED"].ppm == 6.6
    assert race_1.constructors["RED"].price == 77.77
