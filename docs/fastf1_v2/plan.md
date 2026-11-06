# fastf1_v2 — Plan

**Status**: written 2026-11-01. Requirements: `requirements.md`, whose eight questions and working
assumptions are all answered. [2026-11-06: steps 1 to 5 done. Step 6 is next.]

One commit per concern, for review per commit. Each behavioural change is seen failing before it
passes, and the full suite is green at the end of every step. No existing file in `linear/`,
`races/`, `import_data/` or `scripts/` is edited. Anything the code has to work around in them goes
in the R12 ledger in `docs/backtest_v1/requirements.md`.

## Step 1 — The 2024 race 24 fault, in the code

Question 8 and `log.md`, *Reaching fantasy assets, and a fault in 2024 race 24*.

1. Check whether FastF1's `TeamId` stays the same across a rename, using 2024 races 21 to 24. Log
   the answer. If it does not, or cannot be reached, link old and new names through the drivers
   they share in the rolling window.
2. Write a failing test in which a team changes name between races and keeps its rolling points.
   Run the existing tests for a driver changing team, as a wrong link must not move their points.
3. Fix `fast_f1`. No list of names to maintain. The stored `Constructor` and `TeamName` columns stay
   as FastF1 gives them.

## Step 2 — Recompute 2024 race 24 (real system)

**Stop before this step: Alex agrees the check plan first.** The proposed checks:

- A copy of the file is taken first, outside the repo.
- Only 2024 race 24 is recomputed, through the normal `fast_f1` route. Any F1 sign-in goes through
  that route, and the credentials file is not read.
- A cell-by-cell comparison with the copy shows changes to at most 8 driver rows (Red Bull, Alpine,
  RB and Sauber), in `ConstructorRollingPoints` and `ConstructorRollingPointsRank` only.
- `AggregateRank` and `RankPosition` do not move, as that column's weight is zero.
- No row in any season has a missing `ConstructorRollingPoints` from race 2 onwards.

## Step 3 — Re-run the indicator analysis

Run `fast_f1.indicator_analysis` on the corrected file and compare it with
`docs/indicator_analysis_v1/log.md`. Log whether the winning combinations and their verdicts hold.
**If a winner changes, stop and raise it with Alex,** as every later step is built on them.

## Step 3b — A driver's team before the race has results

Added 2026-11-06, as Alex asked for it to be fixed within this effort. It must land before step 4,
which reads the constructor on each driver's row.

Before a race has results, as when picking a live team, `build_race_metrics` takes each driver's
team from the oldest of the previous three races. A driver who changed team in that window gets the
old team's points. A driver with no results in it, such as CAM at Haas in 2026 race 20, gets no
team, so step 4 would give them no position. Read from the code, and not run.

1. Agree with Alex where a driver with no recent results gets their team from, before any code.
   The practice sessions' driver lists are one candidate, as they name each driver's team.
2. A failing test for each case: a team change in the window, and a driver new to it.
3. Fix `fast_f1`, and check the stored file for rows that were built before their race had
   results, as a historical run on a race weekend would save one and never redo it.

## Step 4 — `fast_f1/signal.py`: the signal

Reuse `fast_f1/indicator_analysis.py` (`combination_signal`, the weekend formats and the slots)
rather than defining the signal a second time.

- For a season and race, give each driver's signal position, on driver + constructor + FP3 for a
  normal weekend and driver + constructor for a sprint weekend.
- Give each constructor its place on rolling points, reached through the driver and the archive's
  per-race pairs. Ties break on the identifier, so runs repeat.
- **No look-ahead.** `build_analysis_frame` drops rows using race results, such as drivers who did
  not start. A team is picked before the race, so the signal must not. A test changes a race's own
  results and shows that race's positions do not move.

## Step 5 — `fast_f1/signal.py`: the tables

- Expected fantasy points by driver position and by constructor place, as plain means from the
  archive. A season's table uses 2023–25 minus that season, so 2026's uses all three.
- A position with no history carries the last known value.
- One table across weekend formats, as 18 sprint weekends are too few to split by position. The LP
  compares assets within a race, so a sprint's higher scores matter little. [2026-11-01: checked on
  2023–25, and one table stands. See `log.md`, *One table or two*.]
