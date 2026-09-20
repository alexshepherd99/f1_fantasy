# max_points_v1 — Log

Execution log for the max_points_v1 effort. Newest entries at the bottom.
Requirements and plan live alongside in `requirements.md` and `plan.md`; the
design rationale predates both and is in `proposal.md`.

## Status summary

- Effort picked up off the backlog 2026-09-20. Step 1 in progress; no code
  written yet. [Superseded 2026-09-20: steps 1-3 complete, see below.]
- Step 1 completed 2026-09-20: `requirements.md`, `plan.md`, `log.md`, and the
  DRS helper's shape settled ahead of the code.
- Step 2 completed 2026-09-20: `linear/strategy_max_points.py`,
  `StrategyMaxPoints`.
- Step 3 completed 2026-09-20: registered in `backtest/cli.py`. **Every step up to
  *Verification* 1 is implemented; the measurement run has not been done.**
- *Verification* 1 run 2026-09-20 and **found to be confounded** — the comparison
  measured the objective *and* DRS nomination. Its result is not a finding about
  the objective. See *Verification 1, first attempt* and *Matching P2PM's DRS
  nomination* below.
- Step 4 added 2026-09-20: `StrategyMaxPoints` now nominates a DRS driver by the
  same rule as `StrategyMaxP2PM`, so a re-run compares objectives alone.

## Verification 1, first attempt — confounded (2026-09-20)

Ran in about 30 minutes rather than the planned 2.5 hours: the store already held
*Verification* 4's rows from `backtest_v1`, so the P2PM baseline was skipped and
only the 4,500 challenger simulations ran. Reuse was checked before relying on it —
2023's sample was rebuilt from seed 1 and compared against the store's baseline
teams, 1,500 against 1,500, identical with none on either side. The archive last
changed on 2026-09-09 and the store was written on 2026-09-18, which is why it
reproduces.

**The result, which is not a finding about the objective.** Pooled mean delta per
season: 2023 +104, 2024 −156, 2025 +1. Two seasons positive of three, so
`beats_baseline` and `consistent_sign` both `False` — "no evidence" by R10, not a
win for either side. 2025's pooled mean of +1 hides a median of +48 against a p10
of −281: it beats P2PM on most teams and loses heavily on a few, which is the
concentration risk the proposal predicted, visible in the data.

**Why it is confounded.** `StrategyMaxPoints` nominated no DRS driver in 100% of
teams in all three seasons, so `Team` fell back to the highest-*priced* driver,
while `StrategyMaxP2PM` nominated the highest-rolling-points driver in 100%. DRS
doubles one driver's score every race, which is worth the same order as every delta
reported. R2 copied the race-4 chip so the comparison would measure "the objective
alone", and then left a second, larger difference in place.

**A wrong turn recorded because the reasoning is instructive.** Comparing the
strategies' stored rows showed *identical* end-of-season driver holdings for 2024
and near-identical constructor spend, which was read as "same team, different
score, so DRS must be the cause". The store keeps only each team's final-race row
(`run_for_team(...)[-1]`), so that was one snapshot, not a season. Re-simulating
five 2024 teams across all 24 races showed the strategies hold the same assets in
only 1–5 races of 24. The convergence at the final race was coincidence. DRS is
confirmed *present* as a difference; it is not established as the *cause*, and the
per-race gaps are two-sided — one team's race 8 was +91 and its race 16 −65 — so
selection is doing real work too. The two causes cannot be separated from this run.

## Matching P2PM's DRS nomination (2026-09-20)

`get_drs_driver` copied verbatim from `StrategyMaxP2PM` into `StrategyMaxPoints`,
so the two differ in their objective and nothing else. Duplicated rather than
shared: `strategy_p2pm.py` cannot be edited while P2PM picks a live team, which is
the cost of that guarantee and is noted in the method's docstring.

The nominated *driver* will still often differ between the strategies, because the
teams differ. That is downstream of the objective under test, not a second
variable; what is matched is the rule.

**One asymmetry that remains, named rather than discovered later.**
`StrategyMaxPoints.get_problem` normalises the points derivation, since that is its
objective, so `get_drs_driver` reads filled floats. P2PM normalises only the P2PM
derivation, so its `get_drs_driver` reads the points derivation raw. Identical while
those values are plain floats, which production behaviour implies; if one were ever
`None`, P2PM would raise where `StrategyMaxPoints` would not.

