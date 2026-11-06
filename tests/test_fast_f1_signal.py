import pandas as pd

from fast_f1.signal import driver_positions


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
