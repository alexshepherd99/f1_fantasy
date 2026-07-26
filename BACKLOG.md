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
