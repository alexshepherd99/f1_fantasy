# fastf1_v2 — Requirements

**Status**: agreed 2026-11-01, with all eight questions answered and the working assumptions
confirmed. Plan steps 1 to 8 are built and run. Question 1 was reopened on 2026-11-06, as the
table its answer chose loses how far ahead an asset is, and answered again on 2026-11-07 by the
signal redesign, which also changes questions 2 to 4. See `log.md`, *Signal redesign agreed*.
Questions 4 and 7 changed again on 2026-11-07, for the price-rise reward only, once the game's
price rules were known. See `log.md`, *A rules-based price rise: what it can and cannot show*.

## Picking this up

1. Read this file and `log.md`. Read the `log.md` correction before quoting any field-wide
   driver figure from its first entry.
2. Carry on from `plan.md`, at step 11.

Build a team-selection strategy on the FastF1 indicators and back-test it against
`StrategyMaxP2PM`. Whether the indicators pick better teams than P2PM is the open
question `fast_f1` was built to answer.

## Sources consolidated

- User brief, 2026-11-01. Two things to bear in mind when designing the strategy:
  - Drivers and constructors that score negative points can cause more damage than
    the right selection.
  - Unspent budget means unspent opportunity. Assess whether fully spending as much
    budget as possible should be factored into the choice.
- `BACKLOG.md`, *Build a strategy on the FastF1 indicators*, moved here in full below.
- `docs/indicator_analysis_v1/log.md`, *Conclusions*: the signal to start from.
- `docs/max_points_v1/`: the DRS helper, the DRS ceiling, and the budget and negative
  levers proposed but never tuned (`proposal.md`, *Failure modes*).
- `docs/odds_drs_v1/log.md`: the closest precedent, a forward-looking signal that lost.
- `docs/backtest_v1/`: the harness and the verdict form.

## What the original entry says that has since changed

The entry below is kept as it stood in `BACKLOG.md` when it moved, including its dated notes from
there. These points in it no longer hold:

- **"The back-test data does not exist yet."** It does: the metrics file now holds
  every race of 2023–25 and 2026 races 1–18.
- **"Maximises `AggregateRank`."** `indicator_analysis_v1` found that the current
  aggregate is not clearly better than rolling points, and that a different signal is:
  driver + constructor + FP3 on normal weekends, driver + constructor on sprint
  weekends. Practice is left out on sprint weekends.
- **"`AggregateRank` needs FP2+FP3 (or FP1+Sprint Qualifying) to have run."** The new
  signal needs FP3 on a normal weekend and no session at all on a sprint weekend.
- **"It is a clean 1:1 mapping" of constructor names.** Four 2024 teams change name at race 24,
  and no name mapping is needed. See `log.md`, *Reaching fantasy assets*.
- **"Bias the objective towards getting P1 right."** The DRS helper now exists on
  `StrategyBase`, with `StrategyBettingOdds` as its one caller.
- **"Bring `AggregateRank` into line with those conclusions."** That work is back in
  `BACKLOG.md` as its own item. See question 6.
- **"A `data/test_fastf1_metrics.xlsx` fixture will be needed."** It was not built, as the
  tables need real 2023–25 rows, so the tests stub `load_signal_tables` instead. See `log.md`,
  *Step 6*.

## Open questions, in the order they will be asked

### 1. What does the objective score in? (agreed 2026-11-07: the signal on a championship points scale)

**Each driver's signal value, stretched onto that race's recent championship points per race.**
The race's best signal gets the highest per-race recent championship points in the field, the
worst gets the lowest, and every other driver falls in proportion between. Per race is the
three-race total divided by the races it covers, so the scale holds steady from race 2 rather
than growing over the first three races. The signal is still step 4's, with its inputs added
at equal weight. Nothing is built from other seasons.

This keeps the size of a lead, which the old table lost: in 2023 race 10 VER is 21 points
ahead of the second-ranked LEC, where the table gave them the same 29.0. It also puts drivers
and constructors in one unit. Within a race any straight-line conversion picks the same
drivers, as the LP takes exactly five drivers and two constructors, so the conversion matters
for the mix of drivers and constructors and for the penalty and rewards, which need a unit.

Not chosen:

- **Summing the 0–1 signal with no unit** (2026-11-01): constructors and the extra terms would
  have no unit in common with drivers.
- **Expected fantasy points by signal position** (agreed 2026-11-01, reversed 2026-11-06): it
  loses the size of a lead, and tied positions 1 and 2 in 2023, so the LP never bought VER.
  See `log.md`, *Stepping back*.
