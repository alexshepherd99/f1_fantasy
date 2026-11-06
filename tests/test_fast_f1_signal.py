import pandas as pd
import pytest

from fast_f1.signal import (
    SignalTables,
    constructor_places,
    driver_positions,
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


@pytest.mark.parametrize("rank", [_positions, _places])
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


@pytest.mark.parametrize("rank", [_positions, _places])
def test_a_race_with_no_metrics_rows_gives_no_ranking(rank):
    assert rank([_row(3, "VER", 0.5, 0.5)], _pairs(2, "VER@RED")) == {}


@pytest.mark.parametrize("rank", [_positions, _places])
def test_a_driver_with_no_fantasy_pair_is_an_error(rank):
    with pytest.raises(ValueError, match="2024 race 2: HAM"):
        rank([_row(2, "VER", 0.5, 0.5), _row(2, "HAM", 0.3, 0.3)], _pairs(2, "VER@RED"))


@pytest.mark.parametrize("rank", [_positions, _places])
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


def _archive_only(*races: tuple) -> SignalTables:
    history = _History()
    for season, race, drivers, constructors in races:
        history.race(season, race, drivers, constructors, with_metrics=False)
    return history.tables()


# 2023's table, from races 2 and 3. After a recent negative, 3 of 4 go negative: VER both
# times and PER once, which as exact counts would be all of those after one and half of
# those after two. After none, 1 of 4: HAM at race 3, never RUS. Race 1 builds no row,
# which BOT, negative there alone, would show. The constructors follow their drivers.
_NEGATIVES_2023 = [
    (2023, 1, {"VER@RED": -5, "PER@ALP": -5, "HAM@MER": 10, "RUS@WIL": 10, "BOT@ALF": -5},
     {"RED": -5, "ALP": -5, "MER": 10, "WIL": 10, "ALF": -5}),
    (2023, 2, {"VER@RED": -5, "PER@ALP": -5, "HAM@MER": 10, "RUS@WIL": 10},
     {"RED": -5, "ALP": -5, "MER": 10, "WIL": 10}),
    (2023, 3, {"VER@RED": -5, "PER@ALP": 10, "HAM@MER": -3, "RUS@WIL": 10},
     {"RED": -5, "ALP": 10, "MER": -3, "WIL": 10}),
]


def test_negative_chance_is_by_asset_type_and_any_recent_negative():
    tables = _archive_only(
        *_NEGATIVES_2023,
        (2024, 1, {"VER@RED": 5, "HAM@MER": 5}, {"RED": -5, "MER": 5}),
        (2024, 2, {"VER@RED": 5, "HAM@MER": 5}, {"RED": 5, "MER": 5}),
    )
    assert tables.negative_chance(2024, 2) == {
        "VER@RED": 0.25, "HAM@MER": 0.25, "RED": 0.75, "MER": 0.25,
    }


def test_two_or_three_recent_negatives_count_the_same_as_one():
    tables = _archive_only(
        *_NEGATIVES_2023,
        (2024, 1, {"VER@RED": -5, "HAM@MER": 5}, {"RED": -5, "MER": 5}),
        (2024, 2, {"VER@RED": -5, "HAM@MER": 5}, {"RED": -5, "MER": 5}),
        (2024, 3, {"VER@RED": -5, "HAM@MER": -5}, {"RED": -5, "MER": -5}),
        (2024, 4, {"VER@RED": 5, "HAM@MER": 5}, {"RED": 5, "MER": 5}),
    )
    assert tables.negative_chance(2024, 4) == {
        "VER@RED": 0.75, "HAM@MER": 0.75, "RED": 0.75, "MER": 0.75,
    }


def test_only_the_previous_three_rounds_count():
    tables = _archive_only(
        *_NEGATIVES_2023,
        (2024, 1, {"VER@RED": -5, "HAM@MER": 5}, {"RED": 5, "MER": 5}),
        (2024, 2, {"VER@RED": 5, "HAM@MER": -5}, {"RED": 5, "MER": 5}),
        (2024, 3, {"VER@RED": 5, "HAM@MER": 5}, {"RED": 5, "MER": 5}),
        (2024, 4, {"VER@RED": 5, "HAM@MER": 5}, {"RED": 5, "MER": 5}),
        (2024, 5, {"VER@RED": 5, "HAM@MER": 5}, {"RED": 5, "MER": 5}),
    )
    chance = tables.negative_chance(2024, 5)
    assert (chance["VER@RED"], chance["HAM@MER"]) == (0.25, 0.75)


def test_a_driver_carries_their_negatives_to_a_new_team():
    tables = _archive_only(
        *_NEGATIVES_2023,
        (2024, 1, {"LAW@VRB": -5}, {"VRB": 5}),
        (2024, 2, {"LAW@RED": 5}, {"RED": 5}),
    )
    assert tables.negative_chance(2024, 2)["LAW@RED"] == 0.75


def test_an_asset_with_no_history_counts_as_no_negatives():
    tables = _archive_only(*_NEGATIVES_2023, (2024, 2, {"CAM@HAA": 5}, {"HAA": 5}))
    assert tables.negative_chance(2024, 2) == {"CAM@HAA": 0.25, "HAA": 0.25}


def _negatives_varying(points: int) -> SignalTables:
    """2024 race 1 fixed; 2024 race 2 on and all of 2026 at ``points``."""
    varying = ({"VER@RED": points, "HAM@MER": points}, {"RED": points, "MER": points})
    return _archive_only(
        *_NEGATIVES_2023,
        (2024, 1, {"VER@RED": -5, "HAM@MER": 5}, {"RED": -5, "MER": 5}),
        *((2024, race, *varying) for race in (2, 3)),
        *((2026, race, *varying) for race in (1, 2, 3)),
    )


def test_negative_chance_reads_neither_the_race_its_own_season_nor_2026():
    low, high = _negatives_varying(-1000), _negatives_varying(1000)
    expected = {"VER@RED": 0.75, "HAM@MER": 0.25, "RED": 0.75, "MER": 0.25}
    assert low.negative_chance(2024, 2) == high.negative_chance(2024, 2) == expected


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
