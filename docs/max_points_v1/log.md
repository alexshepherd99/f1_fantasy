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
- Per-race re-simulation run 2026-09-21, closing the handoff below: it reconciles
  exactly with *Verification* 1, **refutes R7's concentration prediction**, shows
  2024 to be a sustained drift rather than a few races, and measures the DRS
  nomination ceiling at +98 to +226 points a season. See *The per-race
  re-simulation* at the end.

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
effort's result.** [2026-09-20: Alex has agreed they should be purged, and
deliberately deferred it until the re-run's results are in — one thing at a time.
Until then the shared store holds confounded rows under a label this effort also
uses, and anything reading it needs to know that.] [2026-09-20: purged, see
*Purging the superseded rows* at the end.]

## Verification 1 — the divisor hypothesis is refuted (2026-09-20)

**done (verified).** About 57 minutes, 9,000 simulations into
`outputs/max_points_v1_results.parquet`, baseline included since the store started
empty. Summary in `outputs/max_points_v1_drs_summary.csv`.

`StrategyMaxPoints` and `StrategyMaxP2PM` now differ in their objective alone, so
this measures what the effort set out to measure.

**The verdict: 0 of 3 seasons positive, `consistent_sign` true, `beats_baseline`
false.** Pooled per-team deltas against the paired baseline:

| Season | Mean | Std err | Mean/se | Median | Per-team SD | Win rate |
|---|---|---|---|---|---|---|
| 2023 | −14.5 | 1.4 | −10.6 | −18 | 52.6 | 41% |
| 2024 | −156.2 | 3.9 | −40.3 | −213 | 150.2 | 18% |
| 2025 | −4.4 | 5.2 | −0.8 | +39 | 203.3 | 58% |

**The hypothesis in `proposal.md` is dead.** It argued that dividing by price
penalises expensive assets a second time on top of a budget cap that already
rations them, so a pure points objective should beat P2PM. It loses in every
season. That is a successful test of a falsifiable claim, not a failed effort.
`proposal.md` annotated in place.

**Fixing the DRS confound changed the answer, which justifies the re-run.** 2023
moved from +104 to −14.5 — its apparent win was entirely the confound. 2024 barely
moved, from −156 to −156.2, so its loss was always the objective. Reporting the
first run would have claimed a two-of-three split where the truth is zero of three.

**The more interesting finding is variance, not the verdict.** In 2025 the strategy
**wins 58% of teams and still loses on the mean**: median +39 against a worst case
of −713. The same shape appears in every season, and the per-team SD against a
fixed reference grows from 52.6 to 203.3. So pure points is not simply worse — it
beats P2PM on most starting teams and loses badly on a minority, and the bad tail
outweighs the frequent small wins. That suggests the divisor is buying **downside
protection**, costing median points and earning it back by not blowing up, which is
close to the opposite of what the proposal assumed it was doing.

**What this does not license.**

- 2025's mean/se of −0.8 is noise. It is recorded as "no difference on the mean,
  with a much wider spread", not as a loss.
- 2023's −14.5 is real at 10 standard errors but small: −0.26%.
- Why 2024 is an order of magnitude worse than the other two is **not** explained.
  It is the most informative open question here.
- n=3 seasons. A consistent sign at n=3 is suggestive, not conclusive.
- **Concentration is not measured.** The variance above is measured; the claim that
  concentration causes it is an inference and nothing more — see *Concentration is
  still an assumption* below.

## Concentration is still an assumption (2026-09-20)

Raised by Alex, and correct. The tail behaviour above was read as the signature of
concentration risk, which R7 predicted. That reasoning has not been tested:

- Whether `StrategyMaxPoints` actually holds a constructor plus both its drivers
  more often than P2PM has **not been counted**.
- Whether the concentrated teams are the ones in the left tail has **not been
  checked**.

Both are measurable. `linear/strategy_odds.py` already defines concentration as the
count of same-constructor driver-driver and driver-constructor pairs, so the metric
exists and does not need inventing. The obstacle is that the results store keeps
only each team's final-race row, which is the snapshot that already produced one
wrong conclusion in this effort; measuring concentration properly means
re-simulating with every race captured.

