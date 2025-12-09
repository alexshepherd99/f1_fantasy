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
        )
    assert str(excinfo.value) == "Multiple entries found for Driver VER in race 1"

    # Even though there are multiple entries for race 2, no exception as we're not checking race 2
    driver_0 = factory_driver(
        pd.DataFrame(
            columns=["Driver", "Race", "col", "Price", "Points"],
            data=[["VER", 1, 3.3, 0.3, 13], ["VER", 2, 4.4, 0.4, 14], ["VER", 2, 5.5, 0.5, 15]]
        ),
        "VER",
        "RED",
        1,
    )
    assert driver_0.constructor == "RED"
    assert driver_0.driver == "VER"
    assert driver_0.derivs["col"] == 3.3
    assert driver_0.price == 0.3
    assert driver_0.points == 13

    driver_1 = factory_driver(
        pd.DataFrame(
            columns=["Driver", "Race", "col", "Price", "Points"],
            data=[["VER", 1, 3.3, 33.33, 13], ["VER", 2, 4.4, 44.44, 14]]
        ),
        "VER",
        "RED",
        2,
    )
    assert driver_1.constructor == "RED"
    assert driver_1.driver == "VER"
    assert driver_1.derivs["col"] == 4.4
    assert driver_1.price == 44.44
    assert driver_1.points == 14

    driver_2 = factory_driver(
        pd.DataFrame(
            columns=["Driver", "Race", "col", "Price", "Points"],
            data=[["VER", 1, 3.3, 33.33, 13]]
        ),
        "VER",
        "RED",
        1,
    )
    assert driver_2.constructor == "RED"
    assert driver_2.driver == "VER"
    assert driver_2.derivs["col"] == 3.3
    assert driver_2.price == 33.33
    assert driver_2.points == 13

    # Derivs column cannot be cast to a float
    with pytest.raises(ValueError):
        factory_driver(
            pd.DataFrame(
                columns=["Driver", "Race", "col", "Price", "Points"],
                data=[["VER", 1, "string", 33.33, 13]]
            ),
            "VER",
            "RED",
            1,
        )

    # Two derived columns
    driver_3 = factory_driver(
        pd.DataFrame(
            columns=["Driver", "Race", "col1", "Price", "Points", "col2"],
            data=[["VER", 1, 0.5, 33.33, 13, 0.6]]
        ),
        "VER",
        "RED",
        1,
    )
    assert driver_3.derivs["col1"] == 0.5
    assert driver_3.derivs["col2"] == 0.6


def test_factory_constructor():
    with pytest.raises(ValueError) as excinfo:
        factory_constructor(
            pd.DataFrame(
                columns=["Constructor", "Race"],
            ),
            "RED",
            1,
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
        )
    assert str(excinfo.value) == "Multiple entries found for Constructor RED in race 1"

    # Even though there are multiple entries for race 2, no exception as we're not checking race 2
    constructor_0 = factory_constructor(
        pd.DataFrame(
            columns=["Constructor", "Race", "col", "Price", "Points"],
            data=[["RED", 1, 3.3, 0.3, 13], ["RED", 2, 4.4, 0.4, 14], ["RED", 2, 5.5, 0.5, 15]]
        ),
        "RED",
        1,
    )
    assert constructor_0.constructor == "RED"
    assert constructor_0.derivs["col"] == 3.3
    assert constructor_0.price == 0.3
    assert constructor_0.points == 13

    constructor_1 = factory_constructor(
        pd.DataFrame(
            columns=["Constructor", "Race", "col", "Price", "Points"],
            data=[["RED", 1, 3.3, 33.33, 13], ["RED", 2, 4.4, 44.44, 14]]
        ),
        "RED",
        2,
    )
    assert constructor_1.constructor == "RED"
    assert constructor_1.derivs["col"] == 4.4
    assert constructor_1.price == 44.44
    assert constructor_1.points == 14

    constructor_2 = factory_constructor(
        pd.DataFrame(
            columns=["Constructor", "Race", "col", "Price", "Points"],
            data=[["RED", 1, 3.3, 33.33, 13]]
        ),
        "RED",
        1,
    )
    assert constructor_2.constructor == "RED"
    assert constructor_2.derivs["col"] == 3.3
    assert constructor_2.price == 33.33
    assert constructor_2.points == 13

    # Derivs column cannot be cast to a float
    with pytest.raises(ValueError):
        factory_constructor(
            pd.DataFrame(
                columns=["Constructor", "Race", "col", "Price", "Points"],
                data=[["RED", 1, "string", 33.33, 13]]
            ),
            "RED",
            1,
        )

    # Two derived columns
    constructor_3 = factory_constructor(
            pd.DataFrame(
                columns=["Constructor", "Race", "col1", "Price", "Points", "col2"],
                data=[["RED", 1, 0.5, 33.33, 13, 0.6]]
            ),
            "RED",
            1,
        )
    assert constructor_3.derivs["col1"] == 0.5
    assert constructor_3.derivs["col2"] == 0.6