- **Championship points by signal position, 25-18-15 and so on** (2026-11-07): top-heavy, but
  it still loses the size of a lead.
- **A fitted weight for each input** (2026-11-07): three seasons are too little data to fit
  them, and Alex prefers equal weights.
- **Each asset's own recent fantasy points, adjusted by the signal** (option 3, 2026-11-07): it
  brings back fantasy rolling points, which the signal does not use, and lets a run of
  retirements outweigh the signal. See `log.md`, *Redesign evidence*.

### 2. How is a constructor scored? (agreed 2026-11-07: the sum of its drivers)

**The sum of its two drivers' values,** reached through the archive's per-race pairs. This is
how championship points work for a team, and the core of how the game scores a constructor,
which adds extras of its own for qualifying progression and pit stops (`log.md`, *Redesign
evidence*). Each driver's signal already holds the team's rolling points, so the team's form
counts inside each driver's value.

Not chosen:

- **Its own rolling place, converted to expected points** (agreed 2026-11-01, reversed
  2026-11-07): the expected-points table is gone.
- **A real constructor indicator** (2026-11-01): there is no constructor practice or odds rank
  to start from.

### 3. How are negative scores handled? (agreed 2026-11-07: a penalty by price third)

This is the first point in Alex's brief. Championship points stop at zero, so the objective
sees no negative risk unless this term adds it.

**A soft penalty on each asset's chance of going negative, by its price third within the
race,** for drivers and constructors, with a coefficient tuned from zero. The chances come from
the other 2023–25 seasons, races 2 onwards. In 2023–25 the cheapest third of drivers went
negative 20.9% of the time and the dearest 10.2%; for constructors, 19.9% and 2.6%. Price was
the only measure tried that beat a flat rate in every season, and it did so for both. Alex
expects the driver part to count for less when tuned. See `log.md`, *Redesign evidence*.

Not chosen:

- **No separate term, relying on expected points** (agreed 2026-11-01, reversed 2026-11-07):
  the expected-points table is gone.
- **A rule that excludes assets** (2026-11-01): a rule cannot be tested at zero.
- **A chance from recent history** (2026-11-07): any negative in the last three races, which
  step 5 built; the asset's own non-classifications; and its team's, over three races or the
  season so far. None beat a flat rate for drivers in 2023–25.
- **Leaving risk to the budget reward** (2026-11-07): it rewards spend whatever the risk, so it
  can buy an expensive asset that is likely to go negative.

### 4. How is unspent budget handled? (agreed 2026-11-07: a spend reward and a price-rise reward)

This is the second point in Alex's brief.

- **A small reward per 1m spent,** tuned from zero (agreed 2026-11-01). It does not stand in
  for the negative penalty.
- **A reward for expected price rises, worked out from the game's price rules** (agreed
  2026-11-07, replacing the table below), for drivers and constructors, tuned from zero. The
  game has set prices by a three-race model since 2025, so the next move is largely known
  when a team is picked: two of its three races are already scored, and the coming one is
  estimated. 2023–24 had a different model, so the reward is off there. See `plan.md`, *Steps
  19 to 22*.

  Until 2026-11-07: a reward by the asset's third on its signal value per 1m within the race,
  with each third's expected rise from the other 2023–25 seasons, races 2 onwards. Of the
  measures tried, value per 1m ordered rises most evenly across 2023–25 (`log.md`, *Redesign
  evidence*). Those tables mixed the two price models, so each season ran with the wrong one
  (`log.md`, *Step 16 read again, in the light of the price rules*).

Final budgets are reported for every variant. The old strategy ended 2–14m behind P2PM, and
paying top prices for top-ranked assets, which do not rise, was part of why. P2PM leaves
2.3–4.3m unspent on average, and spending alone has not helped: Max Budget spends the most and
loses by 21–36%.

Not chosen:

- **A hard rule on maximum spend** (2026-11-01).
- **Recent fantasy points per 1m, P2PM's measure, for price rises** (2026-11-07): it was
  strongest in 2025 but no better than chance for drivers in 2023, and it would blur what this
  strategy tests.

### 5. How is the DRS driver chosen, and is it inside the objective? (agreed 2026-11-01: A, with B as the comparison)

- **A. Inside the objective,** through the existing `get_drs_objective_term` and
  `get_drs_nominee` helper on `StrategyBase`, as `StrategyBettingOdds` does.
