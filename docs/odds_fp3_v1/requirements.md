# odds_fp3_v1 — Requirements

**Status**: agreed 2026-11-24, from Alex's answers in conversation.
Plan in `plan.md`; execution log in `log.md`.

Build a strategy that picks a season's opening team from betting odds and FP3 alone,
and back-test the mix of the two on 2026's normal weekends.

## Sources consolidated

- User decisions, 2026-11-24, taken in conversation. They are recorded under the
  requirements they settle.
- `docs/indicator_analysis_v1/log.md`, which checked Alex's assumption that FP3 is the
  best FastF1 indicator. See *The FP3 assumption* below.

## The FP3 assumption

Alex's starting assumption was that FP3 is the best indicator from the FastF1 API.
`indicator_analysis_v1` mostly supports it. Spearman runs from 1 (the signal orders
drivers exactly as they scored) to 0 (no relationship), scored against fantasy points.

- **Normal weekends, race 2 onwards:** FP3 beat FP2 in every season, 0.46–0.53 against
  0.41–0.45 in 2023–25 and 0.655 against 0.619 in 2026. It was the only practice session
  in the chosen combination. Lap count and stint length were weak, at about 0.25.
- **Race 1:** FP3 averaged 0.595 over four seasons against FP2's 0.483. But in 2026's
  race 1, the only one with odds, FP2 (0.854) beat FP3 (0.760), and odds beat both
  (0.872). So FP3 is the better session on average, not in every race.
- **Odds with FP3 has never been scored together.** The nearest result: within 2026,
  odds added nothing measurable to the best combination without odds (−0.004, −0.018 to
  +0.008).

## R1 — Purpose

A strategy for picking the season's race-1 team from scratch. It must not use fantasy
points, rolling points or any race history, as none exists at race 1. Prices enter only
as the budget constraint every team is picked under.

## R2 — Inputs: existing indicators only

Both come from `data/fastf1_practice_rolling_metrics.csv`, as `fast_f1` already builds
them. No new indicator and no new normalisation.

- **`OddsRank`**: race-winner odds on a log scale, 0–1. Chosen over
  `OddsImpliedProbability`, which puts the same drivers in the same order but bunches all
  but the top two or three near zero. On that scale a 50/50 mix would be mostly FP3.
  R9's odds control tests that choice.
- **`FP3_MinLapTime_rank`**: FP3 fastest lap, 0–1.
- **Missing input scores 0**, as the existing indicators already treat it.
- **Odds are the `Odds` column as captured.** Live, that is whatever odds are latest when
  the strategy is run. The snapshot columns are not read.

## R3 — Value

- Each driver's value = `w × OddsRank + (1 − w) × FP3_MinLapTime_rank`, where `w` is the
  odds share. **The default is `w = 0.5`**, an even split, to keep it simple and avoid
  over-fitting. Only R10 can move it.
- A constructor's value is the sum of its drivers' values, the rule
  `fast_f1/signal.py` and `import_data/odds.py` already use.

## R4 — The linear program

- Maximise the team's total value under the budget cap the caller gives, picking from
  an empty team.
- The DRS driver is chosen inside the LP through `StrategyBase`'s existing helper
  (`get_drs_objective_term` / `get_drs_nominee`), as `StrategyBettingOdds` and
  `StrategyFastF1` do.
- No concentration cap. `max_points_v1` measured no concentration risk, and a cap would
  be a second setting to tune on the same few races.

## R5 — Normal weekends only

The strategy raises a clear error on a sprint weekend, which has no FP3, and on a race
with no rows in the metrics file. It was only tested on normal weekends. Handling a
sprint at race 1 is a backlog item, not this effort.

## R6 — Where the code lives

One new file in `linear/`, subclassing `StrategyBase`. Alex agreed to this 2026-11-24.
No edit to `StrategyBase` or to any existing strategy. The class's shape (constructor
arguments, how the weight is set) is agreed with Alex in conversation before any code
is written.

Using the strategy live at 2027 race 1, through `live.cli` or otherwise, is a separate
later effort (see `BACKLOG.md`).

