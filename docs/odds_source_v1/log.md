# odds_source_v1 — Log

## 2026-11-08 — Effort opened

Picked *Source betting odds directly from a web page* off `BACKLOG.md` and
removed it from that list. `requirements.md` carries the original entry
verbatim, the state of the code and the workbook as checked today, and the
open questions. No code written, and no web page fetched.

Suite green at the start: 543 passed.

The main finding from the assessment: a page of current odds cannot fill the
2023–25 gap the entry calls the binding constraint, because it only shows the
next race. So the first question is whether this effort is about ending manual
entry or about back-filling history, as they need different sources.

Two corrections to the entry, recorded in `requirements.md` rather than by
editing the quoted text:

- There are four odds consumers, not three. `fast_f1/indicator_analysis.py`
  reads the workbook directly.
- Since `aggregate_rank_v1`, `fast_f1` uses odds at race 1 only, so the zero
  column in earlier seasons now costs less than the entry says.

`plan.md` is deferred until the open questions are answered, chiefly which
page and where the fetcher writes.

## 2026-11-08 — First answers

Alex answered the first round. Recorded as D1–D6 in `requirements.md`:
going forward only, race-winner odds, Oddschecker's F1 page as the base, a
script run by hand that reads the weekend's progress from FastF1, the odds
spreadsheet converted to CSV, and names matched through FastF1.

Those answers raised a second, smaller round of questions, which replace the
first in `requirements.md`. The main ones are whether `import_data/odds.py`
may change (the CSV needs it) and how runs before FP1 and on sprint weekends
pick a column and find the entry list.

## 2026-11-08 — Second answers, and the page is blocked

Alex answered the second round, recorded as D7–D12 in `requirements.md`.
D12 folds in the backlog item on threading the odds file path, so that item
leaves `BACKLOG.md`.

One plain request to the Oddschecker F1 page got a 403 and a bot-check page.
`robots.txt` allows the path. So D3's page cannot be fetched by a plain
script, and getting round the check is not something to build. The proposal
now in `requirements.md` is that Alex saves the page from his browser and the
script parses the file.

## 2026-11-08 — Third answers, and the sample page

Alex agreed the saved-page route, the session-named columns and the blank
constructor for an unmapped driver (D13–D15), and saved a sample page.

The sample parses cleanly: the odds sit as JSON inside the page, one entry per
driver with every bookmaker's price. Two findings became open questions:
bookmakers' prices differ widely, so the script needs a rule for which to take,
and the page listed a driver who was not racing. The page also carries browser
and tracking details, so test fixtures are written by hand, not cut from it.
The survey used throwaway scripts outside the repo.

## 2026-11-08 — Requirements agreed, plan written

Alex chose the median price (D16) and dropping thinly priced entries (D17).
No questions remain, and `plan.md` is written: nine steps and two gates.

Two choices made in the plan, for Alex's review:

- **The race and column come from the saved page, not the clock.** The page
  names its race and carries its save time, so a rerun of the same page gives
  the same answer, and Gate 1 can use the Brazil sample after the race. A
  session counts as done an hour after its scheduled start.
- **The workbook's unnamed tenth column is dropped** in the CSV conversion. It
  holds one stray value and nothing reads it.

## 2026-11-08 — Plan approved

Alex approved both choices above. Next is step 1.

## 2026-11-08 — Step 1: odds file path threaded through `fast_f1.output`

`build_race_metrics` takes an `odds_file` and passes it down to `load_odds`.
No test replaces `load_odds` any more: the four that wanted odds or a failure
now write a real one-race workbook in `tmp_path`, or pass the truncated one,
so the real reader runs.

**One choice beyond the plan.** The plan said the parameter defaults to the
real file. Bound as a default, it could not be redirected suite-wide, which is
the reason the old fixture patched the function. So it defaults to `None`,
read at call time as a new module setting, `fast_f1.output.ODDS_FILE`. The
autouse fixture points that at an empty workbook, as `conftest.py` already does
for the cache config and credentials files. The workbook is written once per
session, since the repo's own fixture workbook raises an openpyxl style
warning on every read.

Red first: the new tests failed only on the missing setting and argument,
which shows nothing about behaviour, so behaviour was checked by mutation:

- `_load_driver_odds` ignoring the file it is given: 4 tests red, including
  the guard that tests never read the real workbook.
- `build_race_metrics` ignoring a passed `odds_file`: 3 tests red.

Each restored from a copy, `__pycache__` cleared, and green before the next.
Suite: 543 passed, unchanged in count since the tests were rewritten, not
added. The output test module's warnings are unchanged at 7.

## 2026-11-08 — Step 2: odds workbook converted to CSV, beside it

`data/f1_betting_odds.csv` holds the workbook's 440 rows in the same order,
with its nine named columns as text. Nothing reads it yet.

A survey of stored cell types found the workbook cleaner than feared: no
price had been turned into a date, and every price is stored as text. Two
cells differed from the plan's assumptions:

- **Race 1's `Odds_Pre_Quali` held the number 0 in all 22 rows**, a
  placeholder rather than a price. Alex chose to blank them, so every odds
  cell in the CSV is either blank or a price.
- **The unnamed tenth column** held one midnight time value. Dropped, as
  planned.

The conversion and the check were separate throwaway scripts, so the check
does not reuse the conversion's logic. The check passed: no mismatched cell,
exactly 22 zeros blanked, no date or time cells, and 1,012 odds cells parsed
with `odds_to_pct`, which matches the column counts. It was shown able to
fail on two damaged copies: one price changed, and one zero left unblanked.
Each gave one mismatch and a non-zero exit.

The `load_odds` comparison moves to step 3, where the loader can read the
CSV. Suite: 543 passed.
