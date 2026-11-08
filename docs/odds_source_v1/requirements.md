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

## Folded in (D12): thread the odds file path (backlog entry, unchanged)

Its line numbers are from 2026-07-27 and have since drifted.

> `tests/conftest.py:12-26` autouse-patches `fast_f1.output.load_odds` to
> return `{}` so metric tests never read the real
> `data/f1_betting_odds.xlsx`. That patches a first-party function we own,
> which `agentic`'s `coding-standards` skill says to avoid where a real call
> is practical — prefer making the boundary injectable.
>
> The boundary is already injectable one level down: `load_odds` takes
> `fn: str = _FILE_BETTING_ODDS` (`import_data/odds.py:45-49`), and both
> `linear/strategy_odds.py:14-15` and `tests/test_odds.py` pass it a fixture
> path. Only `fast_f1` skips it — `_load_driver_odds`
> (`fast_f1/output.py:37,45-52`) calls `load_odds` without `fn`, so it always
> resolves to the real workbook and the sole remaining lever is patching the
> function.
>
> Thread the path instead: add an odds-file parameter to `_load_driver_odds`
> and to `build_race_metrics` (`fast_f1/output.py:69`, which calls it at
> :207), defaulting to the real file so production callers are unchanged.
> Tests then pass `data/test_betting_odds.xlsx` — the fixture workbook
> `tests/test_strategy_odds.py:7` already uses — and the autouse fixture and
> the four per-test re-patches in `tests/test_fast_f1_output.py`
> (:512, :538, :563, :583) can point at fixture files or a stub path rather
> than replacing the loader.
>
> Note the conftest docstring (:21-23) justifies the patch by arguing that
> rebinding `import_data.odds._FILE_BETTING_ODDS` has no effect because it is
> bound as a default argument at definition time. That is correct, but it
> rules out patching the *constant* while overlooking the parameter that
> constant defaults to, which is the injection point that already exists.
> Update or drop that paragraph with the change.
>
> Two things to watch. The autouse fixture applies suite-wide, so the
> migration has to cover every test that transitively reaches
> `build_race_metrics`, not just the odds tests. And pointing at a
> nonexistent path is not equivalent to the current stub: `_load_driver_odds`
> catches broadly and degrades to `{}` with a warning
> (`fast_f1/output.py:52-66`), so tests would still pass but emit warning
> noise on every run — use a real fixture file.
>
> Raised 2026-07-27 while checking whether `agentic`'s tightened test-first
> and mocking guidance required changes here. No documentation change was
> needed; this is the one code-level gap it surfaced.

With D5, the fixture becomes a CSV too, `data/test_betting_odds.xlsx`
included.

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
- **D6 — Driver names are matched to codes through the FastF1 API.** The
  drivers are the ones the page lists. A name that cannot be mapped is written
  into the `Driver` column as it appears on the page.
- **D7 — `import_data/odds.py` may change** for the CSV move.
- **D8 — A run fills `Odds` as well as its snapshot column.**
- **D9 — A rerun overwrites.** The file is in git, so an overwrite can be seen
  and undone.
- **D10 — New snapshot columns.** The four existing ones stay as legacy
  columns, unread as now.
- **D11 — Constructor codes come from a fixed table** of FastF1 team name to
  code. A team missing from it stops the run with an error.
- **D12 — *Thread the odds file path through `fast_f1.output`* is folded in**
  and removed from `BACKLOG.md`.

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

## Fetching the page

Checked 2026-11-08 with one plain request from a script. `robots.txt` does not
disallow the F1 pages, but the page itself returned 403 with a bot-check page
instead of the odds. So a plain HTTP fetch does not work. Getting past the
check with a scripted browser is the kind of evasion this repo should not
build. Oddschecker's terms of use have not been read.

## Open questions

1. **How does the page reach the script?** Recommended: Alex saves the page
   from his browser and the script parses the saved file. Everything else
   (FastF1 phase, name mapping, columns, CSV write) stays automatic.
2. **New column names.** Proposed: one per last completed session, so
   `Odds_PreFP1`, `Odds_FP1`, `Odds_FP2`, `Odds_FP3`, `Odds_SQ`, `Odds_Sprint`,
   `Odds_Q`. That covers sprint weekends without a mapping rule.
3. **Constructor for an unmapped driver.** With no code there is no team from
   FastF1. Proposed: leave `Constructor` blank and print a warning, for Alex to
   fix by hand. Until fixed, those odds count for no constructor.
