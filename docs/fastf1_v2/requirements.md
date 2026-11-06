# fastf1_v2 — Requirements

**Status**: agreed 2026-11-01. All eight questions are answered and the working assumptions are
confirmed. `plan.md` is written, and no code has been written. Findings so far are in `log.md`.

## Picking this up

1. Read this file and `log.md`. Read the `log.md` correction before quoting any field-wide
   driver figure from its first entry.
2. Carry on from `plan.md`.

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

The entry below is kept as written. These points in it no longer hold:

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

## Open questions, in the order they will be asked

### 1. What does the objective score in? (agreed 2026-11-01: B, without A)

The indicator work showed only that the signal puts drivers in the right order. The LP adds
the values up, so the gaps matter too, and they are uneven: on average 1st scores 35 points
and 5th 23, while 11th to 20th all score about 1–7.

- **A. Sum the 0–1 signal directly,** as the entry below planned. It is the simplest, but
  it treats the gap between 19th and 20th like the gap between 1st and 2nd. Any negative
  penalty or spending bonus needs an arbitrary weight, as it is not measured in points.
- **B. Convert signal position into expected fantasy points,** using a table of what each
  position has historically scored. Average negative risk is then already included, and
  DRS and budget can be compared in the same unit. The table must be built only from
  other seasons, or the back-test flatters it, and it is a bit more code.

Recommendation put to Alex: B, with A also run as a comparison. Neither has been run, so
whether B picks better teams is unknown. The question put was "A, B or both?"

**Agreed 2026-11-01: B alone.** A is not run as a comparison.

### 2. How is a constructor scored? (agreed 2026-11-01: B)

The conclusions cover drivers only, and there is no constructor-level signal.

- **A. Sum its two drivers' values,** as `StrategyBettingOdds` does. It is cheap and has a
  precedent, but it inherits a driver signal that already contains constructor rolling
  points.
- **B. Score it on its own rolling place,** converted to expected points if question 1
  goes to B.
- **C. Build a real constructor indicator.** There is no constructor practice or odds rank
  to start from.

Evidence: holding a top-four constructor on rolling fantasy points goes negative at most 6%
of the time, against 23–26% at places 9–10 and 59% at place 11. Negative constructors cost
P2PM's teams only 4–20 points a season, so a new objective could lose that protection.

A table built from other seasons has a gap in 2026, which has 11 constructors against 10
before (reasoned, not run). Testing 2026 leaves no history for place 11, so that place needs
a rule, such as carrying place 10's value. The same gap applies to driver positions 21 and 22
under question 1.

Recommendation put to Alex: B. Whichever is chosen needs the constructor name mapping
described in the entry below, which exists nowhere in the repo.

**Agreed 2026-11-01: B.**

### 3. How are negative scores handled? (agreed 2026-11-01: A as the base, B as a variant)

This is the first point in Alex's brief. See `log.md`, *Negative scores*, and its later
check on the rolling indicators.

- **A. No separate term.** Expected points already include average negative risk. This is
  available only if question 1 goes to B.
- **B. A soft penalty** on each asset's chance of going negative, with a coefficient that
  can be tested at zero.
- **C. A rule** that excludes assets, for example after recent negatives.

Evidence: negatives cost P2PM's teams 202, 313 and 275 points a season if every one had
been zero, which is a hindsight ceiling. They are only partly predictable: 9% of the signal's
top five against 24% at the back, and about two-thirds of them are retirements. A negative
makes one more likely (drivers 15%, 20% and 23% after none, one and two in the last three
races; constructors 9%, 19% and 34%), but this does not control for how good the car is.
Swapping fantasy rolling points into the signal did not sort them better.

Question 1 went to B, so A is available. What A misses is anything about a particular asset
beyond its place, because the table gives every asset at a place the same risk.

Recommendation put to Alex: A as the base, with B as a tested variant. Avoid C unless the
back-test supports it, since a rule cannot be tested at zero the same way.

**Agreed 2026-11-01: as recommended.**

### 4. How is unspent budget handled? (agreed 2026-11-01: A)

