# odds_drs_v1 — Log

Execution log for the odds_drs_v1 effort. Newest entries at the bottom.
Requirements and plan live alongside in `requirements.md` and `plan.md`.

## Status summary

- Effort started 2026-10-05. Step 1 (docs) is complete, with requirements and
  plan agreed.
- Step 2 completed 2026-10-05: `StrategyBettingOdds` puts DRS inside its
  objective.
- Step 3 completed 2026-10-05: registered in `backtest/cli.py`. Next is
  step 4, the timing run.

## 2026-10-05 — Scoping

Scope agreed in conversation before writing anything:

- Edit `StrategyBettingOdds` only, with DRS always on, and leave the rest of
  `linear/` alone. The live team is mid-season.
- Run the back-test through the existing harness rather than writing a new
  per-race limitless comparison. It covers 2026 through race 16.
- Keep the code. The findings go here, and the results are discarded.

Found while scoping:

- Odds exist only for 2026 races 1–17, so no other season can be back-tested.
- The harness skips teams already in its store, so this run must not use the
  default store. If it did, the end-of-season run would silently reuse its
  partial-season rows (R7).

Q1 settled as (a): when the LP's DRS nominee has no odds, return `""` so
`Team` keeps its highest-price fallback. The fallback sits in the odds
strategy, not in `StrategyBase`.

## 2026-10-05 — Step 2, DRS inside the odds objective

`get_problem()` now passes each available driver's odds to
`get_drs_objective_term()`, adds the term to the objective, and applies the
constraints. `get_drs_driver()` returns `get_drs_nominee()`, or `""` when the
nominee has no odds.

Two new tests, both seen failing:

- `test_strategy_odds_drs_changes_selection` is a budget-limited case in which
  doubling the DRS driver's odds changes which pair is best. The old code
  failed it by picking A1/A2 (best without DRS) instead of B1/B2.
- `test_strategy_odds_drs_no_odds_falls_back` passed on the old code, which
  already had this fallback. To check that it guards anything, the change was
  first made without the fallback. The test then failed, with the LP
  nominating an arbitrary zero-odds driver (`B2@C2`), before the fallback was
  added.

The existing `test_strategy_odds_run` still expects `Drv3@Con2` to get DRS, and
passes unchanged. Full suite green, 278 passed.

## 2026-10-05 — Step 3, registered in the back-test CLI

`StrategyBettingOdds` is added to `STRATEGIES` in `backtest/cli.py`. R5's "one
line" became an import plus the registry list wrapped over three lines to fit
the width. Nothing else in `backtest/` changed.

In `tests/test_backtest_cli.py`, the exact-match registry test gains the entry
and there is a new `test_betting_odds_is_selectable_as_a_challenger`. Both
failed before registration, the second because argparse rejected the name.
Full suite green, 279 passed.
