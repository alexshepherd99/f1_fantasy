import pandas as pd
import pytest

from fast_f1.signal import (
    SignalTables,
    constructor_places,
    constructor_values,
    driver_positions,
    driver_values,
    load_signal_tables,
)


def _row(race: int, driver: str, driver_rolling: float, constructor_rolling: float,
         fp3: float | None = 0.0, season: int = 2024, **overrides) -> dict:
    """One normal weekend metrics row, with FP2 and odds at zero unless overridden."""
    row = {
        "Season": season,
        "Race": race,
        "Driver": driver,
        "Status": "Finished",
        "Position": 1.0,
        "GridPosition": 1.0,
        "Points": 25.0,
        "RollingPoints": driver_rolling * 100,
        "RollingPointsRank": driver_rolling,
        "ConstructorRollingPoints": constructor_rolling * 100,
        "ConstructorRollingPointsRank": constructor_rolling,
        "OddsRank": 0.0,
        "FP1_MinLapTime_rank": None,
        "FP2_MinLapTime_rank": 0.0,
        "FP3_MinLapTime_rank": fp3,
        "SQ_MinLapTime_rank": None,
    }
    return row | overrides


def _sprint(race: int, driver: str, driver_rolling: float, constructor_rolling: float,
            sq: float | None = 0.9, season: int = 2024) -> dict:
    """One sprint weekend metrics row, with FP1 and SQ high so that using them would show."""
    return _row(
        race, driver, driver_rolling, constructor_rolling, season=season,
        FP1_MinLapTime_rank=0.9, FP2_MinLapTime_rank=None, FP3_MinLapTime_rank=None,
        SQ_MinLapTime_rank=sq,
    )


def _pairs(race: int, *driver_ids: str, season: int = 2024) -> list[dict]:
    return [
        {"Constructor": d.split("@")[1], "Driver": d, "Race": race, "Season": season}
        for d in driver_ids
    ]


def _positions(rows: list[dict], pairs: list[dict], race: int = 2, season: int = 2024) -> dict:
    return driver_positions(pd.DataFrame(rows), pd.DataFrame(pairs), season, race)


def test_normal_weekend_ranks_on_driver_constructor_and_fp3():
    positions = _positions(
        [
            _row(2, "VER", 0.5, 0.0, fp3=0.0),
            _row(2, "HAM", 0.0, 0.4, fp3=0.0),
            _row(2, "NOR", 0.0, 0.0, fp3=0.3),
            _row(2, "ALO", 0.0, 0.0, fp3=0.0, FP2_MinLapTime_rank=1.0, OddsRank=1.0),
        ],
        _pairs(2, "VER@RED", "HAM@MER", "NOR@MCL", "ALO@AST"),
    )
    assert positions == {"VER@RED": 1, "HAM@MER": 2, "NOR@MCL": 3, "ALO@AST": 4}


def test_sprint_weekend_ranks_on_driver_and_constructor_only():
    positions = _positions(
        [
            _sprint(2, "VER", 0.2, 0.2, sq=0.0),
            _sprint(2, "HAM", 0.3, 0.0, sq=1.0),
        ],
        _pairs(2, "VER@RED", "HAM@MER"),
    )
    assert positions == {"VER@RED": 1, "HAM@MER": 2}


def test_2023_sprint_weekend_uses_the_sprint_rule():
    positions = _positions(
        [
            _sprint(2, "VER", 0.2, 0.2, sq=None, season=2023),
            _sprint(2, "HAM", 0.3, 0.0, sq=None, season=2023),
        ],
        _pairs(2, "VER@RED", "HAM@MER", season=2023),
        season=2023,
    )
    assert positions == {"VER@RED": 1, "HAM@MER": 2}


def test_a_tie_breaks_on_the_identifier():
    positions = _positions(
        [_row(2, "VER", 0.2, 0.2), _row(2, "ALB", 0.2, 0.2)],
        _pairs(2, "VER@RED", "ALB@WIL"),
    )
    assert positions == {"ALB@WIL": 1, "VER@RED": 2}


def test_a_tie_hidden_by_floating_point_noise_still_breaks_on_the_identifier():
    # 0.1 + 0.2 is 0.30000000000000004 in floating point, a hair above 0.3 + 0.0.
    positions = _positions(
        [_row(2, "VER", 0.1, 0.2), _row(2, "ALB", 0.3, 0.0)],
        _pairs(2, "VER@RED", "ALB@WIL"),
    )
    assert positions == {"ALB@WIL": 1, "VER@RED": 2}


