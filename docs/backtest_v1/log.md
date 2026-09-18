# backtest_v1 — Log

Execution log for the backtest_v1 effort. Newest entries at the bottom.
Requirements and plan live alongside in `requirements.md` and `plan.md`.

## Status summary

- Step 1 completed 2026-09-18: `backtest/sample.py`, `sample_starting_teams`.
- Step 2 completed 2026-09-18: `backtest/variants.py`, `make_variant`.
- Step 3 completed 2026-09-18: `backtest/runner.py`, `append_results`.
- Step 4 completed 2026-09-18: `backtest/runner.py`, `simulate_sample`.
- Step 5 completed 2026-09-18: `backtest/metrics.py`, `pair_with_baseline`, in
  three commits.
- Step 6 completed 2026-09-18: `backtest/metrics.py`, `season_summary`.
- Step 7 completed 2026-09-18: `backtest/metrics.py`, `rank_challengers` and
  `verdict`.
- Step 8 completed 2026-09-18: `backtest/runner.py`, `run_backtest`.
- Step 9 completed 2026-09-18: `backtest/cli.py`.
- Step 10 completed 2026-09-18: README and CLAUDE.md. **Every plan step is
  implemented; *Verification* 2–4 — the real runs — have not been done.**
- *Verification* 2 passed 2026-09-18: 540 simulations in 3.3 minutes, peak about
  215 MiB, a re-run simulating nothing. *Verification* 3–4 not yet run.

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

## Step 5 — `pair_with_baseline` (2026-09-18)

Suite green at 173 before starting, 183 after. Three commits, one change each.

**The plan's filter could not live where the plan put it.** Plan step 5 tests
that `pair_with_baseline(results, baseline_label, band_edges)` drops teams
outside the current sample, but nothing in that signature names the sample.
Stored rows for **other labels** would leak the same way — a store holding an
earlier Zero-stop run would feed it into a run that asked only for Max budget —
and the plan did not mention those. Only `simulate_sample` computes the keys, so
it now returns just this run's rows (agreed in session, option 1 of 2; the other
was threading a `sim_keys` parameter through). `plan.md` is annotated.

1. **`assign_bands` refactor** (`0c214c6`). Sampling's `pd.cut` labelling became
   a public `assign_bands(values, edges)` in `sample.py`, so sampling and pairing
   cannot band differently. Out-of-band values now come back as NaN rather than
   the string `"nan"`. A pure refactor: two mutations — `right=False` and
   reversed labels — were each caught by step 1's tests.
2. **`simulate_sample` returns only this run's rows** (`e1635b4`), simulated or
   found in the store. New test: a copy of the stored results plus a
   foreign-label row and a foreign-team row, re-run with the engine set to fail
   if called; it failed first for the intended reason, 14 rows returned against
   12. Mutations caught: keys recorded only for teams simulated this time (the
   re-run and filter tests fail), and filtering by label alone (the filter test
   fails). A first attempt at the former deleted the key recording outright,
   which returns nothing and proves little, so it was rerun as the real
   mutation.
3. **`pair_with_baseline`** in `backtest/metrics.py`. Re-derives each row's band
   from `sampled_value` against the current edges; raises `ValueError` if any
   value falls outside every band (after the filter above that can only be a
   bug) or if the baseline has no results; inner-joins every label, the
   baseline included, with the baseline on (season, team); logs how many rows
   were dropped for lacking a baseline; returns `band`, `sampled_value`,
   `total_points`, `baseline_points`, `delta` and `delta_pct`. The baseline
   pairs with itself at zero delta, which the summary needs.
   - `delta_pct` divides by the baseline's season total without a guard: those
     totals are in the thousands.
   - A team the baseline has but a challenger lacks keeps its baseline row. It
     only arises from a partial run, and is left to steps 6–7 if it matters.

**How it failed first.** A stub that pairs correctly but keeps the stored band
and validates nothing failed 5 of 9: the two band tests, both raising tests, and
the column list. The four pairing tests passed, as the stub genuinely pairs, so
they were confirmed by mutation.

**Mutations**, each caught: a left join (the missing-team test fails); joining on
team alone, ignoring season; the delta reversed; the % delta divided by the
challenger's points; the stored band kept; the outside-band check dropped; the
missing-baseline check dropped.

R12: no new entry.