- Plain means are out of order in places, such as driver position 11 above position 10 (same
  entry). Compare them with means forced to fall by position, using that entry's out-of-sample test
  on 2023–25 only, and use whichever errs less. [2026-11-06: forced means erred less for both
  tables. See `log.md`, *Step 5*.]
- The chance of going negative, by asset type and by the number of negatives in its last three
  races, for the negative penalty. Same seasons rule, using only races before the one picked.
  [2026-11-06: by whether there was any negative in them, not how many, as Alex chose. See
  `log.md`, *Step 5*.]
- Cached once per process, as a strategy is built per team per race.
- Tests: a season's own results cannot change its table, and 2026 cannot change a 2023–25 table.

## Step 6 — `linear/strategy_fastf1.py`

`StrategyFastF1(StrategyBase)`, with keyword parameters `fn_metrics`, `drs_coefficient=1.0`,
`negative_penalty=0.0` and `budget_reward=0.0`, and `data/test_fastf1_metrics.xlsx` as a fixture.
[2026-11-06: no fixture file, as Alex agreed. The tables need real 2023–25 metrics rows matched
to the real archive, which no small file can give. Unit tests stub `load_signal_tables` with set
expected points, and one test builds the strategy on the real files for 2025 race 5. Each
keyword parameter arrives with the part that uses it.]
Add one part per commit:

1. Objective of expected points, respecting the base budget, team size and move constraints. **No
   race-4 chip:** a test shows race 4 keeps its normal move limit.
2. DRS: the helper's term scaled by `drs_coefficient`, left out at zero. `get_drs_driver()` returns
   the selected driver with the best value, and an empty string when none has one, so the default
   picks.
3. `budget_reward * TotalCost`, with a test that zero leaves the team unchanged.
4. Minus `negative_penalty * chance`, with the same test at zero.
5. A race with no signal scores every asset zero, and solves.

## Step 7 — Harness

Add the strategy to `STRATEGIES` in `backtest/cli.py`, with its tuning variants built by
`make_variant`, one change from the base each:

| Label | Change from the base |
| --- | --- |
| `StrategyFastF1` | None: DRS coefficient 1, no penalty, no reward |
| `FastF1_Drs0` | DRS coefficient 0 |
| `FastF1_Neg6`, `FastF1_Neg12` | Penalty 6, 12 (a negative averages about −12 points) |
| `FastF1_Bud025`, `FastF1_Bud05`, `FastF1_Bud1` | Reward 0.25, 0.5, 1 point per 1m |

## Step 8 — Tuning on 2023–25 (real run)

Run the variants above at 100 teams a band, in stores of their own (`outputs/fastf1_v2_tuning_*`).
2026 is not run or looked at. Time a small run first, and run in the background.

A penalty or reward is kept only if it clears the harness's bar against the base: a positive pooled
mean delta in each of 2023–25. Otherwise it stays at zero. If one of each clears, the combination is
run too and must clear the same bar. Log every variant tried, including the failures.

## Step 9 — The back-test (real run)

**Run once, with the choice from step 8 logged before it starts.** All at 500 teams a band, seed 1,
in `outputs/fastf1_v2_results.parquet` and `outputs/fastf1_v2_summary.csv`, for 2023–26 with 2026
through race 18:

- the chosen strategy, whose result against `StrategyMaxP2PM` is the verdict;
- the same strategy with DRS coefficient 0, as the comparison;
- `StrategyMaxP2PMNoReset`, to isolate the chip's effect.

Report final budgets for each one. If the chosen strategy falls behind on budget the way the odds
strategy did, say so, as that is the condition for raising the price-rise reward with Alex.

## Step 10 — Findings and close-out

- Findings in `log.md`, in plain language first: the verdict, 2026 as the fair read, 2023–25 as
  flattered, how much of any gap the chip explains, the number of variants tried, and what has not
  been run.
- A row and key findings in `BACKTEST_LOG.md`.
- `CLAUDE.md` and `README.md` updated for the new strategy and `fast_f1/signal.py`.
- A `BACKLOG.md` item to rerun 2026 when the season finishes, as question 7 agreed. Update the
  efforts table.
