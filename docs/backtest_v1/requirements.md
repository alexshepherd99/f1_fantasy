# backtest_v1 — Requirements

**Status**: agreed 2026-09-13; under refinement from 2026-09-18, with more
expected. Implementation plan in `plan.md`, which has **not** yet been brought
in line with the 2026-09-18 changes. [Superseded 2026-09-18: `plan.md` has
since been refined for the value bands and the R12 ledger.] [Superseded
2026-09-19: refinement is finished and the effort is complete; see `log.md`.]

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
  2026-09-13). Anything they lack is worked around inside `backtest/`. Each such
  workaround is called out and logged, so the cost of this decision stays
  visible (R12, added 2026-09-18). [One exception, agreed 2026-09-18:
  `StrategyBase.get_team_selection_dict` in `linear/strategy_base.py` now
  iterates its assets in sorted order rather than hash order, making
  simulations reproducible across processes (commit `534d1a9`; see `log.md`,
  *Verification* 3). The rule otherwise stands.]
- Reuse existing helpers rather than re-implementing them:
  `helpers.load_with_derivations`, `races.first_picks.get_starting_combinations`,
  `races.season.factory_season` / `factory_race`, `races.team.factory_team_row`,
  and `scripts.run_single_team.run_for_team` as the simulation engine.

## Requirements

### R1 — Sampled starting teams

- For each season, draw N starting teams uniformly at random, without
  replacement, from `get_starting_combinations(season, 1, 99.5)`. The race and
  the minimum value match `run_multiple_teams.py`. [Superseded 2026-09-18: the
  draw is per value band, not from one population above 99.5 — see *Value
  bands* below. The race still matches `run_multiple_teams.py`.]
- The sample is seeded and reproducible: the same seed and archive data give the
  same teams. N and the seed are parameters. Default N=500, agreed 2026-09-13
  (see *Evidence*). [Superseded 2026-09-18: N=500 is per band, so 1,500 teams
  per season.]
- Each season gets its own sample, because drivers and constructors change
  between seasons.
- Within a season, every strategy, the baseline included, runs on **the same
  sample**. The comparison is paired, and a sample that differs between
  strategies breaks the pairing.
- If N is at least the number of combinations, run them all. Full enumeration
  stays available.

#### Value bands (agreed 2026-09-18)

A starting team's value is not a thing to maximise. A cheaper start leaves room
to move and may finish ahead of one that spent to the cap, and the framework
should be able to show whether it does rather than assume it either way. The
sample therefore spans the value range instead of sitting at the top of it.

- Three bands, each a `(min, max]` window on a starting team's total value,
  together partitioning `(90, 100]` with no overlap and no gap:
  - **Band A — `(99.5, 100]`** — today's population, the one every historic run
    used.
  - **Band B — `(95, 99.5]`**.
  - **Band C — `(90, 95]`**.
- N is per band: 500 each by default, so 1,500 teams per season. The resulting
  3x run cost is accepted (agreed 2026-09-18), the real runs being planned for
  more capable hardware than the current dev box.
- The set of bands is a parameter, defaulting to those three.
- Every rule above applies within each band: seeded and reproducible, its own
  sample per season, the same sample for every strategy including the baseline,
  and full enumeration when N is at least that band's population.
- The bands are equally sampled but not equally populated — band C holds roughly
  10 to 15 times as many teams as band A (measured 2026-09-18, see *Evidence*).
  Metrics are therefore reported per band (R7), and any figure pooled across
  bands is a mean over the sampled bands, not over the teams that exist.

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
- Each row records the starting team's total value and its value band, so
  metrics can group by band (R7). The band follows from the starting team, so
  the key stays unique without it (agreed 2026-09-18).
- The starting-team key comes from `str(Team)`, which currently uses the
  `DRIVER@CONSTRUCTOR` form. The existing batch parquet is not reused as a
  baseline: its keys change format partway through its history (see *Evidence*).

### R6 — Seasons

- The default is every completed season in `common.F1_SEASON_CONSTRUCTORS`; the
  set of seasons is a parameter. 2026 is left out by default while it is in
  progress, and can be requested explicitly (agreed 2026-09-13).

### R7 — Reported metrics

For each strategy and each season — and, from 2026-09-18, each value band (R1):

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

Bands are reported separately too (agreed 2026-09-18) — whether a cheaper start
does better is the question the bands exist to answer, and pooling it away
would defeat them. The only figure pooled across bands is the per-season mean
delta the R8 verdict tests.

### R8 — Success criterion

Success considers both absolute points and average improvement over P2PM
(agreed 2026-09-13):

- A strategy **beats P2PM** only if its mean paired delta is positive in every
  season. That mean pools all three bands' teams within the season; the band
  breakdown informs the reader but does not gate the verdict (agreed
  2026-09-18). Because the bands are equally sampled and unequally populated,
  the pooled mean over-weights expensive starts relative to how common they
  are — it is not an estimate of the mean over all teams above 90m, and must
  not be reported as one.
- Strategies are ranked by mean paired % delta. [Superseded 2026-09-13: the
  ranking is within each season only; there is no sensible way to compare
  performance across seasons. The every-season verdict above checks sign, not
  size, so it stays.] [2026-09-18: within each season *and* band, bands being a
  reporting dimension (R7).]
- Absolute mean season points are reported alongside the ranking.

