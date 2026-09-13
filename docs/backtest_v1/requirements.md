# backtest_v1 — Requirements

**Status**: draft for review, 2026-09-13. Open questions at the end.

A new back-testing framework: compare each strategy against `StrategyMaxP2PM` on a
fixed random sample of starting teams rather than every combination, and judge
it by both absolute season points and paired improvement over P2PM.

## Sources consolidated

- User request, 2026-09-13 — new top-level `backtest` module, existing scripts
  untouched, random subset of starting teams, P2PM as the paired baseline.
- `docs/max_points_v1/proposal.md`, *Tuning the coefficients* and *Back-test
  harness* — fixed-seed subsample shared across settings, paired per-team deltas,
  per-season reporting with sign consistency, win rate / median / lower decile,
  the sim-key trap, and `functools.partial` lacking `__name__`.
- BACKLOG, *Build a strategy on the FastF1 indicators* — "back-test it against
  the other four"; that strategy would be run through this framework.
- BACKLOG, *No test exercises any script's `__main__` block* — keep `__main__`
  to a single call into a tested function, as `fast_f1/cli.py` does.
- README — a full back-test "can take several hours".

## Scope

- A new top-level package `backtest/`, run as `python -m backtest.cli`.
- **No changes to any file in `scripts/`.** Importing from them is allowed.
  `scripts/run_multiple_teams.py` and its results file stay as they are.
- **No changes to `races/`, `linear/` or `import_data/` either** (agreed
  2026-09-13). Anything they lack is worked around inside `backtest/`.
- Reuse existing helpers rather than re-implementing them:
  `helpers.load_with_derivations`, `races.first_picks.get_starting_combinations`,
  `races.season.factory_season` / `factory_race`, `races.team.factory_team_row`,
  and `scripts.run_single_team.run_for_team` as the simulation engine.

## Requirements

### R1 — Sampled starting teams

- For each season, draw N starting teams uniformly at random, without
  replacement, from `get_starting_combinations(season, 1, 99.5)`. The race and
  the minimum value match `run_multiple_teams.py`.
- The sample is seeded and reproducible: the same seed and archive data give the
  same teams. N and the seed are parameters. Default N=500, agreed 2026-09-13
  (see *Evidence*).
- Each season gets its own sample, because drivers and constructors change
  between seasons.
- Within a season, every strategy, the baseline included, runs on **the same
  sample**. The comparison is paired, and a sample that differs between
  strategies breaks the pairing.
- If N is at least the number of combinations, run them all. Full enumeration
  stays available.

### R2 — P2PM baseline

- The baseline is `StrategyMaxP2PM` as currently coded, which includes the
  race-4 unlimited-moves reset.
- It is simulated on the same sample, and each challenger result is paired to
  the baseline result for the same season and starting team.
- The baseline is computed once per season and sample, then reused by every
  challenger.

### R3 — One simulation engine

- Every strategy, baseline included, is simulated by the existing
  `run_for_team`, unchanged. Its final-race `total_points` is the season result.
- This keeps the proposal's concern: two engines would drift apart on transfer
  carryover, the bonus free transfer, the race-1 skip and the DRS fallback, and
  every difference would land on the number being compared. Only the
  orchestration is new code.

### R4 — Strategy identity

- Each run carries an explicit label, used in results and keys, so that two
  configurations of one strategy class stay distinct. Named variants are in
  scope for v1 (agreed 2026-09-13); a tool that sweeps through settings is not.
- Constraint: `run_for_team` names the strategy through
  `get_strat_display_name` → `strategy.__name__`, and a `functools.partial` has
  no `__name__`. Parameterised variants therefore need to be something that does
  have one, such as a subclass defined in `backtest/`, since `linear/` is off
  limits. The mechanism is left to `plan.md`.

### R5 — Results store

- A new results file in `outputs/`, separate from
  `outputs/f1_fantasy_results_batch.parquet`. The output path is a parameter, so
  tests write to a temp directory.
- Each simulated team gets one row, keyed on (label, season, starting team).
  Resumable: keys already present are skipped.
- Results are written every 100 simulations, bounding both memory use and lost
  work.
- The starting-team key comes from `str(Team)`, which currently uses the
  `DRIVER@CONSTRUCTOR` form. The existing batch parquet is not reused as a
  baseline: its keys change format partway through its history (see *Evidence*).

### R6 — Seasons

- The default is every completed season in `common.F1_SEASON_CONSTRUCTORS`; the
  set of seasons is a parameter. 2026 is left out by default while it is in
  progress, and can be requested explicitly (agreed 2026-09-13).

