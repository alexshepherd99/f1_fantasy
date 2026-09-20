# max_points_v1 — Log

Execution log for the max_points_v1 effort. Newest entries at the bottom.
Requirements and plan live alongside in `requirements.md` and `plan.md`; the
design rationale predates both and is in `proposal.md`.

## Status summary

- Effort picked up off the backlog 2026-09-20. Step 1 in progress; no code
  written yet.

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