def test_only_the_requested_race_is_ranked_and_keys_use_that_races_pairs():
    positions = _positions(
        [
            _row(2, "LAW", 0.1, 0.1),
            _row(3, "LAW", 0.9, 0.9),
            _row(3, "TSU", 0.0, 0.0),
            _row(2, "TSU", 0.0, 0.0),
        ],
        _pairs(2, "LAW@VRB", "TSU@RED") + _pairs(3, "LAW@RED", "TSU@VRB"),
        race=3,
    )
    assert positions == {"LAW@RED": 1, "TSU@VRB": 2}


def _values(rows: list[dict], pairs: list[dict], race: int = 2, season: int = 2024) -> dict:
    return driver_values(pd.DataFrame(rows), pd.DataFrame(pairs), season, race)


@pytest.mark.parametrize("race, races_covered", [(2, 1), (3, 2), (4, 3), (10, 3)])
def test_driver_values_stretch_the_signal_onto_recent_points_per_race(race, races_covered):
    # Signals 1.0, 0.5 and 0.0. The field's recent points run from 6 to 30 a race, and
    # each driver's own points play no part beyond setting that range.
    values = _values(
        [
            _row(race, "VER", 0.5, 0.5, RollingPoints=30 * races_covered),
            _row(race, "NOR", 0.25, 0.25, RollingPoints=6 * races_covered),
            _row(race, "ALB", 0.0, 0.0, RollingPoints=15 * races_covered),
        ],
        _pairs(race, "VER@RED", "NOR@MCL", "ALB@WIL"),
        race=race,
    )
    assert values == pytest.approx({"VER@RED": 30.0, "NOR@MCL": 18.0, "ALB@WIL": 6.0})


def test_a_driver_with_no_recent_points_is_left_out_of_the_range():
    values = _values(
        [
            _row(2, "VER", 0.5, 0.5, RollingPoints=25),
            _row(2, "ALB", 0.0, 0.0, RollingPoints=5),
            _row(2, "BEA", 0.25, 0.25, RollingPoints=None),
        ],
        _pairs(2, "VER@RED", "ALB@WIL", "BEA@FER"),
    )
    assert values == pytest.approx({"VER@RED": 25.0, "BEA@FER": 15.0, "ALB@WIL": 5.0})


def test_a_race_where_every_signal_is_equal_is_an_error():
    with pytest.raises(ValueError, match="Every signal equal for 2024 race 2"):
        _values(
            [_row(2, "VER", 0.5, 0.0, RollingPoints=25), _row(2, "ALB", 0.0, 0.5, RollingPoints=5)],
            _pairs(2, "VER@RED", "ALB@WIL"),
        )


@pytest.mark.parametrize("rolling_points", [None, 25])
def test_race_one_is_an_error_as_it_has_no_recent_points(rolling_points):
    with pytest.raises(ValueError, match="No recent championship points for 2024 race 1"):
        _values(
            [
                _row(1, "VER", 0.5, 0.5, RollingPoints=rolling_points),
                _row(1, "ALB", 0.0, 0.0, RollingPoints=rolling_points),
            ],
            _pairs(1, "VER@RED", "ALB@WIL"),
            race=1,
        )


def _places(rows: list[dict], pairs: list[dict], race: int = 2, season: int = 2024) -> dict:
    return constructor_places(pd.DataFrame(rows), pd.DataFrame(pairs), season, race)


def test_constructors_rank_on_their_own_rolling_points_not_their_drivers_signal():
    places = _places(
        [
            _row(2, "VER", 0.0, 0.3, fp3=0.0),
            _row(2, "PER", 0.0, 0.3, fp3=0.0),
            _row(2, "HAM", 1.0, 0.2, fp3=1.0),
            _row(2, "RUS", 1.0, 0.2, fp3=1.0),
            _row(2, "NOR", 0.0, 0.4, fp3=0.0),
        ],
        _pairs(2, "VER@RED", "PER@RED", "HAM@MER", "RUS@MER", "NOR@MCL"),
    )
    assert places == {"MCL": 1, "RED": 2, "MER": 3}


def test_a_constructor_tie_breaks_on_the_code():
    places = _places(
        [_row(2, "VER", 0.0, 0.2), _row(2, "ALB", 0.0, 0.2)],
        _pairs(2, "VER@RED", "ALB@WIL"),
    )
    assert places == {"RED": 1, "WIL": 2}