## Step 6 — `season_summary` (2026-09-18)

Suite green at 183 before starting, 191 after.

`season_summary(paired, band_edges)` gives one row per (label, season, populated
band) and one pooled row per (label, season), each carrying `teams`,
mean/median/P10/max points, mean delta and mean % delta, median and P10 delta,
and win rate. Choices agreed in session:

- The pooled row's band is **`pooled`**, not `all`, which would read as a mean
  over every team that exists (R8). Its docstring says it is a mean over the
  equally sampled bands.
- **`teams`** is added, the paired count per row, since it is what shows bands
  left unequal by pairing.
- **P10** is pandas' default linearly interpolated `quantile(0.1)`.
- **A tie is not a win** — `win_rate` counts `delta > 0` — so the baseline's own
  win rate is 0.
- **The pooled row is computed from the per-team rows**, never from band means.
  The fixture makes that visible: the pooled mean delta is +50 while the average
  of the two band means is −25.
- Rows are ordered by season, label, band edge and then `pooled`, so the
  signature gained `band_edges` over the plan's `season_summary(paired)`.
- A band with no teams gets no row.

**How it failed first.** A stub with correct per-band metrics, but no pooled row,
ties counted as wins and no ordering, failed 5 of 7. The two band-metric tests
each failed on `win_rate` alone, 1 of 10 values, which also confirmed the other
nine hand-computed values against pandas. The single-team-band and column tests
passed, so they were confirmed by mutation.

**Mutations**, each caught in the end: a tie counted as a win; P10 as P90; P10
by the `lower` rather than linear interpolation; `teams` counting the wrong
thing; max as mean; median delta taken from the % delta; the pooled row averaged
from band means; no pooled row; the index kept unreset; and bands sorted as label
text.

That last one first went uncaught. The default labels happen to sort correctly
as text, `"(90, 95]" < "(95, 99.5]" < "(99.5, 100]" < "pooled"`, so the ordering
test could not tell the two apart. A test on edges `(5, 10, 100)`, whose labels
sort the wrong way as text, was added; it then also went uncaught once more, but
only because the mutation harness filtered tests by name and missed it — rerun
unfiltered, it fails as it should.

R12: no new entry.

## Step 7 — `rank_challengers` and `verdict` (2026-09-18)

Suite green at 191 before starting, 198 after.

Agreed in session, changing plan step 7 (`plan.md` annotated):

- **Two functions, and no `paired` argument.** The summary's `pooled` row is
  already the per-team figure (step 6 pins +50 pooled against −25 averaged), so
  the verdict reads it rather than computing it a second way that could drift.
  That fixture is also run end to end, `season_summary` → `verdict`.
- **`rank_challengers(summary, baseline_label)`** adds a nullable integer `rank`:
  1 is the highest mean % delta within each (season, band), pooled rows ranked
  among themselves as the per-season ranking, ties sharing the best rank
  (`method="min"`), the baseline unranked.
- **`verdict(summary, baseline_label)`** gives per challenger `seasons`,
  `seasons_positive`, `beats_baseline` and `consistent_sign`. It beats the
  baseline only if its pooled mean delta is positive in every season of the
  summary, so a missing season fails it. `consistent_sign` is R7's separate
  "same sign in every season", true when consistently negative too; zero has no
  sign. The plan had dropped it.
- Named `beats_baseline` rather than `beats_p2pm`, the baseline label being a
  parameter.

**How it failed first.** A stub ranking across the whole summary, and judging by
averaging band rows while ignoring zeros and missing seasons, failed 3 of 6 on
behaviour. The tie, unranked-baseline, row-order and column tests passed, as the
stub had those properties, so they were confirmed by mutation.

**Mutations.** Twelve in all, each caught in the end: ranking across everything;
within season only; ascending; dense; the baseline ranked; ranking by points
rather than % delta; the verdict read from any band; zero counted positive; zero
counted negative; seasons counted per label rather than across the summary;
`consistent_sign` meaning positive only; the baseline included in the verdict.

Three went uncaught on the first pass:

- **Points versus % delta** — the fixture ordered both the same way. A test
  where they disagree was added.
- **Zero counted negative** — no label mixed a negative season with a zero one.
  `NegZero` (−10, 0) was added, expecting `consistent_sign` False.
