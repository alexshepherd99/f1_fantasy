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
