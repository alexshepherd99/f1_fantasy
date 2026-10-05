# odds_drs_v1 — Log

Execution log for the odds_drs_v1 effort. Newest entries at the bottom.
Requirements and plan live alongside in `requirements.md` and `plan.md`.

## Status summary

- Effort started 2026-10-05. Step 1 (docs) is complete, with requirements and
  plan agreed.
- Step 2 completed 2026-10-05: `StrategyBettingOdds` puts DRS inside its
  objective.
- Step 3 completed 2026-10-05: registered in `backtest/cli.py`.
- Step 4 completed 2026-10-05: timing run done, sample size agreed as 500
  per band.
- Step 5 completed 2026-10-05: back-test run. The odds strategy lost to
  P2PM by about 390 points (−12%) through race 16.
- Step 6 completed 2026-10-05: close-out. The effort is done.

## 2026-10-05 — Scoping

Scope agreed in conversation before writing anything:

- Edit `StrategyBettingOdds` only, with DRS always on, and leave the rest of
  `linear/` alone. The live team is mid-season.
- Run the back-test through the existing harness rather than writing a new
  per-race limitless comparison. It covers 2026 through race 16.
- Keep the code. The findings go here, and the results are discarded.

Found while scoping:

- Odds exist only for 2026 races 1–17, so no other season can be back-tested.
- The harness skips teams already in its store, so this run must not use the
  default store. If it did, the end-of-season run would silently reuse its
  partial-season rows (R7).

Q1 settled as (a): when the LP's DRS nominee has no odds, return `""` so
`Team` keeps its highest-price fallback. The fallback sits in the odds
strategy, not in `StrategyBase`.

## 2026-10-05 — Step 2, DRS inside the odds objective

`get_problem()` now passes each available driver's odds to
`get_drs_objective_term()`, adds the term to the objective, and applies the
constraints. `get_drs_driver()` returns `get_drs_nominee()`, or `""` when the
nominee has no odds.

Two new tests, both seen failing:

- `test_strategy_odds_drs_changes_selection` is a budget-limited case in which
  doubling the DRS driver's odds changes which pair is best. The old code
  failed it by picking A1/A2 (best without DRS) instead of B1/B2.
- `test_strategy_odds_drs_no_odds_falls_back` passed on the old code, which
  already had this fallback. To check that it guards anything, the change was
  first made without the fallback. The test then failed, with the LP
  nominating an arbitrary zero-odds driver (`B2@C2`), before the fallback was
  added.

The existing `test_strategy_odds_run` still expects `Drv3@Con2` to get DRS, and
passes unchanged. Full suite green, 278 passed.

## 2026-10-05 — Step 3, registered in the back-test CLI

`StrategyBettingOdds` is added to `STRATEGIES` in `backtest/cli.py`. R5's "one
line" became an import plus the registry list wrapped over three lines to fit
the width. Nothing else in `backtest/` changed.

In `tests/test_backtest_cli.py`, the exact-match registry test gains the entry
and there is a new `test_betting_odds_is_selectable_as_a_challenger`. Both
failed before registration, the second because argparse rejected the name.
Full suite green, 279 passed.

## 2026-10-05 — Step 4, timing run and sample size

Ran `--seasons 2026 --strategies StrategyBettingOdds --sample-size 2`, writing
to `outputs/odds_drs_v1_timing_*` so that neither the shared store nor the
step-5 path was touched (R7). That is 6 teams and 12 simulations.

- 11.5 s wall time, including data load and enumerating starting teams, so
  at most about 1 s per simulation.
- 285 MB peak RSS. Enumeration runs at full size whatever the sample size, so
  memory should barely grow with more teams.
- Exit 0, no errors in the log.
- `/usr/bin/time` is not installed here, so wall time and peak RSS came from a
  Python wrapper using `getrusage(RUSAGE_CHILDREN)`.

