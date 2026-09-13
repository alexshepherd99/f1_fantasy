# max_points_v1 — Proposal

**Status**: proposed, not started. Raised 2026-07-30. Back-test requirements
moved to `docs/backtest_v1/requirements.md` on 2026-09-13.

Build a team selection strategy that optimises the three-race rolling *points*
total directly, rather than the points-per-price ratio `StrategyMaxP2PM` uses,
and model the DRS x2 boost inside the LP objective instead of applying it after
the team is chosen.

## What `StrategyMaxP2PM` is actually doing

The objective (`linear/strategy_p2pm.py:36-43`) is

```
maximise  Σ (pts₃ · |pts₃|) / price₃
```

over selected assets, where `pts₃` is the three-race rolling points sum shifted
to exclude the current race, and `price₃` is the *cumulative* price over the same
window (`import_data/derivations.py:94-118`) — roughly 3x current price, though it
drifts for assets whose price is moving fast.

Two separate things are bundled in there:

1. **A points forecast** — "recent form predicts the next race". That is the
   honest signal.
2. **A price penalty** — dividing by price turns it into a value-for-money score
   rather than a points score.

The squaring is a hand-tuned dial between them. PPM (`k=1`) picks eccentric cheap
drivers; P2PM (`k=2`) pulls back toward absolute scorers. Raw rolling points is
the far end of that same dial with the divisor dropped — not a different family
of strategy, but the untested extreme of one already in the repo.

**The hypothesis worth testing.** The LP already carries a hard budget cap
(`linear/strategy_base.py:223`). Dividing by price penalises expensive assets a
second time, on top of a constraint that already rations them. If that is right,
a pure points objective should beat P2PM and the divisor is a hedge left over
from before the constraint was trusted. It is falsifiable and the back-test is
the test.

**The data already exists.** `Points Cumulative (3)` is computed for drivers and
constructors alike in `helpers.load_with_derivations` and threaded into
`derivs_assets` by `linear/strategy_factory.py:31-37`. `StrategyMaxP2PM` already
reads it for `get_drs_driver()` (`linear/strategy_p2pm.py:53`). A v1 strategy is
roughly `StrategyMaxP2PM` with a different derivation name.

## Modelling the DRS boost in the objective

No strategy currently models DRS in its objective. `Team.get_drs_points()`
(`races/team.py:123-142`) adds the nominated driver's points a second time *after*
the team is picked. `StrategyMaxP2PM` overrides `get_drs_driver()` to nominate the
highest-rolling-points driver, but that is a post-hoc pick over an already-chosen
five — the selection itself is DRS-blind.

The true scoring function is `Σ pts_i + max over selected drivers of pts_i`. That
linearises without a `max` operator:

```
y_i ∈ {0,1}          # driver i carries the DRS boost

Σ_i y_i = 1          # exactly one driver carries it
y_i ≤ x_i    ∀i      # and only a driver actually owned

maximise  Σ_i r_i·x_i  +  Σ_i r_i·y_i
```

where `x_i` are the existing driver selection binaries
(`VarType.TeamDrivers`) and `r_i` is the rolling-points indicator — a **constant**,
known before the solve.

**Why no `max` is needed.** The constraints do not force `y` onto the best driver;
they permit it on any selected driver. The objective direction does the rest. Hold
`x` fixed: the second sum is "choose one selected driver and collect its `r_i`",
and a maximising solver takes the largest. Every other placement is feasible but
strictly worse, so the optimum coincides with the max. Machinery is only needed
when the objective pushes *against* a max — minimising a max, or a max inside a
constraint — where the epigraph trick and big-M become necessary. Maximising a max
is the free direction. And because `r_i` is a constant, `r_i·y_i` stays linear; a
variable indicator would be a variable-times-variable product and need
linearising.

**Why `y_i ≤ x_i` is load-bearing.** Binary lower bounds make `x_i = 0` force
`y_i = 0`, while `x_i = 1` leaves `y_i` free — material implication,
`y_i = 1 ⟹ x_i = 1`. Without it the solver would park `y` on the best driver in
the whole field: the DRS term would become the same constant for every candidate
team and stop influencing selection at all, and `get_drs_driver()` would return a
driver not on the team. That second failure is the dangerous one —
`Team.get_drs_points()` guards with `if self.drs_driver in race.drivers`
(`races/team.py:129`), which checks the driver is *in the race*, not that the team
*owns* them, so an unowned nominee's points would be silently added to the score.
A test asserting the nominated DRS driver is in the selected team is warranted;
that guard will not catch it.

