# data_capture_v1 — Requirements

Picked up off `BACKLOG.md` on 2026-07-30. This document carries the original
backlog entry, plus a first high-level assessment of what the effort needs.
`plan.md` is deliberately not written yet — the open questions below want
answers first.

## The problem (original backlog entry, unchanged)

> Points and prices for each race are currently entered by hand into
> `data/f1_fantasy_archive.xlsx`, which holds wide-format Points/Price sheets
> per season with a column per race. Editing that layout race-by-race is
> fiddly and easy to get wrong — in particular the null-vs-zero convention
> (non-participants need both points and price null; expected participants
> with a known price but no result yet need points `0`) that
> `import_data/import_history.py` validates against.
>
> Replace the manual step with a helper script that takes one race's worth of
> points and prices and writes them into the archive, applying the
> null/zero convention itself. That likely needs the workbook simplifying
> first — a tidy long-format layout would be a much easier write target than
> the current wide sheets, but `import_data/import_history.py` melts the wide
> format today, so the loader and its integrity checks change with it.

## Scope, as settled 2026-07-30

- **Input is hand-typed.** The numbers are read off the F1 Fantasy game and
  typed or pasted in. No scraping, no vendor export file. The exact paste
  format is still open (see below).
- **The wide-to-long reshape is in scope, and comes first.** All four seasons
  migrate, `import_data/import_history.py` is rewritten against the new
  layout, and the writer is then built against long format rather than
  against today's sheets.
- **The long-format store is CSV, not `.xlsx`.** A CSV diffs in git, so every
  per-race write is reviewable in the same way a code change is — which is a
  large part of what "safer in-season capture" means here. This replaces
  `data/f1_fantasy_archive.xlsx` for the archive only; `data/f1_betting_odds.xlsx`
  and `data/fastf1_practice_rolling_metrics.xlsx` are out of scope and stay as
  they are. Whether the archive is one CSV or two (drivers, constructors) is
  part of the schema decision in chunk 2 below.

## What the change touches

Today's archive is 16 sheets — 4 seasons × {Drivers, Constructors} ×
{Points, Price} — each wide, with race numbers as column headers
(2026 Drivers Points is 22 rows × `Driver`, `Team`, `1`…`12`). Adding one
race means hand-editing four sheets.

Reading side, everything funnels through two functions:

- `load_archive_data_season` / `load_all_archive_data`
  (`import_data/import_history.py:277,296`), consumed by `helpers.py:16-17`,
  `scripts/check_run_ppm.py:15`, and `tests/test_archive_integrity.py`,
  `tests/test_team.py`, `tests/test_season.py`.

Both return tidy long frames already, so **the reshape should be invisible
above `import_data/`** — that is the property to hold onto, and the thing the
migration is verified against.

Inside `import_history.py`, the reshape removes or rewrites:

- `convert_data_sheet` (:48) — the melt itself, which long format makes moot;
- `load_archive_sheet` (:78) — including the `Team`→`Constructor` rename (:95)
  and the `DRIVER@CONSTRUCTOR` id construction (:99);
- `merge_sheet_points_price` (:156) — points and price stop being separate
  sheets, so the shape/identifier equality checks it performs become a
  different kind of check, not a merge precondition;
- the three integrity checks (:194, :222, :250), which stay but get
  re-expressed.

## The actual simplification win

In long format, non-participation is **row absence** — no null pair to get
right. The remaining case is "price known, race not yet run", which is one
row with a price and `Points = 0`. That collapses the null-vs-zero convention
the backlog entry names as the main hazard from a rule a human has to
remember into a property of the layout. Worth stating explicitly as the goal,
because it is what justifies migrating the data rather than just writing a
smarter writer for the wide sheets.

## Rough shape of the work

Five chunks, in dependency order. Each is a commit or a small run of them.

