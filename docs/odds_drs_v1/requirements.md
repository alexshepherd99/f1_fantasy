# odds_drs_v1 — Requirements

**Status**: agreed 2026-10-05. Implementation plan in `plan.md`;
execution log in `log.md`.

Make `StrategyBettingOdds` choose its DRS driver inside the LP, using the opt-in
DRS helper on `StrategyBase` (`get_drs_objective_term` / `get_drs_nominee`, added
by `max_points_v1`). Then run a small, throwaway back-test of it against
`StrategyMaxP2PM` on the 2026 season so far.

## Why now, mid-season

Alex will play the *limitless* chip at 2026 race 17. The chip lifts both the
budget cap and the move limit for one race, and he will use `StrategyBettingOdds`
to pick that race's team. The strategy is not in use this season, so it can change
mid-season. Nothing else that picks the live team can.

Running the limitless selection is **not** part of this effort. Alex will adjust
`scripts/run_single_team.py` by hand to do it. The back-test is independent of
that selection and does not have to finish before it.

## Sources consolidated

- User decisions, 2026-10-05, taken in conversation before this effort was
  written up. They are recorded under the requirements they settle.
- `docs/max_points_v1/` — the DRS helper's design and tests. This effort is the
  helper's first caller.
- `docs/backtest_v1/` — the harness. Its requirements own sampling, pairing,
  keying and reporting, and are not repeated here.

## Requirements

**R1 — DRS in the objective, always on.** `StrategyBettingOdds.get_problem()`
adds the term from `get_drs_objective_term()` to its objective and applies the
returned constraints. There is no switch: the old "DRS after solving" behaviour
is not kept.

**R2 — DRS value is the driver's odds.** The value passed to the helper for each
driver is the same implied probability the objective already uses for that
driver (`self._odds_assets`). The DRS driver's odds are therefore counted twice.
Constructors are unchanged.

**R3 — `get_drs_driver()` reads the LP's choice.** It returns
`get_drs_nominee()` instead of re-deriving the highest-odds driver after the
solve. If the nominee's odds are 0.0, it returns `""` instead, so `Team` falls
back to the highest-priced driver, as it does today. The fallback lives in
`StrategyBettingOdds.get_drs_driver()`; `StrategyBase` is not edited (Q1).

**R4 — Concentration is unchanged.** The constraint, its definition and the
999.99 default `max_concentration` all stay as they are. The back-test leaves
the default in place, which in effect ignores concentration. Lifting the
concentration calculation into `StrategyBase` (BACKLOG) is out of scope, since
it would edit the base class.

**R5 — Nothing that picks the live team changes.**

- In `linear/`, only `strategy_odds.py` is edited.
- Nothing in `races/`, `import_data/` or `scripts/` is edited.
- In `backtest/`, the only edit is one line in `cli.py`, adding
  `StrategyBettingOdds` to `STRATEGIES` so the CLI can run it. That list only
  controls what the back-test CLI accepts.
- Existing tests are edited only where this change touches them:
  `tests/test_strategy_odds.py`, and the exact-match assertion on `STRATEGIES`
  in `tests/test_backtest_cli.py`.

**R6 — Back-test: the existing harness, 2026, scored through race 16.** Run
through `backtest.cli` with `--seasons 2026 --strategies StrategyBettingOdds`.
P2PM is the baseline, as always. Race 16 is the last race with post-race points.

- The archive already holds race 17, priced, with 0 points for every asset. The
  harness simulates race 17, but no team scores there, so final points equal
  points through race 16 for both strategies. No code is needed to stop early.
- Odds exist for 2026 races 1–17. The strategy first solves at race 2, since
  race 1 is the sampled starting team.
- The sample size is set in `plan.md` after a timing run, because this machine
  is short on memory.

**R7 — Back-test results never enter the shared store.** The run uses its own
`--output` and `--summary` paths under `outputs/`, never the defaults. The
harness skips any team already in its results file. 2026 rows in
`outputs/backtest_v1_results.parquet` would make the end-of-season run silently
reuse these race-16 results instead of re-simulating.

**R8 — What is kept.**

- The code is kept: the strategy change, its tests and the `cli.py` line.
- The results are not committed. `outputs/` is git-ignored.
- The headline findings go in this effort's `log.md` only. There is no
  `BACKTEST_LOG.md` row: the full back-test at the end of the season replaces
  this one and gets that row.

**R9 — Say what the back-test cannot show.** The findings say what the
comparison cannot distinguish before they say what it shows:

- It covers one partial season: 15 decisions per team, races 2–16.
- It runs the strategy under normal budget and move rules, which is not how
  race 17 will use it.
- It changes the objective and the DRS choice together, so it cannot say which
  of the two drove any difference.

## Questions settled

**Q1 — Fallback when every selected driver has zero odds.** Today,
`get_drs_driver()` returns `""` when no selected driver has odds. `Team` then
gives DRS to the highest-priced driver. With the helper, the LP must nominate
exactly one driver. If all candidates are worth 0.0, the nominee is whichever
one CBC happens to return. The options are:

- **(a)** Keep the fallback: return `""` when the nominee's odds are 0.0.
- **(b)** Always return the nominee.

Recommendation: (a). It keeps documented behaviour, costs one line, and the case
cannot arise in the back-test or at race 17, both of which have odds for every
race.

Settled 2026-10-05: **(a)**, now part of R3.
