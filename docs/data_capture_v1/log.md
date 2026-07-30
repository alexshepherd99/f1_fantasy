# data_capture_v1 — Log

## 2026-07-30 — Effort opened

Picked *Simplify in-season data capture* off `BACKLOG.md` as the next effort
and removed it from that list. `requirements.md` carries the original entry
verbatim plus a first high-level assessment; no code written this session.

Three scope decisions taken:

- Input to the writer is **hand-typed/pasted**, not scraped and not a vendor
  export.
- The **wide-to-long reshape of `data/f1_fantasy_archive.xlsx` is in scope and
  comes first**, with the writer built against the new layout.
- The long-format archive is **CSV, not `.xlsx`** — a per-race write should be
  reviewable as a git diff, which is most of what makes the capture safer.
  Only the archive moves; the odds and FastF1 metrics workbooks stay as they
  are.

Assessment findings worth recording:

- `load_archive_data_season` (`import_data/import_history.py:277`) accepts `fn`
  but does not pass it to `load_archive_sheet` (:291-292), so every caller
  reads the real archive whatever they pass. There is no fixture archive
  workbook either. Both block developing the rest of this effort test-first,
  so they come first.
- The reshape should be invisible above `import_data/` — the loaders already
  return tidy long frames, so `helpers.py`, `scripts/check_run_ppm.py` and the
  three test modules that use them should need no changes. That property is
  the migration's verification target.
- The real win of long format is that non-participation becomes row absence,
  removing the null-vs-zero convention rather than automating it.

The CSV decision brings a new question with it, recorded in `requirements.md`:
a diffable store only pays off if a one-race write yields a one-race diff, so
row order and number formatting have to be stable. That gets settled alongside
the schema.

`plan.md` deferred until the remaining open questions in `requirements.md` are
answered — chiefly the schema and the paste format.