### R7 — Reported metrics

For each strategy and each season:

- **Absolute:** mean, median, lower decile (P10) and max of season total points.
- **Against P2PM, paired per starting team:** mean delta in points, mean delta
  in %, median delta, lower-decile delta, and win rate (the share of starting
  teams beating P2PM).
- **Across seasons:** whether the mean delta has the same sign in every season.

The headline improvement is the mean paired % delta, matching the R8 ranking,
with the mean points delta beside it (agreed 2026-09-13).

Seasons are reported separately, never pooled into one headline. The effective
replication unit is the season, so n=3. Pairing removes starting-team noise but
does nothing about season noise.

### R8 — Success criterion

Success considers both absolute points and average improvement over P2PM
(agreed 2026-09-13):

- A strategy **beats P2PM** only if its mean paired delta is positive in every
  season.
- Strategies are ranked by mean paired % delta.
- Absolute mean season points are reported alongside the ranking.

### R9 — Output

- A per-strategy, per-season summary table is written to `outputs/` and logged.
- Per-team rows stay in the results file for drill-down (e.g. Tableau).

### R10 — Operation

- A CLI covering seasons, sample size, seed, strategies and output path, with
  defaults for all of them.
- `__main__` is a single call into a tested function.

### R11 — Testing

- TDD as usual.
- Tests use a tiny sample (a few teams, one season). A single full-season
  simulation takes about 2s, so this stays fast.
- No test writes to the real `outputs/`.

## Evidence for the sample size

Taken from the existing `outputs/f1_fantasy_results_batch.parquet` (January 2026
runs, full populations for 2023–2025 of 3,998, 7,590 and 6,618 starting teams).
Pairing used the starting team as the key, with each strategy compared against
`StrategyMaxP2PM:unlimited_chip_4`:

- **Control strategies are far from a close call.** Zero-stop and Max budget
  trail P2PM by 900–1,800 points per season and win on at most 2.3% of teams.
  Any sample size shows that.
- **A subtle difference is the real test.** Comparing P2PM without the race-4
  reset to P2PM with it gives mean deltas of +2, −38 and −154 per season
  (per-team SD 6, 99, 285). Across 50 resamples of 500 teams, the SD of the
  sample mean was at most 12 points, against a between-season spread of about
  150. At 200 teams it was at most 21.
- **Cost.** At about 2s per season simulation, 500 teams × 3 seasons is about
  50 minutes per strategy. The full population is about 10 hours.
- **What this does not show.** It measures sampling error against the full
  population. It says nothing about season-to-season noise, which only more
  seasons would reduce.
- **Incidental finding.** Starting-team keys in that parquet change format
  across its history. Runs made before commit `9d2f7ed` use bare driver codes
  (`ALO`); later runs use `ALO@AST`. Pairing across those runs needed the suffix
  stripped, which is why R5 does not rely on that file.

## Out of scope

- Any change to `scripts/`.
- `StrategyBettingOdds`: its odds only exist for 2026 races 1–13.
- A coefficient-sweep driver (`max_points_v1`'s step 5). It can be built on top
  of this framework later.
- Chips, beyond P2PM's existing race-4 reset.
- Speeding up the LP or the simulation itself, and parallel runs, given the
  memory-constrained dev environment.

## Relationship to `max_points_v1`

The proposal's *Back-test harness: reuse, do not fork* section and its commit
step 1 (parameterise `run_multiple_teams.py`) conflict with the decision not to
touch `scripts/`. On 2026-09-13 both were replaced in the proposal with pointers
to this document, as was the matching line in its BACKLOG entry. The drift risk it names is still handled here, because R3
reuses `run_for_team` rather than forking it. Of the three defects it lists in
`run_multiple_teams.py`, the hardcoded write path and the module-constant
`_SUB_STRAT` are avoided by not using that script. The `__name__` one still
applies, and R4 covers it.

## Decisions

Agreed 2026-09-13:

- **Success rule:** beats P2PM only if the delta is positive in every season;
  ranked by mean % delta; absolute points reported alongside (R8).
- **2026:** left out by default while in progress (R6).
- **Sample size:** N=500 per season, fixed seed (R1).
- **Named variants:** in v1 (R4).
- **Headline improvement:** the mean paired % delta, with the mean points delta
  beside it (R7).
- **Other modules:** `races/`, `linear/` and `import_data/` are off limits, the
  same as `scripts/` (*Scope*).
- **Conflicting `max_points_v1` passages:** replaced with pointers to this
  document (*Relationship to `max_points_v1`*).

No open questions remain.
