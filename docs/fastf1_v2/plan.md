# fastf1_v2 — Plan

**Status**: steps 1 to 8 are done, and step 8 found every FastF1 label trailing P2PM in 2023–25.
Stepping back found that the expected-points table loses how far ahead an asset is (`log.md`,
*Stepping back*), so the signal design is redone next, as *Next: signal redesign* below. Steps
9 and 10 wait for it. Requirements: `requirements.md`.

One commit per concern, for review per commit. Each behavioural change is seen failing before it
passes, and the full suite is green at the end of every step. No existing file in `linear/`,
`races/`, `import_data/` or `scripts/` is edited. Anything the code has to work around in them goes
in the R12 ledger in `docs/backtest_v1/requirements.md`.

## Next: signal redesign

Before any other step:

1. Reopen requirements question 1, how the signal becomes points the LP adds up, with the
   findings in `log.md`, *Stepping back*. The design must keep the size of an asset's lead,
   not just its order, and must still build only from other seasons. Agree it with Alex
   before any code.
2. Revise steps 4 to 6 to match, with a log entry for what changes. Step 4's positions may
   stay if the agreed design still uses them. Step 5's tables and step 6's objective are what
   carried the fault.
3. Add a check that a redesign scores assets in the right amounts, not only the right
   order, as the indicator analysis's rank correlation cannot see this fault. 2023's VER is
   the known case it must pass.
4. Then rerun step 8 on the new design, in new stores, before step 9.

Steps 1 to 3b stand: the 2024 race 24 fix, the recomputed file, the indicator analysis and a
driver's team before the race are all independent of how the signal is scored.

## Step 1 — The 2024 race 24 fault, in the code

Done. See `log.md`, *Step 1.1* and *Steps 1.2 and 1.3*.

## Step 2 — Recompute 2024 race 24 (real system)

Done, with only the 8 affected rows changed. See `log.md`, *Step 2*.

## Step 3 — Re-run the indicator analysis

Done, and the winners hold. See `log.md`, *Step 3*.

## Step 3b — A driver's team before the race has results

Done, from the practice sessions' driver lists. See `log.md`, *Step 3b*.

## Step 4 — `fast_f1/signal.py`: the signal

Done: driver positions and constructor places, run on every stored race. See `log.md`, *Step
4*. The redesign decides whether its positions stay.

## Step 5 — `fast_f1/signal.py`: the tables

Built (`log.md`, *Step 5*), and reopened by the signal redesign. A table of mean points by
position gives first by a mile the same points as first by a whisker, and in 2023 tied
positions 1 and 2. The negatives table is not at fault, but is revisited with the design.

As built:

- Expected fantasy points by driver position and by constructor place, as means forced to fall
  by position, which erred less than plain means out of sample for both tables. A season's
  table uses 2023–25 minus that season, so 2026's uses all three.
- A position with no history carries the last known value.
- One table across weekend formats, as checked on 2023–25 (`log.md`, *One table or two*).
- The chance of going negative, by asset type and by whether there was any negative in its last
  three races, as Alex chose. Same seasons rule, using only races before the one picked.
- Cached once per process, as a strategy is built per team per race.
- Tests: a season's own results cannot change its table, and 2026 cannot change a 2023–25 table.

## Step 6 — `linear/strategy_fastf1.py`

Built (`log.md`, *Step 6*), and to be revised for the new signal design, as its objective adds up
step 5's table values.

`StrategyFastF1(StrategyBase)`, with keyword parameters `fn_metrics`, `drs_coefficient=1.0`,
`negative_penalty=0.0` and `budget_reward=0.0`. There is no fixture file, as Alex agreed: the
tables need real 2023–25 metrics rows matched to the real archive, which no small file can give.
Unit tests stub `load_signal_tables` with set expected points, and one test builds the strategy on
the real files for 2025 race 5. One part per commit, each keyword parameter arriving with the
part that uses it:

1. Objective of expected points, respecting the base budget, team size and move constraints. **No
   race-4 chip:** a test shows race 4 keeps its normal move limit.
2. DRS: the helper's term scaled by `drs_coefficient`, left out at zero. `get_drs_driver()` returns
   the selected driver with the best value, and an empty string when none has one, so the default
   picks.
3. `budget_reward * TotalCost`, with a test that zero leaves the team unchanged.
4. Minus `negative_penalty * chance`, with the same test at zero.
5. A race with no signal scores every asset zero, and solves.

## Step 7 — Harness

Done: the strategy and its tuning variants are in `STRATEGIES` in `backtest/cli.py`. See
`log.md`, *Step 7*.

## Step 8 — Tuning on 2023–25 (real run)

Run (`log.md`, *Step 8*), and to be rerun on the new signal design. Its results describe a
strategy with the table fault, so its choice of the base settings does not carry over. The rerun
uses new stores, not `outputs/fastf1_v2_tuning_*`.

The variants, built by `make_variant` with one change from the base each:

| Label | Change from the base |
| --- | --- |
| `StrategyFastF1` | None: DRS coefficient 1, no penalty, no reward |
| `FastF1_Drs0` | DRS coefficient 0 |
| `FastF1_Neg6`, `FastF1_Neg12` | Penalty 6, 12 (a negative averages about −12 points) |
| `FastF1_Bud025`, `FastF1_Bud05`, `FastF1_Bud1` | Reward 0.25, 0.5, 1 point per 1m |

Run at 100 teams a band, seed 2, in one store per season, as Alex chose. Seed 1 at 100 teams a
band draws the first 100 of step 9's 500. 2026 is not run or looked at. Time a small run first,
and run in the background.

A penalty or reward is kept only if it clears the harness's bar against the base: a positive pooled
mean delta in each of 2023–25. Otherwise it stays at zero. If one of each clears, the combination is
run too and must clear the same bar. Log every variant tried, including the failures.

## Step 9 — The back-test (real run)

On hold until the redesign and step 8's rerun. Not started, so its one run is still unspent.

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
