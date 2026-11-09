# remove_batch_script_v1 — Log

A small effort, so requirements and plan sit inline here (see `agentic`'s
`shared/persistent-docs.md`, *Collapsing for small efforts*).

## Requirements

Raised by Alex 2026-11-09: remove `scripts/run_multiple_teams.py`, which the sampled
`backtest/` module has superseded, and `scripts/batch_results_xl.py`, which only
converts its output to CSV for Tableau.

The backtest covers what the script did. Its sample takes a whole band when the band
holds fewer teams than the sample size (`backtest/sample.py`), so
`--bands 99.5 100 --sample-size 100000` runs every starting team, as the script did,
except a team worth exactly 99.5, which the backtest's `(min, max]` bands leave out.
It always runs `StrategyMaxP2PM` as a baseline, which costs time but nothing else.

Alex's case-by-case OK for editing `scripts/`, which is a core module, covers this
effort's changes there and nothing beyond them.

Agreed with Alex 2026-11-09:

- **`get_starting_key` and `open_batch_results_file` move to a new
  `backtest/store.py`.** `backtest/` is their only remaining user, and the move ends
  its dependency on `scripts/run_multiple_teams.py`. The key format stays exactly as
  it is, so every existing backtest store still resumes.
- **`select_starting_team.py` drops its batch-results lookup.** It read the script's
  parquet only to log past totals for the team it picks; the lookup never affected the
  choice. `ALL_STRATEGIES` goes with it, having no other user.
- **`get_starting_key` loses its `sub_strat` argument** once the script, its only
  caller passing one, is gone. A key built without it is unchanged.

Out of scope:

- The parquet files the script wrote under `outputs/` are untracked and stay where
  they are.
- `run_for_team`'s own `sub_strat` argument in `scripts/run_single_team.py` stays.
- Finished efforts that mention the script (`backtest_v1`'s R12 ledger among them)
  are left as they are.

## Plan

One commit per step. Suite green at each.

1. **Drop the lookup from `select_starting_team.py`.** Remove the parquet read, the
   `ALL_STRATEGIES` loop and their imports. `tests/test_select_starting_team.py`
   already pins the chosen team, which must not change.
2. **Delete `scripts/batch_results_xl.py`.** Nothing imports it.
3. **Move the two functions to `backtest/store.py`, test first.** Move
   `open_batch_results_file`'s two tests from `tests/test_run_batch.py` into a new
   `tests/test_backtest_store.py` importing from `backtest.store`, and add one pinning
   `get_starting_key`'s exact output for a known team, which no test does today; see
   them fail on the missing module. Then create the module with both functions
   unchanged and repoint `backtest/runner.py`, `backtest/per_race.py`,
   `tests/test_backtest_runner.py`, `tests/test_backtest_per_race.py` and, for this
   commit only, `scripts/run_multiple_teams.py`.
4. **Delete `scripts/run_multiple_teams.py`,** and drop `sub_strat` from
   `get_starting_key`. The pinned key test must pass unchanged.
5. **Docs:** `README.md`, `CLAUDE.md`, and `BACKLOG.md`'s *No test exercises any
   script's `__main__` block*, whose `batch_results_xl.py` instance goes away.

## 2026-11-09 — Effort opened

Suite green at the start: 656 passed.
