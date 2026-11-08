# data_capture_v2 — Log

## 2026-11-08 — Effort opened

Alex cancelled `data_capture_v1` and opened this effort from the backlog item
*Get fantasy points and prices from BoxBox F1 Fantasy*, which is now off
`BACKLOG.md`. The reason is the input route. Instead of typing points and
prices in by hand, as v1 chose on 2026-07-30, they come from BoxBox F1
Fantasy's published JSON.

Scope decisions taken:

- **The move to long-format CSV carries over from v1**, so the fetcher writes
  into a store whose changes can be reviewed as a git diff.
- **`f1_fantasy_archive.xlsx` is the golden source for the history it already
  holds.** Alex's historical analysis must not break, so BoxBox only adds new
  races and the migration has to reproduce the workbook exactly.
- **Both Excel workbooks are still removed**, as v1 planned after the
  2026-09-29 security review. Alex confirmed the two:
  `f1_fantasy_archive.xlsx`, and `test_expected_values.xlsx` (the derivation
  test's expected values, which becomes a text fixture first).

Both BoxBox files were downloaded once and compared against the archive with a
throwaway script. What it found is in `requirements.md`, under *What BoxBox
provides*. In short:

- Every 2026 driver result matched the archive, and so did constructors for
  races 1–3. The rest of the constructor results were not compared.
- There is no price for each race, only the current one, which matched the
  archive's latest race. So prices have to be fetched every race weekend, and
  a missed weekend cannot be filled in later.
- Alex doesn't know what BoxBox's `starting_price` is. It does not match the
  archive's race-1 prices, so it is not used.
- BoxBox numbers 2026 races by calendar round, skipping the two that were
  cancelled, where the archive numbers the races that were held. The fetcher
  maps one to the other.

One thing v1 did not account for: reading the CSV means either editing
`import_data/import_history.py`, a core module that needs Alex's agreement, or
adding a new loader beside it. That is listed as an open question.

`plan.md` is deferred until the open questions in `requirements.md` are
answered.

## 2026-11-08 — Loader rewrite, run cadence and failure handling settled

Alex answered four of the open questions:

- **`import_history.py` is rewritten in place.** This is a granted exception
  to the core-module rule, on condition that very careful checks prove the old
  data and behaviour are preserved. `requirements.md` now proposes those
  checks under *Checks on the loader rewrite*: identical loader output for
  every season, identical derivations, an exact re-simulation of
  `backtest_v1`'s P2PM rows plus a 2026 replay, and the integrity checks still
  failing where they fail today. That is the bar set for the `StrategyBase`
  DRS helper. The checks are agreed with Alex before any data or loader code
  changes.
- **The fetcher runs once per race weekend**, a few days after the race,
  writing that race's points and the next race's prices. When BoxBox updates
  after a race is not known, so the fetcher must detect files that have not
  been updated yet rather than write stale numbers.
- **Wrong or late BoxBox data fails loudly**: nothing is written, and the
  exit is non-zero.
- **Re-runs must correct earlier captures**, because a driver can be changed
  unexpectedly, close to a race weekend, after that race has been captured.

Who gets a row in a race is not settled. Alex asked for a historical analysis
of the BoxBox files first, focused on mid-season driver changes. That is now
chunk 5, ahead of the fetcher (chunk 6). BoxBox serves only the current files,
so where older versions come from is a new open question. How to detect
not-yet-updated files is another, and the same analysis should inform it.

Alex also asked whether the workbook could be recovered after deletion. It
can, byte for byte, from any earlier commit. `requirements.md` now says so and
commits to recording the recovery commit in this log at deletion.

The scope wording on the golden source was tightened. BoxBox never changes a
value the workbook holds. The one gap it fills is 2026 race 20's points,
which the workbook holds as zero placeholders. The earlier wording ("only adds
races") would have stopped that.

## 2026-11-08 — Weekly BoxBox copies, and zero points dropped

**Weekly copies.** BoxBox serves only the current files, so the analysis of
mid-season driver changes needs copies saved over time. Alex chose to save
both files every week from now on, into `outputs/boxbox/<YYYY-MM-DD>/`, which
git ignores. The download made when the effort opened is the first copy
(`2026-11-08`). Until the fetcher exists and saves its own copies, they are
saved by hand with the command in `requirements.md`. A web archive might hold
earlier versions, but that has not been checked.

**Zero points.** The workbook's zero points for a race not yet run are a
workaround for a limitation in today's code, not data. Alex is happy for the
CSV to leave them out. The checks on the loader rewrite are unaffected, as
they compare what the loaders return rather than the files. Whether callers
still need the zeros, and so whether the loader has to fill them in, is a new
open question.

## 2026-11-08 — Plan written

`plan.md` has eleven steps and one gate. Steps 1–5 move the archive to CSV and
are planned in detail. Steps 6–11 are the BoxBox analysis and fetcher, only
outlined until the analysis is done. `requirements.md`'s chunk list now points
to the plan, and each open question names the step that settles it.

**Workbook survey.** A read-only scratch script surveyed every sheet of
`f1_fantasy_archive.xlsx` to decide the CSV layout:

- No duplicate assets, no all-empty rows or race columns, and every cell is
  numeric.
- Each season's Points and Price sheets list the same assets and agree on
  which cells are empty when paired by name. But they list the assets **in
  different orders** in every sheet pair except 2026 drivers. Today's loader
  returns rows in the Points sheet's order, because it merges price onto
  points.
- The loaded types differ by asset: constructor points are integers and
  driver points floats, since only driver sheets have gaps. Prices are floats
  throughout.
- 2026 race 20 holds the placeholder zeros: 22 driver rows and 11
  constructor rows.

The plan's proposed layout follows from this. The CSV rows are grouped by
asset in the Points sheets' order, so the new loader can return exactly
today's frames, row order included, rather than "the same after sorting".
Order can reach the LP solver, as the 2026-09-18 hash-order fix showed, so
matching it is cheaper than proving it does not matter. The cost is that a
race's lines are spread through the file rather than in one block, though
they are still the only lines that change.

Other planning choices:

- **No separate step for the ignored `fn`.** `data_capture_v1` put fixing
  `load_archive_data_season`'s unused `fn` first. No test or caller passes it
  except `fast_f1/signal.py`, which passes the default, so it blocks nothing
  today. The rewrite in step 4 fixes it, with a test.
- **The expected-values fixture goes first.** It is the smallest conversion
  and independent of everything else. Only its two `Expected` sheets are read,
  so only those are converted. The `Actual` sheets stay in git history.
- **Conversion waits for a quiet window.** Alex keeps editing the workbook by
  hand after each race until step 5, so steps 3 and 4 are done between two
  race-data updates from a recorded workbook commit, and are redone if it
  moves.
- **The analysis waits for the end of the season.** Copies from Brazil to Abu
  Dhabi give about five. They may contain no driver change, so step 6 also
  checks a web archive for older versions.
- **The first real run is likely 2027 race 1.** Only three races remain
  after Brazil. If so, the first real run is also the fetcher's first new
  season, which Gate 1 notes.

## 2026-11-08 — Correction: why row order matters

The entry above says row order "can reach the LP solver". It cannot. Since the
2026-09-18 hash-order fix, `StrategyBase.get_team_selection_dict` sorts assets
by name before the LP variables are built, so the order of rows in the data
does not reach the solver.

Row order does still matter, in a different place. `races/first_picks.py`
lists starting teams with drivers and constructors in data order, and
`backtest/sample.py` draws its seeded sample by position in that list
(`band.sample(n, random_state=seed)`). Reordered rows would make the same seed
sample different teams, so results would no longer match the stored ones,
and nothing would raise an error.

The layout is unchanged: keeping the Points sheets' order is still what lets
the loader return exactly today's frames. The reason in `plan.md` is
corrected. This was established by reading the code, not by running it.
Alex caught it by asking what the claim meant.

## 2026-11-08 — Step 1: derivation fixture converted to CSV; workbook removed

`tests/test_derivations.py` now reads its expected values from
`data/test_expected_values_2023.csv` and `data/test_expected_values_2024.csv`.
These are the workbook's `2003 Expected` (22 rows × 16 columns) and
`2004 Expected` (24 × 6) sheets, with their column names unchanged, typos
included, so the test's only change is where it reads from.
`data/test_expected_values.xlsx` is removed, and can be recovered at
`2f0cda9`. The two unused `Actual` sheets were not converted and exist only
there.

Red first: with the test pointed at the CSV paths, it failed with
`FileNotFoundError` on the 2023 file and the other three derivation tests
passed. It went green once the files existed.

**Data check.** The converter and the check were separate throwaway scripts.
The check reads the workbook through openpyxl rather than pandas, and reads
each CSV both as text and through `pd.read_csv` as the test does. It found
every cell equal, blanks as blanks, and the `read_csv` frames exactly equal
to the old `read_excel` frames, dtypes included. It was shown able to fail on
two damaged copies, each giving a non-zero exit:

- one ppm value changed in its fifteenth significant digit;
- one blank filled with a number.

pandas' default CSV reader reproduced every float exactly, so the test needs
no special read options.

`README.md` names the new files. Suite: 594 passed. Only the derivation tests
were run before the change, not the full suite.

## 2026-11-08 — Step 2: layout and checks agreed

Alex agreed the CSV layout in `plan.md` and the checks in `requirements.md`
(*Checks on the loader rewrite*) as written. Both now read as agreed rather
than proposed, and the layout is no longer an open question.

Alex wants steps 3–5 done tonight. The workbook is committed and unchanged,
and Brazil's results are not in it yet, so tonight is a valid window for the
conversion, as long as the workbook is not edited until step 5 lands. After
that, Brazil's points and the Las Vegas prices go into the CSV instead.

Hand-entry into the CSV is the cost of that order. A race's lines are spread
through the file, and saving it from a spreadsheet app could reorder rows or
reformat numbers, which is what the layout exists to prevent. Suggested
instead: until the fetcher exists, a session enters each race from the saved
BoxBox copy and Alex reviews the diff. That has not been decided yet.

## 2026-11-08 — Step 3: archive converted to CSV; "before" state captured

`data/f1_fantasy_drivers.csv` (1,840 rows) and `data/f1_fantasy_constructors.csv`
(920 rows) hold the archive in the agreed layout. Nothing reads them yet. They
were converted from the workbook at `7a0856e`, its last commit (2026-11-06,
the CAM-for-HIR switch at Haas before Brazil). The working tree was clean.

The driver file is 316 rows shorter than the loader's 2,156-row grid. Those
are the empty pairs, which are now absent rows. The constructor file matches
the grid, since no constructor misses a race. All 33 of 2026 race 20's
placeholder zeros are empty points. The converter asserted that each was 0
before blanking it.

**Data check.** A separate throwaway check read the workbook through openpyxl
and the CSVs through the `csv` module, so it shared no code with the pandas
converter. For every workbook cell pair it checked:

- that an empty pair has no CSV row;
- that every other pair has exactly one row with equal points and price, each
  in its shortest form;
- that the placeholders are blank;
- that the CSV has no extra or duplicate rows;
- that the row order is season, then asset in Points-sheet order, then race.

No problems. One bug in the check itself was found and fixed first:
openpyxl's read-only mode drops trailing empty cells, so short rows had to be
padded to the header's width. It was then shown able to fail on five damaged
copies of the driver file, each giving a non-zero exit and naming the fault:
one price changed, one row deleted, two rows swapped, one placeholder filled
with 0, and one price written `27.0`.

**"Before" state**, saved to `outputs/data_capture_v2/before/` (not committed),
from a throwaway script that runs the committed code:

- both loaders' output for every season and both asset types;
- `helpers.load_with_derivations` for every season;
- two 2026 replays through `run_single_team.run_for_team` with
  `StrategyMaxP2PM` (not its `__main__`). One is the live configuration from
  race 20, which re-solves nothing. The other is the full season from the
  race-1 line-up, which re-solves races 2–20.

The back-test "before" is the P2PM rows already stored in
`outputs/backtest_v1_results.parquet`. If step 4's re-simulation matches them,
that is equality with the code before the change. Only a mismatch would need a
fresh run on the old code to tell the two apart.

## 2026-11-08 — Step 4: the loader reads the CSVs

`import_data/import_history.py` now reads `data/f1_fantasy_drivers.csv` and
`data/f1_fantasy_constructors.csv`, under the core-module exception Alex
granted for this effort. What changed:

- **New `read_archive_file`** reads one file and rejects it if its columns
  are not exactly the expected ones, if a season/race/asset appears twice, or
  if a row has no price.
- **`load_archive_data_season` rebuilds the old shape.** It builds every
  asset against every race of the season, in file order, with empty points
  and price where there is no row. It fills 0 points for a race not yet run,
  and gives the old types (constructor points as integers).
- **Removed:** the Excel functions, `convert_data_sheet`, `load_archive_sheet`,
  `get_archive_sheet_infos` and `merge_sheet_points_price`, along with
  `DataSheetType` and `ArchiveSheetInfo`.
- **Unchanged:** the three `check_*` integrity functions, `get_id_cols`, and
  both loaders' names and signatures. Two of the check functions differ from
  `HEAD` only in trailing spaces removed from one blank line each. The editing
  tool will not write a whitespace-only line, so that difference stays.

**`fn` now names a directory**, the one holding both CSVs, since one argument
has to locate two files. `fast_f1/signal.py` passes one archive argument for
both asset types, so this keeps its call working unchanged. The module constant
is now `_DIR_ARCHIVE_INPUTS = "data"`, and `signal.py`'s import and default
were renamed to match. `fn` was ignored by the old loader, and is now used,
which the fixture tests rely on.

**Red first.** Ten new tests went into `tests/test_import_history.py`, using
fixture CSVs written to `tmp_path`. Nine failed against the old loader, which
ignored the fixture path and read the real workbook: wrong shapes and values,
and no `ValueError` on malformed files. The tenth, an unknown season raising
`ValueError`, already passed, as the old loader raised on the missing sheet.
It is kept as a guard rather than claimed as new behaviour.

**Tests removed or rewritten.** The four tests of the removed functions were
deleted from `tests/test_import_history.py`, and its `check_*` tests are
untouched. `tests/test_archive_integrity.py` now loads each season through
`load_archive_data_season` before running the same three checks on the real
archive.

**The agreed checks, all run:**

- **Same data.** Both loaders for every season and asset type, and
  `helpers.load_with_derivations` for every season, compared with step 3's
  "before" pickles by `DataFrame.equals` and by an exact `assert_frame_equal`
  that includes the index. All 16 snapshots were equal.
- **Same results, 2026.** Both replays were equal: the live configuration from
  race 20, and the full season from the race-1 line-up, which re-solves races
  2–20.
- **Same results, back-test.** `backtest_v1`'s P2PM sample was re-simulated
  into a scratch store (seed 1, 500 per band, 2023–25). That is 4,500
  simulations, about 30 minutes. Against the stored P2PM rows there were the
  same 4,500 `sim_key`s with none on either side only, and all 40 columns were
  exactly equal by `DataFrame.equals`. Matching keys means the same teams were
  sampled, which is the row-order risk the layout guards against.
- **Each comparison can fail.** The snapshot comparison caught four doctored
  copies: two rows swapped, constructor points made floats, one replay total
  plus 1, and one derived value moved by one float step. The back-test
  comparison caught one `total_points` plus 1.
- **Same failures.** The integrity checks' own tests are unchanged and pass.
  Run through the new loader on a copy of the driver CSV with one row deleted
  (Leclerc, 2024 race 11), `check_merged_integrity_drivers` rejected it. On
  the real file it passed.

The scratch scripts are not kept, and their outputs are in
`outputs/data_capture_v2/` (not committed).

Suite: 600 passed (594, less the 4 removed tests, plus 10 new). The workbook
is still in the tree, unread. Step 5 removes it and updates `README.md` and
`CLAUDE.md`, which still describe it.

## 2026-11-08 — Step 5: workbook removed; docs describe the CSVs

`data/f1_fantasy_archive.xlsx` is removed and can be recovered at `e40dcfb`.
Its last edit was `7a0856e`. Both Excel-authored workbooks the 2026-09-29
security review flagged are now out of the tree. Their old versions stay in
history, as accepted then.

`README.md`'s input-data section and `CLAUDE.md`'s `import_data/` paragraph
and data convention now describe the two CSVs:

- no row when an asset does not take part;
- empty points for a race not yet run;
- the load-bearing row order, and where a new race's or new driver's rows go;
- the shortest number form;
- not saving the files from a spreadsheet application.

That replaces the null/zero rule. The rule on agreeing a check plan before
editing hand-maintained data (a session memory, not a repo file) was updated
to name the CSVs and say how it applies to a text file.

From here, each race goes into the CSVs until the fetcher exists. Brazil's
points and the Las Vegas prices are the first. Whether that is done by hand
or by a session working from the saved BoxBox copy is still Alex's call.