def test_constructors_are_reached_through_the_requested_races_pairs():
    places = _places(
        [
            _row(2, "LAW", 0.0, 0.1),
            _row(3, "LAW", 0.0, 0.9),
            _row(3, "TSU", 0.0, 0.0),
            _row(2, "TSU", 0.0, 0.0),
        ],
        _pairs(2, "LAW@VRB", "TSU@RED") + _pairs(3, "LAW@RED", "TSU@VRB"),
        race=3,
    )
    assert places == {"RED": 1, "VRB": 2}


def _constructor_values(
    rows: list[dict], pairs: list[dict], race: int = 2, season: int = 2024
) -> dict:
    return constructor_values(pd.DataFrame(rows), pd.DataFrame(pairs), season, race)


def test_a_constructors_value_is_the_sum_of_its_drivers_values():
    # Driver values: VER 25, PER 15, RUS 10, HAM 5.
    values = _constructor_values(
        [
            _row(2, "VER", 0.5, 0.5, RollingPoints=25),
            _row(2, "PER", 0.25, 0.25, RollingPoints=10),
            _row(2, "RUS", 0.125, 0.125, RollingPoints=10),
            _row(2, "HAM", 0.0, 0.0, RollingPoints=5),
        ],
        _pairs(2, "VER@RED", "PER@RED", "HAM@MER", "RUS@MER"),
    )
    assert values == pytest.approx({"RED": 40.0, "MER": 15.0})


def test_a_constructors_driver_with_no_value_counts_as_zero():
    # SAR is in the fantasy pairs but has no metrics row, as in 2024 race 3.
    values = _constructor_values(
        [
            _row(2, "VER", 0.5, 0.5, RollingPoints=25),
            _row(2, "PER", 0.25, 0.25, RollingPoints=10),
            _row(2, "ALB", 0.0, 0.0, RollingPoints=5),
        ],
        _pairs(2, "VER@RED", "PER@RED", "ALB@WIL", "SAR@WIL"),
    )
    assert values == pytest.approx({"RED": 40.0, "WIL": 5.0})


def test_constructor_values_are_reached_through_the_requested_races_pairs():
    values = _constructor_values(
        [
            _row(2, "LAW", 0.0, 0.0, RollingPoints=0),
            _row(3, "LAW", 0.5, 0.5, RollingPoints=30),
            _row(3, "TSU", 0.0, 0.0, RollingPoints=0),
            _row(2, "TSU", 0.5, 0.5, RollingPoints=30),
        ],
        # HAS raced in race 2 only, so has no value in race 3.
        _pairs(2, "LAW@VRB", "TSU@RED", "BEA@HAS") + _pairs(3, "LAW@RED", "TSU@VRB"),
        race=3,
    )
    assert values == pytest.approx({"RED": 15.0, "VRB": 0.0})


@pytest.mark.parametrize("rank", [_positions, _values, _places, _constructor_values])
def test_a_races_own_results_do_not_move_its_signal(rank):
    pairs = _pairs(2, "VER@RED", "HAM@MER", "NOR@MCL")
    before = [_row(2, "VER", 0.5, 0.5), _row(2, "HAM", 0.3, 0.3), _row(2, "NOR", 0.1, 0.1)]
    results = [
        {"Status": "Finished", "Position": 1.0, "GridPosition": 1.0, "Points": 25.0},
        {"Status": "Did not start", "Position": 20.0, "GridPosition": 0.0, "Points": 0.0},
        {"Status": "Retired", "Position": 19.0, "GridPosition": 20.0, "Points": 0.0},
    ]
    after = [row | result for row, result in zip(before, results)]
    assert rank(after, pairs) == rank(before, pairs)
    assert len(rank(after, pairs)) == 3


@pytest.mark.parametrize("rank", [_positions, _values, _places, _constructor_values])
def test_a_race_with_no_metrics_rows_gives_no_ranking(rank):
    assert rank([_row(3, "VER", 0.5, 0.5)], _pairs(2, "VER@RED")) == {}


@pytest.mark.parametrize("rank", [_positions, _values, _places, _constructor_values])
def test_a_driver_with_no_fantasy_pair_is_an_error(rank):
    with pytest.raises(ValueError, match="2024 race 2: HAM"):
        rank([_row(2, "VER", 0.5, 0.5), _row(2, "HAM", 0.3, 0.3)], _pairs(2, "VER@RED"))