- **B. Chosen after the team is picked,** as the selected driver with the best signal.
- **C. The default,** the highest-priced driver.

Evidence: the best possible DRS pick would add 226, 103 and 98 points a season, a hindsight
ceiling. The helper rewards teams with one strong driver, but nominates by whatever values
it is given, so it does not by itself improve the pick. The original entry asks for a
coefficient that can be tested at zero.

Passing the helper the signal values from question 1 makes the term the nominee's value
again, as DRS doubles a driver's points, which gives a coefficient of 1 a meaning. The DRS
driver's chance of going negative and expected price rise are not doubled: the penalty would
barely move, as the nominee is almost always in the dearest third, and DRS does not double a
price change. A and B nominate by the same rule, the
selected driver with the best value, so they differ only in whether DRS affects the team
picked. B is A with the coefficient at zero, as long as its nominee comes from a
`get_drs_driver()` override, since the helper's nominee is arbitrary with zero values
(reasoned from `linear/strategy_base.py:275-307`, not run).

Recommendation put to Alex: A at a coefficient of 1, with zero (B) as the comparison. Neither
needs `StrategyBase` changed.

**Agreed 2026-11-01: as recommended.**

### 6. Does `AggregateRank` get brought into line? (agreed 2026-11-01: B, later change on the backlog)

The entry below asks for this first. The conclusions need weights that differ by weekend
format and for race 1, which one flat `METRIC_WEIGHTS` dict cannot say.

- **A. Change `AggregateRank` first,** then build on it. Doing so moves the stored values in
  `data/fastf1_practice_rolling_metrics.xlsx`.
- **B. The strategy builds its signal from the component columns,** as
  `indicator_analysis_v1` did, and `AggregateRank` is left as it is.

The strategy uses its own signal's values, as question 1 says, and does not sum or maximise
`AggregateRank`. Only `fast_f1` uses the column:
`output.py` derives `RankPosition` from it and `cli.py` prints both, and tests in
`test_fastf1_metrics.py` and `test_fast_f1_output.py` pin today's flat weights (checked by
grep). So until it is changed, the ranking `fast_f1.cli` prints each race stays on the older
signal.

Recommendation put to Alex: B for the strategy, with the signal defined once in `fast_f1` so
that bringing `AggregateRank` into line later can reuse it, and that later step goes back to
`BACKLOG.md` as its own item rather than staying in this effort.

**Agreed 2026-11-01: as recommended.**

### 7. Which seasons, and what counts as a win? (agreed 2026-11-01: as recommended)

The signal was chosen on 2023–25, so a back-test there flatters it, and 2026 is the only
season it has not seen. The metrics file has 2026 races 1–18, race 19 is priced but
unscored, and the season has not finished. The harness verdict is a positive pooled mean
delta in every season, at 500 teams a band.

`indicator_analysis_v1` confirms 2026 played no part in choosing the signal (its *Findings*).
But 2026 could still leak in through anything built from other seasons, now the negative and
price-rise measures: "other seasons" for a 2023 run would include 2026, and tuning there would
then have seen it. 2026 also plays no part in design choices: Alex's view that an unreliable
team makes a −20 more likely comes partly from 2026, and was tested on 2023–25 only.

Recommendation put to Alex:

- Keep the harness verdict, the same bar as every strategy in `BACKTEST_LOG.md`: a positive
  pooled mean delta in every season, at 500 teams a band. Report 2026 on its own as the fair
  read and 2023–25 as flattered. A win in 2023–25 with a loss in 2026 is a loss, and a win in
  2026 with a loss in a flattered season is not a win either.
- Fix every coefficient from questions 3 and 4 on 2023–25, then run only the chosen variants on
  2026, once, and report how many variants were tried.
- While tuning, a season's measures come from the other 2023–25 seasons only, leaving 2026 out.
  The 2026 run's measures come from all of 2023–25.
- 2026 runs through race 18 with the harness's own `--output` and `--summary`, and is rerun
  when the season finishes. Race 19 is priced but has no signal, so the plan must say how that
  race is handled.

**Changed 2026-11-07, for the price-rise reward only:** it is tuned on 2025 alone, as the only
completed season under the current price model. Its bar is a positive pooled mean delta against
the base in 2025, and 2023–24 are not run for it. That is in-sample, so a gain there is weak
evidence, and Alex accepted the limited back-testing. The verdict against P2PM, in every
season with 2026 as the fair read, is unchanged.

### 8. Where does the code go? (agreed 2026-11-01)

