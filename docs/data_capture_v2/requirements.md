# data_capture_v2 — Requirements

Opened 2026-11-08 from the `BACKLOG.md` item *Get fantasy points and prices
from BoxBox F1 Fantasy*, replacing `data_capture_v1`, which Alex cancelled the
same day. `plan.md` is not written yet; the open questions below need answers
first.

## The problem (original backlog entry, unchanged)

> Points and prices are typed into `data/f1_fantasy_archive.xlsx` by hand today.
> Get them from these two JSON files instead:
>
> - <https://boxboxf1fantasy.com/data/driver_history.json>
> - <https://boxboxf1fantasy.com/data/season_summary.json>

## Scope, as settled 2026-11-08

- **Points and prices come from BoxBox, not from typing.** A fetcher reads the
  two JSON files and writes one race's points and prices into the archive.
  This replaces `data_capture_v1`'s writer for hand-typed input (rejected
  2026-11-08: Alex chose a published source over manual capture; see the
  log).
- **`data/f1_fantasy_archive.xlsx` is the golden source for every season and
  race it already holds.** Alex's historical analysis depends on it, so none of
  it may change. BoxBox only adds races the archive does not have yet. It never
  revises one the archive already holds, even where the two disagree.
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

  Removal only stops future versions. The old blobs stay in git history.

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

`import_data/` is a core module, which is not edited without Alex's
case-by-case agreement. Reading the CSV either means rewriting
`import_history.py` in place or building a new loader alongside it. That choice
is open (see below).

## Why long format is worth it

In long format a driver who doesn't take part in a race simply has no row, so
there is no null pair to get right. The remaining case is "price known, race
not yet run", which is one row with a price and `Points = 0`. That turns the
null-vs-zero rule in `CLAUDE.md`, which a person has to remember, into a
property of the layout.

## Rough shape of the work

Chunks 1–4 carry over from `data_capture_v1`. Chunk 5 is new.

1. **Make the archive path injectable end to end.** `load_archive_data_season`
   accepts `fn` but never passes it to `load_archive_sheet` (:291-292), so
   every caller reads the real archive whatever it passes. There is also no
   fixture archive. Both block test-first work on the rest.
2. **Settle the long-format schema**: the columns, one CSV or two (drivers,
   constructors), and a fixed row order and number format.
3. **Migrate the data and prove equivalence.** A one-off converter from the 16
   existing sheets to CSV, plus a check that loads both and asserts the frames
   are identical for every season and asset type. Under
   `verify-before-data-edits`, the check plan is agreed before any CSV is
   written. `odds_source_v1`'s log (*Step 2* and *Step 3*) has a conversion
   method worth reusing.
4. **Read the CSV**, keeping both loaders' signatures and return shapes as they
   are, and keeping the integrity checks. Then remove
   `f1_fantasy_archive.xlsx`, and convert and remove
   `test_expected_values.xlsx`.
5. **Build the BoxBox fetcher.** Fetch both files, map rounds and identifiers,
   validate against the archive, write one race's rows, re-run the integrity
   checks and only then save. The previous values for each asset are shown
   alongside, so a wrong value or a driver in the wrong seat stands out before
   commit. That idea is carried over from `data_capture_v1`'s writer.

## Open questions

- **Rewrite `import_history.py`, or add a new loader beside it?** Rewriting is
  smaller but edits a core module. A new loader leaves the core alone but means
  two loaders until the old one goes. Alex's call.
- **When does the fetcher run, and what does it write?** Prices are known
  before a race and points after it. The likely shape is two writes per race:
  before the lock, the next race's prices with `Points = 0`; after the race,
  that race's points. That means updating existing rows, not only appending,
  and still never touching a race the workbook already holds.
- **Who is expected in a race?** BoxBox lists drivers with no 2026 price
  (`TSU`, `HIR_HAAS`) and drivers with prices but no results (`CAM`). The
  fetcher needs a rule for who gets a row, especially around mid-season seat
  changes.
- **How are the identifier maps kept?** Fixed tables in code, as
  `odds_source`'s `TEAM_CODES` does, raising on anything they lack, or derived
  from the archive's previous race.
- **What if BoxBox is wrong or late?** It is an unofficial third-party source.
  The fetcher needs a way to refuse a write it cannot validate, and Alex needs
  a way to correct a value by hand.
- **Row order and number format in the CSV.** A git-diffable store only pays
  off if writing one race produces a diff for that race alone. Settle this
  with the schema in chunk 2.
- **Migrating mid-season.** 2026 is live, with race 20 holding prices and
  zeroed points. The migration has to keep that state as it is.

## Definition of done

- The full suite is green before and after, and every behavioural change was
  seen failing first.
- The CSV is shown to load identically to `f1_fantasy_archive.xlsx` for all
  four seasons and both asset types, before the workbook is removed.
- Adding a race's prices, and later its points, is a single command that
  fetches from BoxBox, with the layout rules applied by the tool.
- Writing one race produces a git diff covering that race and nothing else.
- The fetcher has been run against the live BoxBox files for a real race
  weekend, not just against test fixtures.
- `README.md` and `CLAUDE.md` describe the CSV archive and its source rather
  than the wide workbook and its null/zero rule.
