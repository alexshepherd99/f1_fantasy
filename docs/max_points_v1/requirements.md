# max_points_v1 — Requirements

**Status**: agreed 2026-09-20, when the effort was picked up off the backlog.
Design rationale and the LP derivations live in `proposal.md` (raised
2026-07-30, extended 2026-09-19) and are not restated here. Implementation plan
in `plan.md`; execution log in `log.md`.

Optimise the three-race rolling *points* total directly rather than the
points-per-price ratio `StrategyMaxP2PM` uses, model the DRS x2 boost inside the
LP objective instead of applying it after the team is chosen, and back-test both
against P2PM.

## Sources consolidated

- `docs/max_points_v1/proposal.md` — the whole design. *What
  `StrategyMaxP2PM` is actually doing*, *Modelling the DRS boost in the
  objective*, *DRS as an opt-in `StrategyBase` helper*, *Failure modes, and a
  tunable coefficient for each*, *Tuning the coefficients*, *Suggested commit
  order*.
- User decisions, 2026-09-20 — the three settled below under *Decisions taken
  on pick-up*.
- `docs/backtest_v1/` — complete 2026-09-19. Supplies the harness this effort's
  step 1 called for; R1, R2, R4, R5, R7, R8 there own the sampling, pairing,
  keying and reporting, and are not duplicated here.
- BACKLOG, *Lift concentration calculation into `StrategyBase`* — named in the
  proposal as a likely prerequisite. Deferred; see R7.

## Decisions taken on pick-up (2026-09-20)

1. **The core-modules exception is granted in full**, covering
   `linear/strategy_base.py`, on the proposal's terms — see R6.
2. **`StrategyMaxPoints` copies P2PM's race-4 unlimited-moves block**, so the
   paired back-test measures the objective change alone — see R2.
3. **The concentration lift is deferred**, to be driven by measurement rather
   than assumption — see R7.

## Scope

- New strategy modules in `linear/`, and an **opt-in** helper added to
  `linear/strategy_base.py`.
- **`linear/strategy_p2pm.py` is not edited.** `StrategyMaxP2PM` is picking a
  live team through the rest of the 2026 season and its behaviour must not
  change at all until that season is complete. DRS-aware P2PM arrives as a
  derived class instead.
- **No other existing file in `linear/` is edited**, and nothing in `races/`,
  `import_data/` or `scripts/` is. `backtest/` is edited freely — it is this
  effort's harness, not a core module.
- **No existing test file is edited** (R6).
- No data work: `Points Cumulative (3)` is already computed for drivers and
  constructors by `helpers.load_with_derivations` and already threaded into
  `derivs_assets` by `linear/strategy_factory.py`. No new fixture workbook, no
  `--historical` run, no constructor-name mapping.

## Requirements

### R1 — `StrategyMaxPoints`, at neutral defaults

- A new strategy maximising the three-race rolling points total over selected
  assets: `Points Cumulative (3)`, via
  `get_derivation_name(DerivationType.POINTS_CUMULATIVE, 3)`.
- An asset with no derivation entry is filled with `0.0`, matching P2PM's
  existing fill. This covers owned-but-unavailable drivers, which
  `get_team_selection_dict` includes at `COST_PROHIBITIVE`. [Corrected
  2026-09-20, on reading `StrategyBase.__init__` end to end: that is not the
  mechanism. `verify_data_available` runs over every derivation
  (`linear/strategy_base.py:116-123`) and **raises** if an *available* asset has
  no entry, so a missing key never reaches the objective. What P2PM's fill
  actually catches is a key present with value `None`, which passes verification
  because derivations are checked with `check_type=False`. Owned-but-unavailable
  drivers are handled by *omission* instead: they have no entry by design (see
  the comment at `:112-113`), and the objective comprehension iterates
  `_all_available_*`, so they are simply absent from it rather than filled. The
  fill is still required, for the `None` case; only the reason changed. This does
  **not** affect R3, where the helper indexes `y` over available ∪ team and so
  genuinely needs its own missing-value rule.]
- It reuses the base class's budget cap, team-size and max-moves constraints
  unchanged. It adds no constraint of its own.
- No DRS term and no tunable coefficients at this stage. This is the control,
  and the direct test of the proposal's falsifiable hypothesis: that dividing by
  price penalises expensive assets a second time on top of a budget cap that
  already rations them.

### R2 — The race-4 unlimited-moves reset is copied

- `StrategyMaxPoints` resets `max_moves` to the full team size at race 4,
  exactly as `StrategyMaxP2PM.__init__` does.
- **Why:** the back-test baseline is `StrategyMaxP2PM`, which has the reset.
  Without it the paired comparison would conflate two changes — the objective,
  and whether the chip was played — and the proposal's *early races are
  degenerate* point makes race 1–3 behaviour exactly where a pure-points
  objective is least trustworthy.
