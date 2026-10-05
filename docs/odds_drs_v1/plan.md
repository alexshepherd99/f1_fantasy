# odds_drs_v1 — Plan

**Status**: agreed 2026-10-05. Requirements: `requirements.md`. Not
yet implemented — no code exists.

One commit per step. Each behavioural change is seen failing before it passes,
and the full suite is green at the end of every step.

## Step 1 — Effort docs

`docs/odds_drs_v1/{requirements,plan,log}.md`, plus a row in the `BACKLOG.md`
efforts table.

## Step 2 — DRS inside the odds objective (R1–R3)

In `linear/strategy_odds.py`:

- Build the driver-odds dict, call `get_drs_objective_term()`, add the term to
  `VarType.OptimiseMax`, and `problem.extend()` the constraints.
- Replace the body of `get_drs_driver()` with `get_drs_nominee()`, plus the
  zero-odds fallback (Q1, settled as (a)).

Tests in `tests/test_strategy_odds.py`, each observed failing first:

- **The LP changes its pick because of DRS.** Use a fixture where, without DRS,
  team A has the higher odds total, but once one driver's odds count twice,
  team B wins. The test asserts team B is picked. This is what proves DRS is
  inside the objective rather than applied afterwards.
- `get_drs_driver()` returns the LP's nominee, and that driver is in the
  selected team.
- The zero-odds fallback: with no odds for any selected driver,
  `get_drs_driver()` returns `""`.

The existing `test_strategy_odds_run` asserts `Drv3@Con2` gets DRS, which should
still hold. If it doesn't, stop and discuss rather than adjust the assertion.

## Step 3 — Register in the back-test CLI (R5)

Add `StrategyBettingOdds` to `STRATEGIES` in `backtest/cli.py`. In
`tests/test_backtest_cli.py`, update the exact-match assertion and add a
"nameable on the command line" test, matching the ones for `StrategyMaxPoints`
and `StrategyMaxP2PMNoReset`.

## Step 4 — Timing run, then agree the sample size (R6)

Run `--sample-size 2` (6 teams across the 3 bands) with separate output paths
(R7), timing it and watching memory. From that, propose a sample size, and agree
it with Alex before the full run.

## Step 5 — The back-test (R6–R9)

```bash
PYTHONPATH=. venv/bin/python -m backtest.cli --seasons 2026 \
    --strategies StrategyBettingOdds --sample-size <agreed> \
    --output outputs/odds_drs_v1_results.parquet \
    --summary outputs/odds_drs_v1_summary.csv
```

Write the headline findings to `log.md`, caveats first (R9). Commit the log
only; the results stay in `outputs/`.

## Step 6 — Close out

- `CLAUDE.md`'s architecture notes say the DRS helper is something "nothing
  calls yet". Update that line, and the `StrategyBettingOdds` description, to
  match.
- Mark the effort done in `BACKLOG.md`.
- End-of-session review.
