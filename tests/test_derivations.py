import pandas as pd

from import_data.derivations import derivation_cum_tot_points


def test_derivation_cum_tot_points():
    ser_points = pd.Series(
        [10, 15, 0, 25, 5, 0, 30, 20, None, 10],
        index=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10])

    # The expected points will exclude the current race from the cumulative total
    assert derivation_cum_tot_points(race=1, ser_points=ser_points) == 0
    assert derivation_cum_tot_points(race=2, ser_points=ser_points) == 10
    assert derivation_cum_tot_points(race=3, ser_points=ser_points) == 25
    assert derivation_cum_tot_points(race=4, ser_points=ser_points) == 25
    assert derivation_cum_tot_points(race=5, ser_points=ser_points) == 50
    assert derivation_cum_tot_points(race=6, ser_points=ser_points) == 55
    assert derivation_cum_tot_points(race=7, ser_points=ser_points) == 55
    assert derivation_cum_tot_points(race=8, ser_points=ser_points) == 85
    assert derivation_cum_tot_points(race=9, ser_points=ser_points) == 105
    assert derivation_cum_tot_points(race=10, ser_points=ser_points) == 105
    assert derivation_cum_tot_points(race=11, ser_points=ser_points) == 115
