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