The 6 teams were a smoke test, not a result. The odds strategy trailed P2PM in
all six, by a mean of −379 points (−11%).

Agreed with Alex: 500 per band, the harness default (1,500 teams, 3,000
simulations), estimated at 30–50 minutes. The timing files are deleted.

## 2026-10-05 — Step 5, the 2026 back-test

Ran the plan's command with `--sample-size 500`: 1,500 teams, 3,000
simulations, and no errors. It took 23.5 minutes, longer than the timing run
suggested, because the time per save rose from about 28 s to 65 s per 100
rows as the run went on. Peak RSS was 285 MB. Results are in
`outputs/odds_drs_v1_*`, which are not committed (R8).

**What this cannot show (R9).** This is one partial season of 15 decisions per
team (races 2–16), played under normal budget and move rules rather than the
race-17 limitless rules. It changes the objective and the DRS choice together,
so it cannot say which of the two caused the gap. Concentration is
effectively off (R4).

**What it shows.** The odds strategy trails P2PM by a wide, consistent margin:

| Band | Mean Δ | Median Δ | p10 Δ | Win rate |
|---|---|---|---|---|
| (90, 95] | −412 (−12.4%) | −410 | −639 | 1.4% |
| (95, 99.5] | −387 (−11.6%) | −386 | −613 | 1.8% |
| (99.5, 100] | −382 (−11.4%) | −379 | −630 | 1.8% |
| pooled | −394 (−11.8%) | −390 | −623 | 1.7% |

The odds strategy wins 25 of 1,500 pairs, and there are no ties. The gap barely
depends on starting value. P2PM's pooled mean is 3,307 and the odds strategy's
is 2,913.

From the stored rows (final race only, so these describe race 17, not the
season): both strategies give DRS to `VER@RED` in every team. The odds
strategy's race-17 line-ups pair VER and ANT with cheap drivers (`PER@CAD`,
`BOT@CAD`, `STR@AST`, `HUL@AUD`) and leave more budget unused than P2PM
(mean 2.44 vs 1.15). This fits an objective that values the two favourites
and gives long shots almost nothing. It is untested, because nothing here
re-simulates the season race by race.

## 2026-10-05 — Step 6, close-out and end-of-session review

- `CLAUDE.md`: the DRS helper is now described as having one caller,
  `StrategyBettingOdds`. The odds strategy's entry gives its in-LP DRS and the
  back-test result.
- `BACKLOG.md`: the effort is marked done. The *better DRS nomination* item
  gets a dated note where it says the helper has no caller.
- `README.md`: the line saying the odds strategy has never been back-tested
  gets a dated note pointing here. The plan did not list this, but it was made
  stale by this effort.
- `plan.md`: its "not yet implemented" status line is annotated.

Review:

- Every step stayed in scope (R5). The only code edits are in
  `linear/strategy_odds.py` and `backtest/cli.py`, plus their tests. The
  shared store `outputs/backtest_v1_results.parquet` was not touched (R7).
- The timing run's estimate of 30–50 minutes held (the run took 23.5), but
  only by luck. Save time grew as the results file grew, so a 6-team run
  understates per-row cost at scale. Next time, take a second timing at a
  larger size, or read the rate off the first few saves of the real run.
- Not fixed, out of scope: `BACKLOG.md` still says odds cover 2026 races 1–11
  (lines 87, 245, 251, 339, 345). The odds file now holds races 1–17.
  [2026-10-05: fixed at Alex's request, with dated markers on lines 87, 251
  and 345. Lines 245 and 339 were wrongly listed. They describe
  `data/fastf1_practice_rolling_metrics.xlsx`, which still holds 2023 races
  1–6 and 2026 races 1–11 (342 rows), so they are accurate.]
- Not executed: the race-17 limitless selection. It was never part of this
  effort, and Alex will run it by hand through `scripts/run_single_team.py`.
- No code changed in this step. The suite was last run green, 279 passed,
  before step 4.