## R7 — Back-test shape

- **Races:** every 2026 normal weekend that has odds and FP3 in the metrics file when
  the back-test runs. Today that is 15: races 1, 3, 6, 7, 8, 10, 11, 13, 14, 15, 16, 18,
  19, 20 and 21.
- **Each weekend is treated as race 1.** A team is picked from scratch and scored on
  that race's fantasy points from the archive, with DRS doubling the nominee.
- **One race only.** No season is simulated and nothing is compared with P2PM.

## R8 — Budget cap

Cap = 100m × (total price of every driver and constructor at the tested race ÷ the same
total at 2026 race 1). Race 1 gets exactly 100m, and if the whole grid is 10% dearer at
a later race, the cap there is 110m.

## R9 — What is run at each race

- **The five mixes:** `w` = 0, 0.25, 0.5, 0.75 and 1. `w = 0` is FP3 alone and `w = 1`
  is odds alone.
- **Three controls**, to show whether the signal beats something simple:
  - *Price only*: `StrategyMaxBudget` from an empty team under the cap, with DRS on the
    dearest driver.
  - *Random teams*: 1,000 random valid teams (5 drivers, 2 constructors) under the cap,
    with a fixed seed and DRS on each team's dearest driver. The control scores their
    mean points.
  - *Odds on implied probability*: the existing `StrategyBettingOdds`, with no cap and
    DRS inside the LP. Close to what Alex played at 2026 race 1, and the test of R2's
    choice of odds scale.

## R10 — The bar for moving off 50/50, fixed 2026-11-24 before any results

For each other mix against 50/50:

1. At each race, take the mix team's points minus the 50/50 team's points.
2. Average those differences.
3. Find the 95% interval on that average: build 10,000 pretend seasons by drawing the
   races at random with replacement, so one race can appear twice and another not at
   all, and average each one. The interval is the middle 95% of those averages
   (`fast_f1.indicator_analysis.bootstrap_interval`, fixed seed).
4. **The default moves to that mix only if the whole interval is above zero.**
   Otherwise the result is "no measurable difference" and 50/50 stays.

If more than one mix passes, the one with the highest average gain is chosen.

The controls go through the same check against 50/50 and are reported, but they never
change the default.

With 15 races, the likeliest result is that no mix passes. The size of every gain is
reported whether or not it passes.

## R11 — Which run decides

- **The run made now decides the default.**
- **A rerun after the 2026 season ends** covers every 2026 normal weekend by then, up to
  17. It is a check. If it gives a different answer under R10, both results are set out
  plainly and Alex decides before 2027 race 1.

## R12 — Records

- Results go to `outputs/` (not tracked) and findings to `log.md`.
- A `BACKTEST_LOG.md` entry, clearly marked as a single-race, from-scratch test rather
  than a season-long comparison with P2PM.

## R13 — Constraints

- `races/`, `import_data/` and `scripts/`, `StrategyBase` and the existing strategies
  are not edited. Anything they force this effort to duplicate or work around goes in
  `log.md`.
- No new dependencies.

## Rejected options

All rejected 2026-11-24 in conversation; see `log.md`, *Scoping*.

- Simulating the rest of the season from each pick: P2PM's 20 races of noise would
  swamp the opening pick.
- Scoring real race 1s only: only 2026 has odds, so that is one race.
- A flat 100m cap at every race: the grid's prices drift, so a later race would buy a
  different share of the field.
- Implied probability as the strategy's odds input, and running both scales at every
  mix: kept as one control (R9) instead.
- A finer weight grid (steps of 0.1): more comparisons on 15 races makes a lucky
  winner likelier.
- Choosing the mix by best mean alone, or after seeing results: replaced by R10's fixed
  bar.
- A concentration cap, fixed or tested.
- DRS on the dearest driver for the strategy itself.
- Falling back to odds alone on a sprint race 1.

## Out of scope

- Live use at 2027 race 1 (a backlog item).
- Sprint weekends.
- Fitted weights, or any input beyond odds and FP3.
- Any change to what `fast_f1` builds into the metrics file.
