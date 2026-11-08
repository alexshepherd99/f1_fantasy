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

## 2026-11-08 — Step 3: the loader reads the CSV; workbooks removed

`load_odds` reads `data/f1_betting_odds.csv`, with `Driver`, `Constructor` and
`Odds` as text, and scores a blank `Odds` as 0.0. `indicator_analysis` reads
the CSV too. The 4-row test workbook became `data/test_betting_odds.csv`, and
the step 1 test helpers and empty fixture write CSV. Both workbooks are gone,
recoverable at `59c79ee`.

Red first, in two stages so each failure meant something: with the fixture
path changed, three reader tests failed because the reader still expected
Excel. Switching only the format left the new blank-price test failing on the
missing value reaching `odds_to_pct`; the blank handling then turned it green.

The truncated-workbook test no longer had a realistic counterpart, since a
truncated CSV just reads as fewer rows. It became a file missing its `Odds`
column, which raises `KeyError`. That still needs the broad catch in
`_load_driver_odds`, and a mutation narrowing the catch to `OSError` and
`ValueError` turned it red. The catch's comment now names the CSV failures.

**Data check**, from a scratch script: the committed loader on the workbook
against the new loader on the CSV, for all 20 races, both asset types and
both driver key formats. 80 calls, no differences. `indicator_analysis`'s
snapshot detection gave the same answer on both files. Run against step 2's
copy with one price changed, the comparison found 4 differences (race 1's
two driver and two constructor lookups), so it can fail.

**Found: `indicator_analysis` will not recognise the new columns.** It
excludes races whose odds were taken after qualifying by the legacy column
name, so a race captured into `Odds_Q` would be scored as if its odds were
blind. Added as step 10, to run before the docs step.

`indicator_analysis.main()` was not run; its snapshot functions were. Suite:
544 passed, with 10 fewer warnings now the test workbook's openpyxl style
warning has gone.

## 2026-11-08 — Step 4: the saved page is parsed

`odds_source/page.py`'s `read_saved_page` returns a `SavedOddsPage`: race
name, race start, the time the page was saved (its `Date` header, which step 5
needs) and each driver's price as the page spells the name.

How it reads the page, with the standard library only: `email` splits the
`.mhtml`, the HTML is decoded as UTF-8 because the page declares that in a
meta tag rather than the MIME header, `html.parser` finds the
`GridGroupIsland` component's props, and Astro's `[type, value]` wrapping is
stripped. The Winner market is the one whose `betTypeName` is `Win Market`.

The median is taken over the bookmakers' **fractional** prices as exact
fractions, rather than decimals. The two give the same median, as decimal is
fractional plus 1, but the fractional strings are exact where the decimals
are rounded (4/7 is `1.571`). An even count takes the midpoint, which can give
an uneven fraction: Sainz at Brazil is `1779/2`, which `odds_to_pct` reads
as written. "Fewer than half" counts against the bookmakers with any active
price in the market, and a suspended price is not counted.

The fixture, `data/test_oddschecker_winner.mhtml`, is written by hand in the
real page's shape, quoted-printable encoding included. Each rule changes a
visible result in it: a suspended price that would move a median, an even
count, a driver at exactly half, one below half, an accented name, and a
podium market listed before the winner market.

The only red possible before the module existed was the import failure, so
behaviour was checked by five mutations, each restored from a copy, with
`__pycache__` cleared and green before the next. Counting suspended prices,
dropping a driver at exactly half, taking the first market, decoding as
Latin-1, and taking the lower middle on an even count turned 1, 2, 5, 2 and
2 tests red.

**Run on Alex's saved Brazil page:** 22 drivers, Ocon dropped (1 of 25
bookmakers), and every price equal to the survey's median decimal less 1.
Suite: 552 passed.

## 2026-11-08 — Step 5: the race and the column are found

`odds_source/schedule.py`'s `find_capture_point(page, schedule)` returns a
`CapturePoint` of season, race and snapshot column. It takes the schedule as
an argument, so tests build schedules in FastF1's shape and patch nothing; the
CLI in step 8 fetches it with `fast_f1.api.get_event_schedule`.
`SNAPSHOT_COLUMNS` lists the D14 columns in weekend order, for step 7.

**The page's race start is not FastF1's.** The real schedule has Brazil's race
at 17:00 UTC (14:00 local). The page says 20:00 UTC, three hours later, for no
reason found. An exact match, as the plan had it, would never have matched.
The race is instead the one starting within 12 hours of the page's; weekends
are at least a week apart, so this cannot pick the wrong race. The
saved-before-the-race check uses FastF1's start.

The other rules, as planned: a session counts as done an hour after its
scheduled start, the column is the last done session's, and none means
`Odds_PreFP1`. Added: a weekend holding a session with no column, such as a
renamed format, stops the run rather than being skipped, checked across every
session and not only the one chosen.

Red was the import failure only, so behaviour was checked by five mutations,
restored and green between each: matching within 1 hour instead of 12 (7 red),
no saved-after-race check (1), a session done at its start (1), no
unknown-session check (1), and the first done session instead of the last
(4).

**Run on the real Brazil page and the live 2026 schedule:** season 2026,
race 20, `Odds_Q`, which is right for a page saved on race morning, and race
20 is Brazil in the odds file. Suite: 560 passed.
