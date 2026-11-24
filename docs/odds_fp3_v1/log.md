# odds_fp3_v1 — Log

Execution log for the odds_fp3_v1 effort. Newest entries at the bottom.
Requirements and plan live alongside in `requirements.md` and `plan.md`.

## Status summary

- Effort started 2026-11-24. Step 1 (docs) is complete, with requirements and plan
  agreed.
- Step 2 (the strategy's shape) agreed 2026-11-24. See *Step 2* below.
- Steps 3–6 done 2026-11-24, while Alex was away: `StrategyOddsFP3`, the single-race
  back-test `backtest/race_one.py`, and its first run. **No mix cleared R10's bar, so the
  default stays 50/50.** The signal clearly beats max budget and random teams, and is
  level with the betting-odds strategy. See *Step 6*.
- **Next:** step 7, the rerun once 2026 race 24 is captured and its metrics are built,
  then step 8, the close-out.

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

## 2026-11-24 — Step 6: the run and findings

### In plain language

Each of 15 race weekends in 2026 was treated as if it were the season's opening race. At
each one, a team was picked from scratch using only betting odds and FP3 lap times, then
scored on that race's real fantasy points. The odds and FP3 were mixed in five ways, from
FP3 alone to odds alone. Each mix was set against the even 50/50 split, which stays the
default unless another mix clears the bar fixed beforehand (R10).

- **No mix cleared the bar, so 50/50 stays the default.** Every mix's interval runs
  from below zero to above it. On 15 races, the differences between the mixes cannot
  be told apart from luck.
- **FP3 alone had the best average, but one race made it.** It was 10.7 points a race
  ahead of 50/50. At race 13 alone it was 144 points ahead. Without that race the lead
  is 1.2.
- **The signal clearly beats picking on price or at random.** 50/50 scored 75 points a
  race more than spending the whole budget, and 87 more than the average random team.
  In both cases the whole interval is clear of zero. Mixing odds with FP3 carries real
  information about who will score.
- **It is level with the betting-odds strategy** Alex played at 2026 race 1. The
  betting-odds strategy was 13.8 points a race behind 50/50, but its interval reaches
  above zero, so there is no measurable difference.
- **At the one real race 1,** 50/50 scored 259, betting odds 234, odds alone 244 and FP3
  alone 220. That is one race and is not evidence on its own.

What this can and cannot show: the intervals are about ±25 points a race wide. A real
difference smaller than that between two mixes would not show up on 15 races. The
result says 50/50 is not beaten by a measurable margin. It does not say 50/50 is best.
The odds were mostly taken before or during the weekend, not after FP3 as live use will
take them (*Scoping*), so live odds may carry a little more information than these did.

### Detail

Run with `PYTHONPATH=. venv/bin/python -m backtest.race_one` at commit `cc2f0c5`, on
the 15 races R7 lists. Results are in `outputs/odds_fp3_v1_races.csv` and
`outputs/odds_fp3_v1_comparison.csv`. The run takes 24 seconds and repeats
byte for byte (step 4).

Against 50/50, gain in points per race (R10's bar: the whole interval above zero):

| Label | Kind | Mean gain | 95% interval | Passes |
| :--- | :--- | ---: | :--- | :--- |
| FP3 alone (`OddsFP3_w0`) | mix | +10.7 | −15.7 to +38.7 | No |
| Odds 0.25 (`OddsFP3_w0p25`) | mix | −7.8 | −24.1 to +9.1 | No |
| Odds 0.75 (`OddsFP3_w0p75`) | mix | −6.1 | −14.9 to +2.7 | No |
| Odds alone (`OddsFP3_w1`) | mix | −8.1 | −22.8 to +5.5 | No |
| Max budget | control | −75.5 | −110.9 to −38.7 | No |
| Betting odds (`StrategyBettingOdds`) | control | −13.8 | −39.1 to +13.6 | No |
| Random teams (mean of 1,000) | control | −87.2 | −117.0 to −57.1 | No |

Points per race, each team picked from scratch under the race's cap (R8):

| Race | Cap | FP3 alone | 0.25 | 50/50 | 0.75 | Odds alone | Betting odds | Max budget | Random |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 100.0 | 220 | 220 | 259 | 259 | 244 | 234 | 142 | 94 |
| 3 | 100.9 | 247 | 248 | 286 | 286 | 286 | 196 | 131 | 109 |
| 6 | 102.1 | 174 | 174 | 106 | 74 | 56 | 79 | −8 | 59 |
| 7 | 101.7 | 146 | 99 | 99 | 73 | 73 | 38 | 138 | 73 |
| 8 | 101.4 | 226 | 194 | 210 | 210 | 210 | 189 | 119 | 82 |
| 10 | 101.6 | 223 | 209 | 209 | 182 | 182 | 166 | 204 | 105 |
| 11 | 102.5 | 237 | 237 | 213 | 236 | 236 | 213 | 149 | 112 |
| 13 | 103.6 | 288 | 144 | 144 | 106 | 160 | 252 | 196 | 170 |
| 14 | 104.6 | 155 | 126 | 140 | 140 | 164 | 164 | 15 | 59 |
| 15 | 104.7 | 130 | 154 | 227 | 227 | 201 | 237 | 24 | 77 |
| 16 | 105.0 | 261 | 200 | 200 | 196 | 196 | 119 | 187 | 152 |
| 18 | 105.3 | 242 | 221 | 265 | 265 | 192 | 190 | 116 | 99 |
| 19 | 105.0 | 132 | 132 | 136 | 142 | 125 | 135 | 76 | 88 |
| 20 | 104.9 | 204 | 189 | 205 | 190 | 231 | 214 | 92 | 114 |
| 21 | 104.7 | 170 | 230 | 195 | 217 | 217 | 261 | 181 | 191 |
| **Mean** | | **203.7** | **185.1** | **192.9** | **186.9** | **184.9** | **179.1** | **117.5** | **105.7** |

Random-team points are rounded to whole points here.

- **The mixes do not rank in weight order.** FP3 alone is first, 50/50 second, and 0.25
  below both. With the intervals this wide, that pattern is what noise looks like, not
  a sign that the scale is wrong.
- **FP3 alone was ahead of 50/50 at 8 races and behind at 7.** Its +10.7 is 161 points
  over 15 races, and race 13 gives 144 of them. The betting-odds control was also 108
  ahead there. At that race the 50/50 and 0.25 mixes picked the same team, and FP3 alone
  did not.
- **Neighbouring mixes often pick the same team,** with the same DRS driver. 50/50 and
  0.75 matched at 6 of 15 races, 50/50 and 0.25 at 4, and 50/50 and odds alone at 2.
- **Max budget spent all but 0.05m of its cap on average, 50/50 left 0.76m and betting
  odds 1.04m.** So the signal's lead over max budget is not from spending less.
- **R3 is unchanged:** the default stays `odds_weight = 0.5`.
- R11's rerun after the season ends (step 7) is a check on this run, not a second
  chance. A different answer there is set out for Alex to decide before 2027 race 1.

## 2026-11-24 — Follow-up: race 13, and 50/50 against betting odds

Alex asked why race 13 swung so far for FP3 alone, and whether 50/50 has any edge over
the betting-odds strategy once race 13 is left out. Both answers below were worked out
from `outputs/odds_fp3_v1_races.csv`, the 2026 archive points and the metrics file.
Nothing was rerun or changed.

### Why race 13 swung

FP3 alone scored 288 there and 50/50 144. FP3 alone held Mercedes and 50/50 held
Ferrari, and the weekend went to extremes.

| | FP3 alone | 50/50 | Difference |
| :--- | :--- | :--- | ---: |
| Constructor | Mercedes, 128 | Ferrari, 24 | +104 |
| Drivers, DRS counted twice | Russell DRS (33 × 2), Colapinto, Gasly, Hülkenberg, Lindblad | Hamilton DRS (26 × 2), Leclerc (−12), Bortoleto, Hülkenberg, Lindblad | +40 |
| Second constructor | Audi, 41 | Audi, 41 | 0 |

- **Odds and FP3 disagreed about Ferrari.** On odds, Leclerc (0.94) and Hamilton (0.90)
  were close to Russell (1.00) and ahead of Antonelli (0.75). In FP3, Russell was
  fastest and Antonelli (0.89) was level with both Ferraris.
- **At 50/50 the two teams all but tied.** A constructor's value is its drivers' sum:
  about 1.82 for Mercedes and 1.81 for Ferrari, from the metrics' rounded inputs.
  Ferrari was 6m cheaper, so the LP took it and spent the difference on drivers. With
  FP3 alone, Mercedes led 1.89 to 1.78 and was picked.
- **The race then went as badly as it could for that choice.** Antonelli won (93
  points) and Russell was second, so Mercedes scored 128 as a constructor. Leclerc
  finished last on −12.

So the 144 points rest on a hundredth of value between two teams, decided by an extreme
result. It is weak evidence for FP3 over 50/50.

### 50/50 against betting odds without race 13

This is a check made after seeing the results, not part of R10's bar. The bar is fixed,
and the default does not move on it.

| 50/50 minus betting odds | Mean (points/race) | 95% interval | Races ahead / behind / level |
| :--- | ---: | :--- | :--- |
| All 15 races | +13.8 | −13.6 to +39.1 | 9 / 5 / 1 |
| Without race 13 | +22.5 | −0.4 to +44.9 | 9 / 4 / 1 |

- **Race 13 cut the other way here.** Betting odds held Mercedes too and scored 252,
  108 ahead of 50/50. It was the worst race for 50/50 against betting odds, so removing
  it helps 50/50 more than removing any other race would.
- **Even so, the interval does not clear zero.** Dropping each of the 15 races in turn
  leaves 50/50 between 8.4 and 22.5 points a race ahead, and none of the 15 intervals is
  wholly above zero. Race 13 is the only removal that comes close.
- **So 50/50 leads betting odds on average, but not measurably.** It was ahead at 9 of
  15 races. The lead could be real, but 15 races cannot show it. Race 13 was chosen
  after seeing the results, so leaving it out is not grounds to call a winner.
