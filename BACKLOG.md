# Backlog

Efforts under `docs/`:

| Effort | State |
| --- | --- |
| [`backtest_v1`](docs/backtest_v1/) | done |
| [`data_capture_v1`](docs/data_capture_v1/) | in progress |
| [`fastf1_v1`](docs/fastf1_v1/) | done |
| [`fastf1_v2`](docs/fastf1_v2/) | in progress |
| [`indicator_analysis_v1`](docs/indicator_analysis_v1/) | done |
| [`max_points_v1`](docs/max_points_v1/) | done |
| [`odds_drs_v1`](docs/odds_drs_v1/) | done |

Global list of not-yet-started work. Freeform. When an item is picked up, create `docs/<effort-name>/` (see `docs/` and `agentic`'s `shared/persistent-docs.md`) and move the item there.

An entry that runs past ~350 words gets its own `docs/<effort-name>/proposal.md`, leaving a short pointer entry in this list. Picking the item up then adds `requirements.md` / `plan.md` / `log.md` beside it as usual. The threshold is a prompt to judge, not a gate — it is where the entries here actually split (2026-07-30: seven at 110-330 words, two at 537 and 766), not a target. Note this puts a `docs/<effort-name>/` directory in place before work starts, which `agentic`'s `shared/persistent-docs.md` does not describe; it is a deliberate local extension, worth proposing upstream if it sticks.

## Unported FastF1 signals from the removed `external_data` prototype

The `external_data/` prototype was removed 2026-07-25; its code is recoverable
at commit `a6616d5` (e.g. `git show a6616d5:external_data/temp.py`). Three
signals in it have no `fast_f1/` equivalent and may be worth porting:

- **Stint / tyre pace** — per-stint lap-time analysis pulling `Compound`,
  `TyreLife` and `FreshTyre`, aggregated to a best-stint-per-driver frame.
  `fast_f1/metrics.py` ranks single fastest laps only, so tyre state and
  pace-over-a-stint are unmodelled.
- **Reliability ratio** — per-driver share of prior races in the season
  actually finished, ranked within each race. A DNF-risk signal with no
  current equivalent.
- **Season aggregate points rank** — cumulative season-to-date points per
  driver, dense-ranked per race; broader than `fast_f1`'s 3-race window.

## Bring `AggregateRank` into line with the indicator conclusions

`AggregateRank` still adds every rank column at weight 1.0, with only
`METRIC_WEIGHTS` in `fast_f1/metrics.py` setting constructor rolling points to
zero. `docs/indicator_analysis_v1/log.md`, *Conclusions*, wants driver +
constructor + FP3 on normal weekends, driver + constructor on sprint weekends,
and odds for race 1, which one flat dict cannot say. So the ranking
`fast_f1.cli` prints each race is on the older signal.

Nothing outside `fast_f1` reads the column. `fastf1_v2` builds its signal from
the component columns and defines it once in `fast_f1`, so reuse that definition
here rather than writing a second one. Changing the column moves the stored
values in `data/fastf1_practice_rolling_metrics.xlsx`, and tests in
`test_fastf1_metrics.py` and `test_fast_f1_output.py` pin today's weights.

Raised by Alex 2026-11-01, and moved here from `docs/fastf1_v2/` as its question 6
decided the strategy does not depend on it.

## Lift concentration calculation into `StrategyBase`

`StrategyBettingOdds.get_problem()` (`linear/strategy_odds.py:36-88`) builds
the concentration measure inline: for every constructor it enumerates
driver-driver and driver-constructor pairs, creates a binary auxiliary
variable per pair and adds the three linearisation constraints by hand,
then sums them into `VarType.Concentration` and caps it at
`self.max_concentration`. It's ~50 lines of near-duplicated pair logic
sitting in the middle of an otherwise short objective function.

Simplify it — the two pair loops differ only in which selection variables
they reference, so one helper for "binary AND of two selection variables"
collapses most of it — and move it up to `StrategyBase`, where
`VarType.Concentration` is already declared. Every strategy would then get
concentration for free; leaving `max_concentration` at its permissive
default keeps the other strategies' behaviour unchanged.

2026-09-20: `max_points_v1` called this a likely prerequisite and then
deliberately declined to treat it as one, requiring evidence first (its R7).
*Verification* 1 measured high variance in `StrategyMaxPoints` — it wins most
starting teams in 2025 and still loses on the mean — which *looks* like
concentration risk but does not measure it. **Concentration itself has not been
counted**, so this item is not yet justified by that effort; see
`docs/max_points_v1/log.md`, *Concentration is still an assumption* and *Next —
the per-race re-simulation*. The definition to reuse when measuring is the one
already in `strategy_odds.py`, so the metric does not need inventing.

2026-09-21: **counted, and it does not support this item.** The per-race
re-simulation measured concentration over all 210,000 team-races.
`StrategyMaxPoints` is not the more concentrated strategy — in 2024, the season
it loses worst, it holds a constructor with both its drivers ten times *less*
often than `StrategyMaxP2PM` — and concentration correlates positively with the
per-team season delta in all three seasons, with the worst teams the less
concentrated ones. So there is no measured concentration risk to constrain, and
`max_points_v1` supplies no argument for this lift. See
`docs/max_points_v1/log.md`, *The per-race re-simulation*.

**The item still stands on its own terms** — it was a simplification and reuse
argument before it was ever a risk argument, and `StrategyBettingOdds` keeps its
concentration constraint regardless. What has gone is the claim that another
strategy needs it. The metric now also exists as
`backtest/per_race.py:concentration`, matching the odds strategy's definition, so
a lift has a tested reference to check itself against.

## Source betting odds directly from a web page

`StrategyBettingOdds` (`linear/strategy_odds.py:5,14-15`),
`scripts/select_odds_start.py` and — since 2026-07-26 — `fast_f1`'s odds
indicator (`fast_f1/output.py:_load_driver_odds`) all read odds from a
hand-maintained `data/f1_betting_odds.xlsx` via
`import_data/odds.py:load_odds` — there is no API/scraper integration
anywhere in the repo. README.md notes odds are a spreadsheet input, with
ideal timing "after FP3 (and obviously before quali)."

Coverage is the binding constraint: the file holds 2026 races 1–11 only, so
the fast_f1 odds indicator contributes nothing to any 2023–2025 race and
`--historical` output is largely a constant-zero column. [2026-10-05: now 2026
races 1–17. There are still no odds for any earlier season.]

Pull odds directly from a betting-odds web page instead of manual entry,
landing in the same `Season`/`Race`/`Driver`/`Constructor`/`Odds` shape
`load_odds` already expects (odds formats like `100/1`, `9/4`, `5:2`, and
odds-on prices like `10/11` are handled by `odds_to_pct()`), so all three
consumers need no changes downstream.

## `get_race_results` downloads sessions it then discards

`get_race_results` warms a session cache as a side effect, loading
FP1/FP2/FP3/SQ in full after the race — since 2026-07-27 in
`_warm_practice_session_cache` (`fast_f1/api.py:253`). When no local cache
directory is configured `_get_local_cache_path()` returns `None`, nothing is
written and those four loads are pure waste — in the validation test that was
~19s of a 27s run. Skip the warming when there is nowhere to write it.

The related concern about the loads themselves is already resolved: `_load_session`
(`fast_f1/api.py:110`) passes `telemetry=False, weather=False` as of 2026-07-25,
which cut a session load from ~4.2s to ~1.5s. `messages=True` is kept
deliberately — it is what populates a lap's `Deleted` flag.

## Thread the odds file path through `fast_f1.output` instead of patching `load_odds`

`tests/conftest.py:12-26` autouse-patches `fast_f1.output.load_odds` to
return `{}` so metric tests never read the real
`data/f1_betting_odds.xlsx`. That patches a first-party function we own,
which `agentic`'s `coding-standards` skill says to avoid where a real call
is practical — prefer making the boundary injectable.

The boundary is already injectable one level down: `load_odds` takes
`fn: str = _FILE_BETTING_ODDS` (`import_data/odds.py:45-49`), and both
`linear/strategy_odds.py:14-15` and `tests/test_odds.py` pass it a fixture
path. Only `fast_f1` skips it — `_load_driver_odds`
(`fast_f1/output.py:37,45-52`) calls `load_odds` without `fn`, so it always
resolves to the real workbook and the sole remaining lever is patching the
function.

Thread the path instead: add an odds-file parameter to `_load_driver_odds`
and to `build_race_metrics` (`fast_f1/output.py:69`, which calls it at
:207), defaulting to the real file so production callers are unchanged.
Tests then pass `data/test_betting_odds.xlsx` — the fixture workbook
`tests/test_strategy_odds.py:7` already uses — and the autouse fixture and
the four per-test re-patches in `tests/test_fast_f1_output.py`
(:512, :538, :563, :583) can point at fixture files or a stub path rather
than replacing the loader.

Note the conftest docstring (:21-23) justifies the patch by arguing that
rebinding `import_data.odds._FILE_BETTING_ODDS` has no effect because it is
bound as a default argument at definition time. That is correct, but it
rules out patching the *constant* while overlooking the parameter that
constant defaults to, which is the injection point that already exists.
Update or drop that paragraph with the change.

Two things to watch. The autouse fixture applies suite-wide, so the
migration has to cover every test that transitively reaches
`build_race_metrics`, not just the odds tests. And pointing at a
nonexistent path is not equivalent to the current stub: `_load_driver_odds`
catches broadly and degrades to `{}` with a warning
(`fast_f1/output.py:52-66`), so tests would still pass but emit warning
noise on every run — use a real fixture file.

Raised 2026-07-27 while checking whether `agentic`'s tightened test-first
and mocking guidance required changes here. No documentation change was
needed; this is the one code-level gap it surfaced.

## No test exercises any script's `__main__` block

Tests reach into `scripts/` for individual functions — `run_multiple_teams`,
`run_single_team` (`tests/test_run_batch.py:9-10`), `check_run_ppm`
(`tests/test_derivations.py:11`) and `select_starting_team`
(`tests/test_select_starting_team.py:1`) — but a `__main__` block never runs on
import, so the wiring inside one is exercised by nothing. That is true of all
six scripts, including the four whose functions are covered. Two have no
test importing them at all: `batch_results_xl.py` and `select_odds_start.py`.

The gap is not theoretical. `scripts/get_fastf1_data.py` was deleted on
2026-07-27 (recoverable at `1282518~1`) after drifting twice without a single
red test: its season list stopped at 2025, and it still passed a `race_numbers`
argument that had been removed from `generate_historical_metrics` hours
earlier, so it would have raised `TypeError` on its first real call. Both
defects sat in its `__main__` block and were found by grepping for callers.

Two live instances of the same shape:

- `batch_results_xl.py:7` imports `_FILE_BATCH_RESULTS_PARQET` and
  `_FILE_BATCH_RESULTS_EXCEL` from `scripts.run_multiple_teams` — private
  names, across module boundaries. Renaming either breaks the script and
  nothing fails.
- `select_odds_start.py:73` hardcodes `select_odds_start_for_season(2026)` in
  its `__main__` block, the same stale-constant shape that made
  `get_fastf1_data.py` wrong.

Worth deciding the standard rather than patching case by case: either keep
`__main__` blocks to a single call into a tested function so there is nothing
in them to drift, or add an import smoke test over `scripts/` that would at
least catch a broken signature or a renamed import. The first is cheaper and
matches what `fast_f1/cli.py` already does.

`scripts/scratch.py` was raised alongside this and is already resolved —
deleted 2026-07-27, having been four lines putting a hardcoded
`/workspaces/f1_fantasy` on `sys.path` that nothing imported.

Raised 2026-07-27, immediately after deleting `get_fastf1_data.py`, when the
question "what else is unprotected in the same way" turned out to have a
concrete answer.

## Refine P2PM: better DRS nomination

Not a priority. P2PM must not change before the 2026 season ends, so build this as a
subclass.

A perfect-hindsight DRS pick would have scored +226 (2023), +103 (2024) and +98
(2025) points a season more than P2PM's current rule. That rule nominates the
selected driver with the highest rolling three-race points, and it already picks
the best driver in 60-76% of team-races. For comparison, the whole objective
change `max_points_v1` tested was worth −4 to −156. See `docs/max_points_v1/log.md`,
*The DRS nomination ceiling, measured while the data was to hand*.

`StrategyBase` now has an opt-in DRS helper: `get_drs_objective_term()` models the
boost inside the LP objective, and `get_drs_nominee()` reads it back. It was added
in `max_points_v1` step 5 and nothing calls it yet. [2026-10-05: `odds_drs_v1`
made `StrategyBettingOdds` its first caller, with odds as the values. P2PM still
does not use it. See `docs/odds_drs_v1/log.md`.] What it can and cannot buy:

- **With rolling points as the values, it nominates the same driver as today's
  rule.** For a fixed team, the LP gives DRS to the highest-valued selected driver.
  So it cannot collect any of the ceiling above. Its only effect is on team
  selection, since it rewards teams with one strong driver. Reasoned from the LP's
  structure, not run.
- **With P2PM values, it would nominate worse than today's rule**, because a value
  ratio predicts a points payoff less well than recent points do.
- **The ceiling needs a better signal, not a better mechanism.** Candidates are
  betting odds (already loaded by `StrategyBettingOdds`) or `fast_f1`'s
  `AggregateRank`. Either works as a post-hoc `get_drs_driver()` override, or as
  the helper's values if team selection should respond too. This overlaps with
  *Build a strategy on the FastF1 indicators* and its regression prerequisite
  above. [2026-11-01: that prerequisite is answered, in
  `docs/indicator_analysis_v1/log.md`, and is off this list. The strategy item has moved
  to `docs/fastf1_v2/`.] A DRS signal is a narrower first use of `AggregateRank`.
- Perfect hindsight is not achievable, so the realistic gain is some unknown
  fraction of the ceiling.

Raised 2026-09-28, from `max_points_v1`.

## Live mid-season picks with `StrategyFastF1`

**Only if** `fastf1_v2`'s back-test finds `StrategyFastF1` more effective than
`StrategyMaxP2PM`, and Alex wants to use it for mid-season picks. Otherwise drop
this item.

The strategy reads only the stored metrics file,
`data/fastf1_practice_rolling_metrics.xlsx`, and never calls FastF1. So a live pick
is two stages: build the race's metrics rows (after FP3 on a normal weekend), then
run the strategy. Today that route has three gaps, reasoned from the code on
2026-11-06 and not run:

- **Single-race mode writes elsewhere.** `fast_f1.cli --season S --race N` saves to
  `outputs/fastf1_race_S_N.xlsx`, which the strategy does not read. Pointing the
  strategy at that file fails, as the expected-points tables need the 2023–25 rows.
- **Historical mode freezes the row.** `--historical --season S` does add the race to
  the strategy's file, but it skips stored races, so the row built before the race
  had results is never rebuilt. Step 3b.3 of `fastf1_v2` had to check for such rows.
  It also exits 1 for the rounds not yet run.
- **A missing race fails quietly.** With no metrics rows for the race, the strategy
  scores every asset zero and still returns a team. That is right for the back-test
  (2026 race 19, plan step 6.5) and wrong for a live pick, which should raise.

The work: a way to put the current race's rows into the strategy's file and rebuild
them once results exist, a live-pick entry point that raises when the race has no
signal, and one command or documented sequence running both stages.
`load_signal_tables` caches per process, so a single process doing both stages
would have to build the rows before its first strategy call.

Raised by Alex 2026-11-06, during `fastf1_v2` step 6.
