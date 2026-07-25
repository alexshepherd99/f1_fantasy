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

## Make the FastF1 API validation test validate the API

`tests/test_fastf1_api_validation.py` was re-enabled 2026-07-25. It hits the
network on purpose — its job is to confirm the live FastF1 API still returns
what we expect. Several things stop it doing that properly.

**Test the API, not our wrappers.** The test currently goes through
`fast_f1.api.get_race_results` / `get_session_laps`, which are caching,
error-swallowing helpers. It should call the underlying FastF1 API directly
(`event.get_session(...)`, `session.load()`, `session.results` /
`session.laps`) so the assertions are about upstream's shape, not ours. The
weekend-detection tests are fine as they are — `get_available_sessions_from_event`
is the thing under test there.

**Use the real cache, but only here.** `tests/conftest.py` autouse-patches
`CACHE_LOCATION_CONFIG_FILE` into a tmp dir, so under pytest no persisted
cache directory is found and nothing calls `fastf1.Cache.enable_cache` —
every run re-downloads full session data. These specific API calls should
instead use the real application cache from `.fastf1_cache_dir`; every
other test keeps the tmp isolation it has now.

**Silent-failure fallbacks make assertions vacuous.**
`fast_f1/api.py:207-214` and `:232-240` catch every exception and return the
empty frames from `_empty_race_results_dataframe()` /
`_empty_session_laps_dataframe()`, which hardcode exactly the columns the
test asserts on — so `set(df.columns) >= {...}` passes even when the call
failed outright. Only the `nunique() == 1` / `not df.empty` checks catch it,
and then a network outage and an upstream schema change look identical.
Calling the API directly sidesteps this for the test, but the wrappers
themselves still swallow failures. Note CLAUDE.md claims `api.py` "raises
`RuntimeError` (never returns `None`) when required session data is
missing" — true of the `weekend.py`/`metrics.py` paths, not of these two
functions. Decide which is meant to be true and align them.

**Pointless session downloads.** `get_race_results` warms a session cache as
a side effect (`fast_f1/api.py:172-205`), loading FP1/FP2/FP3/SQ after the
race. With no local cache dir configured, `_get_local_cache_path()` returns
`None` and none of it is written — four session downloads for nothing, and
20s of the test's 27s runtime. Skip the warming when there is nowhere to
write it.