@pytest.mark.parametrize("rank", [_positions, _values, _places, _constructor_values])
def test_a_driver_matching_two_fantasy_pairs_is_an_error(rank):
    with pytest.raises(ValueError, match="2024 race 2: VER"):
        rank([_row(2, "VER", 0.5, 0.5)], _pairs(2, "VER@RED", "VER@VRB"))


def test_a_missing_signal_input_is_an_error_not_a_last_place():
    with pytest.raises(ValueError, match="2024 race 2: HAM"):
        _positions(
            [_row(2, "VER", 0.5, 0.5), _row(2, "HAM", 0.3, 0.3, fp3=None)],
            _pairs(2, "VER@RED", "HAM@MER"),
        )


def test_a_constructors_drivers_disagreeing_on_its_rolling_points_is_an_error():
    with pytest.raises(ValueError, match="2024 race 2: RED"):
        _places(
            [_row(2, "VER", 0.5, 0.5), _row(2, "PER", 0.3, 0.3)],
            _pairs(2, "VER@RED", "PER@RED"),
        )


class _History:
    """Metrics and archive rows for ``SignalTables``, built one race at a time."""

    def __init__(self):
        self.metrics, self.drivers, self.constructors = [], [], []

    def race(self, season: int, race: int, drivers: dict, constructors: dict,
             with_metrics: bool = True) -> "_History":
        """Add a race. Each dict maps an identifier to its fantasy points, best signal first.

        ``with_metrics=False`` adds the archive rows alone, as for a race priced but not run.
        """
        con_rolling = {con: 0.9 - 0.1 * i for i, con in enumerate(constructors)}
        for i, (driver_id, points) in enumerate(drivers.items()):
            code, con = driver_id.split("@")
            if with_metrics:
                self.metrics.append(_row(race, code, 10.0 - i, con_rolling[con], season=season))
            self.drivers.append({"Constructor": con, "Driver": driver_id, "Race": race,
                                 "Points": points, "Season": season, "Price": 10.0})
        for con, points in constructors.items():
            self.constructors.append({"Constructor": con, "Race": race, "Points": points,
                                      "Season": season, "Price": 20.0})
        return self

    def tables(self) -> SignalTables:
        return SignalTables(
            pd.DataFrame(self.metrics), pd.DataFrame(self.drivers), pd.DataFrame(self.constructors)
        )


def test_expected_points_are_mean_points_by_position_from_the_other_seasons():
    tables = (
        _History()
        .race(2023, 2, {"VER@RED": 30, "HAM@MER": 10}, {"RED": 50, "MER": 20})
        .race(2025, 2, {"VER@RED": 20, "HAM@MER": 0}, {"RED": 30, "MER": 0})
        .race(2024, 2, {"HAM@MER": 1000, "VER@RED": -1000}, {"MER": 1000, "RED": -1000})
        .tables()
    )
    assert tables.expected_points(2024, 2) == {"HAM@MER": 25, "VER@RED": 5, "MER": 40, "RED": 10}


def test_race_one_does_not_build_the_table():
    tables = (
        _History()
        .race(2023, 1, {"VER@RED": 500, "HAM@MER": 500}, {"RED": 500, "MER": 500})
        .race(2023, 2, {"VER@RED": 30, "HAM@MER": 10}, {"RED": 50, "MER": 20})
        .race(2024, 2, {"VER@RED": 0, "HAM@MER": 0}, {"RED": 0, "MER": 0})
        .tables()
    )
    assert tables.expected_points(2024, 2) == {"VER@RED": 30, "HAM@MER": 10, "RED": 50, "MER": 20}


def test_means_are_forced_to_fall_by_position():
    drivers = {"VER@RED": 30, "HAM@MER": 0, "NOR@MCL": 10}
    constructors = {"RED": 50, "MER": 10, "MCL": 20}
    tables = (
        _History()
        .race(2023, 2, drivers, constructors)
        .race(2024, 2, drivers, constructors)
        .tables()
    )
    assert tables.expected_points(2024, 2) == {
        "VER@RED": 30, "HAM@MER": 5, "NOR@MCL": 5, "RED": 50, "MER": 15, "MCL": 15,
    }


def test_a_position_past_the_tables_end_carries_the_last_value():
    tables = (
        _History()
        .race(2023, 2, {"VER@RED": 30, "HAM@MER": 10}, {"RED": 50, "MER": 20})
        .race(2026, 2, {"VER@RED": 0, "HAM@MER": 0, "BOT@CAD": 0},
              {"RED": 0, "MER": 0, "CAD": 0})
        .tables()
    )
    assert tables.expected_points(2026, 2) == {
        "VER@RED": 30, "HAM@MER": 10, "BOT@CAD": 10, "RED": 50, "MER": 20, "CAD": 20,
    }