**It changes the team, not just the pick.** Pick 2 drivers, budget £40:

| Driver | `r_i` | Price |
| --- | --- | --- |
| STAR | 100 | £30 |
| MID_A | 65 | £20 |
| MID_B | 65 | £20 |
| CHEAP | 25 | £10 |

DRS-blind: `{MID_A, MID_B}` scores 130 and wins over `{STAR, CHEAP}` at 125.
DRS-aware: `{MID_A, MID_B}` scores 130 + 65 = 195, `{STAR, CHEAP}` scores
125 + 100 = 225 and wins. Post-hoc assignment would have nominated the same driver
in each case but never found the second team. The DRS term systematically rewards
concentrating budget into one strong driver, which mirrors how the game scores.

Implementation details worth not re-deriving:

- **The coefficient is `r_i`, not `2·r_i`.** `Team.update_points()` sums all five
  drivers then *adds* `get_drs_points()` on top, so DRS contributes exactly one
  extra copy.
- **`Σ y_i = 1`, not `≤ 1`.** The game requires the boost to be assigned. With
  `≤ 1` the solver would drop DRS entirely when every selected driver's indicator
  is negative (possible with penalties over a three-race window).
- **Index `y` over the same set as `x`.** `get_team_selection_dict()`
  (`linear/strategy_base.py:180`) builds the driver binaries over available ∪
  current-team, so unavailable-but-owned drivers are present at
  `COST_PROHIBITIVE`. Those have no derivation entry and, following P2PM's
  existing fill, get `r_i = 0.0`.
- **Read back with a tolerance** — `y_i.value() > 0.5`, not `== 1`; CBC returns
  floats.
- **It generalises for free.** `Σ y_i = k` selects the top *k* selected drivers by
  the same argument — that is how the 3x Boost chip would be modelled, if chips
  ever come into scope.

This also subsumes the *bias the objective towards getting P1 right* concern in
the backlog's *Build a strategy on the FastF1 indicators* item, and does it better
than reshaping a rank curve: it models the actual mechanic that makes P1 worth
more, rather than hand-fitting a coefficient to approximate it.

## Failure modes, and a tunable coefficient for each

Every coefficient defaults to the value reproducing the unbiased objective, so the
untuned case stays reachable as the comparison baseline.

- **Constructors will eat the budget.** Measured over 2026 races 5-11:
  constructors average 88.7 rolling points at 16.8 price, drivers 33.1 at 13.5 —
  about 2.9x the points per £. Slot counts are fixed at 5 and 2 so the LP cannot
  buy *more* constructors, but it will buy the two most expensive and starve the
  driver slots. P2PM has this too, and worse (squaring makes it roughly 7x); the
  2026 team log shows it consistently holding MER/FER. Neither strategy exposes it
  as a choice. **Lever:** a scaling coefficient on the constructor term,
  default 1.0. The DRS term partially counteracts it.
- **The budget will always saturate.** Rolling points are effectively monotone in
  price, so unlike P2PM there is no implicit reason to leave change. Unused budget
  is fully retained here (`Team.total_budget` = value + unused) and has real option
  value against price rises, but is not scored. **Lever:** a bonus coefficient on
  the existing `VarType.UnusedBudget` variable, default 0.0.
- **Price momentum deserves to be a term, not a divisor.** If part of what the
  P2PM divisor buys is "cheap assets appreciate", state it explicitly. **Lever:** a
  separate Δprice term over the window, tunable independently of the points term,
  default 0.0.
- **Concentration risk gets worse.** README's defence is that the cost cap
  mitigates it, which is much weaker when the objective actively wants expensive
  assets — pure points will happily take the top constructor and both its drivers.
  This likely makes the backlog item *Lift concentration calculation into
  `StrategyBase`* a prerequisite rather than a nice-to-have.