**The sim-key trap, avoided.** The store already held 4,500 rows labelled
`StrategyMaxPoints` from the confounded run, and `simulate_sample` skips keys it
already has, so re-running under the same label would have silently returned the
old results — exactly the trap `proposal.md` and `backtest_v1` R4/R5 describe. The
re-run therefore writes to its own store, `outputs/max_points_v1_results.parquet`,
leaving the shared `backtest_v1` store untouched rather than deleting rows from it
without agreement. The cost is that the baseline is simulated again, roughly
doubling the run to about an hour; the benefit is that nothing stale can be reused
and the re-simulated baseline is a free reproducibility check. **The superseded
`StrategyMaxPoints` rows are still in the shared store and must not be read as this
effort's result.**

## Step 1 — Effort docs (2026-09-20)

Suite green at 220 before starting.

The effort had sat as `proposal.md` alone since 2026-07-30, with a 2026-09-19
extension designing the DRS helper. Its step 1, the back-test harness, had
meanwhile been delivered in full as `backtest_v1` (complete 2026-09-19), so the
first substantive work here is the proposal's step 2, `StrategyMaxPoints`.

`requirements.md` consolidates rather than restates: the LP derivations and the
worked DRS example stay in `proposal.md` and are cross-referenced, since
duplicating them would create two places to keep true. Back-test mechanics —
sampling, pairing, keying, reporting, the verdict — are `backtest_v1`'s R1, R2,
R4, R5, R7, R8 and are referenced, not re-specified.

**Three decisions taken on pick-up**, recorded in `requirements.md` under
*Decisions taken on pick-up*:

- The core-modules exception is granted in full, including
  `linear/strategy_base.py`. `linear/strategy_p2pm.py` is still never edited,
  because `StrategyMaxP2PM` is picking a live team for the rest of 2026.
- `StrategyMaxPoints` copies P2PM's race-4 unlimited-moves block. Omitting it
  would make the paired back-test measure two changes at once — the objective,
  and whether the chip was played.
- The concentration lift is deferred (R7). The proposal called it a likely
  prerequisite; that is a prediction the back-test can check, and the lift edits
  `linear/strategy_odds.py`, which wants its own session.

**Two things found by reading the code before planning**, both recorded in
`plan.md`:

- **`factory_strategy` needs no change.** It takes `strategy: type[StrategyBase]`
  and builds it from generic keywords, naming no strategy, so a new strategy
  wires itself in. The proposal did not say otherwise but did not rule it out
  either.
