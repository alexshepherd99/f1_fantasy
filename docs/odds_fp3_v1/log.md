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

## 2026-11-24 — Step 3: the strategy

`StrategyOddsFP3` in `linear/strategy_odds_fp3.py`, in the shape agreed at step 2, with
14 tests in `tests/test_strategy_odds_fp3.py`. The tests write a small metrics file, so
the strategy's real file reading runs. Each test team is 1 or 2 assets, and the tests
assert the LP's objective as well as the pick.

- **Red before green.** The only red before the code existed was the missing module,
  which shows nothing. So each test was checked by breaking the finished code instead.
  All 11 breaks turned at least one test red, and the restored file passed again:
  swapping the weight, a constructor taking its best driver's value rather than the
  sum, no zero for a missing odds or FP3 input, no zero for a driver with no metrics
  row, no DRS term in the objective, always using the LP's DRS nominee, no sprint check,
  no weight check, no check for an empty race, and a default weight of 0.6.
- **Run on the real metrics file.** All 15 eligible races solved, using a placeholder
  team and a flat 100m cap. 2026 race 2, a sprint, raised as intended. The back-test's
  own cap (R8) comes at step 4.
- Nothing in `races/`, `import_data/`, `scripts/`, `StrategyBase` or any existing
  strategy was edited. The strategy reuses `fast_f1.signal._race_rows`, a private
  function, as `linear/strategy_odds.py` already imports `_FILE_BETTING_ODDS`.

## 2026-11-24 — Step 4: the single-race back-test

`backtest/race_one.py`, run as `PYTHONPATH=. venv/bin/python -m backtest.race_one`, with
31 tests in `tests/test_backtest_race_one.py`. It was built in four commits: the cap,
placeholder and scoring; the random teams; finding the races; and running a race plus
the command line.

- **What it does at each race.** The 5 mixes, max budget and betting odds each pick a
  team from the placeholder (the race's cheapest 5 drivers and 2 constructors), with 7
  moves and R8's cap. Each team is scored on that race's archive points, and the DRS
  driver counts twice. That is the strategy's own nominee, or the dearest driver for
  max budget, as the game does. The picks go through the existing
  `simulate.pick.solve_race`. The rows go to `outputs/odds_fp3_v1_races.csv`, one per
  race and label, with the cap, cost, team, DRS driver and points.
- **The cap** reuses `simulate.pick.limitless_cap`, which already sums the grid's prices.
  The 15 races' caps run from 100m (race 1) to 105.3m (race 18).
- **The random teams.** Teams are drawn as 5 drivers and 2 constructors at random, and a
  team is kept only if it fits the cap, so every team that fits is equally likely. That
  continues until 1,000 are kept. The seed is 1, combined with the race number, so
  adding races at the season-end rerun leaves each race's draw unchanged. The draw
  raises, rather than looping for ever, when no team fits or after 1,000 draws per team
  wanted.
- **The eligible races** are found afresh on each run. A race qualifies when:
  - it has been run (some asset scored points, since the archive loads a race not yet
    run with every point 0);
  - its metrics hold FP3 and odds above zero;
  - and the odds file prices it.

  Only a normal weekend runs FP3, so sprints drop out with no format check. A race
  whose metrics scored odds all zero, although the odds file has them, was built
  before the odds were added. It is left out with a warning to rebuild it. On today's
  data the run finds R7's 15 races. Race 22 has odds, but no metrics or points yet.
- **Red before green.** Where the only red possible was a missing name, a stub returning
  nothing turned the tests red on behaviour first. Each piece was then checked by
  breaking it. Four breaks first survived and the tests were strengthened:
  - the constructor tie-break, since the fixture's tie was not at the cut-off;
  - DRS on the first driver by name, since the fixture's dearest driver also sorted
    first;
  - a format check that the FP3 check already covers, so the format check was removed;
  - picks held to 2 moves, since at an 80m cap every best team was within 2 moves of the
    placeholder. The fixture's cap is now 95m, where max budget and odds alone each
    need 3.

  Two breaks that hung rather than failed led to the draw limit above.
- **The real run** took 24 seconds at a peak of 197 MB and wrote 120 rows. A second run
  wrote a byte-identical file. Every pick was within its cap. The results are read at
  step 6.
- **R12 ledger**: the placeholder team is entered in
  `docs/backtest_v1/requirements.md`. It copies four lines that `live.lineup` writes
  inline. Nothing in `races/`, `linear/`, `import_data/` or `scripts/` was edited.
- **Process slip:** one import line in the test file was changed with `sed` rather than
  the Edit tool, so it had no diff for review. It is the `from backtest.race_one import
  ...` line, since rewritten with Edit.

## 2026-11-24 — Step 5: the comparison and the bar

In `backtest/race_one.py`, with 10 more tests (41 in the file).

- **`compare_with_even_split`** pairs each label's points with the 50/50 mix's at the same
  race. A label missing a race raises an error. For each label it gives the mean gain, the
  95% interval from `fast_f1.indicator_analysis.bootstrap_interval` (10,000 resamples, its
  fixed seed) and a pass when the whole interval is above zero. `compare_scores` in the
  same module was not reused. Its win rule adds the every-season condition that R10
  leaves out, and its columns are named for Spearman scores.
- **`choose_default`** takes the passing mix with the highest mean gain, or keeps 50/50
  when none passes. A passing control is reported but never chosen.
- **The command line** now also writes `outputs/odds_fp3_v1_comparison.csv`, and logs the
  comparison table and the default.
- **Built to pass and built to fail.** A mix 10 points ahead at every race passes, with an
  interval of exactly 10 to 10. A mix whose gains swing from +40 to −30, averaging +5,
  fails because its interval reaches below zero. Breaking the code was caught every time:
  - passing on the mean or on the interval's top rather than its bottom;
  - a gain taken the wrong way round;
  - pairing by row position rather than race;
  - no check for a missing race;
  - choosing the lowest passing gain;
  - letting a control become the default;
  - every label counted as a mix;
  - 50/50 compared with itself;
  - the comparison file or the logged default left wrong.
