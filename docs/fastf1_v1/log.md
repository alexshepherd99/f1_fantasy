# fastf1_v1 — Log

Execution log for the fastf1_v1 effort. Newest entries at the bottom of each section. Requirements and plan live alongside in `requirements.md` and `plan.md`.

## Status summary

- Step 1 completed: legacy `external_data/` preserved as reference only.
- Step 2 completed: new `fast_f1/` package skeleton created.
- Step 3 completed: FastF1 cache initialization implemented with directory selection, fallback defaults, and `local_cache` creation.
- Step 4 completed: weekend detection implemented with API validation tests for 2025 races.
- Step 5 completed: metric calculation implemented with offline rolling points, practice performance, aggregate rank, and new unit tests.
- Step 6 completed: actual FastF1 API wrapper implementations and validation tests added.
- Step 7 completed: CLI, output orchestration and caching.
- Step 8 completed: graceful handling for missing FastF1 API data and malformed payloads implemented.

- 2026-07-25: legacy `external_data/` prototype and its tests removed; unported signals captured in `BACKLOG.md`.

Overall: CLI, output, API wrappers, caching, graceful missing-data handling, and targeted unit tests implemented and verified locally. Cache hit logging added and covered by regression tests. Remaining verification: run the full pytest suite and commit changes when ready.

- Step 12 open: centralise the empty/invalid-result cache guard into `_save_cached_dataframe` itself (`fast_f1/api.py:94-97`) rather than relying on each caller to check first. See `plan.md` step 12.

## API wrappers and caching (steps 6–7)

- `fast_f1/api.py`: implemented `get_race_results()` and `get_session_laps()` wrappers that persist responses to a module-level `local_cache` subdirectory so repeated requests are served from disk.
- `fast_f1/api.py`: logs local cache hits when cached data is loaded.
- `fast_f1/cache.py`: helpers to select, persist, create, and expose the FastF1 cache and `local_cache` paths; prompts on first-run when interactive.
- `fast_f1/output.py`: orchestration for building per-race metrics, merging driver/constructor rolling points and practice performance, aggregating ranks, and saving to Excel output files.
- `fast_f1/cli.py`: CLI entrypoints for single-race prediction and historical gather mode.
- Tests added: `tests/test_fast_f1_cli.py`, `tests/test_fast_f1_output.py`, `tests/test_fast_f1_api_cache.py` (targeted tests pass locally).

Notes and behaviors:
- `get_race_results()` will also attempt to warm-cache common practice session laps (FP1/FP2/FP3/SQ) when the Event object is loaded so subsequent `get_session_laps()` calls can be satisfied from `local_cache` without reloading the event.
- Exception handling for missing FastF1 sessions uses `fastf1.exceptions.SessionNotAvailableError` when available; a small fallback alias is provided to remain robust across FastF1 versions.

## Step 7 detail: CLI, output orchestration and caching

- Implemented `fast_f1/cli.py` with two modes:
  - single-race prediction mode accepting `--season` and `--race` (with interactive fallback)
  - `--historical` mode to generate consolidated metrics across seasons
- Implemented `fast_f1/output.py` to orchestrate metric building, persistence to `data/` and `outputs/`, and resume semantics when an existing consolidated file exists.
- Implemented persistent module-level caching for wrapper responses to a `local_cache` subdirectory via `fast_f1/api.py` so repeated calls are served from disk.
- Added `fast_f1/cache.py` helpers to select, persist, ensure, and expose the `local_cache` directory.
- Added targeted tests: `tests/test_fast_f1_cli.py`, `tests/test_fast_f1_output.py`, `tests/test_fast_f1_api_cache.py`.
- Implemented graceful handling for unavailable FastF1 API data and malformed payloads in `fast_f1/api.py`, with clean exit behavior for single-race CLI mode.

## Step 4 detail: Weekend detection

**What was implemented:**
- `fast_f1/weekend.py`: core detection logic with two functions:
  - `is_sprint_weekend(available_sessions)`: returns True if "SprintQualifying" is in sessions
  - `determine_practice_sessions(available_sessions)`: returns ("FP2", "FP3") for normal weekends or ("FP1", "SprintQualifying") for sprint weekends. Raises RuntimeError if required sessions are missing.
- `fast_f1/api.py`: FastF1 Event wrappers:
  - `get_available_sessions_from_event(event)`: attempts to load each known session code (FP1, FP2, FP3, SQ, SS, Q, R) and returns friendly names for available sessions
  - `select_practice_sessions_from_event(event)`: combines event session discovery with weekend detection
  - `select_practice_sessions_from_available(sessions)`: thin wrapper for list-based workflows
- Tests:
  - `tests/test_fastf1_weekend.py`: 5 unit tests for core logic (normal, sprint, missing-session cases)
  - `tests/test_fastf1_api_validation.py`: 2 integration tests against real FastF1 API:
    - 2025 Australia (race 1): normal weekend with FP1, FP2, FP3, Qualifying, Race
    - 2025 China (race 2): sprint weekend with FP1, SprintQualifying, Qualifying, Race (no separate Sprint session)