A new file in `linear/` needs Alex's OK each time, and strategy classes get a design
conversation before any editing, above all `StrategyBase`. Anything the code has to work around
in a core module goes in the R12 ledger in `docs/backtest_v1/requirements.md`.

Recommendation put to Alex, with no edit to any existing file in `linear/`, `races/`,
`import_data/` or `scripts/`:

- **`fast_f1/signal.py`, new.** Builds the signal values from the component columns, and the
  negative and price-rise measures from the metrics file and the archive, cached once per
  process. `factory_strategy` builds a strategy per team per race, so reading the file on each
  build, as the odds strategy does, would be too slow. A season's measures use 2023–25 minus
  that season, which covers both the tuning and the 2026 run with one rule.
- **`linear/strategy_fastf1.py`, new.** `StrategyFastF1(StrategyBase)`, with keyword parameters
  `fn_metrics`, `drs_coefficient=1.0`, `negative_penalty=0.0`, `budget_reward=0.0` and, from
  the redesign, `price_rise_reward=0.0`. `make_variant` passes these through, so
  `factory_strategy` needs no change (checked). The objective is the signal values, plus the
  helper's DRS term unless its coefficient is zero, plus `budget_reward * TotalCost`, plus the
  price-rise reward, minus the penalty. `get_drs_driver()` always returns the selected
  driver with the best value, so zero and non-zero coefficients share one path. **Agreed
  2026-11-01: it does not implement the race-4 chip.**
- **A race with no signal scores every asset zero,** as the odds strategy does, and DRS falls to
  the default. 2026 race 19 has no points to score, so this does not move the result (reasoned).
- **No constructor name mapping, and no edit to `common`.** Assets are reached through the
  driver and the archive's per-race pairs (checked; see `log.md`).
- **`backtest/cli.py` gains the strategy in its `STRATEGIES` list.**

This makes `linear` import `fast_f1` for the first time. There is no cycle, as `fast_f1` imports
nothing from `linear`, `races` or `scripts` (checked). The cost is that `fast_f1/__init__.py`
loads the FastF1 library: 1.2s and 128MB a process, measured with pandas included.

**Agreed 2026-11-01: the shape above.** `StrategyMaxP2PMNoReset` also runs in all four seasons,
to isolate the chip's effect.

**Agreed 2026-11-01: the 2024 race 24 fault in `log.md` is fixed in the code as the first plan
step,** so that a refresh cannot bring it back, with the data edit's check plan agreed first.

## Decisions so far

- **Equal weights across the signal's inputs is the preference.** They may change only if there
  is a case for it, and then only with care about over-fitting limited data. Agreed 2026-11-07.
- **The objective scores the signal value, stretched onto the race's recent championship
  points per race.** Agreed 2026-11-07, see question 1.
- **A constructor scores the sum of its two drivers' values.** Agreed 2026-11-07.
- **Negatives get a soft penalty on each asset's chance by price third,** for drivers and
  constructors, tuned from zero. No exclusion rule. Agreed 2026-11-07.
- **No hard rule on maximum spend.** A reward per 1m spent and a reward for expected price
  rises by value-per-1m third are each tuned from zero, with final budgets reported for every
  variant. Agreed 2026-11-01 and 2026-11-07.
- **The price-rise reward is rebuilt from the game's price rules,** off in 2023–24, and tuned on
  2025 alone, at 5, 10 and 20. The game's rules are taken as unchanged for 2027. Agreed
  2026-11-07.
- **Tuning uses one setting across weekend formats first.** Values are set from a measurement
  of the signal's scale and logged before any run. The chosen setting is then checked race by
  race for whether its gains or losses fall on sprint weekends, and a sprint-specific variant
  is added only if they clearly do. Agreed 2026-11-07.
- **Two checks must pass before tuning,** with pass marks fixed before any result: the signal
  values' sizes match actual fantasy points at least as well as the old table's in every season
  of 2023–25, and the rebuilt strategy holds VER in more than half of 2023's team-races from
  race 10 onwards. If either fails, work stops and is raised with Alex. Agreed 2026-11-07.
- **DRS sits inside the objective at a coefficient of 1,** with zero as the comparison, and the
  nominee is the selected driver with the best value. Agreed 2026-11-01.
- **The strategy builds its signal from the component columns,** defined once in `fast_f1`, and
  `AggregateRank` stays as it is. Bringing it into line is its own item in `BACKLOG.md`. Agreed
  2026-11-01.
