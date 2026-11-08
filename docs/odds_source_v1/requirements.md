# odds_source_v1 — Requirements

**Status**: opened 2026-11-08, not yet agreed. The open questions below need
answers before `plan.md` is written. Execution log in `log.md`.

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
constraint. Back-filling earlier seasons would need a source of archived odds,
which is a different search and possibly a paid one. Question 1 asks which of
the two this effort is for.

## Constraints already in force

- **`import_data/` is a core module.** `load_odds` and `odds_to_pct` are not
  edited without Alex's case-by-case OK. A new fetcher therefore sits in its
  own module and writes the format the loader already reads. If the page shows
  decimal odds (`15.0`) rather than fractional, converting them is the
  fetcher's job unless Alex agrees a change to `odds_to_pct`.
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

## Open questions

1. **What is the goal: no more manual entry going forward, or history for
   2023–25?** As above, a live page only gives the first. If history is what
   matters, the effort starts with a search for an archived source rather than
   a scraper.
2. **Which page?** Ideally the one Alex reads odds from by hand today, so the
   numbers stay comparable with the 2026 rows. Before any code is written,
   check its terms of use and `robots.txt` on automated access, whether it
   serves the odds in its HTML or builds them with JavaScript (a browser
   driver is a much larger dependency than an HTTP fetch), and whether it
   blocks scripted requests.
3. **Which market?** The `Odds` column has been race-winner odds. Confirm the
   fetcher takes the same market and not, say, podium or top-6.
4. **How is a run triggered, and what does it write?** The likely shape is a
   CLI Alex runs by hand at the moment he chooses (after FP2, after FP3),
   writing one snapshot column for that race. Then: does it also fill `Odds`,
   or does Alex still choose which snapshot goes there? And does a second run
   at the same point overwrite, or refuse?
5. **Where does it write?** Into `data/f1_betting_odds.xlsx` in place, keeping
   every consumer unchanged, or to a CSV beside it? `data_capture_v1` moved
   the fantasy archive to CSV so that each race's write shows as a git diff,
   but left this workbook out of its scope. A CSV would need the four
   consumers changed, and `load_odds` is in `import_data/`.
6. **How are names matched?** The page will show full names, so each one
   needs mapping to a driver code and constructor code for that race, mid-season
   switches included (Haas's driver change before Brazil, for example). The
   candidate source is the fantasy archive's priced drivers for that race. A
   name that does not match should stop the run, not be dropped. A priced
   driver with no odds on the page needs a rule.
7. **Should *Thread the odds file path through `fast_f1.output`* (`BACKLOG.md`)
   come first?** It is not required, but it makes the odds file injectable
   everywhere, which tests of a new writer would want.