- **The proposal's placement of the helper's constraints does not fit the data
  structure.** It has the helper adding `Σ y_i = 1` and `y_i ≤ x_i` to
  `self._lp_constraints`. The timing is right — `execute()` applies that dict
  after `get_problem()` returns — but the dict holds **one constraint per
  `VarType` key**, and `y_i ≤ x_i` is one per driver. `StrategyBettingOdds` hit
  the same wall with its pair-linearisation constraints and adds them straight to
  the `problem` object with explicit names, so the helper follows that precedent
  and takes the problem as a parameter. `proposal.md` annotated in place.
  [Corrected below — the helper stays pure instead; see *The DRS helper's shape*.]

## The DRS helper's shape (2026-09-20)

Settled over four rounds of discussion before any code was written, which is
itself the reason [[f1-fantasy-strategy-classes-need-care]] now exists as a
standing note. Recorded in `requirements.md` R3/R4 and `plan.md`, *The helper's
shape*; `proposal.md` annotated in place.

The helper **mutates nothing**. It returns the objective term and the constraints
as a name-keyed dict, and the caller applies them with `problem.extend()`. This
replaces the earlier plan of passing `problem` in, for two reasons: the base class
already declines to own the objective, so declining to own the problem is the same
rule applied consistently rather than stopped halfway; and a caller reading
`get_drs_objective_term(problem, values)` cannot see that ~21 constraints were
attached, which makes an impure call read as a pure one.

**`LpProblem.extend()` takes a `dict[str, LpConstraint]`** and names each
constraint with its key. Confirmed by reading the installed PuLP source, not from
memory — it removed the per-driver `for` loop the earlier design needed, and
asserting it without checking would have been a guess. Its dict branch does assign
into `self.constraints` directly, bypassing `addConstraint`'s validation; accepted,
since these constraints are built in-house and well-formed by construction.

**A convenience wrapper was proposed and rejected.** Alex asked whether a second
method could absorb the caller's two lines, and asked to be challenged on it. The
accounting: it saves exactly one line per caller against a new public method
needing a docstring, type annotations and tests — more code than it removes at two
callers. It also cannot touch the objective, so the call site is never one line
either way, and two public methods differing only in whether they mutate make
"does calling DRS change my problem?" depend on which was called. Agreed to
revisit at three or four callers, or if attaching ever needs more than one
`extend`.

**The read-back raises if the nominee is not on the team.** This is what makes the
pure helper safe: the wrapper's real value was unforgettability, and this buys the
same protection more cheaply. A forgotten `extend` otherwise fails silently —
`Team.get_drs_points()` guards on the driver being *in the race*, not *on the
team*, so an unowned nominee's points are added and the score merely looks
plausible.

## Step 2 — `StrategyMaxPoints` (2026-09-20)

Suite green at 220 before starting.

`linear/strategy_max_points.py`, mirroring `StrategyMaxP2PM` with
`POINTS_CUMULATIVE` in place of `P2PM_CUMULATIVE`, the race-4 unlimited-moves
block copied per R2, no DRS override and no coefficients. No change to
`strategy_factory.py` was needed, as `plan.md` predicted.

**How red-first was reached.** A brand-new module's only pre-implementation red is
`ModuleNotFoundError`, which `coding-standards` rules out as demonstrating
nothing. The module was therefore first committed to the working tree as a stub
whose `get_problem` deliberately maximised **price**, which made six of the eight
tests fail on their assertions rather than on an import. The stub was then
replaced by the real objective.

**Two tests passed against the stub and were diagnosed, not accepted.**

- `test_strat_max_points_is_not_swayed_by_price` was genuinely defective: its
  highest-scoring assets were also the most expensive, so a price objective
  returned the same team and the test could not distinguish the property it was
  named for. Rebuilt so three objectives disagree — points picks the mid-priced
  NOR/BOT/MAG/HUL, price would take the near-pointless PIA/TSU/AST, and
  points-per-price would take VER, whose ratio of 20 leads the field.
- `test_strat_max_points_respects_the_budget_cap` asserted only `total_cost <= 25`
  and `objective > 0`, both true under any objective. Rebuilt so the best scorers
  are also the cheapest: the points-optimal team costs 19.0 and leaves 6.0
  unspent, which an objective that merely filled the budget would not do.

**Two tests could not be made red and were confirmed by mutation instead**, both
asserting the absence of behaviour:

- `does_not_reset_moves_before_race_four`: changing the guard to
  `if self._race_num >= 3` gave `assert 6 == 2`.
- `nominates_no_drs_driver`: adding a `get_drs_driver` override returning a driver
  gave `assert 'VER' == ''`.

Both mutations were reverted.

**A correction to R1, found by reading `StrategyBase.__init__` to the end** rather
than the method being changed. R1 said the `0.0` fill covers owned-but-unavailable
drivers. It does not: `verify_data_available` raises when an *available* asset has
no derivation entry, so a missing key never reaches the objective, and
owned-but-unavailable drivers are excluded by *omission* from a comprehension that
iterates `_all_available_*`. The fill's real job is a key present with value
`None`, which passes verification because derivations are checked with
`check_type=False`. The fill is still needed; only the reason changed. R3 is
unaffected — its helper indexes over available ∪ team and does need its own
missing-value rule. `requirements.md` annotated in place, and the test for this
now exercises a `None` value rather than a missing key, which is what production
data can actually present.

## Step 3 — Registered in the back-test CLI (2026-09-20)

Suite green at 228 before starting, 229 after.

`StrategyMaxPoints` added to `backtest/cli.py`'s `STRATEGIES`, which is what makes
*Verification* 1 runnable. Red first: the new selectability test failed with
argparse's `invalid choice: 'StrategyMaxPoints'`, and the registry test with the
dict mismatch.

**This edited an existing test file, which R6 says not to do.**
`tests/test_backtest_cli.py`'s registry test asserts exact dict equality on
`STRATEGIES`, so it cannot survive a strategy being registered. Called out at the
time rather than absorbed. R6's clause is about tests of `linear/` behaviour —
a test changing to stay green there would be evidence `StrategyMaxP2PM` moved —
and a registry-contents assertion in `backtest/` is the opposite case: it changes
*because* the registry grew, which is the whole point of the step. R6 annotated
in place with that scoping.

**Smoke-run against real data, and what it does not show.** The CLI was run on
2023 with `--sample-size 1`, output directed into a session scratch directory so
`outputs/` was untouched. It completed end to end — six simulations, the summary
and the verdict written — which establishes that the strategy solves against real
`load_with_derivations` output and not only against synthetic fixtures. It
reported `StrategyMaxPoints` ahead of the baseline on all three sampled teams.

**That is not evidence for the divisor hypothesis and is not recorded as any.**
One team per band in a single season cannot separate the two strategies; the
per-team spread in `backtest_v1`'s own sizing work was far larger than the
differences seen here. The run's only claim is "it executes". *Verification* 1, at
the default sample size across three seasons, is the measurement.
