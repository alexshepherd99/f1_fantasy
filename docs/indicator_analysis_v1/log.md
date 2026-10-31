# indicator_analysis_v1 — Log

Execution log for the indicator_analysis_v1 effort. Newest entries at the bottom.
Requirements and plan live alongside in `requirements.md` and `plan.md`.

## Status summary

- Effort started 2026-10-31. Step 1 (docs) is complete.

## 2026-10-31 — Scoping

Found while profiling the file, before any scoring was run:

- The file holds 88 races: 64 normal weekends, 18 sprint weekends with FP1 and
  Sprint Qualifying, and 6 2023 sprint weekends with FP1 alone. Odds cover 18 races,
  all in 2026.
- The `Odds` column uses different capture points by race. Race 4 is post-qualifying
  and race 6 pre-qualifying; the rest are pre-weekend or post-FP2.
- Races 12 and 14 price 13 and 10 drivers at 1000-1. That looks like the bookmaker's
  ceiling rather than a placeholder, so those prices are kept as they are. It does
  leave the back of the field tied on odds in those races.
- The archive identifies drivers as `DRIVERCODE@CONSTRUCTOR` and the metrics file as
  `DRIVERCODE`, so the join has to strip the constructor.
