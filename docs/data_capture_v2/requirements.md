# data_capture_v2 — Requirements

Opened 2026-11-08 from the `BACKLOG.md` item *Get fantasy points and prices
from BoxBox F1 Fantasy*, replacing `data_capture_v1`, which Alex cancelled the
same day. The steps are in `plan.md`.

## The problem (original backlog entry, unchanged)

> Points and prices are typed into `data/f1_fantasy_archive.xlsx` by hand today.
> Get them from these two JSON files instead:
>
> - <https://boxboxf1fantasy.com/data/driver_history.json>
> - <https://boxboxf1fantasy.com/data/season_summary.json>

## Scope, as settled 2026-11-08

- **Points and prices come from BoxBox, not from typing.** A fetcher reads the
  two JSON files and writes the race just held's points and the next race's
  prices into the archive.
  This replaces `data_capture_v1`'s writer for hand-typed input (rejected
  2026-11-08: Alex chose a published source over manual capture; see the
  log).
- **`data/f1_fantasy_archive.xlsx` is the golden source for every season and
  race it already holds.** Its values have been in the CSVs since step 3, which
  were proven identical, and the workbook can be recovered at `e40dcfb`. Alex's historical analysis depends on it, so none of
  it may change. BoxBox never revises a value the workbook holds, even where
  the two disagree. The one gap it fills is 2026 race 20's points, which the
  workbook does not have yet (it holds zeros in their place).
- **Zero points for a race not yet run are not data.** The workbook holds
  them only to work around a limitation in today's code. The CSV need not
  keep them (Alex, 2026-11-08): a race not yet run can have prices and empty
  points. If callers still need the zeros, the loader supplies them, so what
  it returns stays the same.
- **A copy of both BoxBox files is saved every week from 2026-11-08,** into
  `outputs/boxbox/<YYYY-MM-DD>/` (the date saved), which git ignores. These
  copies are the history the analysis in chunk 5 works from, since BoxBox
  serves only the current version. The first copy is from 2026-11-08. Every
  fetcher run will also save the files it read, the same way. Until the
  fetcher exists, the weekly copy is saved by hand, from the repo root:

  ```bash
  d=outputs/boxbox/$(date -u +%F); mkdir -p "$d" && for f in driver_history season_summary; do curl -fsS -o "$d/$f.json" "https://boxboxf1fantasy.com/data/$f.json"; done
  ```
- **The archive moves to long-format CSV, carried over from `data_capture_v1`.**
  A CSV diffs in git, so every race the fetcher writes can be reviewed as a
  diff before it is committed. That matters more for numbers a script fetched
  from a third party than it did for numbers Alex typed. The migration must
  reproduce the workbook exactly (see *Definition of done*). Only the archive
  moves. `data/f1_betting_odds.csv` and `data/fastf1_practice_rolling_metrics.csv`
  are already CSV and are out of scope.
- **Both Excel-authored workbooks are retired and removed from the repo**,
  carried over from `data_capture_v1` (where it was added 2026-09-29, after a
  security review found local machine metadata in their file properties).
  Confirmed by Alex 2026-11-08:
  - `data/f1_fantasy_archive.xlsx` is removed after the CSV has been proven to
    load identically and the loader reads the CSV. Removing it is the last
    step, not the first.
  - `data/test_expected_values.xlsx` is the expected-values fixture for
    `tests/test_derivations.py`. It is converted to a text fixture holding the
    same values, the test is pointed at that, and then it is removed.

  Removal only stops future versions. Both files stay recoverable byte for byte
  from git history (`git show <commit>:<path>`). The log records the commit to
  recover each one from when it is removed.
- **`import_data/import_history.py` is rewritten in place to read the CSV.**
  Alex granted this exception to the core-module rule on 2026-11-08, on
  condition that very careful checks prove the old data and behaviour are
  preserved (see *Checks on the loader rewrite*).
- **The CSV layout is in `plan.md`** (*The CSV layout*), agreed by Alex
  2026-11-08: two files, a row only where an asset took part, rows in the
  workbook's Points-sheet order, and numbers in their shortest exact form.
