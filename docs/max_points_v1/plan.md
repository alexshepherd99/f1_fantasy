# max_points_v1 — Plan

**Status**: draft for review, 2026-09-20. Requirements: `requirements.md`,
agreed 2026-09-20. Design rationale: `proposal.md`. Not yet implemented — no
code exists.

TL;DR — Add `StrategyMaxPoints` (rolling points objective, no DRS, no
coefficients) and back-test it against P2PM to test the divisor hypothesis. Then
add an opt-in DRS helper to `StrategyBase`, verify `StrategyMaxP2PM` is
bit-identical, and give the helper two callers. Then the tunable coefficients,
one per commit, and the sweep. `linear/strategy_p2pm.py` is never edited.

## Design

**New modules.**

- `linear/strategy_max_points.py` — `StrategyMaxPoints` (R1, R2).
- `linear/strategy_p2pm_drs.py` — `StrategyMaxP2PMDrs` (R5).
- The DRS helper goes into the existing `linear/strategy_base.py` (R3).

Tests go in `tests/test_strategy_max_points.py` and
`tests/test_strategy_p2pm_drs.py`, with the helper's own tests in a new
`tests/test_strategy_base_drs.py` rather than appended to any existing file
(R6 forbids editing one).

**Reused unchanged, no edit needed.** `factory_strategy` takes
`strategy: type[StrategyBase]` and builds it from generic keywords, so a new
strategy needs **no factory change** — confirmed by reading
`linear/strategy_factory.py`, which names no strategy. `Points Cumulative (3)`
is already in `derivs_assets` for drivers and constructors, and
`StrategyMaxP2PM.get_drs_driver()` already reads it, so the derivation is
proven present in production data.

**`backtest/cli.py`'s `STRATEGIES` dict gains each new strategy.** That is
`backtest/`, not a core module.

### The helper's shape

Settled in discussion 2026-09-20, over four rounds. The conclusion differs from
`proposal.md`, which is annotated in place.

**Why the proposal's placement does not fit.** It has the helper adding
`Σ y_i = 1` and `y_i ≤ x_i` to `self._lp_constraints`. The *timing* is right —
`execute()` applies that dict after `get_problem()` returns
(`linear/strategy_base.py:258`). But **the dict holds exactly one constraint per
`VarType` key**, and all four existing entries are single constraints, which
`execute()`'s `for constraint in self._lp_constraints.values(): model +=
constraint` loop assumes. `y_i ≤ x_i` is one constraint per driver, about 20 of
them, and the single `VarType.DrsDriver` key cannot hold those without either a
composite-key convention the dict has never carried or an edit to `execute()` —
the one method every strategy runs through, and the last place to widen a change
that R6 promises is behaviour-neutral.

**The helper is pure.** It mutates nothing and returns two values: the objective
term, and the constraints as a name-keyed dict.

```python
def get_drs_objective_term(
    self, driver_values: dict[str, float]
) -> tuple[LpAffineExpression, dict[str, LpConstraint]]:
```

The base class already declines to own the objective — that is why the term is
returned rather than set. It does not own the `problem` either, since the
subclass constructs it, so returning the constraints applies the same rule
consistently instead of stopping halfway. It also keeps the helper testable
without building and solving a model: a test can assert there are
`n_drivers + 1` constraints, and that the sum constraint is `== 1` and not
`<= 1`, directly on the return value.

**The call site is two lines.** `LpProblem.extend()` accepts a
`dict[str, LpConstraint]` and names each constraint with its key — verified by
reading the installed PuLP source, not from memory:

```python
drs_term, drs_constraints = self.get_drs_objective_term(driver_points)
problem.extend(drs_constraints)
problem += lpSum(points_drivers + points_constructors) + drs_term
```

The third line is the objective line the caller writes regardless, so the
DRS-specific cost is two lines. Named constraints matter: dict-routed ones are
auto-labelled `_C1`, `_C2`, and when a model comes back infeasible
`drs_owned_HAM@MER` says which rule bit.

One caveat on `extend`: its dict branch assigns into `self.constraints` directly,
bypassing `addConstraint`'s validation. The constraints here are built in-house
by the helper, so they are well-formed by construction, but it is a real
difference from `problem += constraint, name`.

**No convenience wrapper.** A second method attaching the constraints and
returning the term — `add_drs_to_problem(problem, driver_values)` — was proposed
and rejected. It saves exactly one line per caller, at two callers, against a new
public method needing a docstring, type annotations and its own tests: more code
than it removes. It also cannot do the whole job, since it cannot touch the
objective, so the call site is never one line either way; and two public methods
differing only in whether they mutate make "does calling DRS change my problem?"
depend on which one was called. **Revisit at three or four callers** — the
proposal notes `Σ y_i = k` generalises to the 3x Boost chip, and a FastF1
strategy might want DRS too — or if attaching ever needs more than one `extend`.

**The read-back guards instead.** What the wrapper was really buying was
unforgettability. A cheaper guard belongs in the read-back companion every caller
must use anyway:

```python
def get_drs_nominee(self) -> str:
    """Return the driver whose DRS binary solved true, checking they are on the team."""
    for driver, y in self._lp_variables[VarType.DrsDriver].items():
        if y.value() > 0.5:
            if self._lp_variables[VarType.TeamDrivers][driver].value() <= 0.5:
                raise ValueError(
                    f"DRS driver {driver} is not in the selected team - were the DRS constraints added?"
                )
            return driver
    return ""
