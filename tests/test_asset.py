import pytest
import pandas as pd
import numpy as np

from races.asset import factory_driver, factory_constructor


def test_factory_driver():
    with pytest.raises(ValueError) as excinfo:
        factory_driver(
            pd.DataFrame(
                columns=["Driver", "Race", "Price"],
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
                columns=["Driver", "Race", "Price"],
                data=[["VER", 1, 0.1], ["VER", 1, 0.1]]
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
                columns=["Driver", "Race", "col", "Price"],
                data=[["VER", 1, 3.3, 0.3], ["VER", 2, 4.4, 0.4], ["VER", 2, 5.5, 0.5]]
            ),
            "VER",
            "RED",
            1,
            "col"
        )
    assert str(excinfo.value) == "Multiple price entries found for Driver VER in race 2"

    driver_1 = factory_driver(
        pd.DataFrame(
            columns=["Driver", "Race", "col", "Price", "Points"],
            data=[["VER", 1, 3.3, 33.33, 13], ["VER", 2, 4.4, 44.44, 14]]
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
    assert driver_1.price_old == 33.33
    assert driver_1.points == 13

    driver_2 = factory_driver(
        pd.DataFrame(
            columns=["Driver", "Race", "col", "Price", "Points"],
            data=[["VER", 1, 3.3, 33.33, 13]]
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
    assert driver_2.price_old == 33.33
    assert driver_2.points == 13


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
                columns=["Constructor", "Race", "col", "Price"],
                data=[["RED", 1, 3.3, 0.3], ["RED", 2, 4.4, 0.4], ["RED", 2, 5.5, 0.5]]
            ),
            "RED",
            1,
            "col"
        )
    assert str(excinfo.value) == "Multiple price entries found for Constructor RED in race 2"

    constructor_1 = factory_constructor(
        pd.DataFrame(
            columns=["Constructor", "Race", "col", "Price", "Points"],
            data=[["RED", 1, 3.3, 33.33, 13], ["RED", 2, 4.4, 44.44, 14]]
        ),
        "RED",
        1,
        "col"
    )
    assert constructor_1.constructor == "RED"
    assert constructor_1.ppm == 3.3
    assert constructor_1.price == 44.44
    assert constructor_1.price_old == 33.33
    assert constructor_1.points == 13

    constructor_2 = factory_constructor(
        pd.DataFrame(
            columns=["Constructor", "Race", "col", "Price", "Points"],
            data=[["RED", 1, 3.3, 33.33, 13]]
        ),
        "RED",
        1,
        "col"
    )
    assert constructor_2.constructor == "RED"
    assert constructor_2.ppm == 3.3
    assert constructor_2.price is np.nan
    assert constructor_2.price_old == 33.33
    assert constructor_2.points == 13
