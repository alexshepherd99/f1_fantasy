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
