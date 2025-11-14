import pytest
import pandas as pd
import numpy as np

from races.line_up import factory_driver


def test_factory_driver():
    with pytest.raises(ValueError) as excinfo:
        factory_driver(
            pd.DataFrame(
                columns=["Driver", "Season", "Race"],
            ),
            pd.DataFrame(),
            "VER",
            2020,
            1,
            "col"
        )
    assert str(excinfo.value) == "Driver VER not found for season 2020 and race 1"

    with pytest.raises(ValueError) as excinfo:
        factory_driver(
            pd.DataFrame(
                columns=["Driver", "Season", "Race"],
                data=[["VER", 2020, 1], ["VER", 2020, 1]]
            ),
            pd.DataFrame(),
            "VER",
            2020,
            1,
            "col"
        )
    assert str(excinfo.value) == "Multiple entries found for driver VER in season 2020 and race 1"

    with pytest.raises(ValueError) as excinfo:
        factory_driver(
            pd.DataFrame(
                columns=["Driver", "Season", "Race", "col"],
                data=[["VER", 2020, 1, 3.3], ["VER", 2020, 2, 4.4], ["VER", 2020, 2, 5.5]]
            ),
            pd.DataFrame(),
            "VER",
            2020,
            1,
            "col"
        )
    assert str(excinfo.value) == "Multiple price entries found for driver VER in season 2020 and race 2"

    with pytest.raises(ValueError) as excinfo:
        factory_driver(
            pd.DataFrame(
                columns=["Driver", "Season", "Race", "col", "Price"],
                data=[["VER", 2020, 1, 3.3, 33.33], ["VER", 2020, 2, 4.4, 44.44]]
            ),
            pd.DataFrame(
                columns=["Driver", "Season", "Race"],
            ),
            "VER",
            2020,
            1,
            "col"
        )
    assert str(excinfo.value) == "Driver pairing for VER not found for season 2020 and race 1"

    with pytest.raises(ValueError) as excinfo:
        factory_driver(
            pd.DataFrame(
                columns=["Driver", "Season", "Race", "col", "Price"],
                data=[["VER", 2020, 1, 3.3, 33.33], ["VER", 2020, 2, 4.4, 44.44]]
            ),
            pd.DataFrame(
                columns=["Driver", "Season", "Race"],
                data=[["VER", 2020, 1], ["VER", 2020, 1]]
            ),
            "VER",
            2020,
            1,
            "col"
        )
    assert str(excinfo.value) == "Multiple entries found for driver pairing VER in season 2020 and race 1"

    driver_1 = factory_driver(
        pd.DataFrame(
            columns=["Driver", "Season", "Race", "col", "Price"],
            data=[["VER", 2020, 1, 3.3, 33.33], ["VER", 2020, 2, 4.4, 44.44]]
        ),
        pd.DataFrame(
            columns=["Driver", "Season", "Race", "Constructor"],
            data=[["VER", 2020, 1, "RED"]]
        ),
        "VER",
        2020,
        1,
        "col"
    )
    assert driver_1.constructor == "RED"
    assert driver_1.driver == "VER"
    assert driver_1.ppm == 3.3
    assert driver_1.price == 44.44

    driver_2 = factory_driver(
        pd.DataFrame(
            columns=["Driver", "Season", "Race", "col", "Price"],
            data=[["VER", 2020, 1, 3.3, 33.33]]
        ),
        pd.DataFrame(
            columns=["Driver", "Season", "Race", "Constructor"],
            data=[["VER", 2020, 1, "RED"]]
        ),
        "VER",
        2020,
        1,
        "col"
    )
    assert driver_2.constructor == "RED"
    assert driver_2.driver == "VER"
    assert driver_2.ppm == 3.3
    assert driver_2.price is np.nan