- **The verdict is the harness's: a positive pooled mean delta in every one of four seasons,**
  with 2026 reported as the fair read. Coefficients are fixed on 2023–25, with measures that
  leave 2026 out, before the chosen variants run once on 2026. 2026 is rerun when the season finishes.
  Agreed 2026-11-01.
- **The strategy does not implement the race-4 chip.** `StrategyMaxP2PM` still plays it, so the
  comparison also measures the chip. `StrategyMaxP2PMNoReset` runs in all four seasons to isolate
  that effect, and the verdict stays against `StrategyMaxP2PM`. Agreed 2026-11-01.
- **Code shape as in question 8:** new `fast_f1/signal.py` and `linear/strategy_fastf1.py`, no
  constructor name mapping, and `linear` imports `fast_f1`. Agreed 2026-11-01.

Alex asked for the "rolling indicators use championship points" claim to be checked before
question 1. It is true, and swapping in fantasy rolling points gave no measurable gain (see
`log.md`). Alex ruled on 2026-11-01, with the working assumptions below, that the signal stays
on championship rolling points.

## Working assumptions, confirmed by Alex 2026-11-01

- Race 1 needs nothing built. A back-test's race 1 team is the sampled one, and live
  picks already have `scripts/select_odds_start.py`.
- Odds stay out of the signal after race 1. Within 2026 they add nothing measurable, and
  they cover one season.
- `StrategyMaxP2PM` is not edited until the 2026 season ends.
- The signal's rolling indicators stay on championship points.

Withdrawn: copying P2PM's race-4 chip, so that the comparison would not also measure it. Alex
withdrew it on 2026-11-01 and decided the strategy does not play the chip (*Decisions so far*;
`log.md`, *Two decisions from 2026-11-01, logged late*).

Withdrawn: carrying the last known value to a place or position with no history in the other
seasons. It fell away on 2026-11-07, as the redesign has no tables by place or position
(`log.md`, *Signal redesign agreed*).

## Original entry, moved from `BACKLOG.md` 2026-11-01

[2026-10-31: `docs/indicator_analysis_v1/log.md` has the best-performing indicator
combinations to start from, which differ between normal and sprint weekends.]
[2026-11-01: the same log has a rough estimate of what those combinations' gain is
worth, about 50 to 130 points a season against rolling points. It is not a comparison
with P2PM. Its *Conclusions* entry records the combinations Alex accepted, including
odds for race 1.]

**Bring `AggregateRank` into line with those conclusions** (raised by Alex 2026-11-01).
It still adds every rank column at weight 1.0, so driver rolling points, both practice
sessions and odds count equally, and only `METRIC_WEIGHTS` in `fast_f1/metrics.py` sets
constructor rolling points to zero. The conclusions want driver + constructor + FP3 on
normal weekends, driver + constructor on sprint weekends, and odds for race 1. One flat
dict cannot say that, as the sessions differ by weekend format and race 1 differs again,
so weights will need to depend on those. `fast_f1.cli` writes this column for each race,
and this section's strategy is written to maximise it, so settle this before building on
it. Changing it also moves the stored values in
`data/fastf1_practice_rolling_metrics.xlsx`, which `indicator_analysis_v1` rebuilt from
components and so does not rely on.

`fast_f1` produces a per-driver `AggregateRank` for every race but nothing
consumes it. It is a standalone signal — `docs/fastf1_v1/` is complete as of
2026-07-27, and every strategy in `linear/` still optimises on fantasy points,
price or odds. Whether the indicators actually pick better teams than P2PM is
the open question the module was built to answer, and it cannot be answered
without a strategy and a back-test.

Add a `StrategyFastF1` subclassing `StrategyBase` that maximises `AggregateRank`
subject to the existing budget/team-size/max-moves constraints, and back-test it
against the other four.

**How the signal gets in.** Two precedents. `StrategyMaxP2PM` reads
`derivs_assets`, threaded from the `Race` object by
`strategy_factory.factory_strategy()`. `StrategyBettingOdds`
(`linear/strategy_odds.py:10-25`) ignores that and loads its own file in
`__init__`, defaulting the path to a parameter (`fn_odds`) so tests can point at
a fixture. The odds pattern is the closer fit — `AggregateRank` is a per-race
external file, not a derivation of archive data — and its file-path parameter
should be copied, not its hardcoded-default habit. A
`data/test_fastf1_metrics.xlsx` fixture will be needed, as
`tests/test_strategy_odds.py` has for odds.

