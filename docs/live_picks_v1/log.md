# live_picks_v1 — Log

## 2026-11-09 — Effort opened

Picked *Live mid-season picks with `StrategyFastF1`* off `BACKLOG.md`, removed it
from that list, and quoted it unchanged in `requirements.md`. Alex widened the scope
the same day: move `run_single_team.py`'s shared code somewhere common and review
its tests, and build one pre-race script that collects the week's data, runs P2PM and
FastF1, and records the chosen pick in a committed team file with free moves, team
value and unused budget.

Settled through a grilling session of 21 questions, recorded as D1–D33 in
`requirements.md`. The reasoning that mattered:

- **The app is the truth, not the script** (Q1). Team, unused budget and free moves
  are confirmed every run, as a wrong budget would give a pick the app rejects.
- **Only the played pick is committed** (Q3). A strategy's pick is made from Alex's
  team, chosen by whichever strategy he played, so a season of them does not show
  how that strategy would do alone. That needs shadow teams, moved to the backlog.
- **The file replaces `TEAM_2026.md` without backfill** (Q4): the table lacks
  unused budget, DRS and free moves, so a backfill would invent them.
- **P2PM's race-4 Wildcard spends Alex's real chip** (Q8), free in a back-test but
  not live. `StrategyMaxP2PMNoReset` already gives the no-chip pick, so nothing in
  `linear/` changes for it.
- **Nothing the script runs after race 1 reads odds** (Q13), so missing odds is a
  warning for the record from race 2, an error only at race 1.
- **Limitless needs a finite cap** (Q15). A cap at or above `COST_PROHIBITIVE`
  would make a driver who has left the race affordable, so the cap is the sum of
  every available asset's price.

Race-1 odds check, run 2026-11-09 with `scripts/select_odds_start.py` on today's
data: limit 4 gave the same team as no limit, limits 3, 2, 1 and 0 each a different
one. One season cannot show 4 never matters, so all six limits are kept and
identical teams merged (D29). The limit-1 team today is not the one Alex played at
race 1 (`TEAM_2026.md`), most likely because the stored race-1 odds were replaced
after he picked. Not investigated: live use reads whatever odds are stored at the
time.

Core-module grants for this effort, from Alex 2026-11-09: the move of
`run_single_team.py`'s shared functions (D1, D2), and `max_cost` on
`factory_strategy` (D6), chosen over a team-copy workaround.

Added to `BACKLOG.md`: shadow teams per strategy, and BoxBox capture of a new
season, which race-1 mode needs for real use (D30).

No code written.

## 2026-11-11 — Step 1: shared code moved to `simulate/`

Done. Alex settled four questions up front so the step could run unattended: the
pin is a JSON fixture and stays, replacing `test_run_batch.py`'s length-only check;
`run_single_team.py`'s `__main__` may overwrite its xlsx; on a step 2 mismatch,
investigate and stop; and the API shape for `simulate/pick.py` and `max_cost` as
proposed (below).

- **1.1 Pin.** `data/test_run_for_team_2025.json` holds every per-race row of 2025
  from Alex's 2025 starting team, for `StrategyMaxP2PM` and `StrategyFastF1RuleRise`
  (2 × 24 rows), recorded from the code before anything moved. Two recordings in
  separate processes were byte-identical. P2PM's run includes both 2- and 3-move
  races; FastF1's never carries a move. `tests/test_simulate_season.py` compares
  rows exactly. It cannot fail before a change, so it was checked by mutation: the
  carry rule at `< 1` failed P2PM at race 9, and dropping the DRS assignment failed
  both at race 2.
- **1.2 Move.** `run_for_team`, `get_row_intermediate_results` and
  `get_strat_display_name` moved to `simulate/season.py` unchanged, apart from one
  trailing-whitespace line. `run_single_team.py` keeps its settings and `__main__`.
  `backtest/runner.py`, `backtest/per_race.py` and five test files now import from
  `simulate`. `run_single_team.py` was run before and after the move: its xlsx was
  equal by `DataFrame.equals`. That run starts at 2026 race 21, the last priced
  race, so it re-solves nothing and only shows the script still runs.