- **Verdict read from any band** — a defect in the harness, not the tests. The
  replacement left an unbalanced bracket, so the module failed to import, and
  the harness counted only `FAILED` lines, not collection errors. The mutation
  was corrected and the harness now flags any run that does not complete. The
  same harness served steps 1–6: a mutation there only ever counted as caught
  when named tests failed, and each uncaught one was investigated by hand, so
  none of those results is affected.

Also simplified during the step: an explicit "has every season" guard was
dropped, being implied by `seasons_positive` equalling the summary's season
count.

R12: no new entry.

## Step 8 — `run_backtest` (2026-09-18)

Suite green at 198 before starting, 206 after.

`run_backtest(seasons, n, seed, strategies, band_edges, store_path,
summary_path)` samples and simulates each season in turn, the baseline first,
releasing each season's sample before the next; then pairs, summarises, ranks
and judges the combined rows, writes both tables and logs them with a line
saying `pooled` is a mean over the equally sampled bands (R8). Returns
`(summary, verdicts)`. Agreed in session:

- **The verdict is a second CSV beside the summary**, `<stem>_verdict.csv`, so
  the CLI needs no extra flag. Logging it alone would lose the headline result
  with the terminal; repeating its columns on every summary row would be
  redundant and easy to misread against the per-band rows.
- **Duplicate labels raise `ValueError`**, before any work starts: two
  strategies sharing a label would share keys, and the second would silently
  reuse the first's results.
- The baseline, `BASELINE = StrategyMaxP2PM`, is identified by label and is
  added to the front, or moved there if named. A P2PM variant under another
  label is a challenger.

**A gap the stub exposed.** The re-run test (baseline named, and named last)
passed against the stub, which appended the baseline without de-duplicating.
On a re-run every key is already stored and the returned rows are filtered by
key, so a doubled baseline is invisible there. It is not harmless on a fresh
run: `simulate_sample` does not track keys within a run (step 4 dropped
`done.add` as unreachable, which it is only while labels are unique), so the
baseline would be simulated twice and stored twice. `_with_baseline_first` is
now tested directly on three orderings, and the re-run test's comment no longer
claims to check it.

The test runs 2023 and 2024 with one team per band, baseline plus Zero-stop: 12
real simulations, about 20 seconds for the file. It checks the store, both CSVs
against the returned frames, that the directory holds nothing else, a re-run
simulating nothing, and duplicate labels raising before sampling starts.

**How it failed first.** The stub — baseline appended last, no label check, no
verdict file — failed 3 of 5 on behaviour: the baseline ran second, the verdict
file was missing, and duplicate labels started work instead of raising.

**Mutations**, each caught and each run completing cleanly: the baseline always
prepended (so named twice); appended; the duplicate check dropped; the verdict
not written; the verdict written elsewhere; the summary unranked; only the last
season kept. The old results file was checked byte-identical afterwards.

R12: no new entry.

## Step 9 — `backtest/cli.py` (2026-09-18)

Suite green at 206 before starting, 219 after.

`python -m backtest.cli` takes `--seasons`, `--sample-size`, `--seed`,
`--strategies`, `--bands`, `--output` and `--summary`. `parse_arguments(argv)`
and `main(argv)` take an argument list, so neither touches `sys.argv` in tests;
`__main__` is `setup_logging(); main()`. Agreed in session:

- **Completed seasons are a constant**, `COMPLETED_SEASONS = [2023, 2024, 2025]`,
  edited when a season ends. Forgetting fails safe — a finished season left out,
  never one in progress let in. Deriving it from the calendar year was rejected:
  the default would change silently on 1 January.
- **Seed 1** by default.
- **Default paths** `outputs/backtest_v1_results.parquet` and
  `outputs/backtest_v1_summary.csv`, putting the verdict at
  `outputs/backtest_v1_summary_verdict.csv`.

As planned: `--strategies` required, with choices from a registry of
`StrategyMaxP2PM`, `StrategyZeroStop` and `StrategyMaxBudget` (not
`StrategyBettingOdds`, out of scope); `--seasons` choices from
`F1_SEASON_CONSTRUCTORS`; `--sample-size` 500, its help saying it is per band;
`--bands` 90 95 99.5 100, invalid edges rejected at parse time through
`parser.error`. That reuses step 1's check, made public as
`validate_band_edges`. The `main` test replaces `run_backtest` with a recorder:
a first-party function, but tested end to end in step 8, and running it here
would mean real simulations.

