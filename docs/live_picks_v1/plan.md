# live_picks_v1 — Plan

Decisions are in `requirements.md` (D-numbers). One commit per step, test first for
every behaviour change, suite green at the end of each. Steps 1–4 give a usable
P2PM-only script; a 2026 handover is optional (D33).

Core-module changes in this effort, each granted by Alex 2026-11-09 and no wider:
`scripts/run_single_team.py` loses its shared functions to `simulate/` (D1, D2), and
`linear/strategy_factory.py` gains `max_cost` (D6). Anything else that has to work
around `races/`, `linear/`, `import_data/` or `scripts/` is called out in session
and logged in R12 of `docs/backtest_v1/requirements.md`.

## Shape

- **`simulate/`**: `pick.py` (one race's pick, the free-move rule, the Limitless
  cap) and `season.py` (`run_for_team` and its row and name helpers). D1.
- **`live/`**, run as `PYTHONPATH=. venv/bin/python -m live.cli [--chip
  wildcard|limitless]`: the team file, the data collection steps, the race's
  strategy line-up, the points prediction and the CLI. Prompts go through an
  injectable input function and downloads through injectable fetchers, as
  `boxbox.cli.main` already does, so tests never reach the network or wait for input.
- **Data**: `data/live_team.csv` (committed by Alex); per-run picks under
  `outputs/live_picks/` (not committed).

## Steps

### 1. Move the shared code to `simulate/`

1.1. **Pin today's output.** A test running `run_for_team` for `StrategyMaxP2PM` and
`StrategyFastF1RuleRise` on a fixed 2025 team, asserting every per-race row against
values recorded from today's code. D3.

1.2. **Move** `run_for_team`, `get_row_intermediate_results` and
`get_strat_display_name` to `simulate/season.py` unchanged; update the imports in
`run_single_team.py`, `backtest/runner.py`, `backtest/per_race.py` and the tests.
Check `run_single_team.py` still runs, without its `__main__` overwriting
`outputs/f1_fantasy_results_single.xlsx` unless Alex wants it to.

1.3. **Fill the test gaps** (D4) on hand-built races.

1.4. **Split out the one-race pick** into `simulate/pick.py`, with the free-move rule
as its own function; `run_for_team` calls it. The pinning test stays identical.

1.5. **`bonus_free_transfer` argument** on `run_for_team`. D2.

### 2. `max_cost` on `factory_strategy`

Test first, then the argument (D6). Verify: re-simulate the stored P2PM back-test
rows with exact equality, and a before/after 2026 replay. Then the Limitless cap in
`simulate/pick.py` (D7), with the test of a team holding a driver who has left the
race.

### 3. The team file

Reading, writing (`csv` module, untouched rows keep their bytes) and validation of
`data/live_team.csv` (D9, D10): identifiers known to the race, one chip per race and
each once per season (D19), a final row never rewritten. Deriving the held team,
free moves and unused budget for the next race, including after Limitless (D21). No
network.

### 4. First usable script: P2PM, no data collection

`live/cli.py` with: next race from the archive (D15); confirmations every run
(D12); scoring the last race with chip modelling and override (D24); the strategy
line-up with Wildcard, Limitless and the race-4 rule (D16, D20, D22); the
side-by-side display with prices (D13); the choice prompt with manual entry and DRS
(D14, D23); writing the row and the `outputs/` record (D8). Until step 5, Alex runs
the BoxBox and odds captures by hand first.

### 5. Data collection in the script

BoxBox capture and every saved odds page for the next race (D25), the missing-odds
warning (D27), the step outcomes, summary and exit code (D26).

### 6. FastF1

Whether the weekend's required sessions have run (D17); the writer that replaces
one race's metrics lines and keeps every other line's bytes, and the rebuild once
a race has results with changed inputs reported (D28); running
`StrategyFastF1RuleRise`, refusing a race with no signal (D16, D18).

### 7. Race-1 mode

D29. Depends on D30's backlog item for real use, or the new season's prices entered
into the archive by hand.

## Gates

- **Gate 1 — first real race with the script** (after step 4). D31: the script's
  P2PM pick equals `run_single_team.py`'s for the same team, budget and free moves;
  the prediction equals the app's points or differs by a nameable effect. A
  difference blocks the verified label and is investigated before the next pick.
- **Gate 2 — pre-season 2027** (after step 7). A race-1 run on real prices and a
  real odds page.
- **Gate 3 — first race with a FastF1 pick shown** (after step 6). D32: the pick
  equals a back-test-style `StrategyFastF1RuleRise` run on the same inputs. Also: the
  metrics file's `git diff --numstat` shows only that race's lines changed.

## Before closing

- `CHANGELOG.md` line; `README.md` and `CLAUDE.md` describe `simulate/` and `live/`.
- `TEAM_2026.md` pointer to the file at the handover race (D11).
- Remove the backlog item's remnants and check `BACKLOG.md`'s *No test exercises any
  script's `__main__` block* still describes `run_single_team.py` correctly.
