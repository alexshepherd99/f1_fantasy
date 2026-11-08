# data_capture_v2 — Plan

Requirements and decisions are in `requirements.md`. One commit per step, test
first for every behaviour change, suite green at the end of each. Steps 1–5
moved the archive to CSV. Steps 7–11 build the BoxBox fetcher, and Gate 1
checks its first captures against the app. Step 6 reviews its rules once
enough weekly copies are saved.

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

7. ~~Fetch and save~~ — done 2026-11-08, see log *Step 7*.

8. ~~Map BoxBox to the archive~~ — done 2026-11-08, see log *Step 8*.

9. **Decide the change, or refuse.** Pure logic over the archive and the
   parsed files, following *How a run works* below. It returns the rows to
   write, or raises with a message naming what it found.

10. **Write the change.** Rows of the target race are replaced in place, and
    new rows go after each asset's last row in the season, so untouched rows
    keep their bytes. The result is written to a scratch copy first, loaded
    through `load_archive_data_season`, and checked with the integrity
    checks. Only then does it replace the real files.

11. **The CLI and its docs.** `PYTHONPATH=. venv/bin/python -m boxbox.cli`
    prints each asset's previous and new values, then writes. Update
    `README.md` and `CLAUDE.md`.

## How a run works

The target race `T` is the latest race of the season in the archive. Its
calendar round is the `T`th entry of BoxBox's `rounds` list.

- **`T` has been held (`has_actual`): capture.** Fill `T`'s empty points from
  `driver_history.json`, and add race `T+1` with one row per priced asset in
  `season_summary.json`, at its `current_price`.
- **`T` has not been held: correct.** Rewrite `T`'s rows (who has a row,
  and their prices) from the current prices. This is how a driver change
  after capture is fixed: re-run before the race. Points stay empty.

**It refuses, writing nothing, when:**

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
- **Any slug, key or structure it does not know.**
- **The integrity checks fail on the result**, for example a constructor
  without exactly two drivers.

**It warns, and still writes,** when BoxBox's points for an earlier race of
the season differ from the archive's. The archive stays as it is, and the
warning names each difference for Alex to look at. On 2026-11-08 every one of
the 437 driver and 209 constructor results matched.

**Not handled yet:** a new season. The first 2027 run needs the season in
`common.F1_SEASON_CONSTRUCTORS` and a race 1 written from prices alone. The
fetcher refuses a `season` it does not find in the archive until that is
built, before 2027 race 1.

## Gates

**Gate 1: the first real captures, checked against the app.** Brazil (2026
race 20's points, Las Vegas prices), then at least one more race. Alex checks
the written values against the F1 Fantasy app and reviews the CSV diff before
committing. Running before BoxBox updates should show the "no price has
moved" refusal.
