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

## 2026-11-08 — Step 6: names and teams matched

Two commits. `1c03d3d` has `fast_f1.api.get_session_drivers` return
`FirstName` and `LastName` as well. Its cache was keyed only by season, race
and session, so a list cached before the change would have come back without
names for good, leaving every driver unmatched. A cached list missing them is
now fetched again. The second commit adds `odds_source/drivers.py`.

**FastF1's real names, checked against the sample page first** (Brazil
qualifying): FastF1 has "Kimi Antonelli", as the page does, but "Alexander
Albon" against the page's "Alex Albon", and "Rafael Câmara" against "Rafael
Camara". Surname matching without accents covers both.

`match_drivers` matches a page name on its last word against each driver's
surname, ignoring accents and case. Where two drivers share a surname, the full
name decides. A name matching no driver is kept as spelt, with a blank
constructor and a warning (D6, D15). A team missing from `TEAM_CODES` stops the
run (D11), and so do two names matching one driver, which would otherwise
write a driver twice. `TEAM_CODES` holds the eleven 2026 FastF1 team names,
which map onto the eleven codes in the odds file.

**Which driver list, simplified from the plan.** `load_entry_list` reads the
list for the session the odds follow. Before FP1, or while that session's list
is not yet published, it reads the previous race's race list instead. That
misses a driver change, and the new driver stays unmatched by D6. Race 1
before practice has no list, so every name is unmatched, with a warning. The
fetch is a parameter, so tests pass a recorder and patch nothing.

Red: the wrapper's three tests failed on the missing names and on the stale
cached list. The new module's red was its import failure only, so it was
checked by mutation, each restored from a copy and green before the next:
keeping accents (1 red), matching the first word not the surname (6), no
full-name fallback (1), a blank code for an unknown team (1), no duplicate
check (1), no fallback when a list is unpublished (1) and the previous race's
list read from this race (2). Trusting any cached list turned the wrapper's
stale-cache test red.

**Run on the real Brazil page, end to end with live FastF1:** 22 entries, all
matched, with exactly the driver and constructor pairs hand-entered for race
20, Câmara on Haas included. Suite: 572 passed. Warnings rose by one, a
FastF1 `enable_cache` deprecation notice raised once per test that sets up the
cache, which the new stale-cache test does.

Noted for step 8: an ad hoc session load outside `fast_f1.cli` let FastF1 fall
back to its default cache in the home directory. The CLI must set the cache up
as `fast_f1.cli` does.

## 2026-11-08 — Step 7: the race's rows are written

`odds_source/odds_file.py`'s `write_race_odds(path, point, entries)` reads and
writes the CSV as text with the `csv` module, never pandas, so a row it does
not touch is written back as it was. It writes through a temporary file and
`os.replace`, so a failure part way leaves the file whole.

As planned: each priced driver's `Odds` and snapshot column are set,
overwriting; a driver in the file for that race but not priced this run keeps
the row with both blanked; new drivers follow the race's rows. Settled while
building it:

- **All seven snapshot columns are added on the first write**, after the
  legacy ones. Adding a column changes every line in the file, so the plan's
  "every other race byte-for-byte unchanged" cannot hold for that one write.
  Adding them all at once means it happens once. The tests check other races'
  values after a first write and their bytes after a later one.
- **A race with no rows yet goes after the races before it**, not at the end
  of the file.
- **Nothing else in an existing row changes**, `Constructor` included. A
  driver's team does not change within a weekend, so overwriting it could only
  undo a hand fix, such as a constructor filled in for an unmatched name.

`StrategyBettingOdds` was checked for the D15 case: it looks odds up only for
the drivers it can pick, so an unmatched name's row adds a key it never reads,
and the real driver scores 0.0 until the row is fixed.

Red was the import failure only. Seven mutations, each restored and green
before the next: keeping an unpriced driver's odds (1 red), adding only this
run's column (3), new drivers at the end of the file (1), a new race at the end
of the file (1), setting the column but not `Odds` (2), copying instead of
replacing, which leaves the temporary file (1), and rewriting other races'
text (3).

**Run on real data**, from a scratch script: the whole chain on the Brazil page,
writing into a scratch copy of the real CSV. 440 rows, none added, as all 22
matched existing rows; nothing changed outside race 20; in race 20 only `Odds`
changed besides the new `Odds_Q`, which equals it; the hand-entered
`Odds_Pre_Weekend` prices are kept; `load_odds` reads 22 drivers from the copy.
The real CSV was not touched. Suite: 580 passed.

## 2026-11-08 — Step 8: the command, and Gate 1 cleared

`PYTHONPATH=. venv/bin/python -m odds_source.cli [page] [--odds-file F]
[--cache-dir D]`. As `fast_f1.cli` does, it loads the F1 credentials first and
exits 1 without them, then sets up the FastF1 cache, prompting only when no
location is saved. That closes the step 6 note about an ad hoc load falling
back to FastF1's default cache. With no page named, it takes the newest
`.mhtml` in `outputs/` by modification time, and says which page it read. A
page the chain rejects (no odds grid, no race nearby, saved after the race, an
unknown session or team) exits 1 before the odds file is opened, as every
check runs before the write. It prints the race, column, page, file, every
driver written, and any unmatched names to fix by hand.

The tests patch the cache setup and the two FastF1 fetches on the command
module, as `fast_f1.cli`'s tests do, and run the hand-written fixture page end
to end into a temporary odds file. Red was the import failure only. Five
mutations, each restored and green before the next: skipping the credentials
(2 red), always prompting for the cache (1), the newest page by name not time
(1), any file counting as a page (2), and letting a rejected page raise (1).

