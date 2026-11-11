# live_picks_v1 — Log

## 2026-11-09 — Effort opened

Picked *Live mid-season picks with `StrategyFastF1`* off `BACKLOG.md`, removed it
from that list, and quoted it unchanged in `requirements.md`. Alex widened the scope
the same day: move `run_single_team.py`'s shared code somewhere common and review
its tests, and build one pre-race script that collects the week's data, runs P2PM and
FastF1, and records the chosen pick in a committed team file with free moves, team
value and unused budget.

Settled through a grilling session of 21 questions, recorded as D1–D33 in
`requirements.md`. The reasoning that mattered:

- **The app is the truth, not the script** (Q1). Team, unused budget and free moves
  are confirmed every run, as a wrong budget would give a pick the app rejects.
- **Only the played pick is committed** (Q3). A strategy's pick is made from Alex's
  team, chosen by whichever strategy he played, so a season of them does not show
  how that strategy would do alone. That needs shadow teams, moved to the backlog.
- **The file replaces `TEAM_2026.md` without backfill** (Q4): the table lacks
  unused budget, DRS and free moves, so a backfill would invent them.
- **P2PM's race-4 Wildcard spends Alex's real chip** (Q8), free in a back-test but
  not live. `StrategyMaxP2PMNoReset` already gives the no-chip pick, so nothing in
  `linear/` changes for it.
- **Nothing the script runs after race 1 reads odds** (Q13), so missing odds is a
  warning for the record from race 2, an error only at race 1.
- **Limitless needs a finite cap** (Q15). A cap at or above `COST_PROHIBITIVE`
  would make a driver who has left the race affordable, so the cap is the sum of
  every available asset's price.

Race-1 odds check, run 2026-11-09 with `scripts/select_odds_start.py` on today's
data: limit 4 gave the same team as no limit, limits 3, 2, 1 and 0 each a different
one. One season cannot show 4 never matters, so all six limits are kept and
identical teams merged (D29). The limit-1 team today is not the one Alex played at
race 1 (`TEAM_2026.md`), most likely because the stored race-1 odds were replaced
after he picked. Not investigated: live use reads whatever odds are stored at the
time.

Core-module grants for this effort, from Alex 2026-11-09: the move of
`run_single_team.py`'s shared functions (D1, D2), and `max_cost` on
`factory_strategy` (D6), chosen over a team-copy workaround.

Added to `BACKLOG.md`: shadow teams per strategy, and BoxBox capture of a new
season, which race-1 mode needs for real use (D30).

No code written.

## 2026-11-11 — Step 1: shared code moved to `simulate/`

Done. Alex settled four questions up front so the step could run unattended: the
pin is a JSON fixture and stays, replacing `test_run_batch.py`'s length-only check;
`run_single_team.py`'s `__main__` may overwrite its xlsx; on a step 2 mismatch,
investigate and stop; and the API shape for `simulate/pick.py` and `max_cost` as
proposed (below).

- **1.1 Pin.** `data/test_run_for_team_2025.json` holds every per-race row of 2025
  from Alex's 2025 starting team, for `StrategyMaxP2PM` and `StrategyFastF1RuleRise`
  (2 × 24 rows), recorded from the code before anything moved. Two recordings in
  separate processes were byte-identical. P2PM's run includes both 2- and 3-move
  races; FastF1's never carries a move. `tests/test_simulate_season.py` compares
  rows exactly. It cannot fail before a change, so it was checked by mutation: the
  carry rule at `< 1` failed P2PM at race 9, and dropping the DRS assignment failed
  both at race 2.
- **1.2 Move.** `run_for_team`, `get_row_intermediate_results` and
  `get_strat_display_name` moved to `simulate/season.py` unchanged, apart from one
  trailing-whitespace line. `run_single_team.py` keeps its settings and `__main__`.
  `backtest/runner.py`, `backtest/per_race.py` and five test files now import from
  `simulate`. `run_single_team.py` was run before and after the move: its xlsx was
  equal by `DataFrame.equals`. That run starts at 2026 race 21, the last priced
  race, so it re-solves nothing and only shows the script still runs.
- **1.3 Test gaps (D4).** All on a hand-built world (`tests/simulate_fixtures.py`):
  four drivers in two constructors, and a test strategy that maximises a `score`
  deriv and nominates the cheapest driver for DRS. The tests cover the free-move
  carry-over at both edges of the rule, unused budget and the DRS driver carried
  into the next race, a start after race 1, the error when the solver is not
  optimal, the row's columns and order, and the name helper. Each was confirmed by
  a mutation that turned it red: the rule at `< 1` and at `< 3`, unused budget not
  carried, DRS not set, solving the start race, the raise removed, the name's
  separator, and the row's rounding.
- **1.4 Split.** `simulate/pick.py` has `solve_race(strategy, team, race, race_prev,
  season_year, max_moves) -> Pick`, a frozen dataclass of sorted drivers and
  constructors, DRS driver, `moves_used` (`int` of the solver's value, as before),
  `cost` and `unused_budget` (the solver's value, unrounded, as before). It leaves the
  team unchanged, and its `RuntimeError` now has a message. `next_free_moves` is the
  rule on its own: 3 after fewer than 2 moves, else 2. It tests the `int` where the
  old code tested the float, which gives the same answer for any value ≥ 0.
  `run_for_team` applies each pick. Tests went red against stubs first, and the pin
  is unchanged.
- **1.5 `bonus_free_transfer`** (D2), default `False`: the first race picked gets 3
  moves. It went red with the argument accepted but ignored.

Suite 657 → 676, all green. `run_single_team.py`'s 2026 replay that re-solves races
comes in step 2's verification, before and after `max_cost`.

## 2026-11-11 — Step 2: `max_cost` and the Limitless cap

Done (verified).

- **`factory_strategy(..., max_cost: float | None = None)`** (D6), the only change
  in `linear/`. `None` keeps `team.total_budget(race, race_prev)`. One side effect:
  when a cap is given the team's budget is not computed, so the `KeyError` for a held
  driver priced in neither race does not arise. The test went red on behaviour (30.5
  where 55.5 was given) with the argument accepted but ignored.
- **`solve_race(..., max_cost=None)`** passes it through, and **`limitless_cap(race)`**
  (D7) sums every available driver's and constructor's price. The test of a held
  driver who has left the race uses `StrategyMaxBudget`, which keeps him under any
  cap at or above `COST_PROHIBITIVE`. Mutating the cap to 2,000,000 made the test
  fail with him kept, at a cost of 1,000,019.99.
- **Verification, run, not reasoned**, on the final code of both commits, which also
  covers step 1:
  - **2026 replays** through `run_for_team`, recorded at `3fb7715` before the
    change and again after: the full season from the race-1 line-up (re-solving
    races 2–21) and `run_single_team.py`'s live configuration from race 21. Both
    were exactly equal. A copy with one `total_points` plus 1 compared unequal.
  - **Back-test rows.** `backtest_v1`'s P2PM sample was re-simulated into a
    scratch store: seed 1, 500 per band, 2023–25, 4,500 runs, 27 minutes. Against
    the P2PM rows in `outputs/backtest_v1_results.parquet` there were the same
    4,500 `sim_key`s, none on either side only, and all 40 columns **exactly equal**
    by `DataFrame.equals`. A copy with one `total_points` plus 1 compared unequal.
- Suite 676 → 683, all green. The probe scripts were session scratch files and are
  not kept.

Nothing in this step needed an R12 entry: both core-module changes were granted,
and nothing worked around them.

**Next: step 3, the team file.** No network, and no core-module changes expected.