Until that is done, R7's condition — evidence before constraining — is **not met**,
and the concentration lift stays unjustified rather than justified.

## Purging the superseded rows (2026-09-20)

The confounded run's 4,500 rows were removed from the shared
`backtest_v1` store, on Alex's instruction and after the corrected results were in.
They were labelled `StrategyMaxPoints`, the same label this effort still uses, so
leaving them would have meant a resumed run skipping them as done and a reader
mistaking them for the result.

A copy was taken first, as `backtest_v1_results.parquet.bak_before_purge`, so the
operation is reversible. The checks were stated before the write, not after:

- 18,000 rows before — `backtest_v1`'s 13,500 plus this effort's 4,500 — and 13,500
  after.
- `StrategyMaxBudget`, `StrategyMaxP2PM` and `StrategyZeroStop` each still hold
  4,500.
- Zero `StrategyMaxPoints` rows remain.
- The retained frame is **exactly equal** to the pre-purge frame with those rows
  dropped, by `DataFrame.equals` — which is the check that proves nothing else
  moved, rather than a row count that would pass whatever else had changed.
- Columns, dtypes and `sim_key` uniqueness unchanged; `total_points` sums identical
  either side.

`backtest_v1`'s summary and verdict files were not touched and remain consistent
with the store, since only a label absent from them was removed. This effort's own
results live in `outputs/max_points_v1_results.parquet` and were never mixed in.

## Next — the per-race re-simulation (handoff, 2026-09-20)

> **Done 2026-09-21.** Both open questions below are answered in *The per-race
> re-simulation* at the end of this log. The method described here was followed
> as written, except that it was built as a committed, tested module —
> `backtest/per_race.py` — rather than a one-off, so the evidence that settles R7
> can be re-derived. The full sample was run rather than a slice, which made the
> reconciliation against *Verification* 1 a row-for-row check.

Session closed here with steps 1-4 and *Verification* 1 complete, the suite green at
231, and the working tree clean. Nothing is half-finished in code; what follows is
analysis, not implementation.

**Two open questions, and the argument for answering them in one run.**

1. **Is concentration actually what makes the tail?** R7's condition is unmet — see
   *Concentration is still an assumption* above. Needs counts, not inference.
2. **Why is 2024 an order of magnitude worse?** −156.2 against −14.5 and −4.4, and
   nothing in this session explains it. The single most informative gap.

These plausibly have the same answer, so **one re-simulation capturing every race
serves both**, rather than two separate passes. The store's rows are final-race only
(`run_for_team(...)[-1]` in `backtest/runner.py`), which is what made the per-race
picture unavailable and, twice in this session, invited a wrong conclusion from a
snapshot.

**The method, which worked at small scale here.** The confirmation run for 2024
re-simulated five sampled teams under both strategies and kept every row
`run_for_team` returns, not just the last. Rebuild it by: sampling with
`sample_starting_teams(season, 500, seed=1, band_edges=DEFAULT_BAND_EDGES)`, taking
a slice, building each team with `factory_team_row(sampled.drop(_SAMPLE_COLUMNS)
.to_dict(), starting_race)`, then `pd.DataFrame(run_for_team(strategy, team,
season_data, season, STARTING_RACE))`. Note `factory_team_row` needs the `Race`
object, not the race number. Roughly 0.4 s per team-season, so a few hundred teams
across all races is minutes, not hours — this does not need another overnight run.

**What to measure on it.**

- Concentration per team per race, using `linear/strategy_odds.py`'s definition —
  same-constructor driver-driver pairs plus driver-constructor pairs — so the metric
  matches the constraint that would eventually enforce it.
- Concentration against per-team delta, to test whether the left tail is the
  concentrated teams. That is the claim R7 needs and this session did not make.
- Where in a season the 2024 gap opens, and whether it is one sustained drift or a
  few large races. The five-team confirmation showed two-sided per-race gaps — one
  team's race 8 was +91 and its race 16 −65 — so it is not a simple monotone bleed.