This is the second point in Alex's brief. See `log.md`, *Unspent budget*.

**Agreed 2026-11-01: there is no hard rule on maximum spend, and a soft term gets tested.**
Its form is open.

- **A. A small reward per 1m spent,** tested at zero and a few other values.
- **B. A reward for expected price rises,** aimed at budget growth rather than spending.
- **C. Both.**

Evidence: P2PM leaves 2.3–4.3m unspent on average, worth at most about 70–225 points a
season. Spending alone has not helped: Max Budget spends the most and loses by 21–36%, and
Max Points spends more than P2PM and still loses. Budget growth may matter as much, as
the price-blind odds strategy was about 10m behind P2PM's budget by 2026 race 17.

Question 1 went to B, so a reward can be stated in points per 1m. Within a race, 1m of price
goes with about 1.0–1.3 points for a driver and 2.1–2.8 for a constructor, which gives a
range to test, starting at zero.

Recommendation put to Alex: A, and report final budgets for every variant. Add B only if the
signal falls behind on budget the way the odds strategy did.

**Agreed 2026-11-01: A.** B is not built now.

### 5. How is the DRS driver chosen, and is it inside the objective? (agreed 2026-11-01: A, with B as the comparison)

- **A. Inside the objective,** through the existing `get_drs_objective_term` and
  `get_drs_nominee` helper on `StrategyBase`, as `StrategyBettingOdds` does.
- **B. Chosen after the team is picked,** as the selected driver with the best signal.
- **C. The default,** the highest-priced driver.

Evidence: the best possible DRS pick would add 226, 103 and 98 points a season, a hindsight
ceiling. The helper rewards teams with one strong driver, but nominates by whatever values
it is given, so it does not by itself improve the pick. The original entry asks for a
coefficient that can be tested at zero.

Question 1 went to B, so passing the helper expected points makes the term what DRS really
adds, which gives a coefficient of 1 a meaning. A and B nominate by the same rule, the
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

Question 1 went to expected points by signal position, so the strategy needs only the
signal's order, and does not sum or maximise `AggregateRank`. Only `fast_f1` uses the column:
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
But 2026 could still leak in through the expected-points tables: "other seasons" for a 2023
run would include 2026, and tuning there would then have seen it.

Recommendation put to Alex:

- Keep the harness verdict, the same bar as every strategy in `BACKTEST_LOG.md`: a positive
  pooled mean delta in every season, at 500 teams a band. Report 2026 on its own as the fair
  read and 2023–25 as flattered. A win in 2023–25 with a loss in 2026 is a loss, and a win in
  2026 with a loss in a flattered season is not a win either.
- Fix every coefficient from questions 3 and 4 on 2023–25, then run only the chosen variants on
  2026, once, and report how many variants were tried.
- While tuning, a season's table comes from the other 2023–25 seasons only, leaving 2026 out.
  The 2026 run's table comes from all of 2023–25.
- 2026 runs through race 18 with the harness's own `--output` and `--summary`, and is rerun
  when the season finishes. Race 19 is priced but has no signal, so the plan must say how that
  race is handled.

### 8. Where does the code go? (agreed 2026-11-01)

A new file in `linear/` needs Alex's OK each time, and strategy classes get a design
conversation before any editing, above all `StrategyBase`. Anything the code has to work around
in a core module goes in the R12 ledger in `docs/backtest_v1/requirements.md`.

Recommendation put to Alex, with no edit to any existing file in `linear/`, `races/`,
`import_data/` or `scripts/`:

- **`fast_f1/signal.py`, new.** Builds the signal from the component columns, and the
  expected-points tables from the metrics file and the archive, both cached once per process.
  `factory_strategy` builds a strategy per team per race, so reading the file on each build, as
  the odds strategy does, would be too slow. A season's table uses 2023–25 minus that season,
  which covers both the tuning and the 2026 run with one rule.