- **One run per race weekend.** Alex runs the fetcher once, a few days after a
  race weekend. That run writes the race just held's points and the next
  race's prices (BoxBox's `current_price` by then). When BoxBox updates its
  files after a race is not known yet, so the run may come before the update.
- **If BoxBox is wrong or late, the fetcher fails loudly.** It writes nothing
  and exits non-zero, with a message saying what it found. This includes data
  that has not been updated for the race yet. The fetcher has to detect that
  case rather than write stale numbers as if they were new.
- **Re-runs correct what an earlier run wrote.** Drivers are sometimes changed
  unexpectedly, very close to a race weekend, after that race has already been
  captured. Re-running the fetcher has to rewrite the rows it wrote earlier
  (who has a row, and their prices and points) to match BoxBox. It still
  never touches the history the workbook holds.

## Checks on the loader rewrite

The bar is the one set for the last core-module change that could move results
(`max_points_v1`'s `StrategyBase` DRS helper). Agreed by Alex 2026-11-08,
before any CSV was written or any loader code changed, as
`verify-before-data-edits` requires:

- **Same data.** Before the rewrite, `load_archive_data_season` and
  `load_all_archive_data` are run against the workbook for every season and
  both asset types and their output is saved. After the rewrite they are run
  against the CSV, and each frame must be exactly equal (`DataFrame.equals`,
  so dtypes and row order count too). This holds even where the CSV leaves
  out the zero points the workbook holds, since the comparison is of what the
  loaders return, not of the files.
- **Same derived values.** `helpers.load_with_derivations` gives the same
  three frames for every season, before and after.
- **Same results.** `backtest_v1`'s stored P2PM rows are re-simulated and must
  equal the stored ones exactly, and the live 2026 `run_single_team.py`
  configuration is replayed before and after, without running its
  `__main__`, which overwrites its output file.
- **Same failures.** The integrity checks still reject the malformed inputs
  they reject today, each shown failing first.
- The full suite is green before and after.

## What BoxBox provides (looked at 2026-11-08)

Both files were downloaded once and compared against the archive with a
throwaway script that was not kept.

- **Access is allowed.** The site's `robots.txt` allows all agents on `/data/`
  and says it welcomes automated clients. Responses are cached for five
  minutes. Unlike Oddschecker (`odds_source_v1`), there is no reason not to
  fetch it with a script.
- **The current season only.** Both files hold 2026 and nothing else.
  Seasons 2023–25 have no BoxBox source, which is one more reason the
  workbook stays the golden source for history.
- **Points per race, for drivers and constructors.** `driver_history.json` has
  a `rounds` list per driver and per constructor (`round`, `circuit_id`,
  `points`, and `is_dnf` for drivers). Every one of the 437 driver results for
  2026 matched the archive exactly. Constructors matched for races 1–3. The
  rest of the constructor results have not been compared yet.
- **Prices are a snapshot, not a history.** `season_summary.json` gives each
  driver and constructor a `current_price` and a `starting_price`, with no
  price per race. `current_price` matched the archive's latest race (20) for
  every driver and constructor. What `starting_price` means is unknown: it
  differs from the archive's race-1 price for 9 drivers and 4 of the 11
  constructors, so it is not that, and it is not used.

  So **prices have to be fetched every race weekend**, between the game's
  price update and the next team lock. A missed weekend's prices cannot be
  filled in from BoxBox afterwards.
- **Races are numbered differently.** Two 2026 races were cancelled. BoxBox
  keeps calendar round numbers and skips the cancelled ones (no rounds 4 or
  5), while the archive numbers the races that were held from 1 upwards. So
  BoxBox round 6 is archive race 4. The fetcher has to map one to the other.
  `season_summary.json`'s `rounds` list has a `has_actual` flag per round,
  which marks the races that have been held.
- **Identifiers differ.** Drivers are bare codes (`VER`), with a suffix where
  one is ambiguous (`HIR_HAAS`). Each driver's price entry names a
  constructor slug (`red_bull`), and constructors are keyed by slug as well.
  All of these need mapping onto the archive's `DRIVER@CONSTRUCTOR` ids and
  constructor codes (`RED`).
- **`season_summary.json` carries a `generated_at` timestamp**, which can show
  when a price snapshot was taken.

## What the change touches

Reading the archive goes through two functions,
`load_archive_data_season` and `load_all_archive_data`
(`import_data/import_history.py:277,296`). Their callers are `helpers.py`,
`scripts/check_run_ppm.py`, `fast_f1/signal.py`, `fast_f1/indicator_analysis.py`,
`tests/test_archive_integrity.py`, `tests/test_season.py` and
`tests/test_team.py`. Both functions already return tidy long frames, so **the
move to CSV should be invisible above `import_data/`.** That is the property the
migration is checked against.

`import_data/` is a core module. Rewriting `import_history.py` in place
(rather than adding a loader beside it) was agreed by Alex on 2026-11-08,
under the checks above.

## Why long format is worth it

In long format a driver who doesn't take part in a race simply has no row, so
there is no null pair to get right. The remaining case is "price known, race
not yet run", which is one row with a price and no points. That turns the
null-vs-zero rule in `CLAUDE.md`, which a person has to remember, into a
property of the layout.

## Shape of the work

The steps are in `plan.md`. Moving the archive to CSV comes first (plan steps
1–5), then the analysis of saved BoxBox copies (step 6), then the fetcher
(steps 7–11). The fetcher shows each asset's previous values alongside the
new ones, so a wrong value or a driver in the wrong seat stands out before
commit. That idea is carried over from `data_capture_v1`.

## Open questions

Each is settled at the plan step named.

- **Who gets a row in a race?** This needs a historical analysis of the
  BoxBox files before the rule is designed, above all of what they showed
  when a driver was changed mid-season. Today's snapshot already shows three
  cases: drivers with results but no 2026 price (`TSU` with 3 races,
  `HIR_HAAS` with 1), and a driver with a price but no results (`CAM`). The
  archive records the same seat changes from its side (for example `HAD@RED`
  has no rows for races 12–14). The analysis works from the weekly copies
  saved from 2026-11-08, so it gets richer as the copies build up. Whether a
  web archive holds versions from before then has not been checked. (Step 6.)
- **How does the fetcher tell that BoxBox has not updated yet?** The
  candidates are `has_actual` for the race just held, `generated_at` against
  the race date, and whether any price moved. The analysis above should show
  which of these are reliable. (Steps 6 and 9.)
- **Which rows may a re-run rewrite?** The race just held and the next race
  are the obvious ones. The rule has to keep every value the workbook held
  fixed, apart from filling in 2026 race 20's points. (Step 10.)
- **How are the identifier maps kept?** Fixed tables in code, as
  `odds_source`'s `TEAM_CODES` does, raising on anything they lack, or derived
  from the archive's previous race. (Step 8.)
- **How does Alex correct a value BoxBox has wrong?** Failing loudly stops a
  bad write. Whether a value then gets corrected by hand in the CSV, or by
  waiting for BoxBox to fix it, is not settled. (Step 10.)
- **Do callers need the zero points?** For now the loader fills them in, so
  what it returns stays exactly the same. Dropping them for good would change
  what the loader returns and would need checks of its own, so it is outside
  this plan.

## Definition of done

- The full suite is green before and after, and every behavioural change was
  seen failing first.
- The CSV is shown to load identically to `f1_fantasy_archive.xlsx` for all
  four seasons and both asset types, before the workbook is removed.
- One command, run once per race weekend, fetches the race just held's points
  and the next race's prices from BoxBox, with the layout rules applied by the
  tool. It fails loudly and writes nothing when BoxBox has not updated or
  does not validate. A re-run corrects rows an earlier run wrote.
- Every check in *Checks on the loader rewrite* has passed.
- Writing one race produces a git diff covering that race and nothing else.
- The fetcher has been run against the live BoxBox files for a real race
  weekend, not just against test fixtures.
- `README.md` and `CLAUDE.md` describe the CSV archive and its source rather
  than the wide workbook and its null/zero rule.