- Whether 2024's severity tracks anything structural: that season's price movements,
  a mid-season constructor switch, or an asset whose rolling points collapsed.

**Which file is which, because two are a character apart.** `outputs/` holds both
runs' summaries and the names do not say which is trustworthy:

| File | Run | Use it? |
|---|---|---|
| `max_points_v1_drs_summary.csv` | corrected, DRS matched | **yes** — this is *Verification* 1 |
| `max_points_v1_summary.csv` | first attempt, confounded | **no** — objective and DRS varied together |
| `max_points_v1_results.parquet` | corrected, 9,000 rows | yes, the only per-team store for this effort |

The confounded run's *rows* were purged from the shared store, but its summary CSV
was left on disk and is the same confusion risk one level up. Delete it, or rename it
with a `confounded_` prefix, at the start of the next session. [Resolved 2026-09-20:
deleted, along with its companion `max_points_v1_summary_verdict.csv` — which was the
more dangerous of the two, since it stated "2 of 3 seasons positive", the conclusion
this session retracted. Only the corrected artefacts remain, so the table above now
describes one surviving row and two absent ones.]

**Two decisions left open deliberately.** [Both resolved 2026-09-20, before the
session closed — see the notes on each.]

- **The `.bak_before_purge` copy** of the shared store is still in `outputs/`. Keep
  it until the next session is satisfied the purge caused no surprise, then delete.
  [Resolved 2026-09-20: deleted. Before deleting, the purge was re-verified — the
  live store is 13,500 rows across the three expected labels, `sim_key`s unique, and
  **exactly equal** to the backup with the `StrategyMaxPoints` rows dropped. The
  purge is therefore not reversible from here; it is reproducible instead, since
  nothing was removed that a re-run could not regenerate.]
- **Steps 5-8, the DRS helper**, are untouched and their design is settled in
  `requirements.md` R3-R5 and `plan.md`, *The helper's shape*. They now have a
  properly matched control to be measured against, per step 4's superseding note in
  `plan.md`. Whether to do the analysis above first or the helper first is a genuine
  choice; the analysis is cheap and may change what the coefficients are for, which
  argues for it going first.

**One thing not to redo.** The `StrategyMaxPoints` label is now clean in both stores
— purged from the shared one, and its own store holds only the corrected run. A
future run under that label in `outputs/max_points_v1_results.parquet` **will** be
skipped as already done, so any changed behaviour needs a new label or a new store.

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

## The per-race re-simulation (2026-09-21)

**done (verified).** 9,000 simulations, 210,000 rows, 63 minutes, into
`outputs/max_points_v1_per_race.parquet`. Built as `backtest/per_race.py`
(commits `a81d67d`, `0e8b347`, `9b46da9`, `992ba0d`); nothing in `races/`,
`linear/`, `import_data/` or `scripts/` was touched and `run_for_team` was used
unchanged. Suite green at 261.

This is the run the previous session handed off. It answers both of its open
questions, and the answer to the first is **no**.

### The run reconciles exactly with *Verification* 1

Sampled on the same seed and edges, so each simulation's final race must equal
its stored row from *Verification* 1. All 9,000 keys matched, none on either
side only, and **0 of 9,000 rows differ** on `race`, `total_points`,
`total_value`, `unused_budget`, `drs_driver`, `D1`–`D5`, `C1` or `C2`.

This is the check that would have caught a moved sample, a changed engine or a
changed strategy between the two runs; it was stated before the run, not after.
I ran it — it is not a reasoned claim.

### R7 is refuted: concentration is not what makes the tail

Two separate findings, both against the prediction.

**`StrategyMaxPoints` is not the more concentrated strategy.** Over every
team-race:

