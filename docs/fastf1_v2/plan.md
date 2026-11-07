# fastf1_v2 — Plan

**Status**: steps 1 to 8 are done. Step 8 found every FastF1 label trailing P2PM in 2023–25, and
stepping back found that the expected-points table loses how far ahead an asset is (`log.md`,
*Stepping back*). The signal redesign was agreed with Alex on 2026-11-07 (`log.md`, *Signal
redesign agreed*), and steps 11 to 16 build and tune it. Steps 11, 14.1 and 12 are done, and
so are steps 13.1 to 13.5. Step 13.6 is next. Steps 17 and 18, numbered 9 and 10 before 2026-11-07, follow step 16.
Requirements: `requirements.md`.

One commit per concern, for review per commit. Each behavioural change is seen failing before it
passes, and the full suite is green at the end of every step. No existing file in `linear/`,
`races/`, `import_data/` or `scripts/` is edited. Anything the code has to work around in them goes
in the R12 ledger in `docs/backtest_v1/requirements.md`.

Steps run in the order 11, 14.1, 12, 13, 14.2, 15, 16, 17, 18.

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
4*. Revised by step 11, which gives values rather than positions.

## Step 5 — `fast_f1/signal.py`: the tables

Done. See `log.md`, *Step 5*. Replaced by step 12.

## Step 6 — `linear/strategy_fastf1.py`

Done. See `log.md`, *Step 6*. Revised by step 13.

## Step 7 — Harness

Done: the strategy and its tuning variants are in `STRATEGIES` in `backtest/cli.py`. See
`log.md`, *Step 7*. Its variants give way to step 15's.

## Step 8 — Tuning on 2023–25 (real run)

Done, on the design with the table fault, so its choice of settings does not carry over. See
`log.md`, *Step 8*. Rerun as step 16, in new stores.

## Step 11 — `fast_f1/signal.py`: signal values

Done 2026-11-07. See `log.md`, *Step 11*. As requirements question 1 and 2.

- For a season and race, each driver's value: step 4's signal, stretched onto the race's
  recent championship points per race. That is `RollingPoints` divided by the races it covers,
  up to three. The race's best signal gets the field's highest per-race figure, the worst gets
  the lowest, and every other driver falls in proportion between.
- Each constructor's value is the sum of its two drivers' values, reached through the
  archive's per-race pairs.
- Step 4's rules stand:
  - 2023 sprint weekends take the sprint rule;
  - a fantasy driver with no metrics row gets no value, and step 13 scores them zero;
  - bad data raises an error;
  - no race result is read, and the look-ahead test stays.
- Three cases get a test each, as agreed with Alex on 2026-11-07 (`log.md`, *Step 11: three
  cases agreed*):
  - a race where every signal is equal raises an error;
  - a constructor with a driver who has no value counts that driver as zero;
  - race 1, which has no recent championship points to stretch onto, raises an error.
- Position code that nothing uses once steps 12 and 13 land is removed then. Done with step
  13.1, as Alex agreed.

## Step 12 — `fast_f1/signal.py`: the risk and price-rise measures

Done 2026-11-07. See `log.md`, *Step 12*. As requirements questions 3 and 4. Replaces step
5's tables.

- The chance of going negative by price third within the race, by asset type.
- The expected price rise by third on signal value per 1m within the race, by asset type. A
  rise is the asset's price at the next race less its price at this one. Moves with a price of
  0, which the archive gives some stand-in drivers, are left out.
- Both come from `TABLE_SEASONS` less the season itself, races 2 onwards, so no season sees its
  own results and 2026 enters neither. How ties split a third is settled in the tests.
- Step 5's negatives by recent history are removed, as `negative_chance` keeps its name and
  changes its basis to the price third. The expected-points tables stay until step 13.1, as
  `StrategyFastF1` reads them until then. Agreed with Alex 2026-11-07.
- Moves are taken only where both prices are present. No loaded archive row in 2023–26 is
  priced at 0, so the rule on moves priced at 0 needs no code of its own.
- Cached once per process, as a strategy is built per team per race.
- Tests: a season's own results cannot change its measures, and 2026 cannot change a 2023–25
  measure.

## Step 13 — `linear/strategy_fastf1.py`: the new objective

Revises step 6, one part per commit, each keyword parameter arriving with the part that uses it.

Step 6 already built `drs_coefficient`, `budget_reward` and `negative_penalty`, so Alex agreed
on 2026-11-07 that 13.1 keeps them and they move to values with it. Parts 2 to 4 are therefore
checks of the code against each item below, logged, with a change only where it differs.

1. Done 2026-11-07. See `log.md`, *Step 13.1*.
   The objective sums step 11's values in place of expected points. The base budget, team
   size and move constraints stay, and so does the test that race 4 keeps its normal move
   limit, as there is **no race-4 chip**. The expected-points tables are removed in the same
   change.
