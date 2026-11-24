import math
from pathlib import Path

import pandas as pd
import pytest
from pulp import LpStatusOptimal, value

from linear.strategy_base import VarType
from linear.strategy_odds_fp3 import StrategyOddsFP3

_SEASON = 2026
_RACE = 3

# Two constructors of two drivers each, every asset at the same price unless a test says
# otherwise, so only the values decide the pick
_DRIVER_PAIRS = {
    "A1@CA": "CA",
    "A2@CA": "CA",
    "B1@CB": "CB",
    "B2@CB": "CB",
}
_CONSTRUCTORS = ["CA", "CB"]


def _metrics_file(
    tmp_path: Path,
    rows: dict[str, tuple[float, float]],
    race: int = _RACE,
    sprint: bool = False,
) -> Path:
    """Write metrics rows in the shape of ``data/fastf1_practice_rolling_metrics.csv``.

    Args:
        tmp_path: Folder to write into.
        rows: Bare driver code -> (OddsRank, FP3_MinLapTime_rank).
        race: The race the rows are for.
        sprint: Give the race a sprint weekend's sessions (FP1 and SQ) in place of FP2 and FP3.
    """
    records = []
    for driver, (odds, fp3) in rows.items():
        records.append({
            "Driver": driver,
            "Season": _SEASON,
            "Race": race,
            "RollingPointsRank": 0.5,
            "ConstructorRollingPointsRank": 0.5,
            "FP2_MinLapTime_rank": math.nan if sprint else 0.5,
            "FP3_MinLapTime_rank": math.nan if sprint else fp3,
            "OddsImpliedProbability": 0.1,
            "OddsRank": odds,
            "FP1_MinLapTime_rank": 0.5 if sprint else math.nan,
            "SQ_MinLapTime_rank": fp3 if sprint else math.nan,
        })
    path = tmp_path / "metrics.csv"
    pd.DataFrame(records).to_csv(path, index=False)
    return path


def _strategy(
    fn_metrics: Path,
    num_drivers: int = 1,
    num_constructors: int = 1,
    driver_pairs: dict[str, str] = _DRIVER_PAIRS,
    prices: dict[str, float] | None = None,
    max_cost: float = 100.0,
    **kwargs,
) -> StrategyOddsFP3:
    """A strategy for the fixture race, from a placeholder team with every move allowed.

    The team's size is taken from the placeholder, so a test sets it with `num_drivers`
    and `num_constructors`.
    """
    drivers = list(driver_pairs)
    constructors = sorted(set(driver_pairs.values()))
    if prices is None:
        prices = {asset: 1.0 for asset in drivers + constructors}
    return StrategyOddsFP3(
        team_drivers=drivers[:num_drivers],
        team_constructors=constructors[:num_constructors],
        all_available_drivers=drivers,
        all_available_constructors=constructors,
        all_available_driver_pairs=driver_pairs,
        prev_available_driver_pairs=driver_pairs,
        max_cost=max_cost,
        max_moves=num_drivers + num_constructors,
        prices_assets=prices,
        derivs_assets={},
        race_num=_RACE,
        season_year=_SEASON,
        fn_metrics=fn_metrics,
        **kwargs,
    )


def _solve(strat: StrategyOddsFP3) -> tuple[set[str], float]:
    """Solve, returning the selected assets and the objective's value."""
    model = strat.execute()
    assert model.status == LpStatusOptimal
    chosen = set()
    for var_type in (VarType.TeamDrivers, VarType.TeamConstructors):
        chosen |= {a for a, var in strat._lp_variables[var_type].items() if var.value() > 0.5}
    return chosen, value(model.objective)


# Odds favour A1 and CA; FP3 favours B1 and CB
_SPLIT_ROWS = {
    "A1": (1.0, 0.0),
    "A2": (0.0, 0.0),
    "B1": (0.2, 1.0),
    "B2": (0.0, 0.6),
}


@pytest.mark.parametrize("odds_weight, expected_team, expected_objective", [
    # Odds alone: A1 1.0 counted twice for DRS, CA 1.0 + 0.0
    (1.0, {"A1@CA", "CA"}, 3.0),
    # FP3 alone: B1 1.0 counted twice, CB 1.0 + 0.6
    (0.0, {"B1@CB", "CB"}, 3.6),
    # Even split: B1 0.6 counted twice, CB 0.6 + 0.3, beating A1 0.5 twice and CA 0.5
    (0.5, {"B1@CB", "CB"}, 2.1),
])
def test_strategy_odds_fp3_value_mixes_odds_and_fp3_by_weight(
    tmp_path, odds_weight, expected_team, expected_objective
):
    """Each driver's value is `w * OddsRank + (1 - w) * FP3 rank`, so the weight decides the pick."""
    strat = _strategy(_metrics_file(tmp_path, _SPLIT_ROWS), odds_weight=odds_weight)

    chosen, objective = _solve(strat)

    assert chosen == expected_team
    assert objective == pytest.approx(expected_objective)


def test_strategy_odds_fp3_default_weight_is_an_even_split(tmp_path):
    """Left unset, the weight is 0.5."""
    chosen, objective = _solve(_strategy(_metrics_file(tmp_path, _SPLIT_ROWS)))

    assert chosen == {"B1@CB", "CB"}
    assert objective == pytest.approx(2.1)