```

Both values are already on `self._lp_variables` after the solve, so it is free,
and it converts a silently inflated score into a raised error naming its own
cause (R4).

### Call ordering

The helper needs `VarType.TeamDrivers`, which `initialise()` creates, so it must
be called **after** `initialise()` — meaning from inside `get_problem()`, which
`execute()` calls second. The read-back companion must be called only after the
solve, like `StrategyMaxP2PM.get_drs_driver()` already is.

## Steps

Each step is one commit, TDD throughout: the test is written and **seen to
fail** before the implementation. Suite green before starting and after
finishing each.

### Step 1 — Effort docs

`requirements.md`, `plan.md`, `log.md` created; `BACKLOG.md`'s `max_points_v1`
row flipped to `in progress` and its *Optimise rolling points directly* pointer
entry left as the pointer it already is. `proposal.md` is **not** rewritten —
where requirements supersede it, it gains a dated inline marker.

### Step 2 — `StrategyMaxPoints` at neutral defaults (R1, R2)

- Objective: `Σ pts₃ · x_i` over drivers and constructors, missing values
  filled `0.0`.
- Race-4 `max_moves` reset copied from `StrategyMaxP2PM.__init__` (R2).
- No DRS override, so `get_drs_driver()` returns `""` and `Team` falls back to
  the highest-priced driver. That is the *neutral* case and the control.
- Tests: the objective picks the highest-rolling-points affordable team; an asset
  with no derivation entry contributes zero rather than raising; the budget cap,
  team-size and max-moves constraints still bind; race 4 permits a full-team
  rebuild and race 3 does not.

### Step 3 — Register in the back-test CLI

`StrategyMaxPoints` added to `backtest/cli.py`'s `STRATEGIES`. Test asserts it
is selectable by name.

### Step 4 — The divisor hypothesis, measured (*Verification* 1)

Run the back-test. This answers the proposal's central falsifiable claim before
any further code is written, so a negative result can redirect the effort rather
than being discovered after the coefficients are built.

> **Superseded 2026-09-20, after the run.** The comparison was confounded:
> `StrategyMaxPoints` nominated no DRS driver, so `Team` fell back to the
> highest-priced one while P2PM nominated on rolling points. The run measured the
> objective *and* DRS nomination together, and its numbers say nothing about the
> objective. Step 4 therefore splits:
>
> - **4a — match P2PM's DRS nomination.** `get_drs_driver` copied verbatim into
>   `StrategyMaxPoints`, so the two strategies differ in their objective alone.
> - **4b — re-run *Verification* 1** against its own store, since the shared one
>   already holds rows under the `StrategyMaxPoints` label that `simulate_sample`
>   would skip.
>
> This also improves the experiment the rest of the plan runs. Step 4a's strategy
> is a proper control — points objective, post-hoc DRS nomination, mirroring P2PM —
> which gives three rungs instead of two: P2PM, then `StrategyMaxPoints` isolating
> the **objective**, then step 7's in-objective DRS isolating the **DRS
> modelling** against a matched control rather than against a tangle of both.

### Step 5 — The DRS helper on `StrategyBase` (R3)

Added with **no caller**. Tests construct a throwaway subclass that calls it, so
the helper is exercised without any production strategy opting in.

- `Σ y_i = 1`, not `≤ 1` — the game requires the boost to be assigned, and `≤ 1`
  would drop it whenever every selected driver's indicator is negative, which a
  three-race window with penalties permits.
- Coefficient is `r_i`, not `2·r_i`: `Team.update_points()` sums all five drivers
  then *adds* `get_drs_points()` on top, so DRS is exactly one extra copy.
- Read-back at `> 0.5`.
- Tests: the nominee is always on the selected team (R4); `Σ y_i = 1` holds; a
  driver missing from `driver_values` is treated as `0.0`; the DRS term changes
  the *team*, not just the nomination — the proposal's four-driver worked example
  is a direct test case, since it picks `{STAR, CHEAP}` only when DRS is
  modelled.

### Step 6 — Zero-change verification (*Verification* 2, R6)

Gate on the `StrategyBase` edit. Must pass before step 7. Not a code commit.

### Step 7 — `StrategyMaxPoints` calls the helper

Passing the rolling points it already optimises. `get_drs_driver()` overridden
to return the helper's read-back.

### Step 8 — `StrategyMaxP2PMDrs` (R5)

Registered in `backtest/cli.py` too. Test asserts `StrategyMaxP2PM` itself is
untouched by subclassing it — that the parent's `get_drs_driver()` still returns
the rolling-points nominee.

### Step 9 — Back-test the DRS-aware pair (*Verification* 3)

Both DRS strategies against the P2PM baseline. Report concentration behaviour
here (R7): whether a pure-points objective takes a constructor plus both its
drivers, and whether it costs points.

### Steps 10+ — The tunable coefficients (R8) and the sweep (R9)

One coefficient per commit, each defaulting neutral, with a back-test sweep per
coefficient. Ordering deferred until *Verification* 1 and 3 have run — which
lever matters depends on what they show, and committing to an order now would be
guessing.

## Verification

Separate from the steps, because these need real multi-hour runs rather than the
test suite. A step reaches **done (dev)** without them; a *Verification* item
reaches **done (verified)**. Work continues past an uncleared one — it blocks only
the claim that its step is verified.

**Verification 1 — the divisor hypothesis** (after step 3)

- `PYTHONPATH=. venv/bin/python -m backtest.cli --strategies StrategyMaxPoints`
- About 2.5 hours on `backtest_v1`'s measured 0.38 s a simulation, 13,500
  simulations across three seasons and three bands. Resumable.
- Report per season and band, with the pooled verdict. State plainly whether the
  divisor hypothesis survived (R10) — a null result is a real finding here, not a
  failure of the run.

**Verification 2 — zero change to `StrategyMaxP2PM`** (gate on step 5, R6)

- A fixed-seed `backtest_v1` run's `StrategyMaxP2PM` rows, before and after the
  `strategy_base.py` edit, compared for exact equality.
- The live `run_single_team.py` configuration replayed through its functions —
  never its `__main__` — to an identical team, DRS nomination and points per
  race.
- Full suite green with no existing test file edited.
- **A green suite alone does not clear this gate.**

**Verification 3 — the DRS-aware comparison** (after step 8)

- `StrategyMaxPoints` and `StrategyMaxP2PMDrs` against the baseline.
- Includes the R7 concentration reporting.

**Verification 4 — the coefficient sweeps** (with steps 10+)

- One sweep per coefficient, all grid points for a season in one process (R9).
- Plateau-versus-peak judgement recorded per coefficient, including where the
  answer is "neutral, no evidence it helps".

## Risks

- **Race 1 is degenerate.** Every indicator is zero, so the LP tie-breaks
  arbitrarily. The hash-order fix (`534d1a9`) made that tie-break deterministic
  across processes, so it is reproducible, but it is still arbitrary. It affects
  the P2PM baseline identically, so the pairing is not biased by it.
- **Constructors may starve the driver slots.** Measured over 2026 races 5–11,
  constructors return about 2.9x the rolling points per £ that drivers do. Slot
  counts are fixed so the LP cannot buy more of them, but it can buy the two most
  expensive. R8's constructor scaling coefficient is the lever; the DRS term
  partially counteracts it. Expected to show up in *Verification* 1.
- **The back-test cost is the schedule.** Four verification runs at roughly 2.5
  hours each, on a memory-constrained box. `backtest_v1` measured about 196 MB
  peak for a full run, so memory is not the binding constraint — wall clock is.
- **Step 5 is the only irreversible-feeling change**, since it edits a file every
  strategy inherits from. *Verification* 2 exists precisely because the suite
  cannot see the failure mode that matters.
