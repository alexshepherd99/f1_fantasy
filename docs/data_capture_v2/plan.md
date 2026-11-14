# data_capture_v2 — Plan

Requirements and decisions are in `requirements.md`. One commit per step, test
first for every behaviour change, suite green at the end of each. Steps 1–5
moved the archive to CSV. Steps 7–11 build the BoxBox fetcher, and Gate 1
checks its first captures against the app. Step 6 reviews its rules once
enough weekly copies are saved. Steps 13–17 start a new season (scope added
2026-11-14), and Gate 2 checks the first real start, 2027 race 1.

## Shape

- **Archive:** two CSV files, `data/f1_fantasy_drivers.csv` and
  `data/f1_fantasy_constructors.csv`, read by a rewritten
  `import_data/import_history.py` (the core-module exception granted
  2026-11-08). Both public loaders keep their names, signatures and return
  values.
- **Fetcher:** a new package, `boxbox/`, run as
  `PYTHONPATH=. venv/bin/python -m boxbox.cli`, in the same style as
  `odds_source/`. Nothing in `races/`, `linear/` or `scripts/` changes.

## The CSV layout

Agreed by Alex 2026-11-08 (step 2), from a read-only survey of the workbook
(see the log):

- **Two files, one per asset type**, matching the two loaders. Drivers:
  `Season,Race,Constructor,Driver,Points,Price`. Constructors:
  `Season,Race,Constructor,Points,Price`. `Driver` holds the bare code
  (`NOR`), and the loader builds `NOR@MCL` from it, as it does today.
- **A row only where the asset took part.** No row means the asset did not
  take part, so the CSV never holds empty pairs. A race not yet run has its
  prices and empty `Points`, and the loader fills those points with 0, which
  is what callers get today.
- **Rows grouped by asset, not by race:** season, then each asset in the
  order of the workbook's Points sheet, then race. Today's loader returns rows
  in the Points sheet's order, and that order decides which teams a seeded
  back-test samples. `races/first_picks.py` lists starting teams in data
  order, and `backtest/sample.py` draws from that list by position. Storing
  the order lets the new loader return exactly the same frames rather than
  "the same after sorting". (It does not reach the LP solver, which sorts
  assets by name since the 2026-09-18 hash-order fix.) Adding a race still changes only that race's lines. They
  sit one per asset through the file rather than in one block. A driver new
  to a season is added after that season's last asset.
- **Numbers in their shortest form that reads back to the same value**:
  `21`, `-14`, `27.2`. The loader gives the same types as today: driver
  points and all prices as floats, constructor points as integers.
- **The loader rebuilds the full grid**: every asset of a season against
  every race in that season, with empty points and price where there is no
  row. That is the shape today's melted frames have, and the derivations
  depend on those empty rows.
- **The loader rejects a malformed file**, replacing the checks the
  Points/Price merge does today: a duplicate season–race–asset row, points
  without a price, or a column it does not know.

## Steps

1. ~~Convert the derivation test's expected values to CSV~~ — done
   2026-11-08, see log *Step 1*.

2. ~~Agree the layout and the check plan with Alex~~ — done 2026-11-08, see
   log *Step 2*.

3. ~~Convert the archive and capture the "before" state~~ — done 2026-11-08,
   see log *Step 3*. Converted from the workbook at `7a0856e`. If the workbook
   changes before step 4 lands, steps 3 and 4 are redone.

4. ~~Rewrite the loader to read the CSVs~~ — done 2026-11-08, see log
   *Step 4*.

5. ~~Remove the archive workbook, and update the docs~~ — done 2026-11-08,
   see log *Step 5*.

6. **Review the rules against the saved copies.** Moved after the build on
   2026-11-08: Alex checks the first captures against the app instead (Gate
   1), so the fetcher is built now with the rules below. Once weekly copies
   span the end of the 2026 season, look at what changes between them: when
   points appear, when prices move, and how a driver change shows up. Also
   check a web archive for older versions. Tighten the rules if they need it.
   Since 2026-11-14 this also covers the new-season mode (steps 13–17), built
   before this review. Keep the weekly dry runs going through the winter, so the
   copies show how BoxBox's files change from 2026 to 2027. Do the review
   before Gate 2.

7. ~~Fetch and save~~ — done 2026-11-08, see log *Step 7*.

8. ~~Map BoxBox to the archive~~ — done 2026-11-08, see log *Step 8*.

9. ~~Decide the change, or refuse~~ — done 2026-11-08, see log *Step 9*.

10. ~~Write the change~~ — done 2026-11-08, see log *Step 10*.

11. ~~The CLI and its docs~~ — done (dev) 2026-11-08, see log *Step 11*.
    Verified at Gate 1.

12. ~~Prices from `predictions.json`~~ — done (dev) 2026-11-13, see log
    *Step 12*. Added after `season_summary.json`'s prices went back a race
    (log, 2026-11-12). Verified at Gate 1's second race.

Steps 13–17 start a new season, per `requirements.md`'s *Scope addition,
2026-11-14*. They run unattended (*Working unattended* there), done (dev)
only, and Gate 2 verifies them.

13. ~~A finished season is not a failure~~ — done (dev) 2026-11-14, see log
    *Step 13*. When the archive's latest race is
    BoxBox's last listed round, is held and already has points, the run
    reports that the season is complete, writes nothing and exits 0. The
    copy is still saved, and the earlier-race warnings are still shown.
    `live.collect.collect_boxbox` reports this as nothing to do, not as
    refused. Every other "already has points" case is still refused.