| Season | Label | Mean conc. | Median | Share > 0 | Mean full stacks | Share stacked |
|---|---|---|---|---|---|---|
| 2023 | P2PM | 3.15 | 3 | 99.3% | 0.587 | 54.8% |
| 2023 | MaxPoints | 3.24 | 4 | 99.2% | 0.630 | 59.1% |
| 2024 | P2PM | 1.97 | 2 | 97.5% | 0.065 | 6.5% |
| 2024 | MaxPoints | 1.78 | 2 | 97.4% | **0.007** | **0.7%** |
| 2025 | P2PM | 2.23 | 2 | 98.2% | 0.186 | 18.5% |
| 2025 | MaxPoints | 2.11 | 2 | 97.1% | 0.183 | 18.2% |

It is more concentrated in 2023 only, and marginally. In 2024 — **the season it
loses by an order of magnitude more than the others** — it holds a constructor
with both its drivers in 0.7% of team-races against the baseline's 6.5%, nearly
ten times less. The proposal predicted a pure-points objective would take the top
constructor and both its drivers. In the season that most needed explaining, it
does the opposite of that.

**Concentration is mildly associated with *better* outcomes, not worse.**
Spearman correlation against each team's season delta, and the bottom decile of
delta against the rest:

| Season | ρ(conc., delta) | ρ(stacks, delta) | Bottom decile conc. | Rest |
|---|---|---|---|---|
| 2023 | +0.159 | +0.399 | 3.10 | 3.26 |
| 2024 | +0.064 | +0.168 | 1.77 | 1.78 |
| 2025 | +0.281 | +0.167 | 1.95 | 2.13 |

Every correlation is positive and the worst-performing teams are the *less*
concentrated ones in all three seasons. The tail is not made of concentrated
teams.

**So R7's condition is met, and it clears the backlog item rather than
justifying it.** The requirement said measure before constraining. Measured: the
concentration lift has no support from this effort, and the variance reported in
*Verification* 1 needs a different explanation. The earlier reading — that the
tail "looks like concentration risk" — was inference, is now tested, and was
wrong. `requirements.md` R7 and the BACKLOG entry annotated in place.

### Starting teams barely survive the race-4 chip

Not asked for, and the most surprising thing in the run. Distinct team line-ups
held at each race, out of 1,500 starting teams:

- 2023: 1,500 → 1,226 (race 2) → 272 (race 3) → **1** (races 4 and 5).
- 2024: 1,500 → 1,243 → 408 → 6.
- 2025: 1,500 → 1,254 → 435 → 10.

Both strategies, near-identically. R2's copied race-4 unlimited-moves block lets
the LP rebuild the whole team, and it rebuilds every starting team into the same
one. So essentially all of a season's per-team variance is created in races 1–3
and then carried, not generated through the season.

This bears on the whole back-test design and is recorded for `backtest_v1` as
much as for here: sampling 500 starting teams a band buys far less independent
information after race 4 than the sample size suggests.

### 2024 is a sustained drift, and is still not explained

`mean_cumulative_delta` crosses zero at race 5 and never returns; 16 of the 23
scored races are negative. It is not a few bad weekends — the worst single race
is −48.6 and there are positive spikes of +36.3, +28.7 and +25.7 — and it is not
a collapse onto one team, since 2024 holds 6–19 distinct line-ups where 2023
holds 1–3.

What it is not, measured: not concentration (above), and not budget allocation
between the slot types. Averaged over races 4 onwards, `StrategyMaxPoints` spends
45.1% of team value on constructors against the baseline's 44.0% — and is worse
on **both** halves, scoring 121.0 constructor points against 124.2 and 38.2
driver points against 43.7.

2024 is the season where drivers scored least: constructors returned 74–76% of
all points from 44–45% of the spend, against 56–57% of points in 2023. A rolling
points sum over a compressed driver field discriminates between drivers very
little, where dividing by price still separates them. **That is a hypothesis, not
a finding** — it is consistent with the numbers above and has not been tested.

### The DRS nomination ceiling, measured while the data was to hand

`Team.get_drs_points` pays the nominated driver's actual points, so perfect
hindsight would nominate whichever held driver actually scored most. The gap
between that and what each strategy's rule actually collected is the ceiling on
any nomination rule:

