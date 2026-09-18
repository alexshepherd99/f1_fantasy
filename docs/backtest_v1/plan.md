# backtest_v1 — Plan

**Status**: draft for review, 2026-09-13; refined 2026-09-18 for value bands and
the replication-cost ledger. Requirements: `requirements.md`, settled
2026-09-18. Not yet implemented — no code exists.

TL;DR — A new `backtest/` package: draw a seeded sample of starting teams per
season **and value band**, simulate the P2PM baseline and each challenger on that
sample through the existing `run_for_team`, store one row per simulated team in
its own resumable parquet file, then pair each team with its baseline result and
report per-season, per-band metrics and a verdict. Nothing in `scripts/`,
`races/`, `linear/` or `import_data/` changes, and every workaround that costs
us is logged in the R12 ledger.

## Design

**Modules.**

- `backtest/sample.py` — draws the starting-team sample, one per value band.
- `backtest/variants.py` — builds named strategy variants.
- `backtest/runner.py` — simulates and stores results.
- `backtest/metrics.py` — pairing, per-season and per-band metrics, and the
  verdict.
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

**Sample (R1).**

> [Superseded 2026-09-18 — the single `>99.5` population became three value
> bands.] `get_starting_combinations(season, 1, 99.5)` is indexed by each
> team's position in the full combination set, which is stable for unchanged
> archive data. The sample is `df.sample(n, random_state=seed)`, or every row
> when n is at least the population. The same seed is used for every season. The
> seasons have different populations, so they get unrelated samples anyway (R1,
> per season).

**One call per season, not one per band.**
`get_starting_combinations(season, 1, 90, 100)` enumerates once, and
`pd.cut(total_value, [90, 95, 99.5, 100])` assigns the band. That function
excludes its minimum and includes its maximum, and `pd.cut` defaults to the same
convention, so the cut reproduces the R1 bands exactly rather than
approximately. Three separate calls would enumerate the same 697,680
combinations three times to reach the same answer.

That equivalence was **run, not just reasoned** (2026-09-18): across the values
either side of every edge, `pd.cut` on those bins agrees with
`(total > min) & (total <= max)` at each boundary — 90.0 falls outside all three
bands, 95.0 lands in `(90, 95]`, 99.5 in `(95, 99.5]`, and 100.0 in
`(99.5, 100]`. Step 1's boundary test keeps it that way.

- The widest frame is 2024's, about 152,000 rows. Band assignment and sampling
  are all that touch it, and it is dropped before any simulation starts. Its
  peak memory on the dev box is **not yet measured** — *Verification* 2 covers
  it.
- `df.sample(n, random_state=seed)` per band, or the whole band when n is at
  least its population. That never fires for the agreed bands, the smallest of
  which holds 3,999 teams against N=500 (R1 *Evidence*), but the rule stays.
- The same seed is used for every season and band. Each draws from a disjoint
  population — the bands partition by value, so no team can appear in two — so
  the samples are unrelated regardless.
- The index stays each team's position in the full combination set, so it
  remains a stable identifier across bands and runs.

**Variants (R4).** `make_variant(base, label, **params)` returns
`type(label, (base,), {"__init__": ...})`. The new `__init__` merges `params`
into the keyword arguments that `factory_strategy` passes. `run_for_team` then
names its rows by the label, via `__name__`, with no change to it.

- Labels must not contain whitespace: PuLP names each problem after its class
  and rewrites spaces with a warning. Colons and `=` were checked and are
  accepted.
- A plain strategy class is its own label (`StrategyZeroStop`).

**Simulation and store (R2, R3, R5).** For each season:

1. Load the season once — per season, not per band: all three bands simulate
   against the same race data.
2. Build a fresh `Team` for every (label, band, starting team). This is needed
   because `run_for_team` mutates the team it is given.
3. Keep the final row, plus `sim_key`, `label`, `team`, `total_value` and `band`
   (the last two added 2026-09-18, R5). Both are carried from the sample frame
   rather than recomputed, so a stored row always records the band it was drawn
   for.
4. Skip keys already in the store, and append to it every `flush_every` sims
   (default 100).

The baseline label is `StrategyMaxP2PM` and is always run first. Its rows are
reused by every challenger, and the resume logic skips them on later runs.

The key stays `(label)(season)(team)`, with no band in it, because the starting
team already determines the band (R5). That leaves one trap: if the band edges
are ever changed, a resumed run skips teams it has already simulated and their
stored `band` keeps the *old* definition, silently mixing two groupings in one
summary. The metrics step therefore derives the band from each row's
`total_value` against the current edges, and treats the stored `band` as a
record of what it was drawn as, not as the grouping key. Changed edges then
regroup existing rows correctly without re-simulating anything.

