# Backlog

Global list of not-yet-started work. Freeform. When an item is picked up, create `docs/<effort-name>/` (see `docs/` and `agentic`'s `shared/persistent-docs.md`) and move the item there.

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

## Simplify in-season data capture

Points and prices for each race are currently entered by hand into
`data/f1_fantasy_archive.xlsx`, which holds wide-format Points/Price sheets
per season with a column per race. Editing that layout race-by-race is
fiddly and easy to get wrong — in particular the null-vs-zero convention
(non-participants need both points and price null; expected participants
with a known price but no result yet need points `0`) that
`import_data/import_history.py` validates against.

Replace the manual step with a helper script that takes one race's worth of
points and prices and writes them into the archive, applying the
null/zero convention itself. That likely needs the workbook simplifying
first — a tidy long-format layout would be a much easier write target than
the current wide sheets, but `import_data/import_history.py` melts the wide
format today, so the loader and its integrity checks change with it.

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
`--historical` output is largely a constant-zero column.

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

## Build a strategy on the FastF1 indicators

`fast_f1` produces a per-driver `AggregateRank` for every race but nothing
consumes it. It is a standalone signal — `docs/fastf1_v1/` is complete as of
2026-07-27, and every strategy in `linear/` still optimises on fantasy points,
price or odds. Whether the indicators actually pick better teams than P2PM is
the open question the module was built to answer, and it cannot be answered
without a strategy and a back-test.

Add a `StrategyFastF1` subclassing `StrategyBase` that maximises `AggregateRank`
subject to the existing budget/team-size/max-moves constraints, and back-test it
against the other four.

**How the signal gets in.** Two precedents. `StrategyMaxP2PM` reads
`derivs_assets`, threaded from the `Race` object by
`strategy_factory.factory_strategy()`. `StrategyBettingOdds`
(`linear/strategy_odds.py:10-25`) ignores that and loads its own file in
`__init__`, defaulting the path to a parameter (`fn_odds`) so tests can point at
a fixture. The odds pattern is the closer fit — `AggregateRank` is a per-race
external file, not a derivation of archive data — and its file-path parameter
should be copied, not its hardcoded-default habit. A
`data/test_fastf1_metrics.xlsx` fixture will be needed, as
`tests/test_strategy_odds.py` has for odds.

Five things to settle before writing any of it.

- **Constructor identifiers do not match.** Drivers do: `fast_f1` writes the
  bare FastF1 abbreviation (`ALO`) and `load_odds` already has a
  `qualify_driver_with_constructor` flag to turn that into the repo-wide
  `ALO@AST`. Constructors do not — the fantasy side uses three-letter codes
  (`ALP`, `AST`, `AUD`, `CAD`, `FER`, `HAA`, `MCL`, `MER`, `RED`, `VRB`, `WIL`)
  and `data/fastf1_practice_rolling_metrics.xlsx` carries FastF1 team names
  (`Alpine`, `Aston Martin`, `Audi`, `Cadillac`, `Ferrari`, `Haas F1 Team`,
  `McLaren`, `Mercedes`, `Racing Bulls`, `Red Bull Racing`, `Williams`). It is a
  clean 1:1 mapping that exists nowhere in the repo, and it has to live
  somewhere both `fast_f1` and `linear` can reach — probably `common`. Watch
  mid-season and cross-season renames; `Racing Bulls`/`VRB` and `Audi`/`AUD` are
  the ones that have moved.
- **There is no constructor-level aggregate.** `AggregateRank` is per driver.
  `ConstructorRollingPointsRank` exists but carries zero weight
  (`fast_f1/metrics.py:METRIC_WEIGHTS`), and there is no constructor practice or
  odds rank at all. `StrategyBettingOdds` solved the same problem by summing its
  two drivers' values into a constructor value — "not accurate from a pure stats
  perspective, but works when using as an LP optimise variable", as README puts
  it. Either reuse that, or raise the constructor weight and build a genuine
  constructor indicator. The former is cheaper and consistent; the latter is
  what the zero weight was left adjustable for.
- **The back-test data does not exist yet.**
  `data/fastf1_practice_rolling_metrics.xlsx` currently holds 342 rows: 2023
  races 1-6 and 2026 races 1-11. `run_multiple_teams.py` walks the seasons in
  `common.F1_SEASON_CONSTRUCTORS`, which is 2023-2025, so a full
  `python -m fast_f1.cli --historical` has to complete first. That is ~70 races
  of API fetching, and worth doing before anything else here since it is the
  long pole and everything else depends on it.
- **Back-testing will only exercise part of the signal.** Odds coverage is 2026
  races 1-11 only (see *Source betting odds directly from a web page* above), so
  across 2023-2025 the `OddsRank` component is a constant zero and the back-test
  measures the practice and rolling-points indicators alone. That is the same
  limitation README already records for `StrategyBettingOdds` — "no historical
  odds could be found during development, so it's not been back-tested" — and it
  means a good back-test result understates the live strategy while a bad one is
  not conclusive against it. Say which is being measured when reporting.
- **Bias the objective towards getting P1 right.** A plain "maximise summed
  `AggregateRank`" objective treats a unit of rank at the front of the field the
  same as a unit at the back, but the fantasy scoring does not: P1 pays the most,
  and doubly so once the DRS x2 multiplier lands on that driver (`races/team.py`
  applies it to the highest-priced driver by default, and `StrategyMaxP2PM`
  overrides `get_drs_driver()` to move it). Weight the top of the field
  explicitly — either transform `AggregateRank` so the gap between 1st and 2nd
  is worth more than the gap between 10th and 11th, or add a bonus term on
  whichever driver the strategy nominates for DRS. Whatever the form, it needs
  a coefficient that can be tuned and back-tested at zero, so the unbiased
  objective stays available as the comparison case.

One game mechanic to note: `AggregateRank` needs FP2+FP3 (or FP1+Sprint
Qualifying) to have run, so this strategy cannot pick a team before practice.
That matches the odds strategy's recommended timing and rules out using it for
`select_starting_team.py`-style pre-season picks.

Raised 2026-07-27, on completing `docs/fastf1_v1/` — the module works and is
unused, which is the whole point of the next step rather than a defect in it.

## Regress the FastF1 indicator against rolling points, both versus finishing position

Before building *Build a strategy on the FastF1 indicators* above, establish
whether the new signal actually carries more information than the rolling points
total already in use. Two regressions against actual finishing position — rolling
three-race driver points versus position, and `AggregateRank` versus position —
and compare the fits.

Every column needed is already in `data/fastf1_practice_rolling_metrics.xlsx`, so
this is a single-file read with no join, no LP run and no re-fetch:

- `RollingPoints` — the three-race rolling driver points total, and
  `RollingPointsRank`, its 0–1 normalisation.
- `AggregateRank` — the weighted sum of all the indicators, and `RankPosition`,
  its integer rank within the race.
- `Position` — the actual finish, merged in from `get_race_results` by
  `build_race_metrics` (`fast_f1/output.py:139`, `fast_f1/api.py:204`) alongside
  `ClassifiedPosition`, `GridPosition`, `Status` and `Points`. Populated on every
  row of the 342 the file held at `7dad240`.

That deliberately avoids running `StrategyMaxP2PM` and comparing team outcomes:
the LP, transfer mechanics and budget constraints all sit between a signal and a
finishing position, and the question here is only which per-driver signal ranks
the field better. If the two separate clearly there is no need for the fuller
strategy-output comparison; if they do not, the strategy back-test is where to
look next.

Points to settle:

- **The two signals are not independent.** `RollingPointsRank` is a component of
  `AggregateRank`, at weight 1.0 (`fast_f1/metrics.py:METRIC_WEIGHTS`), so this
  compares the aggregate against one of its own inputs rather than against a
  rival. That is still the question worth answering — does adding practice pace
  and odds beat rolling points alone — but it means the aggregate is expected to
  fit at least as well, and the size of the improvement is the result, not its
  sign. Regressing against the practice ranks alone would give a genuinely
  independent comparison if the marginal one comes out ambiguous.
- **Rolling points here are championship points, not fantasy points.**
  `fast_f1`'s `RollingPoints` accumulates the `Points` column from the FastF1
  results, not the fantasy scoring in `data/f1_fantasy_archive.xlsx`, and P2PM
  divides by price on top of that. So this is a proxy for what `StrategyMaxP2PM`
  optimises, not the thing itself. Good enough to rank drivers; say so when
  reporting rather than calling it a P2PM comparison.
- **Rank correlation, not least squares.** Both signals and the target are
  ordinal within a race, and `Position` is bounded and discrete with retirements
  classified at the back. Spearman or Kendall per race, aggregated across races,
  fits better than pooling raw values into an OLS fit.
- **The sample is too small until `--historical` has run.**
  `data/fastf1_practice_rolling_metrics.xlsx` holds 342 rows covering 2023 races
  1–6 and 2026 races 1–11 — enough to write and sanity-check the regression
  against, not enough to conclude anything from. A full
  `python -m fast_f1.cli --historical` run fills in 2023–2025 and is a
  prerequisite here just as it is for the strategy back-test; it is the long pole
  for both. The run is resumable and skips season/race pairs already present, so
  the existing rows are not recomputed.
- **Odds coverage limits what is being compared.** Outside 2026 races 1–11 the
  `OddsRank` component of `AggregateRank` is a constant zero, so a historical
  regression measures the practice and rolling-points indicators only.

Raised 2026-07-29.