### R9 — Output

- A per-strategy, per-season summary table is written to `outputs/` and logged.
  [Superseded 2026-09-18: per strategy, season **and band** (R7), so three times
  the rows.]
- Per-team rows stay in the results file for drill-down (e.g. Tableau), carrying
  each team's total value and band (R5) so the bands can be cut further there.

### R10 — Operation

- A CLI covering seasons, sample size, seed, strategies and output path, with
  defaults for all of them. [Superseded 2026-09-13: strategies have no default
  and must be named explicitly, because Zero-stop and Max budget are no longer
  planned for use.] [2026-09-18: the value bands are a parameter too (R1),
  defaulting to the three agreed ones. Sample size is now per band.]
- `__main__` is a single call into a tested function.

### R11 — Testing

- TDD as usual.
- Tests use a tiny sample (a few teams, one season). A single full-season
  simulation takes about 2s, so this stays fast.
- No test writes to the real `outputs/`.

### R12 — Replication of core-module functionality is called out

Raised 2026-09-18, as a requirement in its own right.

`races/`, `linear/`, `import_data/` and `scripts/` stay untouched (*Scope*), and
that decision is not up for revision here. But it has a price: every time
`backtest/` reimplements or works around something those modules already do,
that is duplicated logic to maintain and a place the two can drift apart.

- Whenever `backtest/` has to duplicate or work around core-module
  functionality, it is **called out at the time** — in session, not silently
  absorbed — and recorded in the ledger below.
- Each entry names what was needed, what `backtest/` does instead, and what it
  costs.
- This applies during implementation as much as during requirements. New
  entries are appended as they are found.
- The ledger is evidence, not a lever: it exists so the running cost of the
  untouched-modules decision is visible if it is ever worth revisiting.

**Ledger**

| Date | What was needed | What `backtest/` does instead | Cost |
|---|---|---|---|
| 2026-09-18 | Sampling within value bands (R1) | Three calls to `get_starting_combinations`, which already takes `min_total_value` and `max_total_value` with exactly the exclusive/inclusive bounds the bands need. [Superseded 2026-09-18: one call over `(90, 100]`, with the bands cut out by `pd.cut`, whose default bounds match that function's — see `plan.md`, *Sample*.] | **None.** No replication at all. |
| 2026-09-13 | Named, parameterised strategy variants (R4) | Synthetic subclasses built in `backtest/variants.py`, because `run_for_team` names a strategy by `__name__` and a `functools.partial` has none | **Moderate.** A keyword argument on the strategy classes would remove the mechanism entirely. |
| 2026-09-13 | A results store at an injectable path (R5) | Reimplements the append-and-flush loop, because `scripts.run_multiple_teams.write_batch_results` hardcodes its output path. `open_batch_results_file` and `get_starting_key` are reused unchanged. [2026-09-18, step 3: only the write is reimplemented, as `backtest.runner.append_results`; there is no separate open. It also avoids two further defects in the original — it rewrites the whole file when there is nothing new, and concatenating onto the empty store it opens upcasts integer columns to float, which is why the old results file holds `total_points` as `double`.] | **Small.** One short function, duplicating a known-buggy original. |

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
  50 minutes per strategy. The full population is about 10 hours. [Superseded
  2026-09-18: three bands of 500 make it about 2.5 hours per strategy across the
  three seasons.] [Superseded 2026-09-18: *Verification* 4 measured 0.38 s a
  simulation, so about 30 minutes per strategy for three bands of 500.]
- **Band populations** (measured 2026-09-18 from race-1 archive prices, counting
  only; the priced frame was never materialised). Teams per band for
  2023 / 2024 / 2025 — band A: 3,999 / 7,579 / 6,620; band B: 42,799 / 69,809 /
  58,751; band C: 57,575 / 74,907 / 61,777. Every band is far larger than N=500,
  so full enumeration never triggers, and band A is the scarcest by an order of
  magnitude despite being the only one sampled until now.
- **What this does not show.** It measures sampling error against the full
  population. It says nothing about season-to-season noise, which only more
  seasons would reduce. It was also measured entirely within band A, a 0.5m-wide
  window; bands B and C span 4.5m and 5m, so their per-team spread is wider and
  N=500 has *not* been shown to buy the same precision there (noted 2026-09-18).
  The band figures are read per band, so this weakens each band's precision
  rather than biasing the comparison between strategies, which stays paired on
  the same teams.
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
- **Ranking:** within each season only (R8).
- **Strategies:** named explicitly on each run, with no default (R10).

Agreed 2026-09-18:

- **Value bands:** three of them — `(99.5, 100]`, `(95, 99.5]`, `(90, 95]` —
  replacing the single `>99.5` population, because a maximised start is a
  hypothesis to test rather than the only case worth testing (R1).
- **Sample size:** 500 per band, so 1,500 per season. The 3x run cost is
  accepted; the real runs are planned for more capable hardware (R1).
- **Draw:** uniform at random within each band (R1).
- **Reporting:** per strategy, season and band (R7).
- **Verdict:** unchanged in form — the per-season mean delta must be positive in
  every season, pooling the bands. Bands inform but do not gate it (R8).
- **Replication cost:** called out whenever core-module functionality has to be
  duplicated or worked around, and recorded in a ledger (R12).

No open questions remain.
