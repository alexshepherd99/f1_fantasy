## Plan: Implement fast_f1 Module

TL;DR - Build the new `fast_f1` package in the repo, formalize the existing FastF1 pipeline, preserve `external_data/` as legacy experimental code, and implement a CLI-first single-run mode plus a consolidated historical gather mode.

**Current status**
- Step 1 completed: legacy `external_data/` preserved as reference only.
- Step 2 completed: new `fast_f1/` package skeleton created.
- Step 3 completed: FastF1 cache initialization implemented with directory selection, fallback defaults, and `local_cache` creation.
- Step 4 completed: weekend detection implemented with API validation tests for 2025 races.
- Next: Implement metric calculation (step 5).

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
6. Create script entrypoints:
   - single-race prediction mode with CLI args plus optional prompt fallback
   - historical gather mode writing one consolidated Excel file to `data/`
7. Implement graceful handling for missing data:
   - if driver or constructor rolling points are unavailable, log the issue and stop cleanly
8. Add tests:
   - offline unit tests for logic functions
   - one API validation test per FastF1 wrapper to confirm columns/types
   - preserve legacy `external_data` tests without modifying them

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

**All 7 tests passing** (5 unit + 2 API validation).