- The duplicated block is accepted. Lifting it somewhere shared would edit
  `strategy_p2pm.py`, which *Scope* forbids while P2PM is live. The proposal
  already records that as an argument for the lift once the 2026 season closes.

### R3 — The DRS helper on `StrategyBase` does nothing unless called

- A helper that models the DRS boost inside an objective: one selected driver's
  value counted a second time. The mechanics are in `proposal.md`, *Modelling
  the DRS boost in the objective*; they are not re-derived here.
- It creates the `y_i` binaries under `VarType.DrsDriver` — already declared and
  unused — indexed over the **same driver set** as `VarType.TeamDrivers`.
- **It mutates nothing.** It returns two things for the caller to apply: the
  objective term `Σ r_i·y_i`, and the constraints `Σ y_i = 1` and `y_i ≤ x_i`
  (one per driver) as a name-keyed dict. The base class owns neither the
  objective nor the problem — both are built by the subclass in `get_problem()` —
  so it adds neither itself. Agreed 2026-09-20; see `plan.md`, *The helper's
  shape*.
- The call site is two DRS-specific lines: the call, then
  `problem.extend(drs_constraints)`. **No convenience wrapper** around those two
  lines is added — at two callers it would cost more code than it saves. Revisit
  at three or four.
- The values `r_i` are **passed in by the strategy, in that strategy's own
  objective units**. The base class cannot know what an objective is made of, so
  it cannot know which value DRS should count twice. A driver missing from the
  mapping is treated as `0.0`.
- A companion read-back returns the driver whose `y_i` solved above `0.5` — a
  tolerance, not `== 1`, because CBC returns floats. A strategy opts in by
  returning it from `get_drs_driver()`.
- **The read-back raises if the nominee is not on the selected team.** Both
  values are already to hand after the solve, so the check is free, and it is the
  one place the "caller forgot to add the constraints" mistake can be caught.
  Without it that mistake is silent and produces a plausible wrong score (R4).
  The error names the likely cause.
- **No existing strategy's behaviour changes.** Nothing calls the helper unless
  it chooses to, and `StrategyMaxP2PM` will not.

### R4 — The DRS nominee is provably on the team

- Required in its own right, because the existing guard will not catch this.
  `Team.get_drs_points()` checks `if self.drs_driver in race.drivers` — that the
  driver is *in the race*, not that the team *owns* them. An unowned nominee's
  points would be silently added to the score.
- This is what makes `y_i ≤ x_i` load-bearing rather than decorative. Without it
  the solver parks the boost on the best driver in the whole field, the DRS term
  becomes the same constant for every candidate team and stops influencing
  selection at all, and the nominee need not be owned.
- Enforced two ways: the R3 read-back raises at runtime, and a test asserts the
  nominee is always in the selected team.

### R5 — `StrategyMaxP2PMDrs`, for a DRS-aware comparison

- Derived from `StrategyMaxP2PM`, otherwise identical to its parent: it builds
  on `super().get_problem()`, sets the objective to the parent's
  `VarType.OptimiseMax` plus the DRS term, and inherits the race-4 reset.
- It passes the **P2PM values its parent's objective already uses**, after the
  parent's missing-value fill, so DRS counts the nominated driver's P2PM value
  twice and the units match the objective. Rolling points were considered and
  rejected: mixing points into a P2PM objective would need a scaling
  coefficient.
- This differs from `StrategyMaxP2PM`'s post-hoc nomination, which picks the
  selected driver with the highest rolling *points*. That is the point of the
  comparison, not a defect in it.

### R6 — Zero change to `StrategyMaxP2PM`, verified not assumed

The core-modules exception is granted on these terms. A passing suite is
necessary but **not sufficient**: `tests/test_strategy_p2pm.py` cannot detect a
change in which of several equal LP optima is returned. Before and after the
`StrategyBase` change:

- `StrategyMaxP2PM`'s rows from a `backtest_v1` run on a fixed seed must be
  **identical**.
- The live `run_single_team.py` configuration must replay to an identical team,
  DRS nomination and points, race by race. Replay it through its functions, not
  its `__main__`, which overwrites `outputs/f1_fantasy_results_single.xlsx` — as
  was done for the hash-order fix.
- No existing test file is edited. A test that had to change to keep passing is
  evidence the behaviour changed. [Scoped 2026-09-20: this clause covers tests of
  `linear/` behaviour, which is what it was written to protect. It does not cover
  `tests/test_backtest_cli.py`'s registry assertion, which asserts exact dict
  equality on `STRATEGIES` and so must change whenever a strategy is registered —
  that is the intended change, not a symptom of one. Step 3 edited it for exactly
  that reason.]

### R7 — Concentration is measured before it is constrained