1. **Make the archive path injectable end-to-end.** `fn` is accepted by
   `load_archive_data_season` (:277) but never passed down to
   `load_archive_sheet` (:291-292), so every call reads the real archive
   regardless. There is also no fixture archive in `data/` (only
   `test_betting_odds.xlsx`, `test_expected_values.xlsx`). Under CSV a fixture
   is cheap — a handful of text rows rather than a generated workbook — so the
   main point of this chunk is not to carry the path-threading defect forward
   into the rewritten loader. Whether it is worth fixing on the *current*
   loader first, given chunk 4 replaces it, is a judgment call for `plan.md`.
2. **Settle and document the long-format schema** — column set, and whether
   drivers and constructors share one CSV or keep two files.
3. **Migrate the data, and prove equivalence.** A one-shot converter from the
   16 existing sheets to CSV, plus a check that loads old and new and asserts
   the frames are identical for every season and asset type. Per
   `verify-before-data-edits`: agree the check plan before writing any CSV,
   and prove nothing but the layout moved. The converter is throwaway — it
   runs once — but the equivalence check is the evidence, so it wants to be
   readable. Keep `f1_fantasy_archive.xlsx` in the tree until the check has
   passed and the loader is rewritten; deleting it is the last step, not the
   first.
4. **Rewrite the loader and integrity checks** against long format, keeping
   `load_archive_data_season` / `load_all_archive_data` signatures and return
   shapes as they are.
5. **Build the writer.** Takes one race's typed points and prices, validates
   them against the expected roster for that season/race, applies the layout
   rules, re-runs the integrity checks, and only then saves.

   **Show the previous value when asking for each one** (added 2026-07-30).
   When the writer prompts for a driver's or constructor's price or points for
   a race, it displays the value already held for that asset — so a typo, a
   misread row, or a driver entered against the wrong seat stands out at the
   moment of entry rather than at the next integrity check. Two things this
   settles: "previous" needs defining (the prior race's value is the useful
   cross-check for both price and points; the *current* race's value also
   matters on a second pass, where price was entered pre-race and points are
   being added after), and a per-asset prompt showing context implies an
   interactive loop rather than one pasted block — see the paste-format
   question below, which this narrows.

## Open questions

- **Row order and stability in the CSV.** A git-diffable store only pays off if
  a one-race write produces a one-race diff. That needs a fixed sort order
  (season, race, constructor, driver — or season, race appended in place) and
  stable formatting of prices, so the writer never reflows rows it did not
  touch. Settle this with the schema in chunk 2.
- **What does a paste look like — and is it a paste at all?** Column order,
  separator, and how a driver is identified (bare `NOR`, or `NOR@MCL`).
  Determines how much validation the writer does versus how much typing it
  saves. Now partly answered by the previous-value cross-check in chunk 5: a
  prompt-per-asset loop gives somewhere to show that context, a single pasted
  block does not. A hybrid stays open — paste a block, then confirm it back
  row by row with previous values alongside.
- **One write per race or two?** Prices are known before a race, points after.
  If the writer only appends, the second pass has nowhere to go — it likely
  needs to update an existing race's rows, not just add them.
- **Where does the expected roster come from?** `common.F1_SEASON_CONSTRUCTORS`
  has constructors only, so the writer has no list of who *should* appear in a
  given race to validate a paste against. Mid-season seat changes
  (`HAD@RED`-style) make this real rather than theoretical.
- **Migrating mid-season.** 2026 is live and partly filled (race 12 present
  with zeroed points). The migration has to preserve that in-progress state,
  not just the closed seasons.

## Definition of done

- The full suite is green before and after, and every behavioural change was
  seen failing first.
- Old-vs-new equivalence is demonstrated for all four seasons, both asset
  types.
- Adding a race is a single command against typed input, with the layout
  rules applied by the tool rather than by hand.
- Writing one race produces a git diff covering that race and nothing else.
- `README.md` and `CLAUDE.md` both describe the archive as a wide-format
  workbook and both state the null/zero convention; both need updating with
  the reshape and the move to CSV.
