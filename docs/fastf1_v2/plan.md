# fastf1_v2 — Plan

**Status**: steps 1 to 8 are done. Step 8 found every FastF1 label trailing P2PM in 2023–25, and
stepping back found that the expected-points table loses how far ahead an asset is (`log.md`,
*Stepping back*). The signal redesign was agreed with Alex on 2026-11-07 (`log.md`, *Signal
redesign agreed*), and steps 11 to 16 build and tune it. Steps 11 to 16 and 19 to 23 are done.
Step 24 is next, then step 17, with `FastF1_RuleRise2p5` as the chosen strategy, on 2025–26
only (`log.md`, *Step 17 narrowed to 2025–26*). Steps 17 and 18 were numbered 9 and 10 before
2026-11-07.

**Step 17 was held on 2026-11-07 until the game's price rules were assessed. That is now
settled.** The game moved to a three-race price model in 2025. It is unchanged in 2026, and
assumed unchanged in 2027 (`log.md`, *The game's price-change rules* and the entries after it).
Step 16's price-rise reward ran on tables that mixed the old and new models. Steps 19 to 22
rebuild it from the rules and test it on 2025, before step 17. Alex accepted on 2026-11-07 that
this lever can be back-tested on 2025 only.
Requirements: `requirements.md`.

One commit per concern, for review per commit. Each behavioural change is seen failing before it
passes, and the full suite is green at the end of every step. No existing file in `linear/`,
`races/`, `import_data/` or `scripts/` is edited. Anything the code has to work around in them goes
in the R12 ledger in `docs/backtest_v1/requirements.md`.

Steps run in the order 11, 14.1, 12, 13, 14.2, 15, 16, 19, 20, 21, 22, 23, 24, 17, 18.

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
6. Done 2026-11-07, with no code change and the test extended. See `log.md`, *Step 13.6*.
   A race with no signal scores every asset zero, and solves.

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
2. Done 2026-11-07, and passed at 93%. See `log.md`, *Step 14.2*.
   **VER check, once step 13 is done.** Re-simulate 2023 race by race, for the 15 teams of
   *Stepping back* (5 a band, seed 2), with the rebuilt strategy at its defaults. **Pass:** it
   holds VER in more than half of team-races from race 10 onwards, where the old design held
   him in 28% of all team-races and P2PM in 96%.

## Step 15 — Tuning values and harness

1. Done 2026-11-07: penalty 6.5, 13 and 26, budget reward 0.1, 0.25 and 0.5, price-rise
   reward 5, 10 and 20. See `log.md`, *Step 15.1*. A `BACKLOG.md` item has Alex re-assess
   them when 2026 finishes.
   Measure the values' scale on 2023–25: what a negative typically costs in the values' units,
   and what 1m of price and an expected rise are worth in them. From that, set three values
   each for the penalty, the budget reward and the price-rise reward. **Log them before any
   run,** so that they cannot be adjusted after seeing results.
2. Done 2026-11-07. See `log.md`, *Step 15.2*.
   Register 11 labels in `STRATEGIES` in `backtest/cli.py`, each built by `make_variant` with
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

Done 2026-11-07: no lever cleared the bar, so step 17 runs `StrategyFastF1` at its defaults,
with `FastF1_Drs0` as the comparison. The format check, run against P2PM as Alex chose, found
no sprint effect. See `log.md`, *Step 16*.

Run the labels at 100 teams a band, seed 2, in new stores of their own, one per season, not
`outputs/fastf1_v2_tuning_*`. Seed 1 at 100 teams a band draws the first 100 of step 17's 500,
which is why tuning uses seed 2. 2026 is not run or looked at. Time a small run first, and run
in the background.

**A check that no old row is reused, added at Alex's request on 2026-11-07.** This step draws
the same teams as step 8, so step 8's `outputs/fastf1_v2_tuning_*` stores would supply every
team under `StrategyFastF1`, `FastF1_Drs0`, `FastF1_Bud025` and `FastF1_Bud05` from the old
design, silently (`log.md`, *Step 15.2*).

- **Before the run:** each season's `--output` and `--summary` name new files, not
  `fastf1_v2_tuning_*`, and none of those files exists yet. If one does, stop and raise it
  with Alex. The timing run goes to the scratchpad, so it cannot seed a store either.
- **After the run:** each season's "skipped" line in the log reads 0, and each store holds 300
  rows per label for its season. If either fails, the results are not used.

A penalty or reward is kept only if it clears the harness's bar against the base: a positive
pooled mean delta in each of 2023–25. Otherwise it stays at zero. If more than one lever clears,
the best clearing value of each runs combined, and must clear the same bar. Log every variant
tried, including the failures, and final budgets for each.

Then check the chosen setting by format. Re-simulate it race by race, for 15 teams a season (5
a band, seed 2), and report whether its gains or losses against the base fall mainly on sprint
weekends. A sprint-specific variant is added only if they clearly do, and it must clear the
same bar.

## Steps 19 to 22 — A price rise from the game's rules

Agreed with Alex on 2026-11-07 (`log.md`, *A rules-based price rise: what it can and cannot
show*). Under the game's three-race model, the next price move is largely known when a team is
picked, and step 12's table by value third was a weak stand-in for it. These steps replace that
table with the rules.

**The rules as this code applies them,** from the community's version and the four details the
archive check added (`log.md`, *The 2025 model against the archive*):

- The move after race *r* follows the asset's rating: the mean of its points per 1m in races
  *r*−2, *r*−1 and *r*, each race's points over that race's own price. Early in the season only
  the races held so far count, with no zero-padding.
- The step is +0.3, +0.1, −0.1 or −0.3 at or above the split and +0.6, +0.2, −0.2 or −0.6 below
  it, for a rating above 1.2, from 0.9 to 1.2, from 0.6 to 0.9 and below 0.6.
- The split is 18.5m in 2025 and 2026, and an asset priced exactly at it takes the upper steps.
- The new price stops at a floor, 4.5m in 2025 and 3.0m in 2026, and in 2026 at a cap of 34.0m.
  Seasons after 2026 take 2026's figures.
- 2023–24 had a different model, so they get no rise and the lever is off there.

Only the next move counts, as now. Races *r*−2 and *r*−1 use the archive's actual points, which
are known when the team for race *r* is picked. Race *r* is estimated, never read.

### Step 19 — Accuracy check on 2025 (real data)

Done 2026-11-07: estimate (a) chosen, and it passed. Race *r*'s points come from a line fitted by
type, not a single slope, as Alex chose. See `log.md`, *Step 19: the accuracy check on 2025*.

A throwaway script, before any code is written. Pass marks fixed here, before any result.

- **Two estimates of race *r*:**
  - (a) the asset's signal value converted to fantasy points, by the slope of fantasy points on
    value measured on 2023–24 only, and logged before the comparison;
  - (b) race *r* left out, so the rating is the mean of the races before it in the window.
- **Measured on 2025, races 2 onwards,** for assets with a value and a price at both races,
  drivers and constructors separately. Each estimate's expected move is compared with the
  actual one, by mean absolute error. Report also the share of exact matches and the rank
  correlation.
- **The choice:** (a) only if its mean absolute error, drivers and constructors pooled, is at
  least 5% lower than (b)'s. Otherwise (b), as the simpler.
- **Pass:** the chosen estimate's mean absolute error is lower than step 16's 2025 table's, for
  drivers and for constructors. That table is the one built from 2023–24.
- **If it fails, stop and raise it with Alex.**

### Step 20 — `fast_f1/signal.py`: the rules-based rise

Done 2026-11-07, and it reproduces step 19's figures. See `log.md`, *Step 20: the rules-based
rise, in the code*.

Test-first, one concern per commit.

- `price_rise(season, race)` keeps its contract: each asset's expected move in 1m, for every
  asset priced in the race that has a value, and empty when the race has no signal. So
  `StrategyFastF1` and `linear/` do not change.
- It applies the rules above with step 19's chosen estimate. A driver is followed by their code
  across a constructor switch, as the archive check did. A race in the window with no row for
  the asset counts as zero points. That case was left out of the archive check, so it is a
  working assumption.
- 2023–24 give an empty result. The rule figures for each season live in one constant.
- Step 12's rise tables and their tests are removed. The negative chances are untouched.
- Tests, among others: race *r*'s actual points cannot change the result; each band, tier,
  the split itself, the floor and the cap; races 2 and 3 with fewer races held; 2023–24 empty.
- **Real-data check:** the built code reproduces step 19's 2025 figures for the chosen
  estimate.

### Step 21 — The labels

Done 2026-11-07. See `log.md`, *Step 21: the labels*.

Replace `FastF1_Rise5`, `FastF1_Rise10` and `FastF1_Rise20` in `STRATEGIES` with
`FastF1_RuleRise5`, `FastF1_RuleRise10` and `FastF1_RuleRise20`, at the same values. The old
names hold rows in step 16's stores from the old tables, which a resumed run would reuse
silently. The values stay at 5, 10 and 20, as they come from what 1m of budget is worth (step
15.1), not from the table.

### Step 22 — The price-rise reward on 2025 (real run)

Done 2026-11-07: `FastF1_RuleRise5` was chosen, +123.4 points a team against the base, and
step 23 then replaced it with reward 2.5. See `log.md`, *Step 22: the price-rise reward on 2025*.

Run `StrategyFastF1` and the three new labels on 2025 only, at 100 teams a band, seed 2, in a
new store, `outputs/fastf1_v2_step22_2025.parquet`, with its own summary. Time a small run first
into the scratchpad, and run in the background.

- **The check that no old row is reused,** as step 16's: before the run, neither file exists;
  after it, the log's "skipped" line reads 0 and the store holds 300 rows per label.
- **The bar:** a positive pooled mean delta against `StrategyFastF1` in 2025. 2023–24 are not
  run, as the lever is off there. If more than one value clears, the best one is chosen.
  Otherwise the base stays as step 16 chose it.
- Report final budgets for every label, and the gap to P2PM's.
- Log the choice before step 17 starts.

### Step 23 — Lower rewards on fresh teams (real run)

Done 2026-11-07: `FastF1_RuleRise2p5` replaces `FastF1_RuleRise5`, +186.0 points a team against
the base and +30.9 against P2PM. See `log.md`, *Step 23: lower rewards on fresh teams*.

Agreed with Alex on 2026-11-07, after step 22 (`log.md`, *Step 23 agreed*). Reward 5 was the
lowest value tried and did best, so lower values may do better. They are tested on teams step
22 did not look at, so that the choice is not made on the teams that suggested it.

1. Test-first, add `FastF1_RuleRise2p5` and `FastF1_RuleRise1p25` to `STRATEGIES`, at
   price-rise rewards 2.5 and 1.25, continuing the halving from 5.
2. Run `StrategyFastF1`, `FastF1_RuleRise5`, `FastF1_RuleRise2p5` and `FastF1_RuleRise1p25` on
   2025 only, at 100 teams a band, **seed 3**, in a new store,
   `outputs/fastf1_v2_step23_2025.parquet`, with its own summary. Seed 1 is step 17's and seed 2
   is step 22's. Time a small run first into the scratchpad, and run in the background.

- **The check that no old row is reused,** as step 22's: before the run, neither file exists;
  after it, the log's "skipped" line reads 0 and the store holds 300 rows per label.
- **Report how many seed 3 teams step 22 also drew,** as the bands are finite and seeds can
  overlap.
- **The rule, fixed before the run:** a lower reward replaces 5 only if, on seed 3, its pooled
  mean delta against `StrategyFastF1` is positive and higher than `FastF1_RuleRise5`'s. If both
  qualify, the higher one is chosen. Otherwise `FastF1_RuleRise5` stands.
- Report, for every label, the pooled mean and median deltas against the base and against
  P2PM, the share of teams beating each, and final budgets.
- Log the choice before step 17 starts.

## Step 24 — `backtest/`: stop a season at a given race

Agreed with Alex on 2026-11-08 (`log.md`, *Step 17 narrowed to 2025–26*). The archive prices
2026 through race 20, but the signal ends at race 18, and the engine runs every priced race. So
FastF1 would pick races 19 and 20 on an all-zero signal while P2PM picks on real data.

Test-first, one concern per commit:

1. `simulate_sample` and `run_backtest` take an optional `last_race`, and simulate each season
   only up to it. A race the season does not price, or one before the starting race, raises
   `ValueError` before any work. Tests: the stored row is the direct run's row at that race;
   the bad values raise; `run_backtest` passes it on.
2. `backtest.cli` takes `--last-race`, default none, and passes it to `run_backtest`. Its help
   says to use a store of its own, as stored rows are keyed without the last race, so a run to
   a different race would reuse them.

`races/`, `linear/`, `import_data/` and `scripts/` are unchanged.

## Step 17 — The back-test (real run)

The choice from steps 22 and 23 is logged before this starts: `FastF1_RuleRise2p5`.

**Narrowed to 2025–26 by Alex on 2026-11-08** (`log.md`, *Step 17 narrowed to 2025–26*). In
2023–24 the reward is off, so the strategy there is the base, which step 16 measured against
P2PM. Those results are cited in step 18, labelled as the base at 300 teams a season on seed 2,
not rerun.

**Run once.** At 500 teams a band, seed 1, into one store,
`outputs/fastf1_v2_results.parquet`, as two commands so that only 2026 stops early:

- 2025, all 24 races, summary `outputs/fastf1_v2_summary_2025.csv`;
- 2026 with `--last-race 18`, summary `outputs/fastf1_v2_summary_2026.csv`.

Each runs:

- `FastF1_RuleRise2p5`, whose result against `StrategyMaxP2PM` is the verdict, season by season;
- `StrategyMaxP2PMNoReset`, to isolate the chip's effect.

The DRS coefficient 0 comparison was dropped by Alex on 2026-11-07: step 16 already showed it
losing to the base in all three seasons (`log.md`, *Step 23 agreed*). Alex's live 2026 team is
not added: he will run it himself later.

Report final budgets for each one.

**A check that no old row is reused, added at Alex's request on 2026-11-07.** The harness
skips any team already in its store, keyed on label, season and team only. Step 8's
`outputs/fastf1_v2_tuning_*` stores hold old-design rows under `StrategyFastF1`, `FastF1_Drs0`,
`FastF1_Bud025` and `FastF1_Bud05`, and would be reused silently (`log.md`, *Step 15.2*).

- **Before the run:** `--output` and `--summary` name the files above, none of them exists
  before the 2025 command, and the store holds only 2025's rows before the 2026 command. If
  not, stop and raise it with Alex.
- **After the run:** each command's "skipped" line in the log reads 0, and the store holds
  1,500 rows per label per season. Every 2025 row's `race` is 24 and every 2026 row's is 18. If
  any of these fails, the results are not reported.

## Step 18 — Findings and close-out

- Findings in `log.md`, in plain language first: the verdict, 2026 as the fair read, 2025 as
  flattered, 2023–24 from step 16 labelled as the base, how much of any gap the chip explains,
  the number of variants tried, and what has not been run.
- A row and key findings in `BACKTEST_LOG.md`.
- `CLAUDE.md` and `README.md` updated for the new strategy and `fast_f1/signal.py`.
- A `BACKLOG.md` item to rerun 2026 when the season finishes, as question 7 agreed. Update the
  efforts table.
