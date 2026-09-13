# backtest_v1 — Plan

**Status**: draft for review, 2026-09-13. Requirements: `requirements.md`.

TL;DR — A new `backtest/` package: draw a seeded sample of starting teams per
season, simulate the P2PM baseline and each challenger on that sample through
the existing `run_for_team`, store one row per simulated team in its own
resumable parquet file, then pair each team with its baseline result and report
per-season metrics and a verdict. Nothing in `scripts/`, `races/`, `linear/` or
`import_data/` changes.

## Design

**Modules.**

- `backtest/sample.py` — draws the starting-team sample.
- `backtest/variants.py` — builds named strategy variants.
- `backtest/runner.py` — simulates and stores results.
- `backtest/metrics.py` — pairing, per-season metrics and the verdict.
- `backtest/cli.py` — the CLI.

Tests go in `tests/test_backtest_<module>.py`.

**Reused unchanged:**

- `helpers.load_with_derivations`
- `races.first_picks.get_starting_combinations`
- `races.season.factory_season` / `factory_race`
- `races.team.factory_team_row`
- `scripts.run_single_team.run_for_team`
- `scripts.run_multiple_teams.open_batch_results_file` and `get_starting_key`

`get_starting_key(label, season, team)` gives `(label)(season)(team)`, which is
the key R5 needs. `write_batch_results` is not reused, because it hardcodes the
old output path.

**Sample (R1).** `get_starting_combinations(season, 1, 99.5)` is indexed by each
team's position in the full combination set, which is stable for unchanged
archive data. The sample is `df.sample(n, random_state=seed)`, or every row when
n is at least the population. The same seed is used for every season. The
seasons have different populations, so they get unrelated samples anyway (R1,
per season).

**Variants (R4).** `make_variant(base, label, **params)` returns
`type(label, (base,), {"__init__": ...})`. The new `__init__` merges `params`
into the keyword arguments that `factory_strategy` passes. `run_for_team` then
names its rows by the label, via `__name__`, with no change to it.

- Labels must not contain whitespace: PuLP names each problem after its class
  and rewrites spaces with a warning. Colons and `=` were checked and are
  accepted.
- A plain strategy class is its own label (`StrategyZeroStop`).

**Simulation and store (R2, R3, R5).** For each season:

1. Load the season once.
2. Build a fresh `Team` for every (label, starting team). This is needed because
   `run_for_team` mutates the team it is given.
3. Keep the final row, plus `sim_key`, `label` and `team`.
4. Skip keys already in the store, and append to it every `flush_every` sims
   (default 100).

The baseline label is `StrategyMaxP2PM` and is always run first. Its rows are
reused by every challenger, and the resume logic skips them on later runs.

**Metrics (R7, R8).**

- Read the store, then **filter it to the current sample's keys**. Rows from
  another seed or sample size may be in the file and must not leak into a
  summary.
- Inner-join each challenger with the baseline on (season, team).
- Per label and season, report:
  - mean, median, P10 and max of total points;
  - mean delta in points and in %;
  - median delta and P10 delta;
  - win rate against the baseline.
- Within each season: rank the challengers by mean paired % delta. There is no
  ranking across seasons.
- Across seasons: only the *beats P2PM* verdict, which is true when the mean
  delta is positive in every season.
- The baseline appears in the summary with zero deltas, for reference.

**Output (R9, R10).**

- The summary CSV and the per-team parquet are both in `outputs/`, with
  injectable paths.
- The summary is also logged.
- The CLI takes `--seasons`, `--sample-size`, `--seed`, `--strategies`,
  `--output` and `--summary`. `--strategies` is required: names come from a
  registry of the existing classes, with no default.
- `__main__` is `setup_logging(); main()`. `main()` parses the arguments and
  makes one call to a tested `run_backtest(...)`.

## Steps

Each step is one commit, written test-first: see the test fail for the intended
reason, then implement. Where the first failure can only be an `ImportError` or
`TypeError`, show a mutation failing on its value as well.

1. **`sample_starting_teams(season, n, seed)`** — tests:
   - the result has n rows;
   - the same seed gives the same teams;
   - a different seed gives different teams;
   - n ≥ population gives every team;
   - two seasons give independent samples.
