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
