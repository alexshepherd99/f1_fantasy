# data_capture_v2 — Plan

Requirements and decisions are in `requirements.md`. One commit per step, test
first for every behaviour change, suite green at the end of each. Steps 1–5
move the archive to CSV and can be done now. Steps 6–11 build the BoxBox
fetcher and are only outlined, because they wait on the analysis in step 6;
they are rewritten once it is done.

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

3. **Convert the archive and capture the "before" state.** Done in the gap
   between two race-data updates, from the workbook as committed. Its commit
   is recorded, because Alex keeps editing it by hand until step 5. If the
   workbook changes before step 4 lands, steps 3 and 4 are redone from the new
   commit.
   - A throwaway converter writes the two CSVs. Nothing reads them yet.
   - A separate throwaway check, sharing no logic with the converter,
     compares every workbook cell to the CSVs by key: every value, every empty
     pair as an absent row, and the 2026 placeholder zeros as empty points. It
     is shown able to fail on a damaged copy.
   - The "before" state is saved to `outputs/data_capture_v2/` (not
     committed): both loaders' output for every season and asset type,
     `helpers.load_with_derivations` for every season, and the 2026
     `run_single_team` replay. The P2PM rows already stored in
     `outputs/backtest_v1_results.parquet` are the back-test "before".

4. **Rewrite the loader to read the CSVs.** `import_history.py` reads the
   files as laid out above. `fn` is threaded through properly, fixing the bug
   where `load_archive_data_season` ignores it. The three `check_*` integrity
   functions stay unchanged.
   - Red first: loader tests against a small fixture CSV (grid rebuilt, zeros
     filled, dtypes, row order, `fn` honoured, each malformed-file rejection)
     fail against the old loader.
   - `tests/test_import_history.py` loses the tests of the functions that go
     (`convert_data_sheet`, `get_archive_sheet_infos`,
     `merge_sheet_points_price`). `tests/test_archive_integrity.py` is
     rewritten to load through the new loader before calling the same checks.
     Both edits are logged.
   - Then every check in *Checks on the loader rewrite* runs against the
     "before" state: loader output and derivations exactly equal; the
     `backtest_v1` P2PM sample (seed 1, 500 per band, 2023–25, about 30
     minutes) re-simulated into a scratch store and exactly equal; the 2026
     replay exactly equal. Each comparison is shown able to fail.

5. **Remove the archive workbook, and update the docs.** `git rm`
   `data/f1_fantasy_archive.xlsx`, with the recovery commit in the log.
   `README.md` and `CLAUDE.md` describe the two CSVs and the "no row means did
   not take part" rule, replacing the null/zero rule. From here on, Alex
   enters each race into the CSVs by hand until the fetcher takes over.

6. **Analyse the saved BoxBox copies.** Run once weekly copies span the end
   of the 2026 season (Brazil to Abu Dhabi, about five copies). Look at what
   changes between copies: when points appear after a race, when prices move,
   and how a driver change shows up. Also check a web archive for older
   versions. The findings decide the open questions on who gets a row and on
   spotting files that have not been updated. Steps 7–11 are then rewritten
   in detail. Five copies may not include a driver change, and if so the log
   says so.

7. **Fetch and save.** Download both files, save the copy to
   `outputs/boxbox/<date>/` (never overwriting an earlier copy), and check
   the file's `season` is the one being captured.

8. **Map BoxBox to the archive.** Calendar round to archive race. Driver code
   and constructor slug to `DRIVER@CON` and constructor code. Decide here
   between fixed tables in code and deriving them from the previous race. An
   unknown code fails loudly.

9. **Refuse stale or inconsistent data.** Detect files not yet updated for
   the race just held, using the rule chosen in step 6. Also detect values
   that cannot be right, such as a driver with points but no row expected.
   Either way, write nothing, exit non-zero and say what was found.

10. **Write the two races' rows, and support re-runs.** The race just held's
    points and the next race's prices are written as one change. A re-run
    rewrites exactly the rows earlier runs wrote, and never a value the
    workbook held. 2026 race 20's points are the one exception. How Alex
    corrects a value BoxBox has wrong is settled here. Write only after the
    integrity checks pass on the result. Untouched rows keep their bytes, as
    in `odds_source.odds_file`.

11. **The CLI and its docs.** Show each asset's previous values alongside the
    new ones, then write. Update `README.md` and `CLAUDE.md`.

## Gates

**Gate 1: the first real run**, at the first race weekend after step 11
lands: late 2026 if the build is quick, otherwise 2027 race 1. Run against
live BoxBox, before and after its update, to see the stale-data refusal and
then a real write. Alex reviews the CSV diff before committing. If this is
2027 race 1, it is also the first time the fetcher meets a new season.
