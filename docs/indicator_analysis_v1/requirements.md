# indicator_analysis_v1 — Requirements

**Status**: agreed 2026-10-31. Plan in `plan.md`; findings in `log.md`.

Find which combination of the indicators in
`data/fastf1_practice_rolling_metrics.xlsx` best predicts race outcome, given that
each season carries a slightly different set of them.

## Sources consolidated

- User decisions, 2026-10-31, taken in conversation.
- `BACKLOG.md`, *Regress the FastF1 indicator against rolling points, both versus
  finishing position*. This effort answers that item, which is the go/no-go gate
  for *Build a strategy on the FastF1 indicators*. [2026-11-01: removed from the backlog,
  its last text being at commit `0a99751`. Answered in `log.md`.]

## R1 — Targets

Each signal is scored against two targets:

- **Primary: fantasy points**, from `data/f1_fantasy_archive.xlsx`. This is what
  team selection pays on.
- **Secondary: finishing position**, the `Position` column.

Winners are chosen separately for each target, since they may differ.

## R2 — Only information available at team lock

Grid position is known too late to pick a team, so it is only a reference ceiling
and can never be chosen.

2026 race 4's odds are a post-qualifying snapshot, so that race is left out of the
odds comparison.

## R3 — Five indicator slots

Indicators are lined up across weekend formats:

| Slot | Normal weekend | Sprint weekend |
| --- | --- | --- |
| `driver_rolling` | `RollingPointsRank` | `RollingPointsRank` |
| `constructor_rolling` | `ConstructorRollingPointsRank` | `ConstructorRollingPointsRank` |
| `early` | `FP2_MinLapTime_rank` | `FP1_MinLapTime_rank` |
| `late` | `FP3_MinLapTime_rank` | `SQ_MinLapTime_rank` |
| `odds` | `OddsRank` (2026 only) | `OddsRank` (2026 only) |

`RollingPointsRank` and `ConstructorRollingPointsRank` are championship points, not
fantasy points.

Normal and sprint weekends are analysed separately, because Sprint Qualifying is
close to a qualifying session rather than practice. 2023 sprint weekends hold FP1
alone, so they have no `late` slot and are only scored standalone.

Lap count and longest stint are screened standalone, and are not combination
candidates.

## R4 — Like-for-like comparison

- The race is the unit of evidence. Scores are computed per race, and options are
  compared by the race-by-race difference.
- Every comparison uses only races where all its options have data.
- Race 1 is excluded, because rolling points are empty there. [2026-11-01: still true
  of every comparison here. R12 scores race 1 on its own.]
- Drivers who did not start or withdrew are dropped. Retirements stay in, since a
  team picker suffers them too, with a finishers-only rerun as a sensitivity.

## R5 — Scoring

- Primary score: Spearman rank correlation per race, averaged across races.
- Also reported: top-3 and top-5 hit rates, meaning the share of the actual top k
  that the signal also placed in its top k.

## R6 — Candidates and selection

- Candidates are the 15 equal-weight sums of the four non-odds slots.
- Benchmarks are rolling points alone (the baseline every win is measured against),
  the rebuilt `AggregateRank` (`driver_rolling` + `early` + `late`, plus odds in
  2026), and grid position as a ceiling. [Corrected 2026-10-31: grid position turned
  out not to be a ceiling for fantasy points, so it is reported as a plain comparison.
  The odds are only added to the aggregate in the odds comparison, so that the
  all-season comparisons stay like for like. See `log.md`.]
- `AggregateRank` is rebuilt from its components because its stored value adds up
  different inputs by season.
- The winner is chosen on 2023–25 (2024–25 for sprint weekends, the earlier seasons
  having no comparable `late` slot) by highest mean Spearman, then tested on 2026.
- Leave-one-season-out selection shows how stable that choice is.

## R7 — Fitted weights

Least squares on within-race ranks, fitted on all seasons but one and scored on the
season left out. It is adopted only if it beats the equal-weight winner on seasons
it was not trained on, by the bar in R8.

## R8 — The bar for a win, set before any results were seen

A combination beats its comparison only if both of these hold:

1. The 95% interval on the mean per-race Spearman gain excludes zero. The interval
   is a percentile bootstrap, resampling races, with 10,000 resamples and a fixed
   seed.
2. The mean gain is positive in every season.

Anything else is written up as no measurable difference. The size of the gain is
always reported, because passing does not mean it is big enough to matter.

The interval spans the seasons the winner was chosen on, which flatters it, so the
2026-only figure is reported beside it. It does not correct for trying 15
candidates; condition 2's 2026 result is the guard against that.

## R9 — Odds

Judged within 2026 only, on the races left after R2 and R4. Compared race by race:
the best non-odds combination, odds alone, and the two together. Condition 2 of R8
adds nothing with one season, so a modest real gain may well read as no measurable
difference; that is reported as unproven, not as evidence that odds do not help.

Odds are captured at different points in the weekend, so the result is also split
by capture point.

## R10 — Sensitivities on the chosen combination

- True within-race ranks in place of the stored min-max scaled `_rank` columns,
  since one very slow lap squeezes every other driver's score in a sum.
- Dropping drivers who set no lap time, who currently score 0, the same as the
  slowest driver.

## R11 — Constraints

- `races/`, `linear/`, `import_data/` and `scripts/` are not edited. `import_data`
  is read through its existing loaders.
- No new dependencies: numpy, scipy and pandas only.
- Results go to `outputs/` (not tracked) and findings to `log.md`.

## R12 — The first race, added 2026-11-01

Which signal best predicts race 1, where R4 leaves the question unanswered. Agreed in
conversation, from `BACKLOG.md`'s follow-ups to this effort.

- **Signals:** the race 1 fantasy price; each driver's total fantasy points last
  season, across constructors; the `early` and `late` slots and their sum; and odds,
  with R2 applied. Grid position is a reference only, as in R2. FP1 on normal weekends
  and pre-season testing are not in the metrics file and are left out.
- **FP3 counts,** since it runs before team lock. The 2026 team was picked after FP2,
  so the `early` row is the one that matches that routine.
- **Drivers:** as R4, less race 1's exclusion. A driver with no previous season has no
  score from that signal alone, and 2023 has no previous season in the archive.
- **Scoring:** R5, against both targets, per season and averaged. Each signal is scored
  on the data it has, and again on only the drivers and seasons that every signal bar
  odds and grid has, so that those signals can be compared like for like.
- **No winner and no R8 bar.** There is one race per season, so four at most, and
  condition 2 would be a single race's sign. The result is reported as size and spread.
  [2026-11-01: the analysis still declares no winner. Having seen it, Alex took odds as
  the best predictor so far, accepting the very limited data. See `log.md`,
  *Conclusions*.]

## Out of scope

- Whether a better driver ranking makes a better fantasy team. The budget and
  transfer limits sit in between, and only a back-test can show that.
- Changing `METRIC_WEIGHTS`, or building a strategy on the result.
- Weather. The file has no wet-session flag, so wet practice adds unmodelled noise.
