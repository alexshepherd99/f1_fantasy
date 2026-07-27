# fastf1_v1 — Plan

TL;DR — Build the new `fast_f1` package in the repo, formalize the existing FastF1 pipeline, preserve `external_data/` as legacy experimental code, and implement a CLI-first single-run mode plus a consolidated historical gather mode.

> **Superseded 2026-07-25:** `external_data/` and `tests/test_external_data.py`
> have been removed from the repo. References to them below record the plan as
> it stood during the effort.

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
   - aggregate rank as the weighted sum of independent indicators (see `METRIC_WEIGHTS`; constructor rolling points count zero, everything else 1.0)
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

    > **Completed 2026-07-27.** Cache hits log at INFO from
    > `_load_cached_dataframe`; every `_save_cached_dataframe` call site guards
    > against caching an empty result (step 12 below centralises that guard);
    > cache use is covered by tests in `tests/test_fast_f1_api_cache.py`; the
    > event schedule was the last uncached API call and is now cached per
    > season; `--season` restricts a historical run; and race availability is
    > derived from each season's schedule instead of a hardcoded `range(1, 23)`.

10. Add tests:
    - offline unit tests for logic functions
    - preserve legacy `external_data` tests without modifying them

    > **Completed 2026-07-27.** The offline unit tests are in place — the suite
    > runs without network access apart from `tests/test_fastf1_api_validation.py`,
    > which reaches the API deliberately. The `external_data` bullet is obsolete:
    > that prototype and its tests were removed on 2026-07-25 (see the banner
    > above), so there is nothing left to preserve.
11. Checks:
    - Carefully review requirements, plan, code, comments, test, highlighting any inconsistencies or missed requirements.
12. Harden the cache-write path: `_save_cached_dataframe` (`fast_f1/api.py:94-97`)
    persists whatever dataframe it's given with no emptiness/validity check of
    its own. Today's callers happen to guard against this before calling it
    (`get_race_results`/`get_session_laps` raise first on empty/malformed
    results; the FP1–SQ warming loop `continue`s past empty laps), so nothing
    empty is cached in practice — but that correctness lives at each call
    site rather than in the cache layer, so a future or refactored wrapper
    could silently start caching empty results. Move the check into
    `_save_cached_dataframe` itself so "don't cache nothing" holds
    unconditionally.

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