2. **`make_variant(base, label, **params)`** — tests:
   - `__name__` equals the label;
   - params reach `__init__`, using a test-local strategy subclass that takes
     an extra keyword, since no existing strategy has one;
   - a label containing whitespace raises `ValueError`;
   - a variant run through `run_for_team` labels its rows with its name.
3. **Results store** — `open_results` / `append_results` with an explicit path.
   Tests:
   - a missing file opens empty;
   - appending writes to the given path and nowhere else (the old hardcoded-path
     bug is guarded);
   - a round trip preserves rows.
4. **`simulate_sample(season, sample, strategies, store_path, flush_every)`** —
   one season, two teams, the baseline plus one challenger. Tests:
   - it produces one row per (label, team) with the expected key and final
     total points;
   - the result matches a direct `run_for_team` call for the same team, proving
     it is the same engine;
   - a re-run skips every key and simulates nothing;
   - it flushes at the interval.
5. **`pair_with_baseline(results, baseline_label)`** — synthetic frames. Tests:
   - deltas and % deltas per team;
   - teams missing from either side are dropped;
   - teams outside the current sample are filtered out.
6. **`season_summary(paired)`** — synthetic frames with hand-computed expected
   values for every R7 metric, the baseline row included.
7. **`verdict(summary)`** — synthetic frames. Tests:
   - *beats P2PM* is true only when the delta is positive in every season;
   - challengers are ranked within each season by mean % delta, never across
     seasons.
8. **`run_backtest(seasons, n, seed, strategies, store_path, summary_path)`**
   — ties steps 1–7 together, prepends the baseline if it isn't given, writes
   the summary CSV and logs it. Test: one season, two teams, tmp paths.
9. **`backtest/cli.py`** — tests:
   - argument parsing and defaults (completed seasons only, N=500);
   - `--strategies` is required;
   - unknown strategy names are rejected;
   - `main()` calls `run_backtest` with the parsed values.
10. **Docs** — README scripts/modules section, CLAUDE.md *Architecture* and
    *Commands*.

## Verification

1. The full pytest suite is green, and was green at the start.
2. **Small real run.** `python -m backtest.cli --sample-size 20 --strategies
   StrategyMaxBudget StrategyZeroStop` over 2023–2025. Those two challengers are
   used only because the old results file holds their numbers for the
   cross-check in 3. Check that:
   - the summary is written;
   - a re-run simulates nothing;
   - peak memory fits the dev environment.
3. **Engine cross-check against the old results.** For sampled teams also present
   in `outputs/f1_fantasy_results_batch.parquet`, compare the new baseline's
   total points with the old `StrategyMaxP2PM:unlimited_chip_4` values, and the
   challengers with the `:fix_drv_chg` values, stripping `@CON` from the old
   keys. Report the share that match exactly. Archive corrections since January
   2026 can explain differences, so a mismatch is investigated rather than
   assumed to be a bug.
4. **Full default run.** 500 teams × 3 seasons × 3 labels, about 2.5 hours at
   ~2s per simulation. Compare the sampled per-season means with the
   full-population means from the old file, as a check that the sample is
   representative.

Steps 2–4 run against the real archive and are the "it has been run" clause.
They go in `log.md` as prose, without machine details.

## Decisions

Agreed 2026-09-13:

- **Ranking:** within each season only. There is no cross-season ranking; the
  *beats P2PM* verdict is the only cross-season output.
- **Strategies:** `--strategies` is required. Zero-stop and Max budget stay in
  the registry, but only for the verification runs.

## Relevant files

- `docs/backtest_v1/requirements.md`
- `docs/backtest_v1/plan.md`
- `docs/backtest_v1/log.md` (to create at step 1)
- `backtest/__init__.py`, `sample.py`, `variants.py`, `runner.py`, `metrics.py`,
  `cli.py`
- `tests/test_backtest_sample.py`, `test_backtest_variants.py`,
  `test_backtest_runner.py`, `test_backtest_metrics.py`, `test_backtest_cli.py`
- `README.md`, `CLAUDE.md` (step 10)