**Metrics (R7, R8).**

- Read the store, then **filter it to the current sample's keys**. Rows from
  another seed or sample size may be in the file and must not leak into a
  summary.
- Assign each row's band from its `total_value` against the current band edges,
  rather than trusting the stored `band` (see *Simulation and store*).
- Inner-join each challenger with the baseline on (season, team). The band comes
  along with the team, so the join needs no band term.
- Per label, season **and band**, report:
  - mean, median, P10 and max of total points;
  - mean delta in points and in %;
  - median delta and P10 delta;
  - win rate against the baseline.
- Within each season **and band**: rank the challengers by mean paired % delta.
  There is no ranking across seasons, and none across bands.
- Across seasons: only the *beats P2PM* verdict, which is true when the mean
  delta is positive in every season, pooling the bands within each season (R8).
  - **Compute it from the paired per-team rows, not by averaging the three band
    means.** With exactly N teams in every band the two agree, which is why the
    shortcut is tempting; but pairing drops teams missing from either side, so
    the bands can come out unequal and the average of band means silently stops
    being the pooled mean.
  - The summary carries the pooled per-season figure alongside the per-band
    rows, labelled as a mean over the sampled bands rather than over the
    population (R8).
- The baseline appears in the summary with zero deltas, for reference.

**Output (R9, R10).**

- The summary CSV and the per-team parquet are both in `outputs/`, with
  injectable paths.
- The summary is also logged.
- The CLI takes `--seasons`, `--sample-size`, `--seed`, `--strategies`,
  `--bands`, `--output` and `--summary`. `--strategies` is required: names come
  from a registry of the existing classes, with no default. `--bands` defaults
  to the three agreed edges and is given as the edge list `90 95 99.5 100`, so
  that the bands cannot be specified with a gap or an overlap between them
  (added 2026-09-18, R10).
- `--sample-size` is **per band**, so the default 500 draws 1,500 teams per
  season. The help text says so, since the same flag meant a per-season total
  before 2026-09-18.
- `__main__` is `setup_logging(); main()`. `main()` parses the arguments and
  makes one call to a tested `run_backtest(...)`.

## Steps

Each step is one commit, written test-first: see the test fail for the intended
reason, then implement. Where the first failure can only be an `ImportError` or
`TypeError`, show a mutation failing on its value as well.

1. **`sample_starting_teams(season, n, seed, band_edges)`** — tests:
   - the result has n rows *per band*, so 3n for the default edges;
   - every row's `total_value` falls inside the band the row is labelled with;
   - the band edges are honoured exactly at the boundary: a team valued exactly
     95.0 lands in `(90, 95]` and not in `(95, 99.5]` — the one place the
     exclusive-min/inclusive-max convention could silently disagree with
     `pd.cut`;
   - the same seed gives the same teams;
   - a different seed gives different teams;
   - n ≥ a band's population gives that whole band;
   - two seasons give independent samples;
   - edges that overlap or leave a gap raise `ValueError`.
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
   one season, two teams per band, the baseline plus one challenger. The sample
   frame carries the bands, so this function needs no edges of its own. Tests:
   - it produces one row per (label, team) with the expected key and final
     total points, carrying the team's `total_value` and `band` through from the
     sample;
   - the result matches a direct `run_for_team` call for the same team, proving
     it is the same engine;
   - a re-run skips every key and simulates nothing;
   - it flushes at the interval.
5. **`pair_with_baseline(results, baseline_label, band_edges)`** — synthetic
   frames. It takes the edges because it is where the band is re-derived from
   `total_value`; stored rows may carry a band from a previous set of edges.
   Tests:
   - deltas and % deltas per team;
   - teams missing from either side are dropped;
   - teams outside the current sample are filtered out;
   - a row's band is derived from its `total_value` against the current edges,
     so a stored `band` from different edges does not carry into the grouping.
6. **`season_summary(paired)`** — synthetic frames with hand-computed expected
   values for every R7 metric, the baseline row included. Tests:
   - one row per (label, season, band);
   - the pooled per-season row alongside them.
7. **`verdict(summary, paired)`** — synthetic frames. Tests:
   - *beats P2PM* is true only when the pooled delta is positive in every
     season;
   - challengers are ranked within each season and band by mean % delta, never
     across seasons and never across bands;
   - **the verdict is computed from the paired rows, not from the band means**:
     a fixture with unequal band sizes after pairing, where averaging the three
     band means gives a different sign from the pooled mean, pins this down.
