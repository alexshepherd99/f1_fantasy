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

## Silent-failure fallbacks in `fast_f1/api.py`

`get_race_results` (`fast_f1/api.py:207-214`) and `get_session_laps`
(`:232-240`) catch every exception and return the empty frames from
`_empty_race_results_dataframe()` / `_empty_session_laps_dataframe()`, so a
network outage, a missing session and an upstream schema change all surface
identically as a well-formed empty DataFrame. Callers can't tell "no data"
from "the call failed", and any caller asserting on columns alone is
satisfied by the fallback.

Note CLAUDE.md claims `api.py` "raises `RuntimeError` (never returns `None`)
when required session data is missing" — that holds for the
`weekend.py`/`metrics.py` paths but not for these two functions. Decide
which behaviour is meant, then align code and docs.

Found while re-enabling `tests/test_fastf1_api_validation.py` (2026-07-25):
its column assertions passed against the fallback frames, because those
hardcode exactly the columns being asserted. That test now calls the FastF1
API directly and no longer depends on this, but the wrappers are unchanged.

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

`get_race_results` warms a session cache as a side effect
(`fast_f1/api.py:172-205`), loading FP1/FP2/FP3/SQ in full after the race.
When no local cache directory is configured `_get_local_cache_path()`
returns `None`, nothing is written and those four loads are pure waste — in
the validation test that was ~19s of a 27s run. Skip the warming when there
is nowhere to write it.

Worth reviewing the loads themselves at the same time: `session.load()`
defaults to pulling car telemetry, position data, weather and race control
messages, none of which we read. `load(laps=True, telemetry=False,
weather=False, messages=False)` cut a session load from ~4.2s to ~1.5s.

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
seven scripts, including the four whose functions are covered. Three have no
test importing them at all: `batch_results_xl.py`, `select_odds_start.py` and
`scratch.py`.

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

`scripts/scratch.py` is separate and simpler — four lines inserting a
hardcoded `/workspaces/f1_fantasy` onto `sys.path`, a devcontainer path that
does not exist on the current machine. It looks like straightforward deletion.

Raised 2026-07-27, immediately after deleting `get_fastf1_data.py`, when the
question "what else is unprotected in the same way" turned out to have a
concrete answer.