**Design choices:**
- Raises exceptions on missing sessions rather than returning None.
- Event-based API (Option B): accepts FastF1 Event objects and extracts sessions dynamically.
- Generic exception handling in `get_available_sessions_from_event()` to handle multiple FastF1 exception types.

## Step 5 detail: Metric calculation

- `fast_f1/metrics.py`: implemented internal metric derivations for:
  - driver and constructor rolling points over prior races
  - practice session performance ranks with 107% lap-time filtering
  - aggregate rank as the sum of available rank indicators
- `tests/test_fastf1_metrics.py`: added offline unit tests for rolling points, practice performance, and aggregate ranking.
- `fast_f1/api.py` wrapper methods `get_race_results()` and `get_session_laps()` are implemented and persist data into `local_cache`.
- All 7 tests passing (5 unit + 2 API validation).

## Missing race results & aggregate rank fix

- `fast_f1/output.py`: `build_race_metrics()` no longer fails when official Race results are missing. It now derives a minimal `current_results` from available practice session drivers (or from prior rolling drivers) and attempts to infer constructors from prior results. This allows metrics to be computed before the Race session is published.
- `fast_f1/metrics.py`: `aggregate_metrics()` updated to include both PascalCase `...Rank` and snake_case `..._rank` suffixes when summing indicators, ensuring `ConstructorRollingPointsRank` contributes to `AggregateRank`.
- Tests updated:
  - `tests/test_fast_f1_output.py`: updated/added `test_build_race_metrics_works_when_race_results_missing` to verify drivers are derived from practice, constructors are mapped from prior results, and `AggregateRank` equals the sum of rank columns including constructor rank.
  - `tests/test_fastf1_metrics.py`: updated `test_aggregate_metrics_sums_rank_columns` to include `ConstructorRollingPointsRank`.
- Verification: focused tests and the `fast_f1` sub-module test set passed locally.

## Legacy `external_data` removal (2026-07-25)

Step 1 of the plan preserved `external_data/` as a reference implementation while `fast_f1/` was built. With `fast_f1/` complete, the prototype is no longer needed and has been removed.

**Removed:** `external_data/fastf1_common.py`, `get_data.py`, `process_data.py`, `temp.py`, and `tests/test_external_data.py`. Recoverable at commit `a6616d5`.

**Why it was safe:** nothing outside the package imported it — no `scripts/`, `linear/`, `races/`, `import_data/` or `fast_f1/` module referenced it, and `tests/test_external_data.py` was its only importer. `scripts/get_fastf1_data.py` already used `fast_f1` exclusively.

**Test-suite effect:** 106 → 96 passing (the 10 removed tests), and 51s → 16s. Two of the removed tests (`test_practice_and_rolling_metrics_end_to_end`, `..._race_5`) called the live FastF1 API through a hardcoded cache path in `external_data/fastf1_common.py`, bypassing the autouse cache patch in `tests/conftest.py`; the suite is now fully offline. [Superseded 2026-07-25: `tests/test_fastf1_api_validation.py` was re-enabled and does reach the API, deliberately — see the entry below.]

**Signals not ported:** stint/tyre pace analysis (`Compound`/`TyreLife`/`FreshTyre`), per-driver reliability ratio, and season-to-date aggregate points rank had no `fast_f1/` equivalent, so they are recorded in `BACKLOG.md` with the recovery SHA rather than silently dropped.

**References updated:** `CLAUDE.md` architecture notes and the `fast_f1/__init__.py` docstring now describe the current layout. `requirements.md` and `plan.md` keep their original wording with `[Superseded 2026-07-25: …]` annotations, so the effort's history stays readable without implying the module still exists.

## API validation test re-enabled, and session loads narrowed (2026-07-25)

`tests/test_fastf1_api_validation.py` had been disabled by a local rename. It is back in the suite and deliberately reaches the live API — that is its purpose, to catch upstream changing shape under us. It is the only networked test.

**Test rewritten to test the API.** It previously went through `fast_f1.api.get_race_results` / `get_session_laps`, whose empty-frame fallbacks hardcode exactly the columns being asserted, so the column checks could not fail. It now calls FastF1 directly and asserts on known 2025 Australia values (Norris/McLaren/25 points/Finished, 20 classified drivers) and on `LapTime` still being `timedelta64`, which `metrics.py` depends on for its 107% threshold. The weekend-detection tests still go through `get_available_sessions_from_event`, which is the contract under test there.

**One cache, not two.** `tests/conftest.py` isolates the cache config into a tmp dir, so under pytest nothing called `fastf1.Cache.enable_cache` and FastF1 silently filled its own default cache at `~/.cache/fastf1` (255MB of it) instead of the configured one. A module-scoped fixture now points this file - and only this file - at the directory in `.fastf1_cache_dir`, falling back to the FastF1 default where that is unset or unreachable. `fast_f1.cache.get_default_config_file_location()` was added so the fixture can find the genuine config path despite the patch.