8. **`run_backtest(seasons, n, seed, strategies, band_edges, store_path,
   summary_path)`** — ties steps 1–7 together, prepends the baseline if it isn't
   given, writes the summary CSV and logs it. Test: one season, two teams per
   band, tmp paths.
9. **`backtest/cli.py`** — tests:
   - argument parsing and defaults (completed seasons only, N=500 per band, the
     three agreed band edges);
   - `--strategies` is required;
   - unknown strategy names are rejected;
   - invalid band edges are rejected;
   - `main()` calls `run_backtest` with the parsed values.
10. **Docs** — README scripts/modules section, CLAUDE.md *Architecture* and
    *Commands*.

Throughout, R12 applies: any step that ends up duplicating or working around
something `races/`, `linear/`, `import_data/` or `scripts/` already does is
called out in session and appended to the ledger in `requirements.md`, in the
same commit as the step that incurred it.

## Verification

1. The full pytest suite is green, and was green at the start.
2. **Small real run.** `python -m backtest.cli --sample-size 20 --strategies
   StrategyMaxBudget StrategyZeroStop` over 2023–2025 — 20 per band, so 60 teams
   a season. Those two challengers are used only because the old results file
   holds their numbers for the cross-check in 3. Check that:
   - the summary is written, with a row per (label, season, band);
   - every sampled team's value really is inside its band;
   - a re-run simulates nothing;
   - peak memory fits the dev environment. This now includes holding the full
     `(90, 100]` combination frame — about 152,000 rows at its widest, against
     roughly 4,000 before — which is the one place banding could plausibly
     exceed the box (see *Sample*).
3. **Engine cross-check against the old results.** For sampled teams also present
   in `outputs/f1_fantasy_results_batch.parquet`, compare the new baseline's
   total points with the old `StrategyMaxP2PM:unlimited_chip_4` values, and the
   challengers with the `:fix_drv_chg` values, stripping `@CON` from the old
   keys. Report the share that match exactly. Archive corrections since January
   2026 can explain differences, so a mismatch is investigated rather than
   assumed to be a bug.
   - **Band A only** (noted 2026-09-18): that file was built from
     `get_starting_combinations(season, 1, 99.5)`, so it holds no team below
     99.5 and bands B and C have no historical counterpart to check against.
     This is sufficient — the engine is band-blind, so agreement on band A is
     agreement on the engine — but it does mean banding itself is verified by
     step 2 and the unit tests, not by this cross-check.
4. **Full default run.** 500 teams per band × 3 bands × 3 seasons × 3 labels:
   about 7.5 hours at ~2s per simulation, or 2.5 hours per strategy.
   [Superseded 2026-09-18: was 500 per season, about 2.5 hours in total.]
   Compare the sampled per-season means with the full-population means from the
   old file, as a check that the sample is representative — again band A only,
   for the same reason as step 3.

Steps 2–4 run against the real archive and are the "it has been run" clause.
They go in `log.md` as prose, without machine details.

## Decisions

Agreed 2026-09-13:

- **Ranking:** within each season only. There is no cross-season ranking; the
  *beats P2PM* verdict is the only cross-season output. [Superseded 2026-09-18:
  within each season *and band*. The verdict remains the only output that spans
  either dimension, and it spans bands but not seasons.]
- **Strategies:** `--strategies` is required. Zero-stop and Max budget stay in
  the registry, but only for the verification runs.

Agreed 2026-09-18:

- **One enumeration, then `pd.cut`:** one `get_starting_combinations(season, 1,
  90, 100)` per season with the bands cut out of it, rather than one call per
  band, because the bound conventions line up exactly and three calls would
  enumerate the same combinations three times (*Sample*).
- **Band as a derived column:** metrics assign the band from `total_value`
  against the current edges; the stored `band` records what a row was drawn as.
  This keeps resumed runs correct when band edges change (*Simulation and
  store*).
- **Verdict from paired rows:** pooled per season across bands, computed from
  the per-team rows rather than by averaging band means, which diverge once
  pairing drops teams (*Metrics*).
- **`--bands` takes edges, not ranges,** so gaps and overlaps are
  unrepresentable (*Output*).

## Relevant files

- `docs/backtest_v1/requirements.md`
- `docs/backtest_v1/plan.md`
- `docs/backtest_v1/log.md` (to create at step 1)
- `backtest/__init__.py`, `sample.py`, `variants.py`, `runner.py`, `metrics.py`,
  `cli.py`
- `tests/test_backtest_sample.py`, `test_backtest_variants.py`,
  `test_backtest_runner.py`, `test_backtest_metrics.py`, `test_backtest_cli.py`
- `README.md`, `CLAUDE.md` (step 10)
