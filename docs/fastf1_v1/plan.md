# fastf1_v1 — Plan

TL;DR — Build the new `fast_f1` package in the repo, formalize the existing FastF1 pipeline, preserve `external_data/` as legacy experimental code, and implement a CLI-first single-run mode plus a consolidated historical gather mode.

## Steps

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
   - if any expected data from the FastF1 API is unavailable, log the problem and return an empty DataFrame
9. Additional steps:
   - log every cache hit so the user can see when a cache is used
   - do not write empty API results to cache if the result set is empty or invalid
   - check the local cache results are being used when available
   - ensure the local cache is used for every API call
   - historical API runs should handle season parameter, and only default to all if not specified
   - historical API runs should check which races are available within a given season
10. Add tests:
    - offline unit tests for logic functions
    - preserve legacy `external_data` tests without modifying them
11. Checks:
    - Carefully review requirements, plan, code, comments, test, highlighting any inconsistencies or missed requirements.

## Relevant files

- `docs/fastf1_v1/requirements.md`
- `docs/fastf1_v1/plan.md`
- `docs/fastf1_v1/log.md`
- `scripts/get_fastf1_data.py`
- `external_data/fastf1_common.py`
- `external_data/get_data.py`
- `external_data/process_data.py`
- `tests/test_external_data.py`

## Verification

1. Run the full pytest suite and confirm the new `fast_f1` tests pass with existing repo tests.
2. Run the single-race script for a sample season/race and verify an Excel file is written in `outputs/`.
3. Run the historical gather mode and verify a single consolidated file is produced in `data/`.
4. Confirm sprint weekend detection works and missing session data is handled gracefully.
