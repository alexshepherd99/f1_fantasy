# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project does

Applies linear programming (PuLP) to optimise F1 Fantasy team selection. It back-tests strategies (zero-stop, max-budget, max P2PM, betting odds) against all possible starting team combinations for historic seasons, accounting for game mechanics: forced transfers when a team driver becomes unavailable, price variation through the season, and unused-transfer bonuses. See `README.md` for the full strategy write-up, game-mechanic caveats (chips not handled except P2PM's race-4 reset, no cross-team point carry when a driver switches constructors mid-season, concentration risk mostly unmanaged) and the current season's team log.

## Commands

Activate the venv or prefix commands with it: `venv/bin/python`. The repo is not an installed package — modules use fully-qualified imports from repo root (`from races.team import Team`, never relative imports), so **`PYTHONPATH` must include the repo root** when running anything outside pytest (pytest's own rootdir insertion handles tests fine).

```bash
# Run full test suite
venv/bin/python -m pytest

# Run a single test file / test
venv/bin/python -m pytest tests/test_strategy_p2pm.py
venv/bin/python -m pytest tests/test_strategy_p2pm.py::test_strat_p2pm_no_moves_constraint

# Run a script (needs PYTHONPATH=. because scripts import each other as `scripts.xxx`)
PYTHONPATH=. venv/bin/python scripts/run_single_team.py
PYTHONPATH=. venv/bin/python scripts/run_multiple_teams.py

# fast_f1 CLI
PYTHONPATH=. venv/bin/python -m fast_f1.cli --season 2026 --race 10
PYTHONPATH=. venv/bin/python -m fast_f1.cli --historical
```

There is no lint/format tooling configured in this repo (no ruff/black/flake8 config) — just PEP 8 by convention.

## Agent working conventions

These come from `.github/copilot-instructions.md` and apply to Claude Code too:

- Start by running the tests in the area you're touching to confirm they're clean before changing anything; ensure the full pytest suite passes before calling work done.
- Use TDD / red-green for new code.
- Prefer asking clarifying questions over assuming, especially for anything touching more than a few functions.
- For larger changes (>3 functions impacted), propose a plan first; specs/plans get saved to `agent_docs/` (see existing pattern in `fast_f1/PLAN.md` and `fast_f1/REQUIREMENTS.md` — a living plan doc updated as steps complete, plus a separate requirements doc).
- Avoid mocking existing functions in unit tests where possible — prefer exercising real code paths with synthetic/small data.
- Always use fully-qualified imports (`from races.season import Race`), never relative imports.
- For FastF1 data-availability checks specifically: raise `RuntimeError` with a logged message rather than returning `None`/sentinels for missing data — callers must handle it explicitly.

## Architecture

Data flows through four layers, root to leaf:

1. **`import_data/`** — loads `data/f1_fantasy_archive.xlsx` (wide-format Points/Price sheets per season, per driver/constructor), melts to tidy long format, merges points+price, and validates integrity (`import_history.py`). `derivations.py` computes rolling cumulative points/price/PPM/P2PM per asset over a window (default 3 races) — P2PM (points² per million, sign-preserving) is the core "value" signal used by the P2PM strategy. `helpers.load_with_derivations(season)` is the main entrypoint scripts call to get `(driver_ppm_df, constructor_ppm_df, driver_pairs_df)`, memoized with `functools.cache`.

2. **`races/`** — turns those dataframes into an object model: `Asset`/`Driver`/`Constructor` (races/asset.py) hold price/points/derivs for one race; `Race` (races/season.py) holds all drivers+constructors for one race number; `Season` holds all races. `Team` (races/team.py) holds the current driver/constructor selection, computes valuation (falling back to the previous race's price for drivers no longer listed), applies DRS x2 scoring (highest-priced driver by default, overridable via `Strategy.get_drs_driver()`), and enforces asset-count invariants. `races/first_picks.py` enumerates all valid starting-team combinations above a budget threshold for back-testing.

3. **`linear/`** — PuLP-based strategies, all subclassing `StrategyBase` (linear/strategy_base.py). The base class validates that every available asset has a price/deriv entry, builds common LP variables (binary driver/constructor selection, `TotalCost`, `TeamMoves`, `UnusedBudget`) and constraints (budget cap, team size, max moves) in `initialise()`, then `execute()` calls the subclass's `get_problem()` for the strategy-specific objective/constraints and solves with CBC. Concrete strategies: `StrategyZeroStop`, `StrategyMaxBudget`, `StrategyMaxP2PM` (optimises rolling P2PM, overrides DRS selection), `StrategyBettingOdds` (optimises on odds, adds a concentration-risk constraint the others lack). `strategy_factory.factory_strategy()` is the glue that pulls prices/derivs out of a `Race` + current `Team` and constructs a configured strategy instance ready to `execute()`.

4. **`scripts/`** — entrypoints that wire the above together. `run_single_team.py` simulates one team forward race-by-race for one season (re-solving the LP each race, tracking free-transfer carryover); `run_multiple_teams.py` back-tests every starting combination from `first_picks` across all seasons in `common.F1_SEASON_CONSTRUCTORS`, appending to a parquet file every 100 sims so it's resumable after interruption (skips sim_keys already present). `batch_results_xl.py` converts that parquet to CSV for Tableau. `select_starting_team.py` / `select_odds_start.py` pick a season-opening line-up before any race history exists (cost-ratio based, and odds-based with concentration limits, respectively).

**`fast_f1/`** is a separate, newer subsystem (see `fast_f1/REQUIREMENTS.md` and `fast_f1/PLAN.md` for full spec/status) that pulls forward-looking signal from the FastF1 API rather than the fantasy archive: practice-session lap time ranks (FP2+FP3 on normal weekends, FP1+SprintQualifying on sprint weekends, excluding laps >107% of the fastest) combined with rolling driver/constructor points, normalised to 0–1 and summed into an `AggregateRank`. `cache.py` manages the FastF1 on-disk cache location (prompted/persisted outside the repo, plus a `local_cache` subdir for wrapper-level response caching); `api.py` wraps FastF1 calls and raises `RuntimeError` (never returns `None`) when required session data is missing; `weekend.py` detects sprint vs normal weekends; `metrics.py` computes the ranks; `output.py` orchestrates building metrics and writing to `outputs/`/`data/`; `cli.py` exposes single-race and `--historical` (all seasons/races, resumable, skips already-computed season/race pairs) modes. This module is not currently wired into any `linear/` strategy — it's a standalone predictive signal. `external_data/` is legacy/experimental code superseded by `fast_f1/`; preserved as reference only, not to be modified.

## Data conventions

- Driver identifiers are `DRIVERCODE@CONSTRUCTOR` (e.g. `HAD@RED`) in team/script config, disambiguating a driver across mid-season constructor switches.
- In `data/f1_fantasy_archive.xlsx`, a driver/constructor not participating in a race must have **both** points and price as null; if price is known for an upcoming race but points aren't in yet, points must be `0` (not null) for expected participants — this distinction is what integrity checks in `import_history.py` rely on.
- `tests/conftest.py` autouse-patches the FastF1 cache config file path into a tmp dir so tests never touch the real persisted cache location — don't remove that fixture when adding FastF1 tests.
