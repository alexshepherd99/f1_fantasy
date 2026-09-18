# backtest_v1 — Log

Execution log for the backtest_v1 effort. Newest entries at the bottom.
Requirements and plan live alongside in `requirements.md` and `plan.md`.

## Status summary

- Step 1 completed 2026-09-18: `backtest/sample.py`, `sample_starting_teams`.
- Step 2 completed 2026-09-18: `backtest/variants.py`, `make_variant`.
- Step 3 completed 2026-09-18: `backtest/runner.py`, `append_results`.
- Step 4 completed 2026-09-18: `backtest/runner.py`, `simulate_sample`.

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

## Step 2 — `make_variant` (2026-09-18)

Suite green at 154 before starting, 163 after.

- `backtest/variants.py` returns `type(label, (base,), {"__init__": ...})`, whose
  `__init__` calls `base.__init__` with the factory's keywords and the variant's
  params side by side.
- **A param clashing with a `factory_strategy` keyword raises `TypeError`** when
  the strategy is built — Python's own duplicate-keyword error, with no code of
  our own. Merging instead would let a variant silently override what the engine
  sets each race, such as `max_moves`, and break R3's one-engine guarantee.
  Agreed in session, and pinned by a test the plan did not list.
- An empty label is rejected along with whitespace, since it would give an
  unnamed class and an empty key.
- Tests build strategies through the real `factory_strategy` on 2025 race 2 and
  simulate through the real `run_for_team`, using `test_run_batch`'s 2025
  starting team; nothing is patched. The params test uses a test-local
  `StrategyZeroStop` subclass taking an extra keyword.

**How it failed first.** Against the missing module, only an import error. A
naive stub (`type(label, (base,), {})`, ignoring params and not validating) then
failed 6 of 9 on their assertions. The 3 that passed — the name is the label, the
base class is left unchanged, and a run through `run_for_team` labels its rows
and matches the base's points — are behaviour the stub really had, so they were
confirmed by mutation instead.

**Mutations**, each against the finished implementation, and each caught:

- Class named after the base — the name and `run_for_team` tests fail.
- Params dropped — the params and clash tests fail.
- Params merged over the factory's keywords — the clash test fails.
- Label validation dropped — all four invalid-label cases fail.
- Empty label allowed — the empty-label case fails.
- The base's `__init__` patched instead of subclassed — the base-unchanged test
  fails.
- Wrong base class (`StrategyZeroStop`) — the name, params and `run_for_team`
  tests fail.

R12: no new ledger entry. The mechanism's cost is already recorded (2026-09-13).

## Step 3 — results store (2026-09-18)

Suite green at 163 before starting, 168 after.

- **Only `append_results`, no `open_results`** (agreed in session, a change from
  plan step 3). `scripts.run_multiple_teams.open_batch_results_file` already
  takes a path and opens a missing file as an empty `sim_key` frame, and is
  tested in `test_run_batch.py`, so a wrapper would add nothing. The plan's
  "missing file opens empty" test is dropped for the same reason.
- `append_results(store, rows, path)` appends, writes the whole store to `path`
  and returns it. Two changes from `write_batch_results`, agreed in session:
  nothing is written when there are no rows, and the concat uses
  `ignore_index=True` so the stored index does not repeat per batch.
- **Found while testing: the original upcasts integers to float.** Concatenating
  onto the empty `sim_key`-only store turns every integer column missing from it
  into float. The round-trip test caught `total_points` coming back as float64;
  the old results file does hold it as `double`. `append_results` takes the new
  rows alone when the store is empty. Harmless to values, but recorded in the
  R12 ledger row with the other defects.
- The path test runs from `tmp_path` as working directory, so a relative
  hardcoded write would land there, and asserts the given file is the only one
  created.

**How it failed first.** Against the missing module, only an import error. A
stub mirroring `write_batch_results` with the path honoured then failed 4 of 5
on their assertions: the float64 upcast, the repeated index `[0, 1, 0, 1]`, and
a write when there were no rows (to an existing file and to a missing one). The
path test passed, since the stub honoured the path, so it was confirmed by
mutation.

**Mutations**, each against the finished implementation, and each caught:

- Writes to a fixed relative filename instead of `path` — the path test fails.
  Only that test was run for this mutation, as the others do not change working
  directory and could have written into the repo; the old results file was
  checked byte-identical afterwards.
- Empty-store guard dropped — the round-trip test fails.
- `ignore_index=True` dropped — the accumulate test fails.
- No-rows guard dropped — both no-rows tests fail.

R12: no new entry. The existing results-store row is annotated.

## Step 4 — `simulate_sample` (2026-09-18)

Suite green at 168 before starting, 173 after.

- `simulate_sample(season, sample, strategies, store_path, flush_every)` loads
  the season once, builds a fresh `Team` per (strategy, team) with
  `factory_team_row`, keys it with `get_starting_key`, skips keys already
  stored, simulates the rest through `run_for_team` from the starting race, and
  flushes through `append_results` every `flush_every` simulations and at the
  end. Strategies run in the order given; putting the baseline first is
  `run_backtest`'s job (step 8).
- **The sample's value is stored as `sampled_value`** (agreed in session, option
  1 of 3). `run_for_team`'s final row already carries `total_value` — the
  team's end-of-season valuation — so carrying the sample's value under that
  name would have overwritten it. Its `starting_value` was rejected as the
  banding value: checked on 600 sampled 2023 teams, 190 differ from the sampled
  value by float noise (at most 1.4e-14), enough to move a team sitting exactly
  on an edge into the neighbouring band. `plan.md` is annotated.
- `STARTING_RACE` in `backtest/sample.py` is now public, so sampling and
  simulation share one starting race.
- **Bug caught by the tests during implementation:** the first version took
  `str(team)` for the `team` column after `run_for_team`, which mutates the team
  to its end-of-season line-up. The key was right, being computed before the
  run; the column was not. The starting team's string is now taken first.
- **Flush test by crash injection** (agreed in session): `run_for_team` is
  wrapped to call through to the real engine but raise on the 5th call, with
  `flush_every=2`, and 4 rows must already be on disk. This patches a
  first-party function, which the standards discourage, because nothing real
  stands in for a process dying mid-run. The re-run test likewise replaces it
  with one that fails if called at all.
- Tests run 2023, two teams per band, with P2PM and Zero-stop: 12 simulations
  shared through a module-scoped fixture, about 11 seconds for the file.

**How it failed first.** A stub modelled on `run_strategy_for_season` — no skip,
one write at the end, only `sim_key` added — failed 4 of 5 on behaviour: the
carried columns were missing, a re-run called the engine again, and nothing was
on disk after the crash. The direct-`run_for_team` match passed, since the stub
runs the same engine, so it was confirmed by mutation.

**Mutations**, each against the finished implementation, and each caught:

- `team` taken after the run — the row test fails.
- Skip dropped — the re-run test fails.
- No periodic flush, and flushing one simulation late — the crash test fails.
- `sampled_value` taken from the engine's `starting_value` — the row test fails,
  which is the float-noise difference above.
- `band` dropped — the row test fails.
- The first race's row kept instead of the last — the direct-match test fails.
- Label taken from the base class — the row and direct-match tests fail.

The old results file was checked byte-identical after the mutation run.

R12: no new entry. Every call into `scripts/`, `races/` and `helpers` is reused
unchanged.