- **1.3 Test gaps (D4).** All on a hand-built world (`tests/simulate_fixtures.py`):
  four drivers in two constructors, and a test strategy that maximises a `score`
  deriv and nominates the cheapest driver for DRS. The tests cover the free-move
  carry-over at both edges of the rule, unused budget and the DRS driver carried
  into the next race, a start after race 1, the error when the solver is not
  optimal, the row's columns and order, and the name helper. Each was confirmed by
  a mutation that turned it red: the rule at `< 1` and at `< 3`, unused budget not
  carried, DRS not set, solving the start race, the raise removed, the name's
  separator, and the row's rounding.
- **1.4 Split.** `simulate/pick.py` has `solve_race(strategy, team, race, race_prev,
  season_year, max_moves) -> Pick`, a frozen dataclass of sorted drivers and
  constructors, DRS driver, `moves_used` (`int` of the solver's value, as before),
  `cost` and `unused_budget` (the solver's value, unrounded, as before). It leaves the
  team unchanged, and its `RuntimeError` now has a message. `next_free_moves` is the
  rule on its own: 3 after fewer than 2 moves, else 2. It tests the `int` where the
  old code tested the float, which gives the same answer for any value ≥ 0.
  `run_for_team` applies each pick. Tests went red against stubs first, and the pin
  is unchanged.
- **1.5 `bonus_free_transfer`** (D2), default `False`: the first race picked gets 3
  moves. It went red with the argument accepted but ignored.

Suite 657 → 676, all green. `run_single_team.py`'s 2026 replay that re-solves races
comes in step 2's verification, before and after `max_cost`.

## 2026-11-11 — Step 2: `max_cost` and the Limitless cap

Done (verified).

- **`factory_strategy(..., max_cost: float | None = None)`** (D6), the only change
  in `linear/`. `None` keeps `team.total_budget(race, race_prev)`. One side effect:
  when a cap is given the team's budget is not computed, so the `KeyError` for a held
  driver priced in neither race does not arise. The test went red on behaviour (30.5
  where 55.5 was given) with the argument accepted but ignored.
- **`solve_race(..., max_cost=None)`** passes it through, and **`limitless_cap(race)`**
  (D7) sums every available driver's and constructor's price. The test of a held
  driver who has left the race uses `StrategyMaxBudget`, which keeps him under any
  cap at or above `COST_PROHIBITIVE`. Mutating the cap to 2,000,000 made the test
  fail with him kept, at a cost of 1,000,019.99.
- **Verification, run, not reasoned**, on the final code of both commits, which also
  covers step 1:
  - **2026 replays** through `run_for_team`, recorded at `3fb7715` before the
    change and again after: the full season from the race-1 line-up (re-solving
    races 2–21) and `run_single_team.py`'s live configuration from race 21. Both
    were exactly equal. A copy with one `total_points` plus 1 compared unequal.
  - **Back-test rows.** `backtest_v1`'s P2PM sample was re-simulated into a
    scratch store: seed 1, 500 per band, 2023–25, 4,500 runs, 27 minutes. Against
    the P2PM rows in `outputs/backtest_v1_results.parquet` there were the same
    4,500 `sim_key`s, none on either side only, and all 40 columns **exactly equal**
    by `DataFrame.equals`. A copy with one `total_points` plus 1 compared unequal.
- Suite 676 → 683, all green. The probe scripts were session scratch files and are
  not kept.

Nothing in this step needed an R12 entry: both core-module changes were granted,
and nothing worked around them.

**Next: step 3, the team file.** No network, and no core-module changes expected.

## 2026-11-12 — Steps 3–5 settled up front

Alex asked for steps 3, 4 and 5 to run unattended and settled these first:

- **A season with no row, next race after race 1** (a mid-season start, such as a
  2026 handover): the script asks for the held team, unused budget and free moves
  with no defaults, and does not score a last race. Race-1 mode (step 7) only when
  the next race is race 1. This refines D29.
- **Final Fix**: the chip is chosen at the choice prompt like the other chips. When
  its race is scored the script asks for the driver swapped out and in, and predicts
  with that team. The row keeps the pre-race pick, and the next race holds that pick:
  the swap does not carry. This settles D24's "through the team entered".
- **Real runs** may use the network (BoxBox, FastF1's schedule and driver lists) with
  scratch copies of the archive, odds and team files, so nothing in `data/` changes.
- **Defaults accepted**: no `data/live_team.csv` is created, Alex starts it at the
  handover; chip strings `Wildcard`, `Limitless`, `Extra DRS`, `No Negative`,
  `Autopilot`, `Final Fix`, blank for none; Wildcard and Limitless come from `--chip`,
  the rest from the choice prompt, only unused ones offered, and recording
  `StrategyMaxP2PM` at race 4 sets `Wildcard`; a Limitless row's `UnusedBudget` is
  blank; each run's record is `outputs/live_picks/<season>_<race>_<utc>.json`;
  manual entry takes full identifiers; BoxBox's "not yet" refusals get their own
  subclass of `CaptureRefused`; saved odds pages are read every run and never moved;
  step 6 (FastF1) stays out; unforeseen design calls are decided and logged here, and
  any ungranted change to a core module stops the run.

## 2026-11-12 — Step 3: the team file

Done. `live/team_file.py`, no network and no core-module change.

- **Reading** (`read_team_file`): typed `TeamRow`s, or none when the file does not
  exist yet. It refuses a wrong header or field count, a value of the wrong type, a
  driver or constructor list that is not five (two) distinct sorted identifiers, a
  DRS driver not in the team, an unknown chip, a chip twice in a season, races out of
  order or repeated, and an `UnusedBudget` blank anywhere but a Limitless row.
- **Against the race** (`check_known`): every identifier must be in the race in the
  archive. Kept separate from reading, as it needs the season loaded.
- **Writing** (`write_row`): replaces the race's row or inserts it in race order,
  through a temporary file, with money to one decimal place. Every other line keeps
  its bytes: mutating the writer to re-format every row failed the three tests that
  check this, against a hand-written row with extra decimal places. It refuses a
  final row (points filled) and any result that breaks a rule, leaving the file as
  it was.
- **Held team** (`held_for`, D21): team and budget from the last row without
  Limitless, free moves from the last row, passed on by Wildcard or Limitless,
  otherwise `simulate.pick.next_free_moves`. A row for the race itself, from a rerun
  before the race, is ignored (mutating `<` to `<=` failed that test). A missing
  race between rows gets no special rule: the defaults come from the last row, and
  the confirmations (D12) correct them.

`tests/live_fixtures.py` is a hand-built world of twelve drivers in six constructors.
Suite 683 → 729, all green.

One finding for step 4: the archive loader turns a race's empty `Points` into 0, so
"the archive holds its points" (D15, D24) is read from the raw file
(`read_archive_file`), where they are NaN.

## 2026-11-12 — Step 4: first usable script, P2PM only

Done. `PYTHONPATH=. venv/bin/python -m live.cli [--chip wildcard|limitless]`, with
`--team-file`, `--archive-dir` and `--record-dir` for scratch runs.

- **`helpers.load_with_derivations(season, fn=data)`**: the directory now passes
  through, default unchanged, so the script and its tests can point at another
  archive. `helpers.py` is not a core module. Mutating the constructor load to drop
  it failed the test.
- **`live/archive.py`**: the next race (D15) and whether a race has points, both from
  the raw driver file. Today's archive gives 2026 race 21.
- **`live/points.py`** (D24): DRS twice, Extra DRS three times, Autopilot on the
  top-scoring driver, Final Fix's swap, No Negative left out. With DRS on VER it
  gives the app's 329 for the 2026 race-20 team.
  *Decided here:* when Final Fix swaps out the DRS driver, DRS goes to the driver
  swapped in. Not checked against the app.
- **`live/lineup.py`** (D16, D20, D22): P2PM after race 1. At race 4,
  `StrategyMaxP2PMNoReset` is listed before `StrategyMaxP2PM` while the Wildcard is
  unused, so if both pick the same team it is recorded as the one that spends no
  chip. *Decided here.* Options merge on team and DRS driver.
- **`live/display.py`** (D13, D14, D23): the table puts the held team and each option
  side by side, with prices. A held driver who has left the race is priced at the
  race before, as `Team` prices him. A typed team must be five known drivers and
  two known constructors.
- **`live/cli.py`**: scores each unscored row the archive now has points for, then
  confirmations (D12), the line-up, the table, the choice (D23), DRS (D14) and the
  chip (D19). A chip already played refuses `--chip`; the prompt offers only unused
  chips. Race 1 is refused until step 7. *Decided here:* a typed team over budget is
  asked for again; one using more moves than are free is allowed with a warning, as
  the app allows it at a points cost. Before replacing the race's own row, from an
  earlier run, the script asks, defaulting to no. A pick made after a race has run
  but before BoxBox has captured it would otherwise overwrite the row actually
  played.
- **`live/record.py`** (D8): every run, whether or not it records, saves the team
  held, every option, the race's prices and the row written to
  `outputs/live_picks/<season>_<race>_<utc>.json`.

Tests run the script end to end on a 2023 archive cut (`tests/live_archive.py`) with
the real P2PM classes and scripted answers. Its pick must equal `solve_race` on the
same team, budget and moves: the D31 comparison, run on 2023. Two tests passed
before the code existed (recording nothing, declining the replace). Each was then
confirmed by a mutation that made it fail: "x" falling through to option 1, and the
answer to the replace prompt ignored. The Limitless test was added after the code,
and failed when the cap was removed (97.2 against 121.2).

**Run, not only tested.** `live.cli` on the real archive, with a scratch team file
and record folder, answers piped in. Held: the race-20 team, unused 0.2 (race 20's
137.7 budget less its 137.5 value) and 2 free moves (race 20 made two). The script
picked BOR for HUL with DRS on VER, leaving 1.0 unused. That is the race-21 team in
`TEAM_2026.md`, and the unused budget `run_single_team.py` holds for race 21. The
repo was unchanged afterwards. **Not run yet:** scoring a real race (no 2026 race is
unscored with a row before it), and every prompt path with real typing rather than
piped answers. Gate 1 (D31) still needs the first real race.

Suite 729 → 783, all green.

## 2026-11-12 — Step 5: data collection in the script

Done, apart from FastF1 (step 6). Every run now collects before it picks:

- **`boxbox`**: `CaptureNotYet`, a subclass of `CaptureRefused`, for "results in but
  no price moved" and for the workbook race BoxBox does not show held yet.
  `boxbox.cli.capture()` is the old body of `main`, which now only catches. The
  first commit of this step went in with the workbook site unchanged and its test
  red, because a `&&` chain ending in `tail` hid the failure. It was fixed and
  amended before any push.
- **`odds_source.cli`**: `place_page` and `write_page_odds` split out of `main`, each
  taking its FastF1 call as an optional argument. Both refactors were checked by
  mutation: the existing CLI tests fail when the split-out function stops writing.
- **`live/collect.py`**: `collect_boxbox` maps the capture to done (capture or
  correct), not yet, refused (other refusals, files not understood) or failed
  (download and file errors). `collect_odds` places every saved page, skips with a
  note those for another race, and writes the race's pages oldest first by their
  save time. The FastF1 account and cache are set up only when there is a page to
  place. *Decided here:* any exception from FastF1 fails the odds step rather than
  the run, as FastF1 raises its own error types as well as network ones.
- **`live/cli.py`** (D25–D27): BoxBox runs first, then the next race is read, then
  that race's odds pages, then the pick, which loads the archive only after every
  write. Each outcome prints as it ends and again in a closing summary, and a
  refused or failed step gives exit 1 even when a pick was recorded. From race 2,
  a race with no `Odds` gets a banner before the confirmations and a line in the
  summary, without changing the exit code. *Decided here:* `--skip-collection` picks
  from what is already captured, for a rerun in the same week (to change the chip,
  say). Its steps show as skipped. The pick-flow tests use it so they never reach
  the network.

Tests with red first: the BoxBox outcome classes, the odds outcomes and their order,
the summary, the exit code and the warning. Three that passed against stubs were
checked by mutation: a credentials failure (tightened to name the credentials file
after removing the sign-in still passed it), the `Odds` check, and the no-warning
case.

**Run, not only tested.** `live.cli` with the network, on scratch copies of both
archive files and the odds file, a scratch team file holding the real race-20 row
with its points blank, and a scratch pages folder holding the committed
hand-written test page. In order:

- BoxBox downloaded and ran in correct mode for race 21 (done).
- The test page signed in to FastF1 and was placed by the real 2026 schedule as race
  20, so it was skipped with its note. The odds step was "not yet". The real odds
  file already has race 21's `Odds`, so there was no warning.
- Race 20 was scored at 329, the app's figure.
- The defaults came from that row: unused 0.2, 2 free moves.
- P2PM picked BOR for HUL, DRS VER, and the row and the record were written.
- The summary was right and the exit code 0.
- `md5sum` showed the three files in `data/` unchanged, and `git status` was clean.

**Not run:** a capture (results plus new prices) through the script, a real
Oddschecker save, and the missing-odds banner on real data.

**Found on that run, for Alex: BoxBox has gone back to race 20's prices.** Its newest
file (generated 2026-11-09 21:01 UTC) gives every race-21 price equal to the
archive's race-20 price: VER 28.8, HUL 7.8, LEC 24.7, PER 3.0, FER 28.8, RED 33.3.
The archive's race-21 prices came from its 07:12 file that morning (VER 29.1,
HUL 7.2). Any BoxBox run now, by `live.cli` or `boxbox.cli`, rewrites race 21's
prices back to race 20's in correct mode. The script's pick that run then uses
them: the same team, with 2.2 unused instead of 1.0. Nothing in `data/` was
changed. Which set the app shows is not known here. The general point: correct mode
now runs on every live run, so a stale BoxBox file rewrites prices and the same
run's pick uses them before the diff is reviewed. One option, not built: have the
script ask before writing a correction that changes prices.

Suite 783 → 802, all green.

## 2026-11-12 — Handover for the next session

### Start here

1. **Investigate BoxBox's reverted prices** (below). Alex checked the app after this
   session: **VER is 29.1**, the archive's race-21 price. So the archive is right
   and BoxBox's newest file is wrong or stale. Until this is understood, **do not run
   `boxbox.cli` or `live.cli` without `--skip-collection` or `--dry-run` for real**:
   either would rewrite race 21's prices to race 20's.
2. **Review the proposed fix** (below) with Alex. Nothing is built yet.
3. Then step 6 (FastF1). Gate 1 (D31) waits for the first real race picked with the
   script.

### The BoxBox problem

The saved copies under `outputs/boxbox/`, by the time BoxBox generated each file:

| Copy saved | Generated (UTC) | VER | HUL |
| --- | --- | --- | --- |
| `2026-11-08`, `2026-11-08T212131Z` | 2026-11-08 07:23 | 28.8 | 7.8 |
| `2026-11-09T114401Z`, `2026-11-09T120931Z` | 2026-11-09 07:12 | 29.1 | 7.2 |
| this session's scratch copy | 2026-11-09 21:01 | 28.8 | 7.8 |

The 07:12 file was captured as race 21's prices (`data_capture_v2` Gate 1), and Alex
checked every one against the app then. The 21:01 file gives every race-21 price
equal to the archive's race-20 price: VER 28.8, HUL 7.8, LEC 24.7, PER 3.0, FER 28.8,
RED 33.3. In correct mode `decide_change` takes current prices as truth, so it would
rewrite every one of them. The app still shows 29.1, so BoxBox has regressed and the
app has not.

Questions for the investigation:

- Does BoxBox's newest file still show race 20's prices? Fetch a fresh copy with
  `boxbox.cli --dry-run --copy-dir <scratch>`, which writes nothing.
- Is it only `season_summary.json`'s `current_price` that went back, or do
  `rounds`/`has_actual` and `driver_history.json` differ between the 07:12 and 21:01
  files too? Diff the two saved copies.
- Is this a one-off on BoxBox's side, or a pattern after each race, such as a
  rebuild from an older snapshot? Only later races can show that, so the copies
  saved from now on are the evidence.

### Proposed fix, for Alex to review (not built)

Two parts. Each is small and works without the other.

- **A. `live.cli` asks before writing a correction that changes prices.** The BoxBox
  step runs `capture` as a dry run first. If the change is a correction (correct
  mode) and any price differs from the archive's, the script shows the price table
  it already prints and asks: "Write these corrected prices? y/n [n]". On no,
  nothing is written. The step ends as *refused*, "correction declined", so the exit
  code is 1 and the summary shows it, and the pick goes ahead on the archive as it
  stands. On yes, it writes from the same downloaded copy (`--from-copy`), so what is
  written is what was shown. A capture (results plus the next race's prices) and a
  correction that changes only the line-up are written without asking, as now.
  This covers any wrong correction, not just this one, but only in the live script.
- **B. `boxbox.change` refuses a correction that only repeats the race before.** In
  correct mode, if every asset priced in both the target race and the race before
  has its current BoxBox price equal to the race before's archived price, and at
  least one differs from the target's, refuse with `CaptureRefused`: "BoxBox shows
  race N-1's prices for race N; its file looks stale". This covers `boxbox.cli` as
  well. It catches only this exact failure: a real correction made after a price
  update would not look like this.

Recommended: A, because a wrong price correction made without Alex seeing it is the
risk, whatever the cause. B only if the investigation shows BoxBox repeats this
pattern. Each would be tested first in the usual way. A needs `collect_boxbox` to
take the input function. B's test is the 21:01 file's shape against the fixture
archive.

### The session's report, as given to Alex

Steps 3, 4 and 5 are done, committed and pushed. The suite went from 683 to 802
tests, all passing, and the log has an entry for each step.

**Before your next real run:** BoxBox's newest file has gone back to race 20's
prices. Every race-21 price it gives equals the archive's race-20 price (VER 28.8,
HUL 7.8, LEC 24.7). The archive's race-21 prices came from BoxBox's file the morning
of 9 November (VER 29.1, HUL 7.2). So any BoxBox run now, by the new script or by
`boxbox.cli` itself, would rewrite race 21's prices back to race 20's. I haven't
touched `data/`, because I can't tell which set the app shows. It's worth checking
VER's price in the app first.

The same thing is a weak spot in step 5's design: every run now fetches BoxBox and
corrects prices, so a stale BoxBox file changes the prices that run picks with,
before you see the diff. One fix would be for the script to ask before writing a
correction that changes prices. I haven't built it; it's your call.

**What's built:**

- **Step 3, the team file:** reads, checks and writes `data/live_team.csv`, leaving
  rows it doesn't touch byte for byte. It also works out the team, unused budget and
  free moves for the next race, including after Wildcard and Limitless.
- **Step 4, the script:** `PYTHONPATH=. venv/bin/python -m live.cli [--chip
  wildcard|limitless]` follows the plan. It refuses race 1 until step 7, and every
  run saves all the picks it offered under `outputs/live_picks/`.
- **Step 5, data collection:** BoxBox, then the saved odds pages for the next race,
  then the pick. It ends with a summary and exits 1 if a step was refused or failed,
  even when a pick was recorded. It warns loudly when the race has no odds.

**Calls I made, all logged:**

- When Final Fix swaps out the DRS driver, DRS goes to the driver swapped in. I
  haven't checked this against the app.
- A typed team over budget is asked for again. One using more moves than are free is
  allowed, with a warning about the points cost.
- The script asks before replacing a race's existing row, defaulting to no. Without
  that, a run after the race but before BoxBox has the results would overwrite the
  pick you played.
- A new `--skip-collection` flag picks from what's already captured, for a rerun in
  the same week.
- `helpers.load_with_derivations` takes an optional archive folder (same default),
  and `boxbox.cli` and `odds_source.cli` have their main bodies split into functions
  the script calls. None of these are core modules.

**Real runs:** two, with nothing in `data/` changed afterwards:

- **Offline:** given the race-20 team, unused 0.2 and 2 free moves, the script picked
  the team you played at race 21 (BOR for HUL, DRS on VER) with 1.0 unused, matching
  `run_single_team.py`.
- **With the network:** a real BoxBox download and a real FastF1 sign-in and
  schedule. It scored race 20 at 329, the app's figure.

**Not yet run:**

- a BoxBox capture of race results and new prices through the script
- a real Oddschecker page
- the missing-odds warning on real data
- typing answers at a real terminal (I piped them in)
- Gate 1, which needs the first real race picked with the script

**Two slips, both fixed:** I added one block of tests with a shell command instead
of the editor. And I committed one change with a test still failing, because the
failure was hidden in a chained command; I fixed it and amended the commit before
pushing.

Step 6 (FastF1) is next and is best started in a fresh session from the log.
