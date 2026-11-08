# odds_source_v1 — Requirements

**Status**: opened 2026-11-08, partly agreed (see *Decisions*). The open
questions below need answers before `plan.md` is written. Execution log in
`log.md`.

## The problem (original backlog entry, unchanged)

> `StrategyBettingOdds` (`linear/strategy_odds.py:5,14-15`),
> `scripts/select_odds_start.py` and — since 2026-07-26 — `fast_f1`'s odds
> indicator (`fast_f1/output.py:_load_driver_odds`) all read odds from a
> hand-maintained `data/f1_betting_odds.xlsx` via
> `import_data/odds.py:load_odds` — there is no API/scraper integration
> anywhere in the repo. README.md notes odds are a spreadsheet input, with
> ideal timing "after FP3 (and obviously before quali)."
>
> Coverage is the binding constraint: the file holds 2026 races 1–11 only, so
> the fast_f1 odds indicator contributes nothing to any 2023–2025 race and
> `--historical` output is largely a constant-zero column. [2026-10-05: now 2026
> races 1–17. There are still no odds for any earlier season.]
>
> Pull odds directly from a betting-odds web page instead of manual entry,
> landing in the same `Season`/`Race`/`Driver`/`Constructor`/`Odds` shape
> `load_odds` already expects (odds formats like `100/1`, `9/4`, `5:2`, and
> odds-on prices like `10/11` are handled by `odds_to_pct()`), so all three
> consumers need no changes downstream.

## Where things stand, checked 2026-11-08

From the code and the workbook, not from any web page.

- **Coverage:** 2026 races 1–20, 22 drivers a race, `Odds` filled for every
  row. Nothing before 2026.
- **The snapshot columns are sparse.** Of the 20 races, `Odds_Pre_Weekend` is
  filled for 16, `Odds_Post_FP2` for 7, `Odds_Pre_Quali` for 2 and
  `Odds_Post_Quali` for 1. The workbook also carries an unnamed, unread tenth
  column.
- **Four consumers, not three.** `StrategyBettingOdds` (and through it
  `scripts/select_odds_start.py`) and `fast_f1/output.py` read through
  `load_odds`. `fast_f1/indicator_analysis.py:697` reads the workbook directly
  with `pd.read_excel`, so it depends on the file's layout as well as the
  `Odds` column.
- **Odds matter less to `fast_f1` than the entry says.** Since
  `aggregate_rank_v1` (2026-11-08), `AggregateRank` uses odds at race 1 only,
  and `StrategyFastF1`'s signal reads no odds at all. The `OddsRank` column is
  still written for every race.

## What the effort can and cannot fix

**A page of current odds cannot fill the 2023–25 gap.** It shows prices for
the next race only, and once that race is run they are gone. So a scraper
removes the manual entry from now on and builds history from the day it
starts, but it does nothing for the coverage the entry calls the binding
constraint. Back-filling is out of scope (decision D1).

## Decisions, agreed with Alex 2026-11-08

- **D1 — Going forward only.** No back-fill of earlier seasons.
- **D2 — Race-winner odds**, the market the `Odds` column already holds.
- **D3 — Source page:** <https://www.oddschecker.com/motorsport/formula-1>,
  which links to the next race's market. Used as a base: the fetcher follows
  that link.
- **D4 — Run by hand.** Alex runs a script. It asks the FastF1 API how far
  through the race weekend we are, and fills the matching snapshot column.
- **D5 — The odds spreadsheet becomes a CSV file** as part of this effort.
- **D6 — Driver names are matched to codes through the FastF1 API.**

## Constraints already in force

- **`import_data/` is a core module.** `load_odds` and `odds_to_pct` are not
  edited without Alex's case-by-case OK (open question 1). The fetcher sits in
  its own module. If the page shows decimal odds (`15.0`) rather than
  fractional, converting them is the fetcher's job unless Alex agrees a change
  to `odds_to_pct`.
- **The workbook is a data file.** Any automated write agrees its check plan
  first, and proves that nothing else in the file moved.
- **No live calls in the suite.** Tests run against a saved page fixture. A
  saved page can carry cookies, session tokens or location in its markup, so
  the fixture is trimmed down to the odds table, or written by hand, before it
  is committed. Any live check is a separate opt-in test, as
  `tests/test_fastf1_api_validation.py` is for FastF1.
- **No credentials in the repo.** If the source needs an account or an API
  key, it follows the `fast_f1/auth.py` pattern: a file outside the repo, mode
  600, never read into a log or a message.
- **The live team stays on P2PM for 2026.** This effort changes how odds
  arrive, not which strategy picks the team.

## Still to check before code

- **Oddschecker's terms of use and `robots.txt`** on automated access.
- **Whether the page can be fetched by a script at all**: odds in the HTML or
  built by JavaScript (a browser driver is a much larger dependency), and
  whether scripted requests are blocked.

## Open questions

1. **May `import_data/odds.py` change?** D5 means `load_odds` reads a CSV, and
   `import_data/` is a core module.
2. **Does a run also fill `Odds`,** or does Alex still choose which snapshot
   goes there?
3. **A second run at the same point:** overwrite, or refuse?
4. **Which column at which point?** Normal weekends map cleanly. Sprint
   weekends have no FP2 or FP3, and some points fall between columns (after
   FP1, say).
5. **Before FP1 there is no session to read names from.** FastF1 only has the
   weekend's entry list once a session has run, so a pre-weekend run would
   rely on the previous race's drivers and miss a driver change. Reasoned,
   not yet run.
6. **Constructor codes.** FastF1 gives team names (`Haas F1 Team`), and the
   file holds codes (`HAA`). Map them from the fantasy archive for that race,
   or from a fixed table?
7. **Fold in *Thread the odds file path through `fast_f1.output`*?** The CSV
   change touches the same code.