**How it failed first.** A stub parsing every option with the right defaults,
but validating nothing, lacking the per-band help and passing strategy names
rather than classes, failed 9 of 13. The four that passed — defaults, the
seasons constant, the registry, parsing every option — were confirmed by
mutation.

**Mutations**, each caught and each run completing cleanly: 2026 in the default
seasons; an extra entry in the registry; the default sample size, seed and
output path each changed; `--strategies` not required; strategy choices dropped;
season choices dropped; band edges unvalidated; the help not saying per band;
names passed instead of classes; seed and sample size swapped; strategies
reordered.

**Run.** `python -m backtest.cli --help` and a run with `--bands 100 95` were
executed for real: the help renders as intended, and the bad edges are rejected
by argparse before any work, with nothing written to `outputs/`. No simulation
has yet been run through the CLI; that is *Verification* 2.

R12: no new entry.

## Step 10 — docs (2026-09-18)

- **README**: a *Back-testing against P2PM* section — what the module does,
  how to run it, the three output files and how to read them, including that
  the pooled row is a mean over the sampled bands rather than over every team,
  and that seasons are never pooled. `backtest` added to *Modules*, and the
  `run_multiple_teams.py` entry points to it.
- **CLAUDE.md**: the `backtest` commands, and an *Architecture* paragraph on each
  module, the untouched-modules constraint with its R12 ledger, why bands are
  derived from `sampled_value`, and `COMPLETED_SEASONS` needing extending.

The README's run-time figure — about 2.5 hours per strategy at the defaults — is
the plan's estimate from about two seconds a simulation, not yet measured
through this CLI.

## Verification 2 — small real run (2026-09-18)

**Passed on every criterion.** Run through the real CLI, via a wrapper that calls
`backtest.cli.main` and then reports elapsed time and peak memory:

```
python -m backtest.cli --sample-size 20 --strategies StrategyMaxBudget StrategyZeroStop \
    --output outputs/backtest_v1_verify_results.parquet --summary outputs/backtest_v1_verify_summary.csv
```

Separate `verify` paths were used so the default store starts clean for the full
run. Seasons 2023–2025, seed 1, default bands.

- **Outputs written.** 540 rows, 540 unique keys: exactly 20 per (label,
  season, band). A 36-row summary — 3 labels × 3 seasons × (3 bands + pooled) —
  and a 2-row verdict.
- **Every team inside its band.** All 540 `sampled_value`s fall inside the
  stored band's `(min, max]`.
- **Paired.** Every label ran on the same 60 teams in each season.
- **A re-run simulates nothing.** It skipped all 180 simulations per season,
  started no solver, and finished in about 5 seconds. The store was not
  rewritten, and the summary and verdict came out byte-identical, confirmed by
  checksum.
- **Peak memory: about 215 MiB** for the Python process, the 2024 enumeration of
  about 152,000 teams included. The wrapper also reported a child process of the
  same size, but that is a fork carrying the parent's pages at the moment it
  starts, not CBC's own use: the re-run, which starts no solver, reports 0. The
  concern the plan flagged about holding the full `(90, 100]` frame did not
  materialise.

**Run time: 3.3 minutes for 540 simulations, about 0.37 s each**, P2PM the
slowest at about 0.35–0.4 s and Zero-stop the fastest at about 0.2 s. That is
around five times faster than the ~2 s the plan, README and requirements assumed.
Extrapolating, the full default run — 500 per band, 13,500 simulations — would
take roughly 80–90 minutes rather than 7.5 hours. That is an extrapolation from
one small run, not a measurement of the full one; *Verification* 4 will measure
it.

**Results, for the record, not as evidence.** Both controls trail P2PM in every
season: mean pooled deltas of −1,020 to −1,773 points, −22% to −36%, and a win
rate of at most 3.3% (2 of 60 teams, Zero-stop in 2024). Neither beats P2PM;
both are consistently negative. That agrees with the January evidence (trailing
by 900–1,800 points, winning on at most 2.3% of teams), but 60 teams a season
across three bands is a smoke test, not a comparison.

**Noticed, not changed:** `simulate_sample` logs "Simulating X for season Y on
60 teams" even when every key is then skipped. It reads as if simulation
happened; the per-season "skipped" line that follows corrects it. Cosmetic.