- **`linear/strategy_fastf1.py`, new.** `StrategyFastF1(StrategyBase)`, with keyword parameters
  `fn_metrics`, `drs_coefficient=1.0`, `negative_penalty=0.0` and `budget_reward=0.0`.
  `make_variant` passes these through, so `factory_strategy` needs no change (checked). The
  objective is expected points, plus the helper's DRS term unless its coefficient is zero, plus
  `budget_reward * TotalCost`, minus the penalty. `get_drs_driver()` always returns the selected
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

- **No hard rule on maximum spend; a soft term gets tested.** Agreed 2026-11-01.
- **The objective scores in expected fantasy points, by signal position.** Agreed 2026-11-01.
  The 0–1 signal is not run as a comparison.
- **A constructor scores on its own rolling place, converted to expected points.** Agreed
  2026-11-01.
- **Negatives get no separate term in the base strategy.** A soft penalty, with a coefficient
  tested at zero, runs as a variant. No exclusion rule unless the back-test supports one.
  Agreed 2026-11-01.
- **The budget term is a small reward in points per 1m spent,** tested at zero and a few other
  values, with final budgets reported for every variant. Agreed 2026-11-01.
- **DRS sits inside the objective at a coefficient of 1,** with zero as the comparison, and the
  nominee is the selected driver with the best value. Agreed 2026-11-01.
- **The strategy builds its signal from the component columns,** defined once in `fast_f1`, and
  `AggregateRank` stays as it is. Bringing it into line is its own item in `BACKLOG.md`. Agreed
  2026-11-01.
- **The verdict is the harness's: a positive pooled mean delta in every one of four seasons,**
  with 2026 reported as the fair read. Coefficients are fixed on 2023–25, with tables that leave
  2026 out, before the chosen variants run once on 2026. 2026 is rerun when the season finishes.
  Agreed 2026-11-01.
- **The strategy does not implement the race-4 chip.** `StrategyMaxP2PM` still plays it, so the
  comparison also measures the chip. `StrategyMaxP2PMNoReset` runs in all four seasons to isolate
  that effect, and the verdict stays against `StrategyMaxP2PM`. Agreed 2026-11-01.
- **Code shape as in question 8:** new `fast_f1/signal.py` and `linear/strategy_fastf1.py`, no
  constructor name mapping, and `linear` imports `fast_f1`. Agreed 2026-11-01.

Alex asked for the "rolling indicators use championship points" claim to be checked before
question 1. It is true, and swapping in fantasy rolling points gave no measurable gain (see
`log.md`). Alex has not yet ruled on it, so the signal stays on championship rolling points
for now as a working assumption. [2026-11-01: ruled. Alex confirmed this working assumption
below, so the signal stays on championship rolling points.]

## Working assumptions, confirmed by Alex 2026-11-01


- [2026-11-01: withdrawn. Alex decided the strategy does not implement the chip, see *Decisions
  so far*.] The race-4 unlimited-moves chip is copied from P2PM, so that the comparison does not
  also measure the chip.
- Race 1 needs nothing built. A back-test's race 1 team is the sampled one, and live
  picks already have `scripts/select_odds_start.py`.
- Odds stay out of the signal after race 1. Within 2026 they add nothing measurable, and
  they cover one season.
- `StrategyMaxP2PM` is not edited until the 2026 season ends.
- The signal's rolling indicators stay on championship points.
- A place or position with no history in the other seasons carries the last known value:
  constructor place 10 for place 11, and driver position 20 for 21 and 22. This understates
  the risk at constructor place 11, which went negative 59% of the time in 2026.

## Original entry, moved from `BACKLOG.md` 2026-11-01

[2026-10-31: `docs/indicator_analysis_v1/log.md` has the best-performing indicator
combinations to start from, which differ between normal and sprint weekends.]
[2026-11-01: the same log has a rough estimate of what those combinations' gain is
worth, about 50 to 130 points a season against rolling points. It is not a comparison
with P2PM. Its *Conclusions* entry records the combinations Alex accepted, including
odds for race 1.]

[2026-11-01: this paragraph's work is back in `BACKLOG.md` as its own item; see question 6.]
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
