# fastf1_v1 — Requirements

This module provides cached access to the FastF1 API data and derivations thereof.

The `external_data` sub-module within this repo contains sample experimental code that is preserved as legacy/experimental support only. The new `fast_f1` package is the production implementation target for race prediction and historical metric gathering.

## Purpose

Predict the outcome of a Formula 1 race using data available before the race. There are two formats of race weekend, each with a different practice/qualifying signal set.

When considering lap times, any laps that exceed 107% of the session fastest lap time are excluded from the analysis.

### Standard race weekend

Data available:
- Free Practice 2 fastest lap time
- Free Practice 3 fastest lap time

### Sprint race weekend

Data available:
- Free Practice 1 fastest lap time
- Sprint Qualifying fastest lap time

### All race weekends

Use previous performance within the same season:
- rolling total of points from the previous three races for the driver
- rolling total of points from the previous three races for the driver's constructor

## Combining indicators

For each driver, individual indicators are normalised to the range 0–1, where 1 is best.

- Lap time rank: `1 - ((driver min lap time - fastest min lap time) / (slowest min lap time - fastest min lap time))`
- Points rank: `(driver points - lowest points) / (highest points - lowest points)`

The final aggregate rank is the sum of the available indicator ranks.

## FastF1 API

### API-level cache

All source data is obtained through the FastF1 API.

The FastF1 API cache must be enabled via `fastf1.Cache.enable_cache()` before any other FastF1 API call. On first-run, the module should prompt the user to choose a cache directory from two defaults or provide a custom path:
- `/mnt/chromeos/removable/sd256/linux/fastf1_cache`
- `~/fastf1_cache`

The chosen directory must be created if missing, and an error should be raised if it cannot be created.

The cache location is persisted in the local environment when set by the user, and can be reset by the user by manually deleting the entry in the local environment. The cache location must not be committed to the git repo.

### Module-level cache

FastF1 API responses are also cached locally to disk in a subdirectory under the main cache directory. That subdirectory should be named `local_cache` and created automatically.

All wrapper calls in `fast_f1/api.py` must persist their fetched results to `local_cache` so repeated API requests can be served from disk.

## Operation

The module provides two modes of operation in `scripts/`.

### Run for specific race

- Accept season and race number via CLI arguments.
- If arguments are omitted, prompt the user interactively.
- Determine weekend type based on available session data:
  - normal weekend = `FP2` + `FP3`
  - sprint weekend = `FP1` + `SprintQualifying`
- Session availability is discovered dynamically from the FastF1 Event object by attempting to load each known session code (FP1, FP2, FP3, SQ, SS, Q, R).
- If required sessions are unavailable, the module raises `RuntimeError` with a logged message describing which sessions are missing.
- Display expected aggregate rank and ordering.
- Write detailed output to an Excel file in `outputs/` and overwrite the existing file if present.

### Gather historical data

- Process all races from 2023 to current.
- Compute metrics for each race and write all results into one consolidated Excel file in `data/`.
- The file should be checked for existing season/race combinations before recomputation, allowing interruption and resume.
- Deleting the output file should allow a full regenerate.

## Indicators

The final metric must include:
- driver rolling points rank
- constructor rolling points rank
- practice lap time ranks for the selected sessions

Driver and constructor rolling points are separate, independent indicators.

## Error behavior

- If required session data is unavailable, the module raises `RuntimeError` with a logged error message (e.g., missing FP2/FP3 for normal weekends).
- If constructor or driver rolling points data is missing, fail gracefully with a logged error message and stop execution.
- If FastF1 API event, session, or result data is unavailable or malformed, the wrapper functions should log the failure and return an empty DataFrame rather than crash.
- Single-race CLI mode should exit cleanly with an error status if required metrics cannot be built due to missing FastF1 data.
- All errors are logged before raising or stopping to provide debugging context.
- Callers should catch `RuntimeError` when required data is unavailable and handle gracefully (e.g., prompt user to retry or wait for data).

## Testing

- Unit tests must avoid live FastF1 API calls where possible.
- One explicit validation test is permitted for each FastF1 wrapper function to confirm returned columns and data types.
- Offline logic tests should use synthetic or cached data.