def _three_seasons_and_2026(points_2026: int) -> SignalTables:
    history = _History()
    for season, points in ((2023, 30), (2024, 20), (2025, 10)):
        history.race(season, 2, {"VER@RED": points, "HAM@MER": 0}, {"RED": points, "MER": 0})
    history.race(2026, 2, {"VER@RED": points_2026, "HAM@MER": 0}, {"RED": points_2026, "MER": 0})
    history.race(2026, 3, {"VER@RED": points_2026, "HAM@MER": 0}, {"RED": points_2026, "MER": 0})
    return history.tables()


@pytest.mark.parametrize("season, race", [(2023, 2), (2024, 2), (2025, 2), (2026, 3)])
def test_2026_results_never_enter_a_table(season, race):
    low, high = _three_seasons_and_2026(-1000), _three_seasons_and_2026(1000)
    assert low.expected_points(season, race) == high.expected_points(season, race)


def test_2026s_table_comes_from_all_three_earlier_seasons():
    assert _three_seasons_and_2026(1000).expected_points(2026, 3)["VER@RED"] == 20


def test_a_ranked_driver_without_fantasy_points_is_an_error():
    tables = (
        _History()
        .race(2023, 2, {"VER@RED": 30, "HAM@MER": None}, {"RED": 50, "MER": 20})
        .race(2024, 2, {"VER@RED": 0, "HAM@MER": 0}, {"RED": 0, "MER": 0})
        .tables()
    )
    with pytest.raises(ValueError, match="2023 race 2: HAM@MER"):
        tables.expected_points(2024, 2)


def test_a_table_with_no_other_season_to_draw_on_is_an_error():
    tables = (
        _History()
        .race(2024, 2, {"VER@RED": 30, "HAM@MER": 10}, {"RED": 50, "MER": 20})
        .race(2026, 2, {"VER@RED": 30, "HAM@MER": 10}, {"RED": 50, "MER": 20})
        .tables()
    )
    with pytest.raises(ValueError, match="No 2023-25 history for 2024's Driver points table"):
        tables.expected_points(2024, 2)


def test_a_race_priced_but_without_signal_has_no_expected_points():
    tables = (
        _History()
        .race(2023, 2, {"VER@RED": 30, "HAM@MER": 10}, {"RED": 50, "MER": 20})
        .race(2026, 19, {"VER@RED": 0, "HAM@MER": 0}, {"RED": 0, "MER": 0}, with_metrics=False)
        .tables()
    )
    assert tables.expected_points(2026, 19) == {}


def _priced(*races: tuple) -> SignalTables:
    """``SignalTables`` on archive rows alone. Each race is ``(season, race, drivers,
    constructors)``, each dict mapping an identifier to its ``(price, points)``."""
    drivers, constructors = [], []
    for season, race, race_drivers, race_constructors in races:
        for driver_id, (price, points) in race_drivers.items():
            drivers.append({"Constructor": driver_id.split("@")[1], "Driver": driver_id,
                            "Race": race, "Points": points, "Season": season, "Price": price})
        for con, (price, points) in race_constructors.items():
            constructors.append({"Constructor": con, "Race": race, "Points": points,
                                 "Season": season, "Price": price})
    return SignalTables(pd.DataFrame(), pd.DataFrame(drivers), pd.DataFrame(constructors))


# 2023's history, from races 2 and 3, with three of each type, cheapest to dearest. Drivers:
# the cheapest third goes negative both times, the middle once and the dearest never.
# Constructors run the other way, which a table mixing the types would show. Race 1 builds
# no row, which every asset going negative there would show. Race 3's prices are double
# race 2's, which thirds split over the season rather than the race would show.
_NEGATIVES_2023 = [
    (2023, 1, {"CHP@AAA": (5, -5), "MID@BBB": (10, -5), "DER@CCC": (15, -5)},
     {"AAA": (5, -5), "BBB": (10, -5), "CCC": (15, -5)}),
    (2023, 2, {"CHP@AAA": (5, -5), "MID@BBB": (10, -5), "DER@CCC": (15, 5)},
     {"AAA": (5, 5), "BBB": (10, -5), "CCC": (15, -5)}),
    (2023, 3, {"CHP@AAA": (10, -5), "MID@BBB": (20, 5), "DER@CCC": (30, 5)},
     {"AAA": (10, 5), "BBB": (20, 5), "CCC": (30, -5)}),
]


