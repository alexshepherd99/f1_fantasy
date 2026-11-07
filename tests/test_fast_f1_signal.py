import pandas as pd
import pytest

from fast_f1.metrics import get_rolling_window_races
from fast_f1.signal import (
    SignalTables,
    constructor_values,
    driver_values,
    load_signal_tables,
    rule_price_move,
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


def _values(rows: list[dict], pairs: list[dict], race: int = 2, season: int = 2024) -> dict:
    return driver_values(pd.DataFrame(rows), pd.DataFrame(pairs), season, race)


def test_normal_weekend_values_add_up_driver_constructor_and_fp3():
    # Signals 0.5, 0.4, 0.3 and 0.0, stretched onto VER's 50 recent points and the others' 0.
    values = _values(
        [
            _row(2, "VER", 0.5, 0.0, fp3=0.0),
            _row(2, "HAM", 0.0, 0.4, fp3=0.0),
            _row(2, "NOR", 0.0, 0.0, fp3=0.3),
            _row(2, "ALO", 0.0, 0.0, fp3=0.0, FP2_MinLapTime_rank=1.0, OddsRank=1.0),
        ],
        _pairs(2, "VER@RED", "HAM@MER", "NOR@MCL", "ALO@AST"),
    )
    assert values == pytest.approx({"VER@RED": 50.0, "HAM@MER": 40.0, "NOR@MCL": 30.0, "ALO@AST": 0.0})


def test_sprint_weekend_values_add_up_driver_and_constructor_only():
    # Signals 0.4 and 0.3, so VER takes HAM's 30 recent points and HAM VER's 20.
    values = _values(
        [
            _sprint(2, "VER", 0.2, 0.2, sq=0.0),
            _sprint(2, "HAM", 0.3, 0.0, sq=1.0),
        ],
        _pairs(2, "VER@RED", "HAM@MER"),
    )
    assert values == pytest.approx({"VER@RED": 30.0, "HAM@MER": 20.0})


def test_2023_sprint_weekend_uses_the_sprint_rule():
    values = _values(
        [
            _sprint(2, "VER", 0.2, 0.2, sq=None, season=2023),
            _sprint(2, "HAM", 0.3, 0.0, sq=None, season=2023),
        ],
        _pairs(2, "VER@RED", "HAM@MER", season=2023),
        season=2023,
    )
    assert values == pytest.approx({"VER@RED": 30.0, "HAM@MER": 20.0})


def test_signals_apart_only_by_floating_point_noise_count_as_equal():
    # 0.1 + 0.2 is 0.30000000000000004 in floating point, a hair above 0.3 + 0.0.
    with pytest.raises(ValueError, match="Every signal equal for 2024 race 2"):
        _values(
            [_row(2, "VER", 0.1, 0.2), _row(2, "ALB", 0.3, 0.0)],
            _pairs(2, "VER@RED", "ALB@WIL"),
        )


def test_only_the_requested_race_is_valued_and_keys_use_that_races_pairs():
    # Race 3's window covers two races, so LAW's 90 recent points are 45 a race.
    values = _values(
        [
            _row(2, "LAW", 0.1, 0.1),
            _row(3, "LAW", 0.9, 0.9),
            _row(3, "TSU", 0.0, 0.0),
            _row(2, "TSU", 0.0, 0.0),
        ],
        _pairs(2, "LAW@VRB", "TSU@RED") + _pairs(3, "LAW@RED", "TSU@VRB"),
        race=3,
    )
    assert values == pytest.approx({"LAW@RED": 45.0, "TSU@VRB": 0.0})


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


@pytest.mark.parametrize("rank", [_values, _constructor_values])
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


@pytest.mark.parametrize("rank", [_values, _constructor_values])
def test_a_race_with_no_metrics_rows_gives_no_ranking(rank):
    assert rank([_row(3, "VER", 0.5, 0.5)], _pairs(2, "VER@RED")) == {}


@pytest.mark.parametrize("rank", [_values, _constructor_values])
def test_a_driver_with_no_fantasy_pair_is_an_error(rank):
    with pytest.raises(ValueError, match="2024 race 2: HAM"):
        rank([_row(2, "VER", 0.5, 0.5), _row(2, "HAM", 0.3, 0.3)], _pairs(2, "VER@RED"))


@pytest.mark.parametrize("rank", [_values, _constructor_values])
def test_a_driver_matching_two_fantasy_pairs_is_an_error(rank):
    with pytest.raises(ValueError, match="2024 race 2: VER"):
        rank([_row(2, "VER", 0.5, 0.5)], _pairs(2, "VER@RED", "VER@VRB"))


def test_a_missing_signal_input_is_an_error_not_a_zero():
    with pytest.raises(ValueError, match="2024 race 2: HAM"):
        _values(
            [_row(2, "VER", 0.5, 0.5), _row(2, "HAM", 0.3, 0.3, fp3=None)],
            _pairs(2, "VER@RED", "HAM@MER"),
        )


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


def _rising(*races: tuple) -> SignalTables:
    """``SignalTables`` for price rises. Each race is ``(season, race, assets)``, each mapping
    a driver identifier to ``(signal, driver_price, constructor_price)``, the driver being
    their constructor's only one.

    Every race from 2 holds a signal of 1.0 with 30 recent points a race and one of 0.0 with
    none, so a driver's value, and their constructor's, is 30 times their signal. A signal
    of None gives the driver no metrics row.
    """
    metrics, drivers, constructors = [], [], []
    for season, race, assets in races:
        covered = len(get_rolling_window_races(race))
        for driver_id, (signal, driver_price, con_price) in assets.items():
            code, con = driver_id.split("@")
            if signal is not None:
                metrics.append(_row(race, code, signal / 2, signal / 2, season=season,
                                    RollingPoints=30 * signal * covered if covered else None))
            drivers.append({"Constructor": con, "Driver": driver_id, "Race": race,
                            "Points": 5, "Season": season, "Price": driver_price})
            constructors.append({"Constructor": con, "Race": race, "Points": 5,
                                 "Season": season, "Price": con_price})
    return SignalTables(pd.DataFrame(metrics), pd.DataFrame(drivers), pd.DataFrame(constructors))


# 2023's history, races 2 to 4. Values are 30 for A, 15 for B and 0 for C. Per 1m, C is
# lowest and B highest in every race. Driver moves to the next race: C -0.2, 0.0, +0.5,
# whose mean differs from its median; A 0.0, +0.2, +0.4; B +0.2, +0.4, +0.6. Means C 0.1,
# A 0.2, B 0.4. Constructors run the other way: C +0.4, A 0.0, B -0.4 each time. Race 5
# is priced only, so has no moves of its own, and race 1 has no value to build from.
_RISES_2023 = [
    (2023, 1, {"AAA@AAA": (1.0, 30, 30), "BBB@BBB": (0.5, 5, 5), "CCC@CCC": (0.0, 10, 10)}),
    (2023, 2, {"AAA@AAA": (1.0, 30, 30), "BBB@BBB": (0.5, 5, 5), "CCC@CCC": (0.0, 10, 10)}),
    (2023, 3, {"AAA@AAA": (1.0, 30, 30), "BBB@BBB": (0.5, 5.2, 4.6),
               "CCC@CCC": (0.0, 9.8, 10.4)}),
    (2023, 4, {"AAA@AAA": (1.0, 30.2, 30), "BBB@BBB": (0.5, 5.6, 4.2),
               "CCC@CCC": (0.0, 9.8, 10.8)}),
    (2023, 5, {"AAA@AAA": (None, 30.6, 30), "BBB@BBB": (None, 6.2, 3.8),
               "CCC@CCC": (None, 10.3, 11.2)}),
]

# A race to look up. Per 1m ALB is lowest, HAM in the middle and VER highest. By value
# alone HAM would take B's third, and by price alone ALB would, each changing the answer.
_LOOK_UP = {"VER@RED": (1.0, 10, 10), "HAM@MER": (0.5, 15, 15), "ALB@WIL": (0.0, 5, 5)}


def test_price_rise_is_the_mean_rise_in_the_assets_third_on_value_per_million():
    tables = _rising(*_RISES_2023, (2024, 2, _LOOK_UP))
    assert tables.price_rise(2024, 2) == pytest.approx({
        "ALB@WIL": 0.1, "HAM@MER": 0.2, "VER@RED": 0.4, "WIL": 0.4, "MER": 0.0, "RED": -0.4,
    })


def test_a_move_without_a_price_at_the_next_race_is_left_out():
    unpriced = {"AAA@AAA": (None, 30.6, 30), "BBB@BBB": (None, None, None),
                "CCC@CCC": (None, 10.3, 11.2)}
    tables = _rising(*_RISES_2023[:4], (2023, 5, unpriced), (2024, 2, _LOOK_UP))
    rise = tables.price_rise(2024, 2)
    assert (rise["VER@RED"], rise["RED"]) == pytest.approx((0.3, -0.4))


def test_an_asset_with_no_value_gets_no_price_rise_and_no_place_in_the_thirds():
    look_up = _LOOK_UP | {"SAR@SAU": (None, 1, 1)}
    tables = _rising(*_RISES_2023, (2024, 2, look_up))
    rise = tables.price_rise(2024, 2)
    assert "SAR@SAU" not in rise
    assert [rise[d] for d in _LOOK_UP] == pytest.approx([0.4, 0.2, 0.1])


def test_a_race_priced_but_without_signal_has_no_price_rise():
    unsignalled = {driver: (None, *prices) for driver, (_, *prices) in _LOOK_UP.items()}
    tables = _rising(*_RISES_2023, (2026, 19, unsignalled))
    assert tables.price_rise(2026, 19) == {}


@pytest.mark.parametrize("season", [2024, 2026])
def test_a_price_rise_table_with_no_other_season_to_draw_on_is_an_error(season):
    # 2024 has history of its own to leave out; 2026 has none in a table season at all.
    tables = _rising((season, 2, _LOOK_UP), (season, 3, _LOOK_UP))
    with pytest.raises(ValueError, match=f"No 2023-25 history for {season}'s Driver rises table"):
        tables.price_rise(season, 2)


def _rises_varying(price_2024: float, price_2026: float) -> SignalTables:
    """2023 as above, then 2024 and 2026 races 2 and 3, with every race 3 price at the
    season's given figure."""
    def season(year: int, price: float) -> list[tuple]:
        return [(year, 2, _LOOK_UP),
                (year, 3, {d: (s, price, price) for d, (s, _, _) in _LOOK_UP.items()})]
    return _rising(*_RISES_2023, *season(2024, price_2024), *season(2026, price_2026))


@pytest.mark.parametrize("season, varied", [
    (2024, ("2024", "2026")),
    (2023, ("2026",)),
])
def test_price_rise_reads_neither_its_own_season_nor_2026(season, varied):
    def tables(price: float) -> SignalTables:
        return _rises_varying(
            price if "2024" in varied else 20, price if "2026" in varied else 20
        )
    assert tables(1).price_rise(season, 2) == tables(100).price_rise(season, 2)


def test_values_are_the_drivers_and_constructors_values_for_the_race():
    # Each driver is their constructor's only one, so a constructor's value is its driver's.
    tables = _rising(*_RISES_2023, (2024, 2, _LOOK_UP))
    assert tables.values(2024, 2) == pytest.approx({
        "VER@RED": 30.0, "HAM@MER": 15.0, "ALB@WIL": 0.0, "RED": 30.0, "MER": 15.0, "WIL": 0.0,
    })


def test_a_race_priced_but_without_signal_has_no_values():
    unsignalled = {driver: (None, *prices) for driver, (_, *prices) in _LOOK_UP.items()}
    tables = _rising(*_RISES_2023, (2026, 19, unsignalled))
    assert tables.values(2026, 19) == {}


def test_changing_a_returned_dict_does_not_change_the_next_call():
    tables = _rising(*_RISES_2023, (2024, 2, _LOOK_UP))
    for method in (tables.negative_chance, tables.values):
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


@pytest.mark.parametrize("rating, upper, lower", [
    (1.21, 0.3, 0.6),
    (1.2, 0.1, 0.2),
    (0.9, 0.1, 0.2),
    (0.89, -0.1, -0.2),
    (0.6, -0.1, -0.2),
    (0.59, -0.3, -0.6),
])
def test_rule_price_move_steps_by_rating_band_and_price_tier(rating, upper, lower):
    assert rule_price_move(rating, 25.0, 2025) == upper
    assert rule_price_move(rating, 10.0, 2025) == lower


@pytest.mark.parametrize("season", [2025, 2026])
@pytest.mark.parametrize("price, move", [(18.5, 0.3), (18.4, 0.6)])
def test_rule_price_move_counts_a_price_at_the_split_as_the_upper_tier(season, price, move):
    assert rule_price_move(1.5, price, season) == move


@pytest.mark.parametrize("season, price, move", [
    (2025, 4.7, -0.2),
    (2025, 4.6, -0.1),
    (2025, 4.5, 0.0),
    (2026, 3.2, -0.2),
    (2026, 3.1, -0.1),
    (2026, 3.0, 0.0),
])
def test_rule_price_move_stops_a_fall_at_the_seasons_floor(season, price, move):
    assert rule_price_move(0.7, price, season) == move


@pytest.mark.parametrize("season, price, move", [
    (2026, 33.9, 0.1),
    (2026, 34.0, 0.0),
    (2025, 34.0, 0.3),
])
def test_rule_price_move_stops_a_rise_at_the_seasons_cap(season, price, move):
    assert rule_price_move(1.5, price, season) == move


@pytest.mark.parametrize("rating, price", [(1.5, 35.0), (0.1, 2.8)])
def test_rule_price_move_never_pushes_an_asset_back_inside_a_limit(rating, price):
    assert rule_price_move(rating, price, 2026) == 0.0


@pytest.mark.parametrize("rating, price, move", [(0.1, 3.2, -0.2), (1.5, 33.9, 0.1)])
def test_rule_price_move_takes_2026s_figures_after_2026(rating, price, move):
    # 2025's floor of 4.5m and lack of a cap would give 0.0 and +0.3.
    assert rule_price_move(rating, price, 2027) == move


@pytest.mark.parametrize("season", [2023, 2024])
def test_rule_price_move_refuses_a_season_before_the_three_race_model(season):
    with pytest.raises(ValueError, match=f"No price rules for {season}"):
        rule_price_move(1.0, 10.0, season)
