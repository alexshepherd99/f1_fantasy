# backtest_v1 — Log

Execution log for the backtest_v1 effort. Newest entries at the bottom.
Requirements and plan live alongside in `requirements.md` and `plan.md`.

## Status summary

- Step 1 completed 2026-09-18: `backtest/sample.py`, `sample_starting_teams`.

## Step 1 — `sample_starting_teams` (2026-09-18)

Suite green at 138 before starting, 154 after.

- `backtest/sample.py` enumerates a season once over the outermost band edges
  from race 1, cuts it into `(min, max]` bands with `pd.cut`, and draws
  `df.sample(n, random_state=seed)` per band, or takes a band whole when it holds
  no more than n teams. The index is left as each team's position in the full
  combination set.
- **Band labels are strings** such as `"(99.5, 100]"`, not `pd.Interval`
  categoricals, so they round-trip through parquet (step 3) and read cleanly in
  the CSV and Tableau. Agreed in session.
- **"Edges that overlap or leave a gap"** (plan step 1) became "edges fewer than
  two or not strictly increasing raise `ValueError`": an edge list cannot express
  a gap, and an unsorted or repeated edge is the only way to get an overlap.
- **Tests stand in for `get_starting_combinations`** with a synthetic frame that
  puts teams exactly on 90, 95, 99.5 and 100, since the real enumeration is too
  coarse to pin boundaries and is about 100,000 rows. One unpatched test on 2023
  keeps the real enumeration exercised.

**How it failed first.** Against the missing module, only an import error. A
naive stub (enumerate once, label everything one band, no sampling or
validation) then failed 11 of 16 on their assertions, e.g. `assert 33 == 9` for
n rows per band. The 5 that passed exercise behaviour the stub really had — one
enumeration from race 1, season and index passed through, the default edges,
and same-seed reproducibility (vacuous with no sampling) — so they were
confirmed by mutation instead.

**Mutations**, each against the finished implementation, and each caught:

- `pd.cut(..., right=False)` — the boundary, per-band and custom-edge tests fail.
- `random_state=None` — the same-seed test fails.
- `random_state=0` — the different-seed test fails.
- Whole-band guard dropped — fails four tests including the whole-band one. That
  test first used n=11, exactly each band's population, where `sample(11)`
  returns the same set, so it did not catch this mutation; it now uses n=50.
- `ignore_index=True` on the concat — the index and per-season tests fail.
- Season hardcoded to 2023 — the per-season test fails.
- Validation dropped — all four invalid-edge cases fail.
- Race 2 instead of race 1 — the enumeration test fails.

R12: no ledger entry. `get_starting_combinations` is reused unchanged, and one
call with `pd.cut` replaces the three calls the ledger first described.
