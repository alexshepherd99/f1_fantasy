## Plan: Implement fast_f1 Module

TL;DR - Build the new `fast_f1` package in the repo, formalize the existing FastF1 pipeline, preserve `external_data/` as legacy experimental code, and implement a CLI-first single-run mode plus a consolidated historical gather mode.

**Current status**
- Step 1 completed: legacy `external_data/` preserved as reference only.
- Step 2 completed: new `fast_f1/` package skeleton created.
- Step 3 completed: FastF1 cache initialization implemented with directory selection, fallback defaults, and `local_cache` creation.
- Step 4 completed: weekend detection implemented with API validation tests for 2025 races.
- Step 5 completed: metric calculation implemented with offline rolling points, practice performance, aggregate rank, and new unit tests.
- Step 6 completed: actual FastF1 API wrapper implementations and validation tests added.
-- Next: create script entrypoints and historical gather mode (step 7).

Step 7 completed: CLI, output orchestration and caching

- Implemented `fast_f1/cli.py` with two modes:
   - single-race prediction mode accepting `--season` and `--race` (with interactive fallback)
   - `--historical` mode to generate consolidated metrics across seasons
- Implemented `fast_f1/output.py` to orchestrate metric building, persistence to `data/` and `outputs/`, and resume semantics when an existing consolidated file exists.
- Implemented persistent module-level caching for wrapper responses to a `local_cache` subdirectory via `fast_f1/api.py` so repeated calls are served from disk.
- Added `fast_f1/cache.py` helpers to select, persist, ensure, and expose the `local_cache` directory.
- Added targeted tests covering the new functionality:
   - `tests/test_fast_f1_cli.py`
   - `tests/test_fast_f1_output.py`
   - `tests/test_fast_f1_api_cache.py`

Status: CLI, output, API wrappers, caching, and targeted unit tests implemented and verified locally. Remaining verification: run the full pytest suite and commit changes when ready.

**Steps**
1. Keep `external_data/` and its associated tests as legacy experimental code. Use it only as a reference for the new implementation.
2. Create the `fast_f1/` package with separate modules for:
   - cache configuration and initialization
   - FastF1 API wrappers
   - practice and rolling metric computations
   - output persistence and CLI orchestration
3. Implement FastF1 cache initialization:
   - first-run prompt for cache directory choice
   - support default directories and optional custom path
   - create the directory if missing
   - create a `local_cache` subdirectory for module-level caching
4. Implement weekend detection:
   - normal weekends use `FP2` and `FP3`
   - sprint weekends use `FP1` and `SprintQualifying`
   - if required sessions are not available, stop gracefully with a log message
5. Implement metric calculation:
   - driver rolling points over the previous three races
   - constructor rolling points over the previous three races
   - practice session performance ranks
   - aggregate rank as the sum of independent indicators
6. Add API validation tests for FastF1 wrappers:
   - one API validation test per FastF1 wrapper to confirm columns/types
7. Create script entrypoints:
   - single-race prediction mode with CLI args plus optional prompt fallback
   - historical gather mode writing one consolidated Excel file to `data/`
   - cache FastF1 wrapper responses to `local_cache` for all API calls
8. Implement graceful handling for missing data:
   - if driver or constructor rolling points are unavailable, log the issue and stop cleanly
9. Add tests:
   - offline unit tests for logic functions
   - preserve legacy `external_data` tests without modifying them
10. Additional steps:
   - log every cache hit so the user can see when a cache is used
   - drivers and constructors always referred to by the three letter acronym, e.g. NOR for Norris, MCL for McLaren
11. Checks:
   - Carefully review requirements, plan, code, comments, test, highlighting any inconsistencies or missed requirements.

**Relevant files**
- `fast_f1/REQUIREMENTS.md`
- `fast_f1/PLAN.md`
- `scripts/get_fastf1_data.py`
- `external_data/fastf1_common.py`
- `external_data/get_data.py`
- `external_data/process_data.py`
- `tests/test_external_data.py`

**Verification**
1. Run the full pytest suite and confirm the new `fast_f1` tests pass with existing repo tests.
2. Run the single-race script for a sample season/race and verify an Excel file is written in `outputs/`.
3. Run the historical gather mode and verify a single consolidated file is produced in `data/`.
4. Confirm sprint weekend detection works and missing session data is handled gracefully.

## Step 4 Implementation: Weekend Detection

**What was implemented:**
- `fast_f1/weekend.py`: Core detection logic with two functions:
  - `is_sprint_weekend(available_sessions)`: Returns True if "SprintQualifying" is in sessions
  - `determine_practice_sessions(available_sessions)`: Returns ("FP2", "FP3") for normal weekends or ("FP1", "SprintQualifying") for sprint weekends. Raises RuntimeError if required sessions are missing.

- `fast_f1/api.py`: FastF1 Event wrappers:
  - `get_available_sessions_from_event(event)`: Attempts to load each known session code (FP1, FP2, FP3, SQ, SS, Q, R) and returns friendly names for available sessions
  - `select_practice_sessions_from_event(event)`: Combines event session discovery with weekend detection
  - `select_practice_sessions_from_available(sessions)`: Thin wrapper for list-based workflows

- Tests:
  - `tests/test_fastf1_weekend.py`: 5 unit tests for core logic (normal, sprint, missing-session cases)
  - `tests/test_fastf1_api_validation.py`: 2 integration tests against real FastF1 API:
    - 2025 Australia (race 1): Normal weekend with FP1, FP2, FP3, Qualifying, Race
    - 2025 China (race 2): Sprint weekend with FP1, SprintQualifying, Qualifying, Race (no separate Sprint session)

**Design choices:**
- Raises exceptions on missing sessions rather than returning None, per copilot instructions
- Event-based API (Option B): accepts FastF1 Event objects and extracts sessions dynamically
- Generic exception handling in `get_available_sessions_from_event()` to handle multiple FastF1 exception types

**Step 5 Implementation: Metric calculation**

- `fast_f1/metrics.py`: implemented internal metric derivations for:
  - driver and constructor rolling points over prior races
  - practice session performance ranks with 107% lap-time filtering
  - aggregate rank as the sum of available rank indicators
- `tests/test_fastf1_metrics.py`: added offline unit tests for rolling points, practice performance, and aggregate ranking.
- The `fast_f1/api.py` wrapper methods `get_race_results()` and `get_session_laps()` remain placeholders; actual FastF1 data fetch is pending in step 6.

**All 7 tests passing** (5 unit + 2 API validation).