14. **Seasons in the archive match `common.py`.** A test reads the archive
    CSVs and fails if they hold a season that `common.F1_SEASON_CONSTRUCTORS`
    does not list. It passes on today's data, so it is proved by mutation
    (a scratch archive with an extra season turns it red). A kept test also
    shows that a race-1-only season (prices, empty points) loads through
    `load_archive_data_season` and passes the integrity checks.

15. **Decide a start.** `decide_change` gains a third mode, *start*, for
    BoxBox's season when it is exactly one after the archive's latest. It
    returns race 1's rows with empty points from `predictions.json`, in the
    previous season's order with new assets after, and the number of
    constructors BoxBox prices. It refuses:
    - a season that is not the next one, or one already in the archive that
      the existing modes handle;
    - any round already held (race 1's prices can no longer be had: enter it
      by hand);
    - prices for a round other than BoxBox's first listed round (as not yet);
    - provisional prices (as not yet);
    - every carried-over asset still at its final previous-season price (as
      not yet);
    - unknown teams or driver keys, as today.
    `driver_history.json` is not read for a start, so a pre-season file
    without results is no obstacle. A test shows that a re-run before race 1
    is held is an ordinary correction.

16. **Write and report a start.** `write_change` places a new season's rows
    after the previous season's last row, in the order step 15 gives, and
    integrity-checks them against the constructor count from the change
    rather than `common.py`. The report shows each asset's final price from
    the previous season beside its new price, and marks assets new to the
    season. After writing, it prints the line to add to
    `common.F1_SEASON_CONSTRUCTORS` in the same commit. `live.collect`'s
    summary names a start as one.

17. **Rehearse, and update the docs.** Build a hand-made 2027 copy from a
    saved 2026 copy: season 2027, no round held, prices for round 1, with
    one team renamed and one driver moved. Run `boxbox.cli --from-copy`
    against a scratch copy of the archive, never `data/`. Check that the
    written rows load, follow the agreed order, and that each refusal
    triggers on a copy edited to provoke it. Record the run in the log.
    Then update `README.md`'s and `CLAUDE.md`'s BoxBox paragraphs and the
    *Not handled yet* paragraph below, replacing "not handled yet" with how
    a start works.

## How a run works

The target race `T` is the latest race of the season in the archive. Its
calendar round is the `T`th entry of BoxBox's `rounds` list, in
`season_summary.json`. Points come from `driver_history.json`. Prices come
from `predictions.json`, whose top-level `round` is the race they are for.

- **`T` has been held (`has_actual`): capture.** Fill `T`'s empty points from
  `driver_history.json`, and add race `T+1` with one row per priced asset in
  `predictions.json`, at its `current_price`.
- **`T` has not been held: correct.** Rewrite `T`'s rows (who has a row,
  and their prices) from the current prices. This is how a driver change
  after capture is fixed: re-run before the race. Points stay empty.

**It refuses, writing nothing, when:**

- **The prices are for another round.** `predictions.json`'s `round` must
  be the round of the race being priced: `T+1` for a capture, `T` for a
  correction. Still `T`'s round on a capture means BoxBox has the results
  but not the new prices yet.
- **Any price is provisional** (`price_provisional`, an optional flag).
- **Capture, but no price has moved.** Every current price equals `T`'s
  price, which means BoxBox has the results but not the new prices yet.
- **Capture, and `T` has points already.** Nothing is waiting to be filled.
- **Capture, and a driver with a row in `T` has no BoxBox result for it.**
  The same goes the other way: a BoxBox result for a driver with no row in
  `T`. Either means the line-up captured for `T` was wrong when the race ran.
  It is fixed by hand.
- **Correct, on a race that came from the workbook (2026 race 20).** Its
  values are the golden source. It is changed by hand if ever needed.
- **A BoxBox round before `T`'s has no `has_actual`, or there is no round
  after `T`.**
- **Any team name, driver key or structure it does not know.**
- **The integrity checks fail on the result**, for example a constructor
  without exactly two drivers.

**It warns, and still writes,** when BoxBox's points for an earlier race of
the season differ from the archive's. The archive stays as it is, and the
warning names each difference for Alex to look at. On 2026-11-08 every one of
the 437 driver and 209 constructor results matched. It also warns when
`season_summary.json`'s prices differ from `predictions.json`'s, naming
each; that shows whether BoxBox's 2026-11-09 fault in that file comes back.

**Not handled yet:** a new season (being built in steps 13–17). The first 2027 run needs the season in
`common.F1_SEASON_CONSTRUCTORS` and a race 1 written from prices alone. The
fetcher refuses a `season` it does not find in the archive until that is
built, before 2027 race 1.

## Gates

**Gate 1: the first real captures, checked against the app.** Brazil (2026
race 20's points, Las Vegas prices), then at least one more race. Alex checks
the written values against the F1 Fantasy app and reviews the CSV diff before
committing. A run before BoxBox updates is a correction of the not-yet-held
race at unchanged prices, which leaves the files as they are. Points and
prices now come from different files, which BoxBox can rebuild at different
times, so the round check is the expected guard against a partial update;
"no price has moved" stays behind it. The second race is also the first
capture with prices from `predictions.json`.

**Gate 2: the first real start, 2027 race 1.** This runs once the game has
published 2027's prices, after winter testing, and after step 6's review of
the winter copies. Alex runs the capture and checks every race-1 price and
seat against the F1 Fantasy app. He adds the printed line to
`common.F1_SEASON_CONSTRUCTORS`, plus any `TEAM_CODES` entry a new team needs,
then reviews the CSV diff and commits with the suite green. Expect it to find
differences in BoxBox's pre-season files that the hand-made copy could not
foresee (an empty `driver_history.json`, a season change that lands in one
file before the others, new fields). A re-run before race 1 that corrects a
late driver change is part of the gate if one happens.