| Season | Baseline DRS points | Perfect hindsight | Ceiling | % of season | Rule already optimal |
|---|---|---|---|---|---|
| 2023 | 816 | 1,043 | **+226** | 4.1% | 60.3% of team-races |
| 2024 | 591 | 694 | **+103** | 2.3% | 70.5% |
| 2025 | 774 | 872 | **+98** | 2.0% | 76.2% |

Set against *Verification* 1's deltas of −14.5, −156.2 and −4.4, DRS nomination
is a larger lever than the objective change this effort tested.

**But modelling DRS inside the objective cannot collect any of it.** For a fixed
team the LP maximises `Σ r_i·x_i + Σ r_i·y_i` subject to `Σ y_i = 1` and
`y_i ≤ x_i`, so its optimal `y` is `argmax r_i` over the selected drivers. When
`r` is `Points Cumulative (3)` that is **exactly** what
`StrategyMaxP2PM.get_drs_driver` already returns (`linear/strategy_p2pm.py:47-71`).
In matching units the in-objective nomination and the post-hoc one are the same
driver, by construction. The entire value of R3–R5 is therefore the **selection**
feedback — that the objective will pay more for a team containing one strong
driver — and none of it is nomination.

This is reasoned from the LP's structure and the existing code, not run. It is
the argument that should be checked first if R5 is picked up.

**Reproducing the ceiling.** It is not committed code. From
`outputs/max_points_v1_per_race.parquet`, for each row take the nominated
driver's points where `drs_driver` matches one of `D1`–`D5`, and the
highest-*priced* held driver's points where it does not — that second case is
`Team.get_drs_points`'s fallback and occurs only at race 1, where no strategy has
run yet, in exactly 9,000 of 210,000 rows. "Perfect" is the maximum of `D1_pts`
through `D5_pts`. Sum each per simulation, then average per label and season.

## Next session — start here (handoff, 2026-09-21)

Session closed here at Alex's request, with the working tree clean, the suite
green at 261 and everything pushed. **No decision on next steps was taken** — the
options are laid out below and are deliberately still open.

This section is written plainly and from the beginning, because the detail above
assumes the reader followed the whole session. Nothing here is new; it is the
same findings in fewer terms.

### The words you need

- **P2PM** — the strategy picking a live 2026 team. It scores an asset by
  points² ÷ price, so it prefers good value rather than the highest scorer.
- **MaxPoints** — the strategy this effort built. Same machinery, but it scores
  an asset by its recent points alone, ignoring price. It is the test of whether
  P2PM's division by price was a mistake.
- **DRS** — each race, one driver on your team scores twice. The strategy
  nominates which one, after the team is chosen.
- **Concentration** — how much of your team sits with one constructor. Holding a
  constructor *and* both of its drivers is the extreme case, and the proposal
  predicted MaxPoints would do it and get burned by it.

### What happened before this session

`StrategyMaxPoints` was built and back-tested. **It lost in all three seasons**,
so the idea that P2PM's price divisor was hurting it is dead. But the losses were
strange: in 2025 MaxPoints beat P2PM on 58% of starting teams and *still* lost on
average, because a few teams lost badly. That looked like concentration risk. The
previous session was explicit that it had not actually checked, because the saved
results only kept each team's last race and so could not show what a team held
during the season.

### What this session did

Re-ran all 9,000 simulations keeping **every race**, not just the last — 210,000
rows, 63 minutes. Built as a proper tested module, `backtest/per_race.py`, so the
numbers can be re-derived. Nothing in the core engine was touched.

### Finding 1 — the run is trustworthy

Each team's final race here matches its stored row from the earlier back-test
exactly: 9,000 of 9,000, zero differences. Same teams, same points, same
everything. So the new detail sits on top of results we already trusted.

### Finding 2 — the concentration theory is wrong

It was the main question, and the answer is no.

- MaxPoints is **not** the more concentrated strategy. In 2024 — the season it
  loses worst by far — it holds a constructor plus both its drivers in 0.7% of
  team-races, against P2PM's 6.5%. It concentrates *ten times less* in the season
  it does worst.