def test_strategy_odds_fp3_constructor_value_is_the_sum_of_its_drivers(tmp_path):
    """CB's drivers sum to 1.4, beating CA's 1.0, though CA holds the best single driver."""
    rows = {"A1": (1.0, 0.0), "A2": (0.0, 0.0), "B1": (0.7, 0.0), "B2": (0.7, 0.0)}

    chosen, objective = _solve(_strategy(_metrics_file(tmp_path, rows), odds_weight=1.0))

    # A1 1.0 counted twice for DRS, then CB 0.7 + 0.7
    assert chosen == {"A1@CA", "CB"}
    assert objective == pytest.approx(3.4)


def test_strategy_odds_fp3_missing_input_scores_zero(tmp_path):
    """A driver with no odds keeps their FP3 share, and one with no FP3 keeps their odds share."""
    rows = {"A1": (math.nan, 1.0), "A2": (0.0, 0.0), "B1": (0.8, math.nan), "B2": (0.0, 0.0)}

    chosen, objective = _solve(_strategy(_metrics_file(tmp_path, rows), odds_weight=0.25))

    # A1 0.75 counted twice, then CA 0.75 + 0.0, against B1 0.2 twice and CB 0.2
    assert chosen == {"A1@CA", "CA"}
    assert objective == pytest.approx(2.25)


def test_strategy_odds_fp3_driver_with_no_metrics_row_scores_zero(tmp_path):
    """A fantasy driver the metrics do not hold has no value, and can still be picked."""
    rows = {"A1": (1.0, 1.0), "A2": (1.0, 1.0), "B1": (1.0, 1.0)}
    # Only B2, who has no row, and the constructors are affordable
    prices = {"A1@CA": 50.0, "A2@CA": 50.0, "B1@CB": 50.0, "B2@CB": 1.0, "CA": 1.0, "CB": 1.0}

    chosen, objective = _solve(_strategy(_metrics_file(tmp_path, rows), prices=prices, max_cost=2.0))

    # B2 counts zero, twice; CA holds two drivers worth 1.0 each
    assert chosen == {"B2@CB", "CA"}
    assert objective == pytest.approx(2.0)


# P is worth most alone; R and S together beat P and Q unless P counts twice for DRS
_DRS_PAIRS = {"P@CP": "CP", "Q@CP": "CP", "R@CR": "CR", "S@CR": "CR"}
_DRS_PRICES = {"P@CP": 6.0, "Q@CP": 1.0, "R@CR": 3.0, "S@CR": 3.0, "CP": 1.0, "CR": 1.0}
_DRS_ROWS = {"P": (1.0, 1.0), "Q": (0.0, 0.0), "R": (0.6, 0.6), "S": (0.6, 0.6)}


def test_strategy_odds_fp3_chooses_drs_inside_the_lp(tmp_path):
    """Counting P twice makes P and Q worth 2.0 against R and S's 1.8, so the DRS term decides the team."""
    strat = _strategy(
        _metrics_file(tmp_path, _DRS_ROWS),
        num_drivers=2,
        num_constructors=0,
        driver_pairs=_DRS_PAIRS,
        prices=_DRS_PRICES,
        max_cost=7.0,
    )

    chosen, objective = _solve(strat)

    assert chosen == {"P@CP", "Q@CP"}
    assert objective == pytest.approx(2.0)
    assert strat.get_drs_driver() == "P@CP"


def test_strategy_odds_fp3_leaves_drs_to_the_default_when_no_driver_has_value(tmp_path):
    """With every value zero the LP's DRS pick means nothing, so the default rule (dearest driver) is left to choose."""
    rows = {"A1": (0.0, 0.0), "A2": (0.0, 0.0), "B1": (0.0, 0.0), "B2": (0.0, 0.0)}
    strat = _strategy(_metrics_file(tmp_path, rows))

    _solve(strat)

    assert strat.get_drs_driver() == ""


def test_strategy_odds_fp3_raises_on_a_sprint_weekend(tmp_path):
    """A sprint weekend has no FP3, so the strategy refuses it rather than scoring FP3 as zero."""
    with pytest.raises(ValueError, match="sprint"):
        _strategy(_metrics_file(tmp_path, _SPLIT_ROWS, sprint=True))


def test_strategy_odds_fp3_raises_on_a_race_with_no_rows(tmp_path):
    """Rows for another race only are no rows for this one."""
    with pytest.raises(ValueError, match="No metrics rows"):
        _strategy(_metrics_file(tmp_path, _SPLIT_ROWS, race=_RACE + 1))


def test_strategy_odds_fp3_raises_on_a_missing_metrics_file(tmp_path):
    """A metrics file that does not exist holds no rows."""
    with pytest.raises(ValueError, match="No metrics rows"):
        _strategy(tmp_path / "missing.csv")


@pytest.mark.parametrize("odds_weight", [-0.1, 1.1])
def test_strategy_odds_fp3_raises_on_a_weight_outside_zero_to_one(tmp_path, odds_weight):
    """A weight outside 0-1 would score one input negatively."""
    with pytest.raises(ValueError, match="odds_weight"):
        _strategy(_metrics_file(tmp_path, _SPLIT_ROWS), odds_weight=odds_weight)