- `StrategyMaxPoints` runs **unconstrained** on concentration at first. The
  proposal argues a pure-points objective will take the top constructor and both
  its drivers; that is a prediction, and the back-test can check it.
- Report whether it happens and whether it costs points. If it does, that is the
  evidence for the backlog item *Lift concentration calculation into
  `StrategyBase`* — which edits `linear/strategy_odds.py`, an existing core
  file, and wants its own session.
- Deliberately **not** treated as a blocking prerequisite (agreed 2026-09-20).

[2026-09-20, after *Verification* 1: this requirement's condition is **not yet
met**. The run measured high variance — `StrategyMaxPoints` wins most starting
teams in 2025 and still loses on the mean, with a left tail reaching −713 — which
*looks* like concentration risk, but concentration itself was never counted.
Whether the strategy holds a constructor plus both its drivers more often than
P2PM, and whether those teams are the ones in the tail, are both unmeasured. The
metric already exists in `linear/strategy_odds.py` and does not need inventing; the
obstacle is that the results store keeps only each team's final-race row, so
measuring it properly needs a re-simulation capturing every race. Until then the
lift stays unjustified, which is exactly what this requirement was written to
prevent.]

[2026-09-21, after the per-race re-simulation: **this requirement is met, and the
prediction it was hedging is refuted.** Measured over all 210,000 team-races,
`StrategyMaxPoints` is the more concentrated strategy in 2023 alone; in 2024 it
holds a constructor with both its drivers in 0.7% of team-races against
`StrategyMaxP2PM`'s 6.5%, and 2024 is the season it loses by an order of magnitude
more than the others. Concentration correlates *positively* with the per-team
season delta in all three seasons (Spearman +0.16, +0.06, +0.28), and the bottom
decile of teams by delta is **less** concentrated than the rest. So concentration
does not make the tail, this effort supplies **no evidence** for the backlog lift,
and *Verification* 1's variance needs another explanation. Full numbers in
`log.md`, *The per-race re-simulation*; the metric itself is
`backtest/per_race.py`. The corresponding clause in `plan.md` step 9 — "report
concentration behaviour here (R7)" — is discharged early by that run.]

### R8 — Tunable coefficients, each defaulting to neutral

- The levers in `proposal.md`, *Failure modes*: constructor scaling (default
  1.0), an unused-budget bonus (default 0.0), and a Δprice term (default 0.0).
- **Every coefficient defaults to the value that reproduces the unbiased
  objective**, so the untuned case stays reachable as the comparison baseline and
  the null hypothesis is never lost.
- One coefficient per commit.
- They are constructor parameters, so `backtest.variants.make_variant` can build
  a named variant per setting with no further mechanism.

### R9 — Tuning protocol

- Coordinate descent over a coarse grid, per `proposal.md`, *Tuning the
  coefficients*: one coefficient at a time over ~5 values, locking in a value or
  locking in "neutral, no evidence it helps" — a perfectly good outcome.
- One final 2D check of the **DRS term against the constructor scaling
  coefficient**: both move budget between driver and constructor slots, in
  opposite directions, and are the pair coordinate descent most plausibly
  misses.
- **Prefer plateaus to peaks.** A sharp spike is fitted to three seasons and
  will not survive 2027; the shape of the sweep is more informative than its
  argmax.
- No four-dimensional grid search. 5⁴ back-tests is not something this box will
  do, and at n=3 seasons it would be fitting noise.
- `load_with_derivations` is `functools.cache`d and the derivations do not depend
  on the coefficients, so run every grid point for a season inside one process.

### R10 — What a result may claim

- The verdict form is `backtest_v1`'s (R8 there): a positive pooled per-season
  mean delta in **every** season, bands informing but not gating.
- A delta smaller than its own run-to-run spread is not evidence. At n=3 seasons
  a result that flips sign between seasons is reported as "no evidence", not as
  a win for whichever side has two of the three.
- Say which of "I reasoned it" and "I ran it" applies to every claim.

## Open questions

- **Is unused budget worth anything in practice?** Determines whether R8's
  budget-saturation lever needs tuning at all or is a non-issue. Rolling points
  are effectively monotone in price, so unlike P2PM there is no implicit reason
  for this objective to leave change; unused budget is fully retained
  (`Team.total_budget` = value + unused) and has real option value against price
  rises, but is not scored.
- **Rolling sum vs mean.** `fillna(0).shift(1).rolling(3).sum()` scores a driver
  who missed a race as having zeroed it, and keeps them depressed for three races
  after returning. Defensible for "who will score next", clearly wrong for a
  mid-season debutant. Which effect is being accepted is undecided; it affects
  P2PM identically today, so it is not a regression introduced here.
- **Whether `StrategyMaxP2PM` should adopt the helper directly** once the 2026
  season is complete. Out of scope here by *Scope*; a separate decision.