- **Early races are degenerate.** Race 1 has every indicator at zero and the LP
  tie-breaks arbitrarily; races 2-3 run on a partial window. Same rationale as
  P2PM's race-4 unlimited-moves reset (`linear/strategy_p2pm.py:17-20`), which
  argues for lifting that behaviour somewhere shared rather than copying the block.
- **Rolling sum vs mean.** `fillna(0).shift(1).rolling(3).sum()` scores a driver
  who missed a race as having zeroed it, and keeps them depressed for three races
  after returning. Defensible for a "who will score next" signal, clearly wrong for
  a mid-season debutant. Decide which effect is being accepted.

Lower priority: recency weighting (a flat three-race sum weights t-3 as much as
t-1; exponential decay or 3/2/1 weights is a one-line derivation change with a
parameter that back-tests at "flat"), and transfer hysteresis (`max_moves` is a
hard cap with no cost to using it, so the strategy churns on indicator noise).

## Tuning the coefficients

**Paired comparison and its limits** — per-team deltas against a baseline, the
season as the unit of replication, and requiring the same sign in every season:
moved to `docs/backtest_v1/requirements.md` (R2, R7, R8). One tuning-specific
consequence stays here:

- **Prefer plateaus to peaks.** Flat across α ∈ [0.7, 1.3] with a mild peak at 0.9
  → take 1.0. A sharp spike is fitted to three seasons and will not survive 2027.
  The shape of the sweep is more informative than its argmax.

**Protocol** — coordinate descent, coarse grid, one coefficient per commit:

1. All coefficients neutral. This is the null hypothesis and must stay reachable.
2. Sweep one over ~5 coarse values. Lock in a value, or lock in "neutral, no
   evidence it helps" — a perfectly good and probably common outcome.
3. Next coefficient.
4. One final 2D check on the **DRS term against the constructor scaling
   coefficient** — both move budget between driver and constructor slots, in
   opposite directions, and are the pair coordinate descent most plausibly misses.

Do not grid-search four dimensions: 5⁴ full back-tests is not something this box
will do, and with n=3 seasons it would be fitting noise. Leave-one-season-out
(tune on two, measure on the third, rotate) is the honest validity check if one is
wanted — weak at n=3, but the difference between "we tuned it" and "we tuned it
and checked it generalised once".

**Cost management** — a fixed-seed sample of starting teams shared by every
setting, and periodic results writes: moved to `docs/backtest_v1/requirements.md`
(R1, R5). Tuning-specific: `load_with_derivations` is `functools.cache`d and the
derivations do not depend on the coefficients, so run all grid points for a season
inside one process.

**The trap** — coefficient values missing from the results key, so a re-run at a
new setting is silently skipped as already done: moved to
`docs/backtest_v1/requirements.md` (R4, R5), where each variant's name is part of
the key.

**What to report** — moved to `docs/backtest_v1/requirements.md` (R7).

## Back-test harness

Moved to `docs/backtest_v1/requirements.md` on 2026-09-13. That effort builds a
new `backtest/` package rather than changing `run_multiple_teams.py`, while
reusing `run_for_team` as the single simulation engine (R3, R4, R5, R10).

## Suggested commit order

1. The back-test harness — moved to `docs/backtest_v1/requirements.md`.
2. `StrategyMaxPoints` at neutral defaults — the control, and a direct test of the
   "divisor double-penalises price" hypothesis.
3. Add DRS to the objective. The highest-value structural change, and cheap.
4. Add the tunable coefficients, all defaulting neutral.
5. The sweep driver. (The paired-delta analysis moved to
   `docs/backtest_v1/requirements.md`, R7 and R9.)

## Open questions

- **Is unused budget worth anything in practice?** Determines whether the
  budget-saturation point needs a lever or is a non-issue.
- **Should DRS be modelled in P2PM's objective too?** It would make the back-test a
  cleaner comparison — both strategies DRS-aware — but it changes an existing
  strategy's results, and the 2026 team log in README.md is live against current
  P2PM behaviour.

## Relationship to the FastF1 backlog items

Independent of both *Build a strategy on the FastF1 indicators* and *Regress the
FastF1 indicator against rolling points*. Those ask whether practice pace and odds
beat rolling points as a *signal*; this asks whether the LP *objective shape*
around a signal already in use is right. This one has no data prerequisite — no
`--historical` run, no constructor-name mapping, no new fixture file.
