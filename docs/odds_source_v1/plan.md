# odds_source_v1 — Plan

Requirements and decisions D1–D17 in `requirements.md`. One commit per step,
test first for every behaviour change, suite green at the end of each.

## Shape

A new package, `odds_source/`, run as
`PYTHONPATH=. venv/bin/python -m odds_source.cli`. It reads Alex's saved page,
asks FastF1 where the weekend is, and writes one race's rows into
`data/f1_betting_odds.csv`. FastF1 calls go through `fast_f1/api.py`, and
credentials through `fast_f1.auth`, as `fast_f1.cli` does. Nothing in `races/`,
`linear/` or `scripts/` changes. `import_data/odds.py` changes under D7.

## Steps

1. **Thread the odds file path through `fast_f1.output`** (D12). Add an
   odds-file parameter to `_load_driver_odds` and `build_race_metrics`,
   defaulting to the real file. Point the `tests/conftest.py` autouse fixture
   and the per-test patches in `tests/test_fast_f1_output.py` at fixture files
   instead of replacing `load_odds`, and fix the conftest docstring. Covers
   every test that reaches `build_race_metrics`.

2. **Convert the real odds workbook to CSV, beside it.** A data-only commit:
   `data/f1_betting_odds.csv` is written, the workbook stays and nothing reads
   the CSV yet. Every column is kept as text except `Season` and `Race`, and
   the unnamed tenth column is dropped (it holds one stray value). Checks,
   which must all pass before committing:
   - every kept cell in the CSV equals the workbook's cell, compared as text,
     and no cell was read as a date;
   - `load_odds` gives the same dict from both files for every season, race
     and asset type, once step 3's loader can read the CSV (run then, from a
     scratch script, and recorded in the log);
   - every non-blank odds cell in every odds column parses with
     `odds_to_pct`.

3. **Switch the loader to CSV.** `load_odds` reads CSV with odds columns as
   text, treating a blank `Odds` as no price (0.0), which a CSV can now hold
   for a driver missing from a run. `_FILE_BETTING_ODDS` becomes the CSV path.
   `fast_f1/indicator_analysis.py` reads it with `read_csv`. Test fixtures
   `data/test_betting_odds.xlsx` and any others become CSV. Then run step 2's
   `load_odds` comparison, and remove both odds workbooks with `git rm`.

4. **Parse the saved page.** `odds_source/page.py` reads an `.mhtml` file and
   returns the race name, its start time and, for the *Winner* market, each
   driver's median price across bookmakers (D16), dropping entries priced by
   fewer than half of them with a warning (D17). The median decimal price is
   written as a fractional string `odds_to_pct` reads (2.25 becomes `5/4`). A
   page with no *Winner* market raises. Tests use a small `.mhtml` fixture
   written by hand in the page's JSON shape, never cut from a real save.

5. **Find the race and the column.** Both come from the page and FastF1's
   event schedule, not from the clock, so a rerun of the same page gives the
   same answer. The race is the event whose race start matches the page's; no
   match stops the run. The page's save time (its `Date` header) must be
   before that start. The column (D14) is the last session whose scheduled
   start was at least an hour before the save time; none means
   `Odds_PreFP1`. Tests stub the FastF1 boundary.

6. **Map names and teams.** `get_session_drivers` also returns each driver's
   first and last names. A page name matches on its accent-free, case-free
   surname if that is unique in the list, else on the full name. A pre-FP1 run
   uses the previous race's last session. An unmatched name is written as it
   appears, with a blank `Constructor` and a warning (D6, D15). The step first
   checks FastF1's real name forms against the sample page's names. FastF1 team
   names map to codes through a fixed table, from the 2026 names in the
   metrics file; a missing team raises (D11).

7. **Write the race's rows.** For the race, set the column and `Odds` for
   every driver priced, overwriting (D8, D9). A driver already in the file for
   that race but not priced this run keeps his row, with this column and
   `Odds` blank. New drivers are appended after that race's rows. A test
   proves every other race's rows are byte-for-byte unchanged.

8. **The CLI.** `odds_source/cli.py` loads the credentials first, as
   `fast_f1.cli` does, takes the page path (default: newest `.mhtml` in
   `outputs/`) and `--odds-file` (default: the real CSV), and prints the race,
   the column, the drivers written and any warnings.

9. **Docs.** `README.md` (odds input: CSV, new columns, the capture command),
   `CLAUDE.md` (the workbook references and the new package), `BACKLOG.md`
   (mark done), log close.

## Gates

**Gate 1 — the Brazil sample, live FastF1.** Run the CLI against Alex's saved
Brazil page with `--odds-file` pointing at a scratch copy of the CSV. Expect
column `Odds_Q`, 22 drivers, Ocon dropped, Camara on `HAA`, and medians
matching the survey in `requirements.md`. The real CSV is not touched.

**Gate 2 — the first real run**, at the next race weekend. Alex reviews the
git diff of the CSV before committing it.
