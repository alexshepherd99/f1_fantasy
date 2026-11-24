# odds_fp3_v1 — Log

Execution log for the odds_fp3_v1 effort. Newest entries at the bottom.
Requirements and plan live alongside in `requirements.md` and `plan.md`.

## Status summary

- Effort started 2026-11-24. Step 1 (docs) is complete, with requirements and plan
  agreed.

## 2026-11-24 — Scoping

Alex asked for a race-1 strategy built on betting odds and FP3 only, back-tested on
2026's normal weekends with odds, and starting from an even split of the two. The
requirements were settled through a series of questions in conversation. Each answer
is recorded under the requirement it settles, and every option turned down is in
`requirements.md`, *Rejected options*.

Found while scoping:

- **The FP3 assumption mostly holds.** It is summarised in `requirements.md`, *The FP3
  assumption*, from `docs/indicator_analysis_v1/log.md`.
- **15 races are eligible today.** 2026 has odds for races 1–22. Of those, races 1, 3,
  6, 7, 8, 10, 11, 13, 14, 15, 16, 18, 19, 20 and 21 are normal weekends with FP3 in the
  metrics file. Race 22's metrics are not built yet.
- **The odds were taken at different points in the weekend.** Of the 15 races, 6 were
  taken before the weekend, 7 after FP2 (race 1 among them), 1 before qualifying
  (race 6) and 1 before FP1 (race 21). Live use will take the latest odds when the strategy runs, so the
  back-test's odds mostly predate what live use will see. This cannot be corrected, as
  the stored snapshots are all there is.
- **The two odds columns differ only in spacing.** `OddsRank` and
  `OddsImpliedProbability` put drivers in the same order, so `indicator_analysis_v1`'s
  Spearman scores cannot separate them. At 2026 race 3, implied probability gave
  0.52, 0.36 and 0.06 to the top three and 0.03 or less to everyone else, while
  `OddsRank` spread the field from 1.00 down to 0. `fastf1_v1` chose the log scale to
  keep the midfield apart. That settled `OddsRank` for the strategy, with
  `StrategyBettingOdds`, which reads implied probability, kept as a control.
- **The bar was explained before it was fixed.** It is the percentile bootstrap from
  `indicator_analysis_v1`'s R8, set out in plain steps in `requirements.md` R10. Its
  second condition, a positive gain in every season, adds nothing with one season and
  is left out.
- **One rule was added in drafting, not discussed:** if more than one mix passes R10,
  the highest average gain is chosen. Alex accepted it on reviewing these docs.
