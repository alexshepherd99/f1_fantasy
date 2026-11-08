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
