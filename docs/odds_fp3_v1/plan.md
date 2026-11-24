# odds_fp3_v1 — Plan

**Status**: agreed 2026-11-24. Requirements: `requirements.md`. No code exists yet.

One commit per step. Each behavioural change is seen failing before it passes, and the
full suite is green at the end of every step.

## Step 1 — Effort docs

`docs/odds_fp3_v1/{requirements,plan,log}.md`, a row in the `BACKLOG.md` efforts table,
and two backlog entries: live use at race 1, and sprint weekends at race 1 (R5, R6).

## Step 2 — Agree the strategy's shape (R6)

In conversation, no code. A starting proposal to discuss:

- `StrategyOddsFP3(StrategyBase)` in `linear/strategy_odds_fp3.py`.
- A keyword `odds_weight: float = 0.5` (R3), and a metrics-file path defaulting to the
  file `fast_f1` writes, reused from wherever it is already defined.
- It reads the race's `OddsRank` and `FP3_MinLapTime_rank` rows, reusing `fast_f1`'s
  existing weekend-format detection to refuse sprint weekends (R5).
- It picks from an empty team. Before agreeing this, check that `StrategyBase` accepts
  empty team lists, which `scripts/select_odds_start.py` sidesteps with a placeholder
  team. If it doesn't, stop and discuss rather than edit `StrategyBase`.

[Done 2026-11-24: agreed as proposed. `StrategyBase` does not accept an empty team, so
the back-test passes a placeholder team with every move allowed. See `log.md`, *Step 2*.]

## Step 3 — The strategy (R2–R5)

`linear/strategy_odds_fp3.py`, with tests in `tests/test_strategy_odds_fp3.py`, each
seen failing first. Tests to cover at least:

- A fixture where the pick changes with `odds_weight`: odds favour one team and FP3
  another, and weights 1 and 0 each pick theirs.
- A constructor's value is the sum of its drivers' values.
- A missing input scores 0.
- DRS is chosen inside the LP: a fixture where counting one driver twice changes the
  team.
- It raises on a sprint weekend and on a race with no rows.

## Step 4 — Single-race back-test harness (R7–R9)

A new module under `backtest/` (name agreed at this step; `backtest/race_one.py`,
agreed at step 2), with tests:

- The cap rule (R8).
- Scoring one team on one race, with DRS.
- Running the five mixes and three controls at a race, including the seeded random
  teams.
- Finding the eligible races from the metrics and odds files, so the season-end rerun
  picks up races 22 and 23 without a code change.

Results are written to `outputs/odds_fp3_v1_*.csv`.

## Step 5 — The comparison and the bar (R10)

The per-race differences against 50/50, the interval through
`fast_f1.indicator_analysis.bootstrap_interval`, the verdict, and the tie rule. Tests
include a case built to pass and one built to fail.

## Step 6 — Run and report (R10–R12)

Run on today's eligible races, then write the findings to `log.md` in plain language.
Update `R3`'s default only if R10 says so. Add the `BACKTEST_LOG.md` entry.

## Step 7 — Season-end rerun (R11)

Once 2026 race 24 is captured and its metrics built, rerun and report it against step 6.

## Step 8 — Close-out

`CHANGELOG.md` line, the `BACKLOG.md` state set to done, and update `CLAUDE.md` and
`README.md` where the new strategy needs mentioning.
