# odds_fp3_v1 — Log

Execution log for the odds_fp3_v1 effort. Newest entries at the bottom.
Requirements and plan live alongside in `requirements.md` and `plan.md`.

## Status summary

- Effort started 2026-11-24. Step 1 (docs) is complete, with requirements and plan
  agreed.
- Step 2 (the strategy's shape) agreed 2026-11-24. See *Step 2* below.

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

## 2026-11-24 — Step 2: the strategy's shape

Agreed with Alex in conversation before he left steps 3–6 to run unattended.

- **`StrategyBase` does not accept an empty team.** `initialise()` takes the team's
  size from the team passed in, so an empty team would pick 0 drivers and 0
  constructors. `StrategyBase` stays unedited. Instead, the back-test passes a
  placeholder team, the race's cheapest 5 drivers and 2 constructors as
  `live.lineup` already does for race 1, with 7 moves allowed and the cap given
  through `factory_strategy`'s `max_cost`. Every asset can be replaced and the
  objective never reads the held team, so the placeholder cannot change the pick.
  It is entered in `docs/backtest_v1/requirements.md`'s R12 ledger at step 4. (The
  question put to Alex said the first 5 and 2 in data order. The cheapest was used
  to match the existing race-1 code, which makes no difference to the pick.)
- **The class:** `StrategyOddsFP3(StrategyBase)` in `linear/strategy_odds_fp3.py`.
  - Keywords `odds_weight: float = 0.5`, refusing anything outside 0–1, and
    `fn_metrics`, defaulting to `fast_f1.output.DEFAULT_HISTORICAL_OUTPUT`.
  - It reads the race's rows through `fast_f1.signal._race_rows` and
    `fast_f1.metrics.add_signal_inputs`. These reuse `fast_f1`'s matching of driver
    codes to fantasy identifiers and its weekend-format rule. The drivers are matched
    against the strategy's own available drivers, so no archive is loaded.
  - It raises `ValueError` on a sprint weekend or a race with no rows.
  - Driver value is `w × OddsRank + (1 − w) × FP3_MinLapTime_rank`. A missing input
    scores 0, and so does a driver with no metrics row. A constructor's value is the
    sum of its drivers' values.
  - DRS is chosen in the LP through `get_drs_objective_term`. `get_drs_driver`
    returns the LP's nominee, or `""` if the nominee's value is 0, as
    `StrategyBettingOdds` does.
  - The back-test builds the mixes with `backtest.variants.make_variant`.
- **The back-test module** is `backtest/race_one.py`, run as
  `python -m backtest.race_one`.
- **Scope of the unattended run:** steps 3–6, with each step pushed when done. R3's
  default changes only if R10's bar is passed.