Five things to settle before writing any of it.

- **Constructor identifiers do not match.** Drivers do: `fast_f1` writes the
  bare FastF1 abbreviation (`ALO`) and `load_odds` already has a
  `qualify_driver_with_constructor` flag to turn that into the repo-wide
  `ALO@AST`. Constructors do not — the fantasy side uses three-letter codes
  (`ALP`, `AST`, `AUD`, `CAD`, `FER`, `HAA`, `MCL`, `MER`, `RED`, `VRB`, `WIL`)
  and `data/fastf1_practice_rolling_metrics.xlsx` carries FastF1 team names
  (`Alpine`, `Aston Martin`, `Audi`, `Cadillac`, `Ferrari`, `Haas F1 Team`,
  `McLaren`, `Mercedes`, `Racing Bulls`, `Red Bull Racing`, `Williams`). It is a
  clean 1:1 mapping that exists nowhere in the repo, and it has to live
  somewhere both `fast_f1` and `linear` can reach — probably `common`. Watch
  mid-season and cross-season renames; `Racing Bulls`/`VRB` and `Audi`/`AUD` are
  the ones that have moved.
- **There is no constructor-level aggregate.** `AggregateRank` is per driver.
  `ConstructorRollingPointsRank` exists but carries zero weight
  (`fast_f1/metrics.py:METRIC_WEIGHTS`), and there is no constructor practice or
  odds rank at all. `StrategyBettingOdds` solved the same problem by summing its
  two drivers' values into a constructor value — "not accurate from a pure stats
  perspective, but works when using as an LP optimise variable", as README puts
  it. Either reuse that, or raise the constructor weight and build a genuine
  constructor indicator. The former is cheaper and consistent; the latter is
  what the zero weight was left adjustable for.
- **The back-test data does not exist yet.**
  `data/fastf1_practice_rolling_metrics.xlsx` currently holds 342 rows: 2023
  races 1-6 and 2026 races 1-11. `run_multiple_teams.py` walks the seasons in
  `common.F1_SEASON_CONSTRUCTORS`, which is 2023-2025, so a full
  `python -m fast_f1.cli --historical` has to complete first. That is ~70 races
  of API fetching, and worth doing before anything else here since it is the
  long pole and everything else depends on it.
- **Back-testing will only exercise part of the signal.** Odds coverage is 2026
  races 1-11 only [2026-10-05: now 1–17] (see *Source betting odds directly from a web page* above), so
  across 2023-2025 the `OddsRank` component is a constant zero and the back-test
  measures the practice and rolling-points indicators alone. That is the same
  limitation README already records for `StrategyBettingOdds` — "no historical
  odds could be found during development, so it's not been back-tested" — and it
  means a good back-test result understates the live strategy while a bad one is
  not conclusive against it. Say which is being measured when reporting.
- **Bias the objective towards getting P1 right.** A plain "maximise summed
  `AggregateRank`" objective treats a unit of rank at the front of the field the
  same as a unit at the back, but the fantasy scoring does not: P1 pays the most,
  and doubly so once the DRS x2 multiplier lands on that driver (`races/team.py`
  applies it to the highest-priced driver by default, and `StrategyMaxP2PM`
  overrides `get_drs_driver()` to move it). Weight the top of the field
  explicitly — either transform `AggregateRank` so the gap between 1st and 2nd
  is worth more than the gap between 10th and 11th, or add a bonus term on
  whichever driver the strategy nominates for DRS. Whatever the form, it needs
  a coefficient that can be tuned and back-tested at zero, so the unbiased
  objective stays available as the comparison case. [2026-09-19:
  `docs/max_points_v1/proposal.md` argues that modelling DRS inside the LP
  objective subsumes this; see its *Modelling the DRS boost in the objective*.]
  [2026-09-28: only partly. The helper now exists on `StrategyBase`, and it
  rewards teams with one strong driver, but it nominates by whatever values it is
  given. So it biases selection towards the top of the field without improving
  the DRS pick itself. See *Refine P2PM: better DRS nomination* below.]

One game mechanic to note: `AggregateRank` needs FP2+FP3 (or FP1+Sprint
Qualifying) to have run, so this strategy cannot pick a team before practice.
That matches the odds strategy's recommended timing and rules out using it for
`select_starting_team.py`-style pre-season picks.

Raised 2026-07-27, on completing `docs/fastf1_v1/` — the module works and is
unused, which is the whole point of the next step rather than a defect in it.