def test_negative_chance_is_the_share_negative_in_the_assets_price_third_by_type():
    tables = _priced(
        *_NEGATIVES_2023,
        (2024, 2, {"VER@RED": (30, 5), "HAM@MER": (20, 5), "NOR@MCL": (10, 5)},
         {"RED": (30, 5), "MER": (20, 5), "MCL": (10, 5)}),
    )
    assert tables.negative_chance(2024, 2) == {
        "VER@RED": 0.0, "HAM@MER": 0.5, "NOR@MCL": 1.0, "RED": 1.0, "MER": 0.5, "MCL": 0.0,
    }


def test_a_remainder_falls_to_the_lower_price_thirds():
    drivers = {f"D{i}@C{i}": (10 * i, 5) for i in range(1, 6)}
    constructors = {f"C{i}": (10 * i, 5) for i in range(1, 5)}
    tables = _priced(*_NEGATIVES_2023, (2024, 2, drivers, constructors))
    chance = tables.negative_chance(2024, 2)
    assert [chance[d] for d in drivers] == [1.0, 1.0, 0.5, 0.5, 0.0]
    assert [chance[c] for c in constructors] == [0.0, 0.0, 0.5, 1.0]


def test_assets_on_the_same_price_share_the_lower_third():
    drivers = {"D1@C1": (10, 5), "D2@C2": (20, 5), "D3@C3": (20, 5), "D4@C4": (30, 5)}
    tables = _priced(*_NEGATIVES_2023, (2024, 2, drivers, {"C1": (10, 5)}))
    chance = tables.negative_chance(2024, 2)
    assert [chance[d] for d in drivers] == [1.0, 1.0, 1.0, 0.0]


def test_an_unpriced_asset_gets_no_chance_and_no_place_in_the_thirds():
    drivers = {"D1@C1": (10, 5), "D2@C2": (20, 5), "D3@C3": (30, 5), "D4@C4": (None, None)}
    tables = _priced(*_NEGATIVES_2023, (2024, 2, drivers, {"C1": (10, 5)}))
    assert tables.negative_chance(2024, 2) == {
        "D1@C1": 1.0, "D2@C2": 0.5, "D3@C3": 0.0, "C1": 0.0,
    }


def _negatives_varying(points_2024: int, points_2026: int) -> SignalTables:
    """2023 as above; 2024 races 2 and 3 at ``points_2024``; 2026 races 2 and 3 at
    ``points_2026``. Every race prices its three assets of each type 10, 20 and 30."""
    def race(season: int, number: int, points: int) -> tuple:
        return (season, number,
                {"VER@RED": (30, points), "HAM@MER": (20, points), "NOR@MCL": (10, points)},
                {"RED": (30, points), "MER": (20, points), "MCL": (10, points)})
    return _priced(
        *_NEGATIVES_2023,
        *(race(2024, number, points_2024) for number in (2, 3)),
        *(race(2026, number, points_2026) for number in (2, 3)),
    )


@pytest.mark.parametrize("season, varied", [
    (2024, ("2024", "2026")),
    (2023, ("2026",)),
])
def test_negative_chance_reads_neither_its_own_season_nor_2026(season, varied):
    def tables(points: int) -> SignalTables:
        return _negatives_varying(
            points if "2024" in varied else -5, points if "2026" in varied else -5
        )
    assert tables(-1000).negative_chance(season, 2) == tables(1000).negative_chance(season, 2)


def test_changing_a_returned_dict_does_not_change_the_next_call():
    history = _History()
    for season in (2023, 2024):
        history.race(season, 2, {"VER@RED": 30, "HAM@MER": 10}, {"RED": 50, "MER": 20})
    tables = history.tables()
    for method in (tables.expected_points, tables.negative_chance):
        first = method(2024, 2)
        expected = dict(first)
        first["VER@RED"] = 999.0
        assert method(2024, 2) == expected


def test_load_signal_tables_refuses_a_missing_metrics_file(tmp_path):
    missing = tmp_path / "no_such_metrics.xlsx"
    with pytest.raises(FileNotFoundError, match="no_such_metrics.xlsx"):
        load_signal_tables(missing)


def test_load_signal_tables_reads_the_files_once_per_process(tmp_path):
    metrics = tmp_path / "metrics.xlsx"
    pd.DataFrame([_row(2, "VER", 0.5, 0.5, season=2023)]).to_excel(metrics, index=False)
    assert load_signal_tables(metrics) is load_signal_tables(metrics)