**Session loads narrowed to what we read.** All three `session.load()` calls in `fast_f1/api.py` now go through `_load_session()`, which passes `telemetry=False, weather=False`. Neither is ever read and telemetry dominates load time. Messages stay on: they cost roughly nothing and populate a lap's `Deleted` flag, which a future fastest-lap metric may want for excluding track-limits laps.

Verified equivalent before changing: for a normal weekend, a sprint session and a race, a selective load returns the same shape, the same columns, and byte-identical values across every column `api.py` returns.

| call | before | after |
| --- | --- | --- |
| `get_race_results(2025, 1)` | 22.6s | 5.5s |
| `get_session_laps(2025, 1, "FP2")` | 4.2s | 1.6s |
| `tests/test_fastf1_api_validation.py` | 27.2s | 4.6s |
| full suite | 98.9s | ~21s |

**Known behaviour change:** with telemetry off, race-lap `TrackStatus` values differ from a full load (practice laps are unaffected). Nothing reads that column.

**Test-suite effect:** 96 → 101 passing — the 4 re-enabled validation tests, plus `test_api_loads_only_the_session_data_it_reads`, which pins the load flags so a future full load is caught. The fake sessions in `tests/test_fast_f1_api_cache.py` and `tests/test_fast_f1_output.py` needed `**kwargs` on their `load()` methods; without it the new call raises `TypeError`, which `get_race_results` would have swallowed into an empty frame.

**Still open in `BACKLOG.md`:** the silent-failure fallbacks in `api.py` (and the `CLAUDE.md` claim that it raises `RuntimeError`), and `get_race_results` warming a session cache with four session loads that are discarded when no local cache directory is configured.

## Betting odds added as a weighted indicator (2026-07-26)

`AggregateRank` now includes a driver betting-odds rank at double the weight of
every other indicator. Odds come from the existing `data/f1_betting_odds.xlsx`
through `import_data.odds.load_odds`, not a new loader.

**Two bugs in `odds_to_pct` surfaced first and were fixed on their own commits.**
The implied probability of fractional odds `a/b` is `b/(a+b)`, not the `b/a` the
function returned. The error was negligible at long odds (100/1 gave 0.0100
against a true 0.0099) but large at short ones (9/4 gave 0.444 against 0.308).
Summed across a race, `b/a` ranged from 1.25 to 2.04 over 2026 with no stable
meaning, where `b/(a+b)` sums to 1.02–1.15 — a ~9% overround, which is what an
outright market should look like. Separately, a guard rejected any odds-on price
as invalid input; odds-on is how a strong favourite is priced, and it already
appeared twice in the data (`RUS 10-11` in race 3, `ANT 4-6` in race 10), so
`StrategyBettingOdds` could not run those two races at all.

The overround is left in rather than normalised away. Dividing every value by the
same constant changes neither the argmax of the LP objective nor a min-max
normalised rank, so de-vigging would be a no-op for both consumers. Recorded in
the `odds_to_pct` docstring so the question stays answered rather than reopened.

**Measured effect of the formula fix on `StrategyBettingOdds`:** across 2026, team
selection changed in 3 of the 9 races that previously solved, identically at
`max_concentration` 999.9 and 2.0. Two were genuine and both scored better on
actual fantasy points (+40 in race 2, +57 in race 5); the third swapped two
Cadillac drivers priced within a rounding error of each other and flips on solver
tie-breaking. Two races is not evidence the corrected formula picks better teams,
but it is not evidence of harm either, and the correctness argument stands alone.

**Log rather than linear normalisation.** Race-winner odds are skewed enough that
a linear min-max puts 18 of 22 drivers within 0.07 of zero. Checked against actual
2026 fantasy points, the odds correlate at +0.50 across the front 10 and +0.34
across the back 12 — the bookmaker prices the back of the grid coarsely (~4.5
distinct prices for 12 drivers, largest tie group ~5.5 drivers) but that grouping
still carries signal, so it is worth keeping separable rather than collapsing.

**On the 2x weight.** Odds alone correlate with fantasy points at 0.601 against
0.572 for the current `AggregateRank`; blended at 2x it scores 0.580, beating
current in 5 of 9 races with a mean delta of +0.008 (sd 0.016). At nine races,
one season and a single bookmaker snapshot, that cannot distinguish 1x from 2x
from 3x. 2x is a judgement call, and `METRIC_WEIGHTS` makes it a one-line change
once coverage accrues.

**Odds coverage is 2026 races 1–11 only**, so every 2023–2025 race takes the zero
path and the indicator has no effect there. This is expected to build over time.

**`data/fastf1_practice_rolling_metrics.xlsx` is deliberately left mixed.**
`generate_historical_metrics` skips season/race pairs already present, so existing
rows keep their unweighted `AggregateRank` and have no `OddsRank` column, while
newly computed rows have both. Delete the file and re-run `--historical` to put
every row on the new scheme.

**Test-suite effect:** 108 → 118 passing. One pre-existing test needed pinning:
`test_build_race_metrics_works_when_race_results_missing` used 2026 race 6 with
drivers ALO and PER, all of which exist in the real odds spreadsheet, so it would
have silently started reading live data through the new code path.