2. Done 2026-11-07, with no change needed. See `log.md`, *Step 13.2*.
   DRS as now: the helper's term on the values, scaled by `drs_coefficient` and left out at
   zero. The nominee is the selected driver with the best value, or the default when none has
   one.
3. Done 2026-11-07, with no code change and one test added. See `log.md`, *Step 13.3*.
   Minus `negative_penalty * chance`, from step 12, with a test that zero leaves the team
   unchanged.
4. Done 2026-11-07, with no change needed. See `log.md`, *Step 13.4*.
   `budget_reward * TotalCost`, with the same test at zero.
5. Done 2026-11-07. See `log.md`, *Step 13.5*.
   Plus `price_rise_reward * expected rise`, from step 12, with the same test at zero.
6. A race with no signal scores every asset zero, and solves.

The DRS driver's chance and expected rise are not doubled. There is no fixture file: unit tests
stub the loader with set values, and one test builds the strategy on the real files for 2025
race 5.

## Step 14 — The amounts checks (real data)

Pass marks fixed on 2026-11-07, before any result. **If either check fails, stop and raise it
with Alex,** rather than tuning around it.

1. Done 2026-11-07, and passed in every season. See `log.md`, *Step 14.1*.
   **Size check, once step 11 is done and before step 12 removes the old table.** In each race,
   the linear correlation between each asset's value and its actual fantasy points, for step
   11's values and for the old table's expected points, by season on 2023–25. **Pass:** step
   11's values do at least as well as the table in every season. Also report actual fantasy
   points by fifths of value, to show whether the top fifth's lead is real.
2. **VER check, once step 13 is done.** Re-simulate 2023 race by race, for the 15 teams of
   *Stepping back* (5 a band, seed 2), with the rebuilt strategy at its defaults. **Pass:** it
   holds VER in more than half of team-races from race 10 onwards, where the old design held
   him in 28% of all team-races and P2PM in 96%.

## Step 15 — Tuning values and harness

1. Measure the values' scale on 2023–25: what a negative typically costs in the values' units,
   and what 1m of price and an expected rise are worth in them. From that, set three values
   each for the penalty, the budget reward and the price-rise reward. **Log them before any
   run,** so that they cannot be adjusted after seeing results.
2. Register 11 labels in `STRATEGIES` in `backtest/cli.py`, each built by `make_variant` with
   one change from the base:

| Labels | Change from the base |
| --- | --- |
| `StrategyFastF1` | None: DRS coefficient 1, no penalty, no rewards |
| One label | DRS coefficient 0 |
| Three labels | Negative penalty at each of its three values |
| Three labels | Budget reward at each of its three values |
| Three labels | Price-rise reward at each of its three values |

Step 7's labels give way to these. Label names follow from the values chosen.

## Step 16 — Tuning on 2023–25 (real run)

Run the labels at 100 teams a band, seed 2, in new stores of their own, one per season, not
`outputs/fastf1_v2_tuning_*`. Seed 1 at 100 teams a band draws the first 100 of step 17's 500,
which is why tuning uses seed 2. 2026 is not run or looked at. Time a small run first, and run
in the background.

A penalty or reward is kept only if it clears the harness's bar against the base: a positive
pooled mean delta in each of 2023–25. Otherwise it stays at zero. If more than one lever clears,
the best clearing value of each runs combined, and must clear the same bar. Log every variant
tried, including the failures, and final budgets for each.

Then check the chosen setting by format. Re-simulate it race by race, for 15 teams a season (5
a band, seed 2), and report whether its gains or losses against the base fall mainly on sprint
weekends. A sprint-specific variant is added only if they clearly do, and it must clear the
same bar.

## Step 17 — The back-test (real run)

Waits for step 16.

**Run once, with the choice from step 16 logged before it starts.** All at 500 teams a band,
seed 1, in `outputs/fastf1_v2_results.parquet` and `outputs/fastf1_v2_summary.csv`, for 2023–26
with 2026 through race 18:

- the chosen strategy, whose result against `StrategyMaxP2PM` is the verdict;
- the same strategy with DRS coefficient 0, as the comparison;
- `StrategyMaxP2PMNoReset`, to isolate the chip's effect.

Report final budgets for each one.

## Step 18 — Findings and close-out

- Findings in `log.md`, in plain language first: the verdict, 2026 as the fair read, 2023–25 as
  flattered, how much of any gap the chip explains, the number of variants tried, and what has not
  been run.
- A row and key findings in `BACKTEST_LOG.md`.
- `CLAUDE.md` and `README.md` updated for the new strategy and `fast_f1/signal.py`.
- A `BACKLOG.md` item to rerun 2026 when the season finishes, as question 7 agreed. Update the
  efforts table.