- More concentration goes with **better** results, not worse, in all three
  seasons. The worst-performing tenth of teams is *less* concentrated than the
  rest.

So the bad tail is caused by something else, still unknown. The backlog item that
was waiting on this evidence does not get it, and has been annotated rather than
dropped — it was always a code-tidiness argument as well as a risk one.

### Finding 3 — the starting team stops mattering by race 4

Not something anyone asked for, and possibly the most useful thing here.

All 1,500 different starting teams end up holding the **same single line-up by
race 4** in 2023 (6 in 2024, 10 in 2025), under both strategies. The race-4 rule
that allows unlimited transfers lets the optimiser rebuild from scratch, and it
rebuilds everyone into the same team.

So whatever separates one starting team from another is decided in races 1–3 and
then carried to the end. This matters beyond this effort: the whole back-test
design samples 500 starting teams per value band on the assumption they are
meaningfully different seasons, and after race 4 they largely are not.

### Finding 4 — DRS nomination is worth real points, but not the way the plan assumed

Measured how many points a *perfect* DRS pick would have scored versus what the
current rule actually scored: **+226 in 2023, +103 in 2024, +98 in 2025**. The
current rule already picks the best available driver 60–76% of the time, so those
numbers are the value of the remaining 24–40%.

For scale, the whole objective change this effort tested was worth −14, −156 and
−4. So *how DRS is nominated* is a bigger lever than *what the objective
optimises*.

**The catch.** The proposal's plan was to move the DRS choice inside the
optimiser. But if you give the optimiser the same numbers the current rule uses,
it picks the same driver — that follows from how the maths is set up, and the one
exception that could break it never happens in 210,000 races. So moving DRS
inside the optimiser collects **none** of that +98 to +226. Its only real effect
is changing which *team* gets picked in the first place, which is a smaller and
different benefit than the proposal claimed.

This is a reasoned argument from the code and the maths, **not** something that
was run. It is the first thing to check if that route is taken.

### The four options, and the trade-off

Alex proposed testing P2PM with DRS moved into the optimiser. That is option B.
No option is started; this is a genuine choice.

**A — improve how DRS is nominated, leave everything else alone.** Chase the +98
to +226 directly by changing the rule that picks the DRS driver. Smallest change
available: one method on a new subclass, no edit to the shared `StrategyBase`, no
multi-hour verification gate, and it tests on the harness that already exists.
The obvious things to try as the criterion are betting odds, which the odds
strategy already loads, or `fast_f1`'s `AggregateRank`, which is built, tested,
and currently connected to nothing.
*Risk:* perfect hindsight is not achievable — the rule only knows what happened
before the race — so the realistic gain is some unknown fraction of the ceiling.

**B — P2PM with DRS inside the optimiser, as Alex proposed, but respecified.**
The plan's R5 says to feed the optimiser P2PM values. That would make the DRS
pick *worse* than today's rule, because today's rule uses recent points, which
predicts a points payoff better than a value ratio does. It would need to use
points instead — and then, per Finding 4, the nomination is unchanged and the
test measures team selection only. Also needs the shared `StrategyBase` edited
first, which carries a mandatory before-and-after verification (R6) that this
session's data now makes both cheaper and stronger.
*Risk:* several steps and a long gate to measure what is now expected to be a
small effect.

**C — explain 2024 first.** −156 against −14 and −4 is the largest unexplained
number in the effort. Untested hypothesis: 2024's drivers scored so little
(constructors gave 74–76% of all points from 44–45% of the spend) that ranking
drivers on recent points barely separates them, while dividing by price still
does. Cheap to test on data already on disk.
*Risk:* diagnostic only — it explains a result rather than improving anything.

**D — close `max_points_v1`.** Its question was "is the price divisor a
mistake?", answered no, and R7 is now closed too. The DRS work could restart as
its own effort with a corrected premise: a selection lever worth a little, not a
nomination lever worth 200.

**Nothing blocks any of these.** They are not sequential, except that B needs
steps 5 and 6 of `plan.md` first.