**Gate 1, cleared.** The command on Alex's saved Brazil page, live FastF1, the
saved cache location (no `--cache-dir`, which would have overwritten that
setting), writing into a scratch copy of the real CSV. As expected: race 20,
`Odds_Q`, 22 drivers, Ocon dropped, Câmara on `HAA`, every price the survey's
median. A separate comparison: 440 rows before and after, nothing changed
outside race 20, only `Odds` changed in its existing rows besides `Odds_Q`,
which equals it, and `load_odds` reads 22 drivers and 11 constructors from the
copy. The real CSV was not touched. FastF1's `enable_cache` deprecation warning
prints on every run, as it does for `fast_f1.cli`.

Suite: 587 passed. Gate 2 waits for the next race weekend.

## 2026-11-08 — Step 10: `indicator_analysis` reads the captured columns

`ODDS_LEAK_SNAPSHOT` and `ODDS_PRE_WEEKEND_SNAPSHOT` became tuples,
`ODDS_LEAK_SNAPSHOTS` (`Odds_Post_Quali`, `Odds_Q`) and
`ODDS_PRE_WEEKEND_SNAPSHOTS` (`Odds_Pre_Weekend`, `Odds_PreFP1`). The new names
are imported from `odds_source.schedule` rather than repeated. The three
places that compared against one name now test membership: the held-out
season's odds races, race 1's odds, and the pre-weekend split.

How a captured race is placed is unchanged: `odds_capture_points` already takes
the first `Odds_` column matching every driver. Should two snapshots of a race
be identical, it takes the earlier one, whose odds knew no more, so nothing
leaks.

Red in stages: with a capture map putting race 4 in `Odds_Q` and race 2 in
`Odds_PreFP1`, the held-out season scored 6 odds races instead of 5, and race 1
scored a season captured into `Odds_Q`. With the leak rule fixed, the
pre-weekend split then counted 2 races instead of 3; fixing it turned all
green. The existing tests, which use the legacy names, cover the unchanged
branch. `indicator_analysis.main()` was not run. Suite: 589 passed.

## 2026-11-08 — Step 9: docs; every step done (dev)

- `README.md`: the odds input section describes the CSV, the capture command
  and its columns, and marks the four hand-entered snapshot columns as legacy.
  The Excel date warning went, as a CSV has no cell formats. It also corrects
  an old claim: `Odds` is the only column the strategies and the `fast_f1`
  indicator read, but `indicator_analysis` has always read the snapshot
  columns, to find which one `Odds` came from.
- `CLAUDE.md`: a paragraph on `odds_source/`, the CSV path in the `fast_f1`
  paragraph, the odds data rule rewritten for the new columns, and the conftest
  rule now names the odds fixture.
- `docs/data_capture_v1/requirements.md`, an effort still in progress: its
  scope said the odds workbook stays as it is, now stale. Corrected in place,
  pointing at this effort's conversion method.
- `BACKLOG.md`: done (dev), Gate 2 pending. Finished efforts' docs that name
  the workbook are left as they are.

Every step is done; steps 1–7 and 9–10 are done (dev), and step 8 is verified
at Gate 1. **What has not been run:** a real write into
`data/f1_betting_odds.csv` itself, which is Gate 2, and
`indicator_analysis.main()`. Gate 2, at the next race weekend: Alex saves the
page, runs the command, and reviews the CSV's git diff before committing. The
first real run adds the seven snapshot columns, so every line of that diff
changes once; after that a run changes only its race's lines.

## 2026-11-09 — Gate 2: the first real run; effort done

The day after Brazil, with Las Vegas two weeks away, Alex saved Oddschecker's
Las Vegas winner page and the command ran against the real
`data/f1_betting_odds.csv` (`41abc78`). Suite green before the run: 656
passed.

It placed the page as 2026 race 21, `Odds_PreFP1` (saved 12:08 UTC, before
any session), and read the driver list from Brazil's race, as planned for a
run before FP1. All 22 drivers matched, with the same driver and team pairs as
race 20, and none was dropped: all 15 active bookmakers priced every driver
but Câmara, who had 11.

Checked against a copy of the file taken before the run, by a scratch script:
440 rows became 462, the 22 new ones together after race 20; no value changed
in any existing row, and the seven new columns are blank on all of them; in
race 21, `Odds` equals `Odds_PreFP1` and no other snapshot is filled. The
script caught one changed race 20 price in a damaged copy, so it can fail.
`load_odds` reads 22 drivers and 11 constructors for race 21.

Two findings, neither a fault:

- **Fourteen drivers are all at 500/1.** Their median is 500/1 because 8–11
  of the 15 bookmakers quote every back-of-grid driver at that price this far
  out. A snapshot this early cannot rank them; a later one, which Alex may
  take as routine use, can.
- **`Odds` changes method at race 21.** Alex's hand-entered prices for races
  1–20 were each driver's best price across the bookmakers; captured prices
  are the median (D16). Alex is happy with the median. `README.md` now says
  so beside the legacy columns.

Alex reviewed the diff and confirmed the odds. As expected, the first write
changes every line once, adding the seven columns' commas to the older rows.

**Every step and both gates are done.** Refreshing the odds nearer the race is
routine use, outside this effort.

**`indicator_analysis.main()` run on the real data afterwards**, the last item
listed as not run. It took about 2 minutes and wrote all seven tables
byte-for-byte identical to the previous run's, as expected: it scores only
races already in the metrics file, so race 21 does not enter it, and every
earlier race is found in the same legacy columns. That previous run, at 17:58
on 2026-11-08, came after steps 3 and 10 but was not logged here, so the note
above that it had not run was already stale. Nothing from the effort remains
unrun.
