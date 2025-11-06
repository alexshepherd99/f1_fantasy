import pandas as pd
import pytest

from import_data.derivations import (
    derivation_cum_tot_points,
    derivation_cum_tot_price,
)


def test_derivation_cum_tot_points():
    ser_points = pd.Series(
        [10, 15, 0, 25, 5, 0, 30, 20, None, 10],
        index=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10])

    # The expected points will include the current race from the cumulative total
    assert derivation_cum_tot_points(race=1, ser_points=ser_points) == 10
    assert derivation_cum_tot_points(race=2, ser_points=ser_points) == 25
    assert derivation_cum_tot_points(race=3, ser_points=ser_points) == 25
    assert derivation_cum_tot_points(race=4, ser_points=ser_points) == 50
    assert derivation_cum_tot_points(race=5, ser_points=ser_points) == 55
    assert derivation_cum_tot_points(race=6, ser_points=ser_points) == 55
    assert derivation_cum_tot_points(race=7, ser_points=ser_points) == 85
    assert derivation_cum_tot_points(race=8, ser_points=ser_points) == 105
    assert derivation_cum_tot_points(race=9, ser_points=ser_points) == 105
    assert derivation_cum_tot_points(race=10, ser_points=ser_points) == 115
    assert derivation_cum_tot_points(race=11, ser_points=ser_points) == 115


def test_derivation_cum_tot_price():
    ser_price = pd.Series(
        [10.1, 15.2, 0, 25.3, 5.4, 0, 30.5, 20.6, None, 10.7],
        index=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10])

    # The expected points will include the current race from the cumulative total
    assert derivation_cum_tot_price(race=1, ser_price=ser_price) == pytest.approx(10.1, abs=1e-2)
    assert derivation_cum_tot_price(race=2, ser_price=ser_price) == pytest.approx(25.3, abs=1e-2)
    assert derivation_cum_tot_price(race=3, ser_price=ser_price) == pytest.approx(25.3, abs=1e-2)
    assert derivation_cum_tot_price(race=4, ser_price=ser_price) == pytest.approx(50.6, abs=1e-2)
    assert derivation_cum_tot_price(race=5, ser_price=ser_price) == pytest.approx(56.0, abs=1e-2)
    assert derivation_cum_tot_price(race=6, ser_price=ser_price) == pytest.approx(56.0, abs=1e-2)
    assert derivation_cum_tot_price(race=7, ser_price=ser_price) == pytest.approx(86.5, abs=1e-2)
    assert derivation_cum_tot_price(race=8, ser_price=ser_price) == pytest.approx(107.1, abs=1e-2)
    assert derivation_cum_tot_price(race=9, ser_price=ser_price) == pytest.approx(107.1, abs=1e-2)
    assert derivation_cum_tot_price(race=10, ser_price=ser_price) == pytest.approx(117.8, abs=1e-2)
    assert derivation_cum_tot_price(race=11, ser_price=ser_price) == pytest.approx(117.8, abs=1e-2)
