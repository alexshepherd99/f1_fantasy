# fastf1_v2 — Log

Execution log for the fastf1_v2 effort. Newest entries at the bottom. Requirements live
alongside in `requirements.md`, and the steps in `plan.md`.

## Status summary

- Effort opened 2026-11-01. The backlog item has moved to `requirements.md`. Questions
  are being asked one at a time, and no code has been written.
- All eight questions answered and the working assumptions confirmed 2026-11-01. `plan.md` is
  written and no step has started.
- Step 1.1 done 2026-11-06: `TeamId` survives the rename, but the fix links names through the
  drivers instead. See the entry of that date.
- Step 1 done 2026-11-06, with the fix in code and tested.
- Step 2 done 2026-11-06: 2024 race 24 recomputed, with only its 8 affected rows changed.
- Step 3b added 2026-11-06, at Alex's request: a driver's team before the race has results.
- Step 3 done 2026-11-06: the winners hold, and one robustness check moved from pass to fail.
- Step 3b done 2026-11-06, and checked on two past races. Its first real pre-race run is
  São Paulo, 2026 race 20.
- Step 4 done 2026-11-06: `fast_f1/signal.py` gives driver positions and constructor places,
  run on every stored race. Step 5 is next.
- Step 5 done 2026-11-06: expected points and the chance of going negative, with means forced
  to fall by position and negatives split on any recent one. Step 6 is next.
- Step 6 done 2026-11-06: `StrategyFastF1` in `linear/strategy_fastf1.py`, with its DRS term,
  budget reward and negative penalty, run once on a real race with no signal. Step 7 is next.
- Step 7 done 2026-11-06: the strategy and its six tuning variants are in `backtest/cli.py`,
  and a 3-team run went through the harness. Step 8 is next.
- Step 8 done 2026-11-06: none of the six variants cleared the bar against the base, so
  step 9 runs `StrategyFastF1` at its defaults. Every label trailed P2PM in all of 2023–25.
  Step 9 is next.
- Stepped back 2026-11-06, before step 9, at Alex's request. The signal ranks well, but the
  expected-points table loses how far ahead an asset is, and in 2023 it never bought VER.
  Step 9 is on hold, and the signal design is to be redone in a fresh session. See the entry
  of that date, *Stepping back*.
- Signal redesign agreed 2026-11-07, with steps 11 to 16 added to build and tune it. Steps 9
  and 10 were renumbered 17 and 18 the same day, to run in number order; entries dated
  before then name them by their old numbers.
- Step 11 done 2026-11-07: `driver_values` and `constructor_values`, run on every stored race
  from race 2. Step 14.1 is next.
- Step 14.1 done 2026-11-07: the size check passes in every season of 2023–25, by a small,
  consistent margin. Step 12 is next.
- Step 12 done 2026-11-07: `negative_chance` by price third and `price_rise` by value-per-1m
  third, run on every stored race from race 2. The expected-points table stays until step
  13.1. Step 13 is next.
- Step 13.1 done 2026-11-07: `StrategyFastF1` scores step 11's values, and the
  expected-points table and position code are gone. Step 13.2 is next.
- Step 13.2 done 2026-11-07: the DRS code already matches the plan, with no change needed.
  Step 13.3 is next.
- Step 13.3 done 2026-11-07: the negative penalty already matches the plan. One rule had no
  test, so one was added. Step 13.4 is next.
- Step 13.4 done 2026-11-07: the budget reward already matches the plan, with no change
  needed. Step 13.5 is next.
- Step 13.5 done 2026-11-07: the price-rise reward, new code. Step 13.6 is next.
- Step 13.6 done 2026-11-07: a race with no signal already solves at every setting, with the
  test extended. Step 13 is done, and step 14.2 is next.
- Step 14.2 done 2026-11-07: the VER check passes, with VER held in 93% of 2023's team-races
  from race 10 onwards against a mark of more than half. Step 15 is next.
- Step 15 done 2026-11-07: the tuning values were fixed before any run (penalty 6.5/13/26,
  budget reward 0.1/0.25/0.5, price-rise reward 5/10/20), and the 11 labels are in
  `backtest/cli.py`. Step 16 is next.
- Decisions so far: see `requirements.md`, *Decisions so far*, which is kept current.

## 2026-11-01 — Sizing the two levers in the brief

[2026-11-01: some field-wide driver figures in this entry are diluted, including the budget
bound, and its claim about the indicators was only reasoned. Both are dealt with in the next
entry, which has the corrected figures.]

Alex's brief names negative scores and unspent budget. Both were sized from data already
on disk, before asking any design question. The numbers came from throwaway scripts that
are not kept, and the method below is enough to rebuild them.

The P2PM figures use `outputs/max_points_v1_per_race.parquet`, the only store with every
race: 1,500 teams a season over 2023–25. As a check on what its columns mean, each race's
`points` was rebuilt from the held drivers, the constructors and one extra DRS copy, for
all 100,500 P2PM rows after race 1, with no mismatches. The field-wide figures use the
archive through `load_with_derivations`, leaving out 2026's unscored race 19.

### In plain language

- **Negative scores are as big a lever as any measured so far.** Negative results cost
  P2PM's teams 202, 313 and 275 points in 2023–25. The best possible DRS pick would gain
  226, 103 and 98, and the signal itself is estimated to add about 50–130. All of these
  bar the last are hindsight ceilings, not gains anyone can collect.
- **They are only partly predictable.** The worst quarter of the field goes negative
  about a quarter of the time, but the best five drivers still do 9% of the time. A
  negative score costs about the same wherever the driver ranks.
- **Spending the budget has not, by itself, bought points.** P2PM leaves more money
  unspent than the Max Points strategy it beat, and Max Budget spends the most of all and
  loses by 21–36%. So whether spending helps a signal strategy is still open.
- **What a strategy earns in budget growth may matter as much as what it spends.** The
  price-blind odds strategy was about 10m behind P2PM's budget by 2026 race 17.

### Negative scores

Across the field, per season:

| Season | Driver results negative | Mean when negative | Constructor results negative | Mean when negative |
| --- | --- | --- | --- | --- |
| 2023 | 14.9% | −11.0 | 10.0% | −14.0 |
| 2024 | 12.2% | −12.2 | 13.3% | −12.8 |
| 2025 | 15.9% | −11.7 | 12.1% | −11.4 |
| 2026 | 18.5% | −14.4 | 18.2% | −16.2 |

What they cost P2PM's teams, as a mean per team-season. "If zero" is the gain if every
held asset's negative score had been zero instead, with hindsight:

| Season | Season points | Drivers | Extra DRS copy | Constructors | If zero | Share of season |
| --- | --- | --- | --- | --- | --- | --- |
| 2023 | 5,505 | −184 | −14 | −4 | +202 | 3.7% |
| 2024 | 4,547 | −268 | −27 | −18 | +313 | 6.9% |
| 2025 | 4,948 | −236 | −19 | −20 | +275 | 5.6% |

Between 56% and 66% of P2PM team-races hold at least one negative asset. Drivers are
nearly all of the cost, so P2PM already mostly avoids negative constructors. A new
objective could lose that protection.

**Predictability, drivers.** Position is the driver's place on the winning signal
(driver + constructor + FP3, or driver + constructor on sprint weekends), races 2 onwards
across all four seasons. Each row covers about 420 driver-races.

| Signal position | Mean fantasy points | Share negative | Mean when negative |
| --- | --- | --- | --- |
| 1–5 | 26.8 | 9.0% | −10.0 |
| 6–10 | 13.7 | 12.1% | −12.9 |
| 11–15 | 5.1 | 20.2% | −11.7 |
| 16+ | 3.0 | 23.9% | −12.8 |

**Predictability, constructors.** Holding a top-four constructor on rolling fantasy points
goes negative at most 6% of the time, against 23–26% at places 9–10 and 59% at place 11
(2026 only, 17 races).

**A negative tends to follow a negative.** The chance of a driver going negative is 12%
after no negatives in the last three races, 20% after one and 23% after two. For
constructors it is 9%, 19% and 34%. This does not control for how good the car is, so it
may only be measuring that again.

**The indicators cannot see a negative.** `RollingPointsRank` and
`ConstructorRollingPointsRank` use championship points, which stop at zero, so a
retirement looks the same as an uneventful 11th. This is reasoned from their definition,
not measured. The archive's fantasy rolling points do include negatives, and were not
candidates in `indicator_analysis_v1`.

**The mean already includes the negatives.** The mean points above are after negative
results. So an objective in expected points would price average negative risk in without
a separate term, while a rank-based one would not.

### The signal's shape

`indicator_analysis_v1` validated the signal's order, and an LP adds the values up, so
the gaps matter too. Those gaps are uneven. Mean fantasy points by signal position run
from 34.8 at 1st to 20–23 at 4th and 5th, then 6.8 at 11th and about 1–6 from there to
20th. Places 11 to 20 are close to interchangeable, and the front is not.

Whether that changes which team wins has not been run. It is the reason behind
question 1 in `requirements.md`.

### Unspent budget

| Season | Mean unused, P2PM | Share of budget | Median | 90th percentile | Mean unused, Max Points |
| --- | --- | --- | --- | --- | --- |
| 2023 | 4.30 | 3.8% | 2.8 | 10.1 | 2.39 |
| 2024 | 2.25 | 2.0% | 1.8 | 5.2 | 1.99 |
| 2025 | 3.67 | 3.1% | 2.2 | 9.0 | 1.98 |

All are races 2 onwards. P2PM has under 0.5m left in only 10–23% of team-races.

**A rough upper bound on what it is worth: 55 to 225 points a season.** Within a race, 1m
of price goes with about 1.0–1.25 points for a driver and 2.1–2.8 for a constructor.
Multiplying by the mean unused budget and the races solved gives 55–113 at the driver rate
and 146–223 at the constructor rate. This is reasoned, and it is an upper bound: price and
points going together does not mean that spending buys the points, and the move limit
stops a team spending it all.

**The evidence so far does not say spending helps:**

- Max Budget spends the most and trails P2PM by 21–36%.
- Max Points leaves less unspent than P2PM in all three seasons, and still loses.
- Across P2PM's own teams within a race, more unused goes with slightly fewer points
  (Spearman −0.05, −0.24, −0.19). That is confounded by which line-up each team holds,
  and those are few after race 4.

**Budget growth is a separate effect.** A strategy's budget grows only through the price
rises of what it holds, and cash earns nothing.

| Strategy | Final budget 2023 | 2024 | 2025 |
| --- | --- | --- | --- |
| P2PM | 135.8 | 127.3 | 138.4 |
| Max Points | 134.6 | 126.0 | 136.0 |

P2PM's budget grows about 1.1–1.5% a race on the money invested. At that rate, 3m left
uninvested all season forgoes only about 1m. The larger gap is between objectives: in
`odds_drs_v1`'s 2026 store the odds strategy had a mean budget of 114.6 at race 17 against
P2PM's 124.6. A price-blind signal strategy could fall behind the same way.

**A hard "spend it all" rule cannot work.** With two moves a race, a team often has no
pair of swaps that uses the money exactly, so a strict rule would make the LP infeasible
(reasoned). Any budget term has to be a soft one in the objective, which can be tested at
zero. `max_points_v1`'s proposal described this lever and never tuned it.

## 2026-11-01 — Checking the rolling indicators' source, and a correction

Alex asked for the "indicators cannot see a negative" claim above to be checked, given
that fantasy points are available. Alex also agreed there will be no hard rule on maximum
spend, with a soft term to be tested. Again from a throwaway script, not kept.

### In plain language

**The claim is true, but on this evidence it does not matter much.** The rolling
indicators are championship points. Swapping in the archive's fantasy rolling points
predicts race results no better, and does not sort negative scores any better. This tests
the order of drivers only, not the teams a strategy would pick.

### Is it championship points? Yes, run

- The metrics file's race `Points` only ever hold championship values, from 0 to 26.
- `RollingPoints` rebuilds exactly from the previous three races of that column: 1,700
  rows, no mismatches. Both rolling columns have a minimum of 0.
- Of 312 negative fantasy results, 305 scored zero championship points and 7 scored some.
- 204 of those 312 have the status `Retired`, about two-thirds, which fits their being
  only partly predictable.

### Is fantasy rolling usable? Yes, run

`Points Cumulative (3)` in the archive derivations covers the previous three races only,
so it has no look-ahead: all 2,092 rows match a rebuild from prior races. Negative values
do occur in it (264 of 1,696 driver rows, and 146 for the driver's constructor). It runs
close to the championship version, with a mean within-race Spearman of 0.85 for drivers
and 0.91 for constructors. It restarts when a driver changes constructor, as README notes.

### Does swapping it in help? Not measurably

The rolling slots were swapped in the winning signal, min-max scaled within each race as
the stored ranks are, then compared with the winner against fantasy points. None passes
`indicator_analysis_v1`'s bar.

| Normal weekends, 60 races (winner 0.600) | Spearman | Gain | Season gains 2023 to 2026 |
| --- | --- | --- | --- |
| Fantasy driver, championship constructor | 0.601 | +0.001 | −0.005, −0.008, +0.026, −0.016 |
| Championship driver, fantasy constructor | 0.598 | −0.003 | −0.007, −0.008, +0.010, −0.009 |
| Both fantasy | 0.593 | −0.007 | −0.021, −0.010, +0.023, −0.028 |

| Sprint weekends, 18 races (winner 0.569) | Spearman | Gain | Season gains 2024 to 2026 |
| --- | --- | --- | --- |
| Fantasy driver, championship constructor | 0.565 | −0.003 | −0.029, −0.025, +0.044 |
| Championship driver, fantasy constructor | 0.583 | +0.015 | +0.014, +0.015, +0.015 |
| Both fantasy | 0.548 | −0.021 | −0.015, −0.043, −0.004 |

The sprint +0.015 is the only row positive in every season. Its interval spans zero, about
−0.018 to +0.052, and it is the best of six tries.

Sorting negatives, by share of drivers going negative at each signal position:

| Signal position | Championship rolling | Both fantasy |
| --- | --- | --- |
| 1–5 | 9.0% | 8.6% |
| 6–10 | 12.1% | 14.5% |
| 11–15 | 20.2% | 18.1% |
| 16+ | 23.9% | 24.1% |

### Correction to the sizing entry above

The derivations frame holds a row for every `DRIVER@CONSTRUCTOR` at every race, with zero
points for a stint the driver was not in. So 2,092 rows stood for 1,818 real driver-races,
and that entry's field-wide driver figures were diluted. Restricted to real driver-races:

| Figure | As logged | Corrected |
| --- | --- | --- |
| Driver results negative, 2023 to 2026 | 14.9%, 12.2%, 15.9%, 18.5% | 16.4%, 15.2%, 18.3%, 20.2% |
| Negative after no negatives in the last three races | 12% | 15% |
| Points per 1m of driver price | 1.0–1.25 | 1.0–1.3 |
| Budget bound at the driver rate, points a season | 55–113 | 68–118 |
| Overall budget bound, points a season | 55–225 | about 70–225 |

Unaffected: everything measured on P2PM's held teams, which were reconciled to their
points, the signal-position tables, which come from a frame validated one row per driver
per race, and all constructor figures. The other negative-after-negative figures hold, at
20% after one and 23% after two.

## 2026-11-01 — Reaching fantasy assets, and a fault in 2024 race 24

Checked for question 8, from throwaway read-only scripts, not kept. No data file was changed.

### In plain language

- **No constructor name mapping is needed.** Each driver row in the metrics file already leads
  to the right fantasy constructor through the archive's per-race driver pairs.
- **2024 race 24 has a real fault.** Four teams changed name in the FastF1 data at that race
  alone, so they lost their rolling points and rank as if they had scored nothing.

### Reaching fantasy assets

Joining the metrics file's bare driver code to the archive's per-race pairs:

| Season | Rows | Unmatched | Matching more than one pair | Race-constructors whose drivers differ on rank |
| --- | --- | --- | --- | --- |
| 2023 | 440 | 0 | 0 | 0 of 220 |
| 2024 | 479 | 0 | 0 | 0 of 240 |
| 2025 | 479 | 0 | 0 | 0 of 240 |
| 2026 | 396 | 0 | 0 | 0 of 198 |

A first attempt matched on rows with a price, and wrongly found some drivers ambiguous, because
the archive prices stints a driver was not in (`LAW@RED` in 2026 race 1). The pairs do not have
that problem.

### The 2024 race 24 fault

| Team at race 23 | Rolling points, race 23 | Name at race 24 | Rolling points, race 24 | Rank, race 24 |
| --- | --- | --- | --- | --- |
| Red Bull Racing | 45 | Red Bull | missing | 0 |
| Alpine | 34 | Alpine F1 Team | missing | 0 |
| RB | 10 | RB F1 Team | missing | 0 |
| Kick Sauber | 0 | Sauber | missing | 0 |

`_calculate_rolling_points` in `fast_f1/metrics.py` groups by the name, which fits a rename
losing the history, though the cause has not been traced further. No other season has a team
under two names. Red Bull and Alpine are clearly understated; RB too; Kick Sauber's rank of 0 may
be right by chance.

`AggregateRank` is unaffected, as constructor rolling points carry zero weight in it. The winning
signal in `indicator_analysis_v1` does use the column, so this race fed into that analysis. It is
one of 60 normal weekends, and its effect on those conclusions has not been sized.

**How it happens, read from the code and not run.** `get_race_results` copies `TeamName` from
FastF1 into `Constructor` (`fast_f1/api.py:243`). `build_race_metrics` sums the prior races'
points by that name, then left-joins them to the current race on it (`fast_f1/output.py:202`). A
name that differs from the prior races finds no match, which leaves the points missing and the
rank 0, with no error. So the fault is in the code, and a delete and refresh would run it again.

The four race 24 names look like the older Ergast naming rather than the live timing naming, which
would mean a fallback in FastF1 for that race. That is an inference, not checked. If it is right,
which races get those names could depend on the day of the refresh, so a refresh could put the
fault at other races too. A rename mid-season would trigger it in a live season as well.

## 2026-11-01 — One table or two across weekend formats

Asked for by Alex before plan step 5. From a throwaway read-only script, not kept. It covers 2023–25
only, so 2026 stays unseen, and leaves out race 1 and the faulty 2024 race 24: 48 normal and 18
sprint weekends. The driver fantasy points were reconciled to the archive, all 1,307 rows, after a
first run was discarded for mixing championship points into them.

### In plain language

**Keep one table.** Sprint weekends score about 20–30% more, but a sprint-only table is too noisy to
help. It predicted sprint weekends worse than one table did, and changed the team on nearly every
sprint weekend with no reliable gain. Scaling one table up for sprints changed almost nothing.

### What each format scores

| Drivers, position | 1 | 2–3 | 4–5 | 6–10 | 11–15 | 16–20 | Field total a race |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Normal | 31.2 | 26.6 | 19.7 | 12.1 | 4.4 | 3.7 | 224.0 |
| Sprint | 42.6 | 30.6 | 23.5 | 15.9 | 5.4 | 6.5 | 288.3 |
| Ratio | 1.36 | 1.15 | 1.19 | 1.31 | 1.23 | 1.78 | 1.29 |

| Constructors, place | 1–2 | 3–4 | 5–7 | 8–10 | Field total a race |
| --- | --- | --- | --- | --- | --- |
| Normal | 58.8 | 45.7 | 18.3 | 10.0 | 293.8 |
| Sprint | 71.1 | 52.5 | 19.4 | 16.5 | 355.1 |
| Ratio | 1.21 | 1.15 | 1.06 | 1.65 | 1.21 |

The rise is broadly even, with more at the very top and at the back. The intervals are wide on 18
weekends, and the back's extra points are small in absolute terms.

### Out-of-sample error

Each season is scored on a table from the other two. Within-race error removes each race's mean,
which is closer to what the LP uses. Lower is better.

| Sprint weekends, within-race error | One table | Sprint-only | One table, scaled |
| --- | --- | --- | --- |
| Drivers | 14.97 | 15.45 | 15.02 |
| Constructors | 23.19 | 24.07 | 23.25 |

| Normal weekends, within-race error | One table | Normal-only | One table, scaled |
| --- | --- | --- | --- |
| Drivers | 12.70 | 12.72 | 12.64 |
| Constructors | 20.79 | 20.97 | 20.72 |

### The teams each table picks

A team picked fresh each race, with DRS, ignoring the move limit, at a fixed budget. So this shows
whether the table changes the choice, and is not a back-test. Mean actual points a race, with the
change against one table and its 95% interval:

| Budget | Format | One table | Split | Change | Teams differing | Scaled | Change | Teams differing |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 100 | Sprint | 215.3 | 201.1 | −14.2 (−35.6 to +4.1) | 17 of 18 | 215.3 | 0.0 | 0 |
| 110 | Sprint | 241.2 | 242.0 | +0.8 (−25.2 to +28.8) | 16 of 18 | 235.8 | −5.3 (−16.0 to 0.0) | 1 |
| 120 | Sprint | 252.7 | 233.8 | −18.9 (−39.4 to +0.4) | 16 of 18 | 248.2 | −4.6 (−13.7 to 0.0) | 1 |
| 100 | Normal | 173.1 | 175.4 | +2.4 (−6.7 to +13.4) | 29 of 48 | 173.1 | 0.0 | 0 |
| 110 | Normal | 189.4 | 187.9 | −1.5 (−7.5 to +4.4) | 26 of 48 | 190.2 | +0.8 (0.0 to +2.2) | 1 |
| 120 | Normal | 198.7 | 197.2 | −1.4 (−5.3 to +2.5) | 29 of 48 | 200.0 | +1.4 (0.0 to +4.1) | 1 |

### Limits and a side finding

The budget reward and negative penalty are not in this test. Both are fixed-point terms, so they
weigh about 20–30% too much relative to expected points on a sprint weekend. Not measured.

The 18 sprint weekends here include 2023's six, which the signal can use as it needs no session.
So a table has 12 sprint weekends in tuning and 18 for 2026. The requirement that 2023's sprints be
treated separately in `indicator_analysis_v1` does not apply to the tables.

**Plain means are out of order in places, even on 48 weekends.** Driver position 11 averages 7.2
against 4.6 at position 10, and position 18 averages 6.6 against 2.5 at position 12. That looks like
noise, and an LP would treat it as real. Plan step 5 now compares them with means forced to fall by
position.

| Driver position, normal weekends | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 18 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Mean fantasy points | 16.4 | 17.4 | 11.9 | 10.1 | 4.6 | 7.2 | 2.5 | 4.8 | 6.6 |

## 2026-11-06 — Step 1.1: does `TeamId` survive the rename?

Read-only checks from a throwaway script, not kept. It loaded 2024 races 21–24 from the FastF1 cache
in offline mode. One public request went to the Ergast mirror (`api.jolpi.ca`) for 2024 race 24,
which needs no sign-in. No data file and no cache was changed.

### In plain language

- **Yes, `TeamId` stays the same across the rename.** The four race 24 names are Ergast's names
  for the same teams. Ergast gives the same team id under both names.
- **This confirms the earlier guess.** Race 24 was served by FastF1's Ergast fallback, not by live
  timing.
- **The code cannot use `TeamId` today.** The wrapper's own cache keeps `TeamName` and not
  `TeamId`, for every race in every season.

### What was run

| Race | Source | Red Bull | Alpine | RB | Sauber |
| --- | --- | --- | --- | --- | --- |
| 21–23 | FastF1 cache, live timing names | Red Bull Racing / `red_bull` | Alpine / `alpine` | RB / `rb` | Kick Sauber / `sauber` |
| 24 | Ergast mirror | Red Bull / `red_bull` | Alpine F1 Team / `alpine` | RB F1 Team / `rb` | Sauber / `sauber` |

Each cell is the name, then the team id. The other six teams had the same name and id in all four
races. The race 24 names match the stored metrics file exactly.

FastF1 3.9.0 always takes `TeamId` from Ergast's `constructorId` (`fastf1/core.py`, the
`rename_return` mapping). It takes `TeamName` from live timing when it has the race, and from Ergast
when it does not. That is why the name moves and the id does not.

### What else this found

- **Race 24 is in neither cache.** FastF1 has no live timing or Ergast responses for it, and the
  wrapper has no `race_results_2024_24`. Races 21–23 are in both. So the stored race 24 row was
  built before the current cache, and cannot be rebuilt offline.
- **`TeamId` comes only from Ergast.** FastF1 warns that Ergast often has no results for recent
  sessions. So in a live season the latest race may have no `TeamId` for a while. This is reasoned
  from FastF1's warning, and was not checked against a 2026 race.

### Decision: link through the drivers

Agreed with Alex 2026-11-06. Keying on `TeamId` would mean fetching every cached race again with
sign-in. It would also still need a fallback for races Ergast has not reached yet. So the join links
names through the drivers, under a rule that also covers a name changing back and forth:

- A name from the previous races that is also in the current race keeps its own points.
- A name that is missing from the current race goes to the current team its drivers now race
  for, if that is exactly one team.
- A missing name that cannot be linked logs a warning, so a failed link is never silent.

The second condition leaves a mid-season driver swap alone, since both names are in the
current race.

## 2026-11-06 — Steps 1.2 and 1.3: the fix

`link_renamed_constructors` in `fast_f1/metrics.py` applies the rule above. `build_race_metrics`
now works out constructor rolling points after the current race's teams are known, and links them
first. The stored `Constructor` and `TeamName` values are unchanged.

Four tests in `tests/test_fast_f1_output.py`, seen failing before the fix:

| Test | Before the fix |
| --- | --- |
| Single rename, as in 2024 race 24 | Points missing |
| Name changing back and forth | 35 points from one race, not 105 from three |
| Missing name with drivers split across two teams | No warning |
| 2025-style driver swap | Passed, as a guard |

The swap test was checked by mutation instead. With the "missing from the current race" condition
dropped, it failed on the warnings logged for two teams that still race. Its points did not move
under that mutation, because the "exactly one team" condition also blocks the link. There was no
`fast_f1` test for a driver changing team before this, so there were no existing ones to run.

Full suite 381 passed. Not run against real data: that is step 2, after Alex agrees its checks.

## 2026-11-06 — Step 2: 2024 race 24 recomputed

Run with the checks in `plan.md`, which Alex agreed, plus two found to be needed after step 1.
Race 24 was in neither cache, so it needed a live fetch. And since `--historical` skips races it
already has, its rows were removed first, so the run would recompute that race alone.

### In plain language

- **Fixed.** The four teams now have their rolling points at race 24, and nothing else in the
  file moved.
- **The new code was not what fixed it.** This time FastF1 served race 24 from live timing, so
  its team names match races 21–23 and the old join would have worked too. The new code guards
  against the next time FastF1 falls back to Ergast.
- **The four teams' stored names changed back** to the live timing ones, for example "Red Bull"
  to "Red Bull Racing". That was allowed for in the agreed checks.

### What was run

1. The metrics file was copied outside the repo, and the copy's checksum matched.
2. The comparison script was first run on the copy against itself. It reported no changed cells
   and found the 8 known rows with missing constructor points, so it could catch a fault.
3. A script using `fast_f1.output`'s own reader and writer removed the 20 race 24 rows. Compared
   with the copy, only those 20 rows had gone and no cell had changed.
4. `fast_f1.cli --historical --season 2024` signed in through `fast_f1`'s credentials loader
   and computed race 24 only, skipping the other 23. It exited 0 and logged no link warnings.
5. Cell by cell, against the copy:

| Check | Result |
| --- | --- |
| Rows and keys | 1,794 before and after, none added or lost, no duplicates |
| Changed | 32 cells in 8 rows, all 2024 race 24, all Red Bull, Alpine, RB and Sauber drivers |
| Columns changed | `ConstructorRollingPoints` and its rank, and `Constructor` and `TeamName` for the names |
| `AggregateRank` and `RankPosition` | No cell changed |
| Missing `ConstructorRollingPoints` from race 2 onwards, all seasons | None, against 8 before |

| Team at race 24 | Rolling points | Rank | Before |
| --- | --- | --- | --- |
| Red Bull Racing | 62 | 0.91 | Missing, rank 0 |
| Alpine | 43 | 0.63 | Missing, rank 0 |
| RB | 10 | 0.15 | Missing, rank 0 |
| Kick Sauber | 4 | 0.06 | Missing, rank 0 |

The other six teams' ranks did not move, so the corrected teams fell inside the range the six
already set.

## 2026-11-06 — Step 3: the indicator analysis on the corrected file

### In plain language

- **The winners hold.** Both targets on both weekend formats pick the same combinations as
  `indicator_analysis_v1`. So steps 4 onwards stand as planned.
- **One robustness check no longer passes.** That check picks the normal-weekend combination
  without each season in turn, then scores it on the left-out season. Its 2024 score was about
  zero before (+0.00004) and is about zero now (−0.003). That is enough to fail the bar's
  "positive in every season" condition. This does not say the check got worse, only that 2024
  never supported it. Every other verdict is unchanged.
- **Race 24 accounts for all of it.** Run on the file as it was before step 2, the analysis
  reproduces the saved v1 outputs exactly.

### What was run

`fast_f1.indicator_analysis` was run as-is on the corrected file. Its own `main()` was also
run on the copy taken before step 2, writing to a scratch directory. The outputs saved on
2026-11-01 were set aside first.

| Outputs compared | Result |
| --- | --- |
| Saved v1 outputs and the run on the copy | All seven tables identical, byte for byte |
| Run on the copy and the run on the corrected file | Winners and race 1 tables identical, five others differ |

Across the five that differ:

| Check | Result |
| --- | --- |
| Winners, both targets and formats | Unchanged |
| Combination chosen with each season left out | Unchanged |
| Top combination in every target, format and split | Unchanged |
| Verdicts, of 82 comparison rows | 1 changed |
| Largest move in any mean gain | 0.0018 |

The rows that moved, on normal weekends against fantasy points, the primary target:

| Comparison | 2024 gain before | 2024 gain after | Mean gain | Verdict |
| --- | --- | --- | --- | --- |
| Winner vs rolling | +0.008 | +0.004 | 0.039, from +0.020 to +0.058 | Pass, unchanged |
| Choice made without each season vs rolling | +0.00004 | −0.003 | 0.034, from +0.011 to +0.055 | Pass to fail |
| Winner vs aggregate | | | 0.016, from −0.006 to +0.041 | Fail, unchanged |

Only 2024's figures moved. The other seasons' gains are identical to the fourth decimal.

Why the corrected data scores slightly lower in 2024 was not checked. One possible reason: in
the archive, PER scored −18 at Abu Dhabi 2024, 19th of 20, though VER was 5th on 23. So for PER,
a constructor rank of 0 for Red Bull predicted better than the true 0.91. That is reasoned, and
not run.

The `indicator_analysis_v1` log's table now carries a dated marker on the row that changed.

## 2026-11-06 — Step 3b: a driver's team before the race has results

Alex chose the practice sessions' driver lists as the source.

### In plain language

- **Fixed and checked on real data.** Before a race has results, each driver's team now comes
  from that weekend's practice sessions. Two past races were rebuilt with their own results
  hidden, and both match the stored rows exactly.
- **The fault was real.** The code from before the fix put Tsunoda and Lawson in each other's
  teams at 2025 race 4. That gave Tsunoda 4 constructor points instead of 55.
- **Not yet run for real before a race.** São Paulo, 2026 race 20, has its last practice
  session on 7 November. So the first true pre-race run, and the first real check of a new
  driver such as CAM, is Alex's usual run that weekend.

### What changed

- `get_session_drivers` in `fast_f1/api.py` gives each driver in a session and the team FastF1
  names for them. It has its own cache files, as the cached laps do not keep the team.
- When the race has no results, `build_race_metrics` takes each driver's team from the
  practice sessions it already uses, with the latest session winning. A driver no session
  names raises an error. It used to take the team from the oldest of the previous three races.

### Tests

Five new tests, plus one updated. The updated one is the existing test for a race without
results, which now supplies the practice driver lists.

| Test | Before the fix |
| --- | --- |
| `get_session_drivers` returns and caches the driver list | Failed, against a stub returning nothing |
| It returns an empty frame when the session has no data | Failed, the same way |
| A network failure propagates, added to the existing test | Failed, nothing raised |
| A driver who moved team in the window gets the new team | Failed: Racing Bulls, not Red Bull Racing |
| A driver new to the window gets a team | Failed: no team |
| A driver no session names raises an error | Failed, nothing raised |

"Latest session wins" was added after the fix. It was checked by mutation: with the first
session winning instead, the test failed. Full suite 387 passed.

### Real-data check

Each race was rebuilt through `build_race_metrics`, set up as `fast_f1.cli` sets it up, with
only that race's own results hidden. It was then compared with the stored rows, which were built
with results.

| Race | Teams | Constructor points and rank | `AggregateRank`, `RankPosition` |
| --- | --- | --- | --- |
| 2025 race 4, after the Tsunoda–Lawson swap at race 3 | All 20 match | All match | All match |
| 2026 race 18, a sprint weekend | All 22 match | All match | All match |

The same script, run on the code before the fix in a throwaway worktree, found Tsunoda and
Lawson swapped at 2025 race 4. So the check can fail.

The run added `session_drivers` files to the FastF1 wrapper's own cache, as any normal run
now does. The step 3b.3 check found no stored row built before its race had results, so
no data needed repair.

## 2026-11-06 — Step 4: the signal

### In plain language

- **Done, and run on every stored race.** `fast_f1/signal.py` gives each driver a signal
  position and each constructor a place, for any race from 2 onwards. It agrees with the
  indicator analysis's own signal on every one of the 84 stored races.
- **Two rules agreed by Alex before any code.** 2023 sprint weekends, which had only FP1
  before team lock and which the analysis left out, use the sprint rule: driver + constructor
  rolling. A fantasy driver with no row in the metrics file gets no position, and step 6
  scores them zero, as for a race with no signal. There are two such drivers, SAR in 2024
  race 3 and STR in 2025 race 9.
- **Bad data raises an error rather than being ranked around.** This covers a driver with no
  fantasy pair or two of them, a missing input, and two drivers disagreeing on their
  constructor's points. None of these happens in the stored file.

### What changed

- `indicator_analysis.py` gained `add_signal_inputs`, which sets up the weekend format and the
  inputs from metrics rows alone. The analysis needs fantasy points on every row, which a race
  not yet run lacks, so it could not be reused as it was. Behaviour is unchanged: with the FP3
  input pointed at the wrong session, 4 existing tests fail.
- `signal.py` has `driver_positions` and `constructor_places`, each taking the metrics rows,
  the archive's per-race pairs, a season and a race. Each returns a dict keyed by fantasy
  identifier, `VER@RED` or `RED`, with 1 as best. Ties break on that identifier. A sum that
  differs only by floating point noise also counts as a tie.
- No race result is read. A test changes a race's status, finishing and grid positions and
  points, and shows that no position or place moves, and that a driver who did not start keeps
  a position. Nothing filters on results, so this was checked by mutation: dropping
  non-starters, or ranking on the race's points, fails it.

### Tests

19 new tests. Each was seen failing first, against a stub or with the check missing. The
exceptions are the look-ahead test and the empty race test, which were checked by mutation.
Every slot choice was also mutated: adding FP2 or odds, dropping FP3, adding Sprint
Qualifying on a sprint weekend, dropping the 2023 sprint rule, reversing the tie-break,
dropping the rounding, and ranking constructors on driver points. Each one fails a test.
Full suite 406 passed.

### Real-data check

From a throwaway script, not kept, on `data/fastf1_practice_rolling_metrics.xlsx` and the
archive's pairs:

| Check | Result |
| --- | --- |
| Races 2 onwards, all seasons | 84, none raised |
| Positions per race | One per metrics row, numbered 1 to n |
| Constructors per race | 10 in 2023–25, 11 in 2026 |
| Driver order against the analysis's own signal, where it puts one driver strictly ahead | 16,100 pairs, 0 disagree |
| SAR 2024 race 3, STR 2025 race 9 | No position |

The order check was run again with the analysis side scored on driver rolling alone. It found
1,313 disagreements, so it can catch a different signal.

Not run: a race before its results exist. Step 3b's checks cover the metrics rows for such a
race, and the signal reads no results.

## 2026-11-06 — Step 5: the tables

### In plain language

- **Done, and run on every stored race.** `SignalTables` in `fast_f1/signal.py` gives each
  asset in a race its expected fantasy points and its chance of going negative.
  `load_signal_tables` reads the files once per process.
- **Expected points use means forced to fall by position.** They predicted the left-out
  season better than plain means in every season, for drivers and constructors both. The gain
  is small, under 1%. The stronger reason is that plain means have bumps an LP would chase,
  such as driver position 18 at 6.2 points against 3.6 at position 12.
- **The chance of going negative splits on whether there was any negative in the last three
  races, as Alex chose.** In 2023–25, two recent negatives were no riskier than one, and three
  were too rare to measure. The "more negatives, more risk" pattern came mostly from 2026,
  which Alex expects to be an odd season, with AST and CAD poor all year.
- **2026's penalty will understate AST and CAD,** at 17.8% after any recent negative for a
  constructor. The working assumptions already note the same gap at constructor place 11.

### Plain means against forced means

From a throwaway script, not kept. It is the out-of-sample test from *One table or two*: each
of 2023–25 is scored on a table from the other two, by RMSE after taking each race's mean
off both the actual and the predicted points.

The script first reproduced that entry's figures exactly (drivers 12.70 and 14.97,
constructors 20.79 and 23.19), so the test is the same one. Doing so found that the entry
had dropped drivers who never started, as `build_analysis_frame` does. Those 11 drivers
mostly scored −20 to −3, and dropping them is look-ahead. The run below keeps them, and
also 2024 race 24, which that entry left out only for the fault fixed in step 2.

| Error, lower is better | Plain | Forced |
| --- | --- | --- |
| Drivers, all weekends | 13.547 | 13.450 |
| Drivers, held-out 2023 / 2024 / 2025 | 14.01 / 13.16 / 13.50 | 13.87 / 13.07 / 13.44 |
| Constructors, all weekends | 21.481 | 21.440 |
| Constructors, held-out 2023 / 2024 / 2025 | 20.07 / 20.44 / 23.64 | 20.05 / 20.33 / 23.64 |

Forced also errs less on normal and sprint weekends taken apart. Constructors in 2025 are a
tie to two decimals.

### The negatives rule

With the agreed definition (the previous three rounds of the season, the driver carrying
their history to a new team, races 2 onwards), 2023–25 gave:

| Negatives in the last three | Drivers | Constructors |
| --- | --- | --- |
| 0 | 14.9% of 817 | 9.6% of 479 |
| 1 | 19.0% of 416 | 18.4% of 152 |
| 2 | 18.6% of 102 | 10.8% of 37 |
| 3 | 0% of 5 | 100% of 2 |

Across 2023–26 the same definition gives drivers 15%, 20% and 22%, and constructors 9%, 19%
and 32%, close to the 12/20/23% and 9/19/34% in the sizing entry. So it measures the same
thing. Fifteen of the 19 constructor negatives after two recent negatives are in 2026.

Alex chose none against any (option A) over capping at two and forcing a rise (B, which came
out almost the same) and exact counts (C).

### What changed

- `SignalTables(metrics, driver_archive, constructor_archive)`, with
  `expected_points(season, race)` and `negative_chance(season, race)`, each a dict keyed by
  driver identifier and constructor code.
- A season's tables come from `TABLE_SEASONS` (2023–25) less itself, races 2 onwards, so no
  season sees its own results and 2026 enters none. Every table is built once, and each race's
  values are computed once, with every caller getting its own copy.
- Expected points cover assets with a position or place, and a position past a table's end
  takes the last value. A race with no signal, such as 2026 race 19, gives none.
- The chance of going negative covers every asset priced in the race, including SAR and STR,
  which have no position. It never reads the race's own result.
- `load_signal_tables(fn_metrics, fn_archive)` reuses `load_existing_metrics` and
  `load_all_archive_data`, and raises if the metrics file is missing or empty.

### Tests

21 new tests, 40 in `tests/test_fast_f1_signal.py`. Each was seen failing first, against a stub
or, for the negatives rule, against exact counts. Two needed rework: the negatives history first
gave both buckets 50%, so it could not tell the rules apart, and the table first made no
difference with race 1 left in. The exceptions to red first were checked by mutation: 2026
staying out of every table, a race with no signal, and the per-race cache handing out copies.
Each of these mutations fails a test:

- reading the own season or 2026;
- adding race 1;
- plain means;
- no carry past a table's end;
- filling unranked assets with zero;
- reading the race's own result;
- four rounds instead of three;
- the seat carrying the history instead of the driver;
- sharing the cached dict.

Full suite 427 passed.

### Real-data check

From a throwaway script, not kept, on the real metrics file and archive:

| Check | Result |
| --- | --- |
| Races 2 onwards, all seasons | 84, none raised |
| Expected points per race | 29–30 assets in 2023–25, 33 in 2026 |
| Chances per race | Every priced asset: 30 in 2023–25, 33 in 2026 |
| 2026's points tables against the measurement script's forced means on all of 2023–25 | Equal to one decimal, every position and place |
| 2026's negative tables | Drivers 14.9% and 18.7%, constructors 9.6% and 17.8% |
| 2026 race 19 | No expected points, chances for all 33 assets |
| Time | 1.8s to load, 5.7s to build every table and race, under 1ms a race after |
| Peak memory | 200MB |

Not run: a race before its results exist, as in step 4.

## 2026-11-06 — Step 6: the strategy

### In plain language

- **Done.** `StrategyFastF1` in `linear/strategy_fastf1.py` picks the team with the most
  expected fantasy points, within the usual budget, team size and move limit. It does not
  play the race-4 chip.
- **Three tuning settings, each off at its default except DRS:**
  - `drs_coefficient` (default 1) counts the DRS driver's expected points again;
  - `budget_reward` (default 0) adds points per 1m spent;
  - `negative_penalty` (default 0) takes points off for each selected asset's chance of
    going negative.
- **DRS goes to the selected driver with the best expected points,** at any coefficient,
  with a tie going to the first identifier. With no selected driver above zero, the default
  picks the highest-priced driver.
- **Bad data raises an error rather than being scored around.** This covers expected points
  or chances naming an asset the race does not have, and an available asset with no chance.
  An asset with no signal position, such as SAR in 2024 race 3, still scores zero.
- **A race with no signal solves,** with every asset at zero, as for 2026 race 19.

### Choices Alex made in this step

- **No fixture file.** The plan named `data/test_fastf1_metrics.xlsx`, but the tables need
  real 2023–25 metrics rows matched to the real archive, which no small file can give. The
  unit tests stub `load_signal_tables`, a first-party function, with set values. One test
  builds the strategy on the real files for 2025 race 5. The plan is annotated.
- **Each keyword parameter arrived with the part that uses it,** so none was ever accepted
  and ignored.
- **The chances are read only when the penalty is not zero, and the DRS driver's chance is
  not doubled.** The game doubles a DRS driver's negative score too. Doubling it here would
  tie the penalty to the DRS variables, and the penalty is a variant to tune anyway.
- **Live use is a backlog item.** The strategy reads only the stored metrics file, so a live
  pick is two stages, and today's route has gaps. They matter only if the strategy wins.
  See *Live mid-season picks with `StrategyFastF1`* in `BACKLOG.md`.

### Tests

29 tests in `tests/test_strategy_fastf1.py`, with every LP scenario's best team found by
brute force first, so each is the only best team. Each behaviour was seen failing first,
against a stub objective or with its parameter accepted but unused. The exceptions were
checked by mutation: a coefficient or penalty of zero, the race-4 move limit, and a race with
no signal. Each of these mutations fails a test:

- pasting in P2PM's race-4 chip;
- scoring an asset with no signal as a missing key rather than zero;
- swapping season and race, or ignoring `fn_metrics`;
- leaving constructors out of the objective, or out of the penalty;
- always adding the DRS term, leaving its coefficient off, or dropping its constraints;
- the DRS driver by the race's order, a tie going to the last, ignoring the selection,
  taking the helper's nominee, or no floor at zero;
- a reward fixed at 1, or rewarding unspent budget;
- a penalty not scaled, or chances read at zero;
- dropping or loosening any of the asset checks;
- raising on a race with no signal.

Two of the DRS mutations at first failed only through a `KeyError` from a second dictionary
lookup, not on the value. The code now looks the points up once, and both fail on the value.

A test of a race with no signal found that PuLP gives `None`, not 0, as the value of an
objective whose coefficients are all zero, as it swaps in a `__dummy` variable that CBC never
sets. Nothing on the run path reads the objective's value (checked by grep), so the test does
not assert it.

Full suite 456 passed.

### Real-data check

The real-race test builds the strategy by the factory for 2025 race 5, with and without a
penalty. It solves with a full team, every selected asset has positive expected points, and
every available asset has a chance. It was checked by mutation: a race with no signal fails
it, identifiers that disagree raise naming all 30 assets, and chances from a race not run
raise for all 30.

From a throwaway script, not kept, on 2026 race 19, which is priced but has no metrics rows:

| Settings | Status | Expected points | Chances | Selected | DRS |
| --- | --- | --- | --- | --- | --- |
| Defaults | Optimal | None | Not read | 7 | Default |
| Penalty 6, reward 0.5 | Optimal | None | All 33 assets | 7 | Default |

Not run: the strategy through a season. Steps 8 and 9 do that.

## 2026-11-06 — Step 7: the harness

### In plain language

- **Done.** `backtest/cli.py` can now run `StrategyFastF1` and the six tuning variants in the
  plan's table, each built by `make_variant` with one change from the base: `FastF1_Drs0`,
  `FastF1_Neg6`, `FastF1_Neg12`, `FastF1_Bud025`, `FastF1_Bud05` and `FastF1_Bud1`.
- **Nothing outside `backtest/cli.py` changed.** `make_variant` passes the settings
  through, so `factory_strategy` needed nothing, as question 8 expected.

### Tests

One test per label shows it is accepted by `--strategies`, has its label as its name, is a
`StrategyFastF1`, and is built with its three settings, against a stubbed
`load_signal_tables`. They failed first as the labels were not registered. The settings were
then checked by mutation: Neg12 given 6, Bud05 given 0.25, Drs0 given a second change, and
Bud1 changing the penalty instead each fail a test. Full suite 463 passed.

### Real run

`--seasons 2025 --sample-size 1 --strategies StrategyFastF1 FastF1_Neg6`, into the
scratchpad rather than `outputs/`. It exited 0 in 15s with no error or warning. It stored 9
rows, one per strategy per team, all at race 24 with the right labels, and `FastF1_Neg6`'s
totals differ from the base's, so its setting reaches the harness. Three teams are too few to
read anything from the results, and nothing is read from them here. Step 8's small timing
run is still to come, as the store's growth slows a run.

## 2026-11-06 — Step 8: tuning on 2023–25

### In plain language

- **No variant cleared the bar, so nothing is tuned.** Step 9 runs `StrategyFastF1` at its
  defaults: DRS coefficient 1, no negative penalty and no budget reward. No combination run
  was needed, as no penalty or reward cleared.
- **Six variants tried,** all listed below with the failures. 2026 was not run or looked at.
- **Every FastF1 label trailed P2PM in every season,** by 200 to 700 points a team. The base
  trailed by 315 to 385 and beat P2PM on 0 to 7% of teams. These are the seasons that flatter
  the signal, so step 9 is very unlikely to clear the verdict in 2023–25.
- **The race-4 chip explains little of the gap.** P2PM without it trailed P2PM by +1.8, −32.3
  and −168.0 in 2023–25 (`BACKTEST_LOG.md`), against a gap of 315 to 385 here.
- **The DRS term and the budget reward pull the opposite way in 2025 from 2023–24.** Leaving
  DRS out or rewarding budget gained 100 to 120 points a team in 2024, and lost 90 to 360 in
  2025. No setting is positive in all three.

### Choices Alex made in this step

- **Seed 2, not seed 1.** The plan named no seed. With pandas' sampling, seed 1 at 100 teams a
  band draws exactly the first 100 of the 500 that step 9 draws at seed 1, so tuning there
  would choose settings on the teams it is later judged on. Checked on a synthetic frame: the
  seed-1 100 equal the first 100 of the seed-1 500, and a seed-2 100 shares 10 of them.
- **One store per season,** `outputs/fastf1_v2_tuning_2023.parquet`, `_2024` and `_2025`,
  each with its own `_summary.csv`, run in parallel. Each store's summary and verdict cover
  one season, so the cross-season comparison below was computed from the three stores together.

### What was run

A timing run first: 2025, 10 teams a band, base strategy only, into the scratchpad. 60
simulations in 40.5s at a peak RSS of 266 MB, about 0.4s a simulation for P2PM and 0.7s for
FastF1.

Then, for each of 2023, 2024 and 2025, one background process:

`backtest.cli --seasons <season> --sample-size 100 --seed 2 --strategies StrategyFastF1
FastF1_Drs0 FastF1_Neg6 FastF1_Neg12 FastF1_Bud025 FastF1_Bud05 FastF1_Bud1
--output outputs/fastf1_v2_tuning_<season>.parquet --summary outputs/fastf1_v2_tuning_<season>_summary.csv`

All three exited 0 with no error or warning in their logs, in 38 to 43 minutes, at a peak RSS
of 255 to 279 MB each. Each store holds 300 rows per label for its season, 7,200 in all.

The bar against the base is the harness's own: `pair_with_baseline`, `season_summary` and
`verdict` from `backtest/metrics.py`, run with `StrategyFastF1` as the baseline from a
throwaway script, not kept.

### Against the base, `StrategyFastF1`

Pooled mean delta, in points a team, with the share of teams that beat the base:

| Label | 2023 | 2024 | 2025 | Seasons positive |
| --- | --- | --- | --- | --- |
| `FastF1_Drs0` | +69.7 (59%) | +121.7 (69%) | −355.8 (16%) | 2 of 3 |
| `FastF1_Neg6` | −26.6 (18%) | +6.5 (51%) | −31.9 (39%) | 1 of 3 |
| `FastF1_Neg12` | +15.0 (45%) | −15.5 (46%) | −34.0 (39%) | 1 of 3 |
| `FastF1_Bud025` | +13.9 (53%) | +103.7 (75%) | −91.5 (33%) | 2 of 3 |
| `FastF1_Bud05` | +110.9 (65%) | +119.1 (72%) | −97.3 (32%) | 2 of 3 |
| `FastF1_Bud1` | −2.0 (55%) | +118.5 (76%) | −148.8 (26%) | 1 of 3 |

Each band gives the same sign as the pooled row in every season for every label except
`FastF1_Neg6` in 2024 and `FastF1_Bud1` in 2023, both close to zero pooled. The reward is not
monotonic: 0.5 beat 0.25 and 1 in 2023.

### Against P2PM, for context

| Label | 2023 | 2024 | 2025 |
| --- | --- | --- | --- |
| `StrategyFastF1` | −315.0 | −385.4 | −357.8 |
| `FastF1_Drs0` | −245.3 | −263.7 | −713.7 |
| `FastF1_Neg6` | −341.6 | −379.0 | −389.7 |
| `FastF1_Neg12` | −300.0 | −401.0 | −391.8 |
| `FastF1_Bud025` | −301.1 | −281.7 | −449.3 |
| `FastF1_Bud05` | −204.1 | −266.4 | −455.1 |
| `FastF1_Bud1` | −316.9 | −266.9 | −506.6 |

The base beat P2PM on 0%, 5% and 7% of teams.

### Final budgets

Mean `total_budget` at the last race, in millions:

| Label | 2023 | 2024 | 2025 |
| --- | --- | --- | --- |
| `StrategyMaxP2PM` | 135.8 | 127.3 | 138.5 |
| `StrategyFastF1` | 133.9 | 122.5 | 124.6 |
| Variants, range | 133.5–135.9 | 122.1–124.6 | 121.2–124.5 |

The base ends 2 to 14m behind P2PM. Step 9's budget report on the 500-team run decides
whether that is raised with Alex, as the plan says. The reward variants moved it by under 2m
in 2023–24 and lowered it in 2025, so a reward per 1m spent does not close the gap.

Not run: 2026, and any combination of settings.

## 2026-11-06 — Stepping back: why the strategy trails P2PM

Alex was surprised by how badly step 8 went, and asked for the assumptions to be checked
before step 9, starting with the table that maps signal position to fantasy points.

### In plain language

- **The signal is not the problem.** Per race, it puts drivers and constructors in order of
  fantasy points at least as well as rolling points or price, and much better than P2PM's
  own value measure. P2PM wins on value for money, not on predicting points.
- **The table is.** It gives every position a fixed number of points, so it cannot tell
  first by a mile from first by a whisker. Each season's table comes from the other seasons,
  so it also cannot know when one driver dominates.
- **In 2023 that cost the whole gap.** 2023's table, from 2024–25, gave positions 1 and 2
  the same 29.0 points. The signal ranked VER first, but he cost 6m to 9m more than the
  driver ranked second, for no extra points in the table, so the LP left him out. He then
  scored 46 to 68 points a race. FastF1 led P2PM until race 9 and then lost about 540 points
  in four races without him.
- **2024 shows the same fault the other way.** Its table, from 2023 and 2025, expected 38.6
  points at position 1, and position 1 scored 25.6 on average that season.
- **Budget is a second, smaller effect.** The strategy pays top prices for top-ranked assets,
  which do not rise, so it ends 2025 about 13m behind P2PM. Step 8's reward per 1m spent did
  not help.
- **Consequences.** Step 9 is on hold. Step 8's results describe a strategy with this fault,
  so they do not carry over to a redesign. The signal design, from step 4's use of
  position onwards, is to be redone in a fresh session. No fix has been designed.
- **My step 5 choice made 2023 worse, but is not the cause.** Forcing means to fall tied
  positions 1 and 2. Plain means would have put position 1 below position 2.

### What was run

Two throwaway scripts, not kept, on the real metrics file and archive, reading no 2026
result.

**The table and the signal**, for every race from 2 onwards in 2023–25:

| Mean per-race rank correlation with points | Signal's table | Rolling 3-race points | Price | P2PM (3) |
| --- | --- | --- | --- | --- |
| Drivers, 2023 / 2024 / 2025 | 0.583 / 0.617 / 0.527 | 0.441 / 0.570 / 0.436 | 0.560 / 0.636 / 0.500 | 0.342 / 0.527 / 0.354 |
| Constructors, 2023 / 2024 / 2025 | 0.698 / 0.708 / 0.551 | 0.640 / 0.666 / 0.557 | 0.702 / 0.723 / 0.607 | 0.558 / 0.650 / 0.465 |

Rolling points and P2PM here are the archive's `Points Cumulative (3)` and
`P2PM Cumulative (3)`, which read only earlier races. The mean points of the top five drivers
a race by the table, rolling points and price were within 1.2 points of each other in every
season, with P2PM's top five 1.4 to 4.1 points below the best.

Split into fifths by expected points, the table is calibrated to within 1.4 points for the
lower four fifths of drivers, and overstates the top fifth: 27.7 expected against 25.1 scored.

The 228 asset-races with no expected points, which the strategy scores zero, are all drivers
not in that race. All have zero points and price except SAR in 2024 race 3 and STR in 2025
race 9, who withdrew during the weekend.

Plain mean driver points by signal position, the input to the table before means are forced
to fall:

| Position | 2023 | 2024 | 2025 | All three |
| --- | --- | --- | --- | --- |
| 1 | 46.3 | 25.6 | 31.6 | 34.1 |
| 2 | 28.3 | 27.6 | 31.3 | 29.1 |
| 3 | 19.3 | 35.8 | 21.4 | 25.7 |

Constructor place 1 varies the same way: 79.2, 64.4 and 68.2. The standard deviation at
driver position 1 is 18.4 points, from 67 races.

**Race by race.** 15 teams a season (5 a band, seed 2) re-simulated through `run_for_team`
for `StrategyMaxP2PM`, `StrategyMaxP2PMNoReset` and `StrategyFastF1`, as the stores hold only
the last race. Cumulative mean gap, FastF1 minus P2PM:

| Season | After race 9 | End of season | Worst single races |
| --- | --- | --- | --- |
| 2023 | +116 | −312 | 17: −201, 10: −126, 16: −112, 12: −100 |
| 2024 | −81 | −356 | 23: −66, 20: −64, 9: −63 |
| 2025 | −131 | −379 | 15: −102, 22: −86, 10: −77 |

In each of 2023's four worst races, every FastF1 team was without VER and every P2PM team held
him, as its DRS driver in three of the four. The signal ranked him first in all four, at 27.9m
to 29.1m, against 19.9m to 21.8m for the driver ranked second. Share of team-races holding VER:

| Season | FastF1 | P2PM |
| --- | --- | --- |
| 2023 | 28% | 96% |
| 2024 | 22% | 11% |
| 2025 | 18% | 28% |

2024–25's worst races show no single cause like this. FastF1 often held both McLaren drivers
in 2025, where P2PM held one and spent the difference elsewhere.

Mean budget, P2PM against FastF1, at the end of each season: 2023 135.6m and 134.0m (FastF1
was ahead to race 15), 2024 127.3m and 123.1m, 2025 139.5m and 126.6m.

Moves are not a cause. Mean moves used per race were 1.76 to 1.97 for FastF1 and 1.82 to 1.92
for P2PM, and the race-4 chip again explains little: the gap against P2PM without the chip
ends 2025 at −243 rather than −379, and is the same in 2023.

### What this changes

- The plan is revised: step 9 and step 10 wait for a new signal design, and step 8 is to be
  rerun on it. See `plan.md`.
- Question 1's answer, expected points by signal position, is reopened in `requirements.md`.
- The indicator analysis judged the signal on rank correlation, which cannot see this fault.
  A redesign needs a check on how much each asset scores, not just their order.

## 2026-11-07 — Two decisions from 2026-11-01, logged late

`requirements.md` recorded these when they were made, but the log did not. They are logged
now so that the requirements can be rebuilt under the living-documents rule without losing
them. Neither reason was written down at the time, in the docs or in commit `e53e566`, so none
is given here.

- **The strategy does not play the race-4 chip.** The working assumptions first had it copy
  P2PM's chip, so that the comparison would not also measure the chip. Alex withdrew that on
  2026-11-01. `StrategyMaxP2PM` still plays the chip, so the verdict against it also measures
  the chip, and `StrategyMaxP2PMNoReset` runs in all four seasons to show how much.
- **The signal's rolling indicators stay on championship points.** Alex confirmed this with
  the other working assumptions on 2026-11-01, after the check in *Checking the rolling
  indicators' source* found that fantasy rolling points gave no measurable gain. The
  requirements still called it unruled until commit `49b0c54` corrected them on 2026-11-06.

## 2026-11-07 — Plan and requirements converted to living documents

`plan.md` and `requirements.md` now follow `agentic`'s living-documents rule: they say what is
true now, with no dated notes, and the reasoning stays here. Every note removed had a log
entry first, two of them written in the entry above. Nothing was decided or changed in meaning.

- **Plan.** Finished steps 1 to 4 and 7 are one line each, pointing to their entries. Steps 5,
  6 and 8 keep their detail, now in the present tense, as the redesign revises them. Step 7's
  variant table moved into step 8, which runs it. *Revision: signal redesign* is now *Next:
  signal redesign*, and its step 2 says to log what changes, where it said to annotate.
- **Requirements.** The status, question 1 and the decisions read as current state. The
  withdrawn race-4 chip assumption is one line under the working assumptions. The original
  backlog entry keeps the notes it carried in `BACKLOG.md`. The two added to it during this
  effort moved to the list of what has since changed.

## 2026-11-07 — Redesign evidence: the game's rules and three checks

Gathered while agreeing the signal redesign with Alex, which the next entry records.

### In plain language

- **The game's scoring rules are now written down here,** from text Alex pasted, as the rules
  page could not be fetched. A constructor scores its two drivers' points plus extras of its
  own, and the −20 for not being classified dominates the negatives.
- **A retirement cannot be predicted from recent history.** Neither a driver's own recent
  retirements nor their team's, over three races or the season so far, did better than one flat
  rate for everyone, in any of 2023–25.
- **Price does predict going negative.** The cheapest third of drivers went negative twice as
  often as the dearest third, and constructors in the dearest third almost never did.
- **Price rises are partly predictable,** weakly in 2023–24 and strongly in 2025. The signal's
  own value for money is the most even predictor across the three seasons.
- **Option 3, starting from each asset's own recent fantasy points, was considered and not
  pursued.** See the last section.

### The game's rules

The rules page builds its content with JavaScript, so a fetch returned only the page's shell.
Alex pasted the text on 2026-11-07. It covers scoring, not price changes or chips.

- **Team lock:** just before qualifying on a normal weekend, and after sprint qualifying on a
  sprint weekend.
- **Qualifying:** 10 points for pole down to 1 for 10th, and −5 for not classified,
  disqualified or no time set in Q1.
- **Sprint:** 8 points for 1st down to 1 for 8th, ±1 a place gained or lost (losses capped at
  −10), +1 an overtake, 5 for fastest lap, and −10 for not classified or disqualified.
- **Race:** 25-18-15-12-10-8-6-4-2-1 for the top ten, ±1 a place gained or lost with no cap,
  +1 an overtake, 10 for fastest lap, 10 for Driver of the Day (driver only), and −20 for not
  classified or disqualified. The −20 applies to a driver who does not start too.
- **Constructors:** their two drivers' qualifying, sprint and race points, less Driver of the
  Day, plus:
  - qualifying progression: −1 if neither driver reaches Q2, 1 for one in Q2, 3 for both in Q2,
    5 for one in Q3 and 10 for both in Q3;
  - pit stops: 0 to 20 points a stop by time band, 5 for the fastest, and 15 for a world record;
  - a further −5, −10 or −20 per driver disqualified in qualifying, the sprint or the race.
- **Transfers:** −10 per transfer beyond the free allowance.

### Negatives

From a throwaway script, not kept, on the metrics file and the archive, 2023–25 races 2
onwards: 1,340 driver-races with 220 negatives, and 670 constructor-races with 80. 143 drivers
were not classified, which here means retired, disqualified or withdrawn, and 140 of those were
negative. Each season was predicted from bucket rates in the other two.

The score is the chance a measure ranks an asset that hit the outcome above one that did not:
0.50 is a coin toss. By held-out season, 2023 / 2024 / 2025:

| Measure | Driver not classified | Driver negative | Constructor negative |
| --- | --- | --- | --- |
| A. Any negative in the last three races (step 5's) | 0.49 / 0.38 / 0.49 | 0.49 / 0.57 / 0.53 | 0.58 / 0.60 / 0.55 |
| B. Own non-classification in the last three | 0.50 / 0.43 / 0.47 | 0.49 / 0.46 / 0.51 | 0.53 / 0.53 / 0.51 |
| C. Team's non-classified cars in the last three | 0.50 / 0.43 / 0.48 | 0.49 / 0.49 / 0.44 | 0.50 / 0.54 / 0.45 |
| Price third within the race, added as a control | 0.55 / 0.55 / 0.51 | 0.59 / 0.57 / 0.55 | 0.73 / 0.72 / 0.64 |

A first run scored all three seasons together, which mixed their different base rates into the
score: a flat rate scored 0.46–0.49, not 0.50. The table is scored within each season and
averaged. The price control was added because every candidate scored near 0.50, which needed a
measure the check could be seen to detect.

Share going negative by price third, all three seasons together:

| Price third | Drivers | Constructors |
| --- | --- | --- |
| Cheapest | 20.9% | 19.9% |
| Middle | 18.4% | 16.4% |
| Dearest | 10.2% | 2.6% |

### Team reliability over the season so far

Alex expected an unreliable team to make its drivers' −20 more likely, noting that the view may
come from 2026, with two teams unreliable all season. 2026 stays out of the design, so this was
tested on 2023–25 with a longer window than C. A team's rate was its non-classified cars over
its cars in the season's earlier races, against the whole field's rate over the same races.
That gave three buckets: none yet, at or below the field's rate, and above it. The script
stopped with an error if any race at or after the one predicted was read. A control version
that deliberately included the race itself shows the check would notice a leak.

| Driver not classified, by held-out season | 2023 | 2024 | 2025 |
| --- | --- | --- | --- |
| Team's season so far | 0.49 | 0.48 | 0.45 |
| Control, including the race itself | 0.68 | 0.73 | 0.68 |

Drivers whose team was above the field's rate went on to be not classified 10.7% of the time,
and drivers whose team had none yet 10.1%. Constructors show the same. 2023–25 may simply hold
no team that was unreliable all season, which a back-test of 2026 would then show as a cost the
design could not foresee.

### Price rises

From a second throwaway script, not kept. The target is the asset's price at the next race less
its price at this one. Each measure was known at team lock, and the archive's points per 1m
ends at the race before (`shift(1)` in `import_data/derivations.py`). Nothing was fitted, so no
season is scored on what it taught.

Moves are small: on average +0.11m a race for a driver and +0.18m for a constructor. The
largest real move was about 1.5m in 2023, 1m in 2024 and 0.6m in 2025, when moves came in fixed
steps, so the game's price rules differ by season.

Mean within-race rank correlation with the move, 2023 / 2024 / 2025, where 0 is no better than
chance:

| Measure | Drivers | Constructors |
| --- | --- | --- |
| Price | 0.16 / 0.09 / 0.02 | 0.26 / 0.14 / −0.10 |
| Signal value, option (b) | 0.21 / 0.12 / 0.24 | 0.32 / 0.13 / 0.02 |
| Option (b) per 1m | 0.14 / 0.13 / 0.38 | 0.24 / 0.09 / 0.20 |
| Recent fantasy points per 1m, P2PM's idea | 0.08 / 0.12 / 0.57 | 0.19 / 0.11 / 0.44 |

On (b) per 1m, the dearest third rose more than the cheapest third by 0.05, 0.07 and 0.37m a
race for drivers, and 0.08, 0.02 and 0.24m for constructors. 2025, the season the old strategy
fell furthest behind on budget, is where every measure predicts best.

A first run gave drivers a spread of 1.24m a race, against 0.32m for constructors. Some archive
rows price a stand-in driver at 0 for a race and at full price around it, such as BEA in 2024
and DEV in 2023, which gives moves of ±14m that are not real. The run above drops any move
with a price of 0, 14 asset-races. Whether those rows fit the archive's rule that a
non-participant has both points and price null was not checked, and the archive was not edited.

### Option 3, considered and not pursued

Alex asked for this to be recorded in detail.

Option 3 was to start from each asset's own recent fantasy points, such as VER's 45.7 a race
before 2023 race 10 against LEC's 21.7, and adjust that by the signal. Like (b), it keeps the
size of a lead in real point totals, which was its purpose. It was not pursued for two reasons:

- **It brings fantasy rolling points back.** Alex ruled on 2026-11-01 that the signal stays on
  championship rolling points, after fantasy rolling points gave no measurable gain.
- **Each asset's own total counts too much.** A driver with a poor run hit by retirements would
  start low whatever FP3 said, where (b) takes only the race's top and bottom totals and lets
  the signal place everyone between.

It is also close to `StrategyMaxPoints`, which optimised recent fantasy points and trailed P2PM
in all of 2023–25.

## 2026-11-07 — Signal redesign agreed

Agreed with Alex in conversation, item by item, before any code. The evidence is in the entry
above.

### In plain language

- **The objective now scores the signal's value, not its position.** Each driver's signal is
  stretched onto that race's recent championship points per race, so a driver well clear of
  the field stays well clear. In 2023 race 10 VER comes out 21 points ahead of LEC, where the
  old table gave both 29.0.
- **A constructor scores the sum of its two drivers,** as championship points do and as the
  game mostly does.
- **Negative risk comes from a penalty by price third,** for drivers and constructors, as price
  was the only measure that predicted it.
- **Budget gets two rewards:** one per 1m spent, as before, and a new one for expected price
  rises, by the signal's value per 1m.
- **Everything new is tuned from zero on 2023–25,** with values fixed before any run, one
  setting across weekend formats, and two checks that must pass first.
- **Alex prefers equal weights** across the signal's inputs, changed only with a case and care
  about over-fitting.

### How the design was reached

- **A straight-line conversion changes no driver pick.** The LP takes exactly five drivers and
  two constructors (`linear/strategy_base.py:232-233`), so scaling every driver's value by one
  factor and adding one amount moves every team equally. That was reasoned, not run. So the
  conversion matters only for the mix of drivers and constructors, and for the penalty and
  rewards, which need a unit. Alex chose championship points as that unit, with a constructor
  as the sum of its drivers, letting FP3 move drivers within the top-heavy rolling-points
  inputs.
- **Two readings of "into championship points" were put to Alex.** One gave positions on the
  25-18-15 scale, which is top-heavy but still loses the size of a lead. The other stretches
  the value onto the race's recent championship points. Alex chose the second.
- **Per race, not the three-race total.** On the totals, the race's top figure was about 25 at
  race 2, 44 at race 3 and 47–78 after, so a fixed penalty or reward would weigh about three
  times more at race 2. Dividing by the races covered keeps the scale steady. Within a race it
  picks the same team.
- **The stretch spreads the bottom of the field rather than squashing it.** Drivers with no
  recent championship points still differ by their FP3 and team scores, such as TSU at 17 and
  SAR at 21 on the total scale in 2023 race 10. Nothing in the signal knows retirement risk,
  which left that to the penalty.
- **Alex set aside a fitted weight for each input,** as too little data, and option 3, recorded
  in the entry above.
- **Alex saw that the budget reward is not a risk term.** It rewards spend whatever the risk,
  and could buy an expensive asset likely to go negative, so the penalty stays.
- **Step 8's tuning no longer says anything about the penalty or the rewards,** as Alex pointed
  out: it measured them on the broken design. They are all tuned again.
- **Per-format settings are allowed for, not assumed.** The harness judges whole seasons, and
  only about 6 of ~22 races are sprints, so a sprint-only setting would be judged mostly on
  races it does not touch. The chosen setting is checked race by race instead.
- **DRS is unchanged.** Doubling the nominee's value matches the game doubling their points.

### What changed in the documents

- `requirements.md`: questions 1 to 4 have new answers, each listing the options not chosen in
  one line. Questions 5 to 8 and the decisions follow them. The working assumption about places
  with no history is withdrawn, as there are no tables by place.
- `plan.md`: steps 4 to 8 are one line each, pointing to the steps that revise them. New steps
  11 to 16 build the values, the risk and price-rise measures, the objective, the two checks,
  the tuning values and labels, and the tuning run. Step 9 now waits for step 16, and no longer
  makes a price-rise reward conditional on falling behind on budget, as the reward is now built.

## 2026-11-07 — Step 11: three cases agreed

Agreed with Alex before any code, after each case was checked against the stored metrics for
2023–26 with a throwaway script.

- **A race where every driver's signal is equal raises an error.** It has never happened: the
  narrowest race after race 1 still spreads 1.81 between best and worst signal (2026 race 9).
  With no spread there is nothing to stretch, and it could only come from broken metrics.
- **A constructor with a driver who has no value counts that driver as zero.** It has
  happened twice, both drivers who withdrew and left the team one car: SAR@WIL in 2024 race 3
  and STR@AST in 2025 race 9. Zero matches step 13 scoring the driver zero, and a team still
  running one car keeps that car's value.
- **Race 1 raises an error.** No driver has recent championship points there, so the scale
  has no top or bottom. Nothing calls the strategy at race 1, as `run_for_team` takes the
  starting team as given, so a call there is a mistake. This case was not in the plan.

Also found, and handled without a decision: drivers with no rolling points, as newcomers or
stand-ins with no race in the window (12 rows after race 1), are left out of the field's
highest and lowest. That changes nothing, as the lowest is 0 in every race after race 1.

## 2026-11-07 — Step 11: signal values

### In plain language

- **Each driver and constructor now has a value in championship points per race.** In 2023
  race 10 VER is 25.7 and LEC 18.7, 7.0 apart, the 21 points the design agreed on the
  three-race scale. RED is 43.2 and FER 34.7.
- **It ran on every stored race from race 2, 84 in all, with no error and no missing value.**
  The two withdrawn drivers leave their teams with one car's value: Williams 3.21 in 2024
  race 3, Aston Martin 3.23 in 2025 race 9.
- **Nothing uses the values yet.** Step 13 puts them in the strategy; step 14.1 checks first
  whether they track fantasy points at least as well as the old table.

### Code

`fast_f1/signal.py` gains `driver_values` and `constructor_values`, keyed as
`driver_positions` and `constructor_places` are, which stay until steps 12 and 13 stop using
them. The signal sum moved into `_signal_rows`, shared with `driver_positions`, with no change
in behaviour.

### Tests

Each behaviour was seen failing before it passed, against a stub returning nothing or as a
silent return where an error was due. Mutations each failed the suite: reading the next race,
dividing by 3 at every race, dropping the bottom of the range, counting missing rolling
points as zero, and, for constructors, leaving a constructor unvalued when a driver has none,
dropping the empty-race guard, and taking pairs from every race. Two things surfaced and were
fixed:

- The rule that a missing driver counts as zero passes with any plain sum, so it is checked by
  mutation, and a redundant `fillna` was removed.
- Taking pairs from every race first passed, as other races' drivers have no value; the test
  now holds a constructor in another race only, which that mutation would value at zero.

The look-ahead, no-rows, no-pair and two-pairs tests now run on both new functions too. The
full suite is green, 482 tests, up from 463.

### Real-data check

Both functions on every stored race from race 2, 2023–26:

| Season | Mean top driver value | Mean top constructor value |
| --- | --- | --- |
| 2023 | 24.0 | 42.0 |
| 2024 | 19.4 | 36.6 |
| 2025 | 21.2 | 38.5 |
| 2026 | 21.3 | 38.8 |

The lowest driver value is 0 in every race, and the highest runs 15.7 to 26.0. Every
constructor in a race's pairs gets a value.

## 2026-11-07 — Step 14.1: the size check

### In plain language

- **It passes in every season.** Step 11's values track actual fantasy points slightly better
  than the old table's expected points: a mean correlation per race of 0.69–0.76 against
  0.67–0.73. The values do better in 15 or 16 of each season's 21–23 races.
- **The gain is small, and it is not from ranking drivers better.** The two never order two
  drivers in opposite directions, so they rank drivers alike. The gain comes from keeping the
  size of a lead, where the table gave the same figure to many drivers, and from ranking
  constructors by the sum of their drivers.
- **The top fifth's lead is real.** On average, the fifth of assets the values rank highest
  in a race score about 46–50 fantasy points. The next fifth scores about 21–24.

### How it was measured

Agreed with Alex before the run:

- **One correlation per race, over drivers and constructors together, decides pass or
  fail.** Within-type correlations are reported for context only. Correlating the types
  together tests the balance between drivers and constructors, which is all step 11's scale
  can change.
- **A season's figure is the plain mean of its races' correlations.**

A throwaway script, not kept, ran on 2023–25 from race 2. It used `driver_values`,
`constructor_values` and `load_signal_tables().expected_points`, with actual points from the
archive. Each race used the same assets for both measures: 2,008 asset-races. Two dropped
out: the withdrawn drivers SAR@WIL (2024 race 3) and STR@AST (2025 race 9), who have no
metrics row and so neither measure.

| Season | Races | Values | Table | Races the values win |
| --- | --- | --- | --- | --- |
| 2023 | 21 | 0.754 | 0.728 | 16 |
| 2024 | 23 | 0.755 | 0.733 | 16 |
| 2025 | 23 | 0.691 | 0.672 | 15 |

Within type, for context, the values also lead in every season. Drivers are 0.632 / 0.642 /
0.569 against 0.579 / 0.590 / 0.559. Constructors are 0.777 / 0.772 / 0.679 against
0.732 / 0.738 / 0.604. A gap of about 0.02 in a figure that moves 0.06 between seasons is a
consistent lead, not a large one.

Mean actual fantasy points by fifth of value, within each race, drivers and constructors
together:

| Season | Top fifth | 2nd | 3rd | 4th | Bottom fifth |
| --- | --- | --- | --- | --- | --- |
| 2023 | 49.6 | 20.7 | 14.5 | 6.2 | 4.6 |
| 2024 | 45.8 | 23.8 | 9.0 | 4.5 | 5.3 |
| 2025 | 45.6 | 22.3 | 12.0 | 5.8 | 6.0 |

The bottom two fifths are close and swap places in 2024 and 2025, so the values do not
separate the bottom of the field. That is where retirements and negatives fall, which step
12's penalty is for.

### Checked along the way

- **Drivers: same order, different spread.** Across every race, no pair of drivers is ordered
  one way by the values and the other way by the table. That fits both being built from the
  same signal. The table ties 1,444 driver pairs that the values separate, through its
  isotonic flats. Constructors differ in order, in 189 pairs, as the values sum the drivers
  where the table used the constructor's own rolling points.
- **Fifths are reported for the values only.** Within-race fifths need a tie-break, and the
  table's ties fell back on archive row order. That made its driver fifths an artefact of row
  order rather than a measure.

## 2026-11-07 — Step 12: the risk and price-rise measures

### In plain language

- **Each asset now has a chance of going negative, by its price third.** The cheapest third of
  drivers went negative 20.8% of the time in 2023–25 and the dearest 9.2%. For constructors
  it was 19.6% and 3.0%. Every season's table keeps that order.
- **Each asset now has an expected price rise, by its third on value per 1m.** The top third
  rose more than the bottom third in every season, most of all in 2025: by 0.38m a race for
  drivers and 0.27m for constructors, against 0.06–0.11m before then.
- **2025's own price-rise table is weak.** It comes from 2023 and 2024, where the effect was
  small, so it barely separates drivers. Tuning on 2025 will test the reward on its weakest
  table.
- **Both ran on all 84 stored races from race 2, 2023–26, with no error.** Every priced asset
  got a chance. Every one got a rise except the two withdrawn drivers, who have no value.
- **Nothing new uses them yet.** Step 13 puts them in the strategy.

### Choices Alex made in this step

Agreed before any code:

- **`negative_chance` keeps its name and changes its basis** from any negative in the last
  three races to the price third. The recent-negative code is removed.
- **The expected-points table stays until step 13.1,** as `StrategyFastF1` reads it until then.
  The plan had it removed here.
- **How thirds split.** Rank r of n falls in third `(r − 1) × 3 // n + 1`, so a remainder goes
  to the lower thirds: 20 drivers split 7/7/6, 22 split 8/7/7, and 10 constructors 4/3/3.
  Equal values share the third of their lowest rank.
- **Moves priced at 0 need no rule.** No loaded archive row in 2023–26 is priced at 0: an
  absent driver has no price instead, and the largest move is 1.5m. The ±14m moves in
  *Redesign evidence* must have come from how that throwaway script loaded prices. A move is
  taken only where the asset is priced at both races.

### Code

`fast_f1/signal.py`: `SignalTables.negative_chance` looks assets up by price third, and the new
`SignalTables.price_rise` by third on value per 1m. Both learn from the other 2023–25 seasons,
races 2 onwards, through the shared `_table`, and each table is built once per instance.
`load_signal_tables` already keeps one instance per process. An asset with no value gets no
rise and takes no place in the thirds.

### Tests

- **`negative_chance`:** the new tests first failed by crashing, as the old table had no key
  for an asset without a recent negative. That proves nothing about behaviour, so each rule
  was checked by mutation instead. Ten mutations each failed the suite, and every file was
  restored with a green run in between:
  - ties broken by row order, at their average rank, or at their highest rank;
  - a remainder given to the upper thirds;
  - race 1 counted in the history;
  - thirds split over the season rather than the race;
  - the asset types mixed in one table;
  - a season's own results in its table;
  - 2026 in the history;
  - unpriced assets counted in the thirds.
- **`price_rise`:** against a stub returning nothing, the main test failed on its assertion.
  Three tests passed vacuously against the stub, so they too rest on mutation. Eleven
  mutations each failed the suite, among them thirds on value alone or price alone, the move
  taken from the previous race, a missing next price counted as no move, the median in place
  of the mean, and the empty-history fallback removed.
- **Four of those mutations first passed, each from a fixture gap, fixed before commit:**
  - the race looked up mirrored the history, so thirds on value alone or price alone gave the
    same answer;
  - each third had only two moves, whose median equals their mean;
  - the empty-history test still held history.

The full suite is green, 490 tests, up from 482.

### Real-data check

From a throwaway script, not kept, on the metrics file and the archive. The history behind
the tables matches *Redesign evidence*: 1,340 driver-races with 220 negatives and 670
constructor-races with 80. The mean move is +0.109m for drivers and +0.181m for constructors.

Share going negative by price third, all three seasons together:

| Price third | Drivers | Constructors |
| --- | --- | --- |
| Cheapest | 20.8% of 480 | 19.6% of 270 |
| Middle | 18.1% of 459 | 10.6% of 199 |
| Dearest | 9.2% of 401 | 3.0% of 201 |

The evidence gave 20.9 / 18.4 / 10.2% and 19.9 / 16.4 / 2.6%. The gap, largest for the middle
constructors, fits a different split. Under the agreed one, the fourth-cheapest of 10
constructors joins the cheapest third, so the middle third is smaller and dearer.

Mean price move in m a race, by third on value per 1m and season, with the top third less
the bottom:

| Season | Drivers, bottom / middle / top | Top less bottom | Constructors, bottom / middle / top | Top less bottom |
| --- | --- | --- | --- | --- |
| 2023 | 0.19 / 0.18 / 0.24 | 0.06 | 0.12 / 0.16 / 0.23 | 0.11 |
| 2024 | 0.17 / 0.13 / 0.25 | 0.08 | 0.13 / 0.14 / 0.16 | 0.03 |
| 2025 | −0.18 / −0.11 / 0.20 | 0.38 | 0.10 / 0.29 / 0.36 | 0.27 |

The evidence gave 0.05, 0.07 and 0.37 for drivers and 0.08, 0.02 and 0.24 for constructors.

Each season's tables, as it sees them from the others:

| Season | Negative, drivers | Negative, constructors | Rise, drivers | Rise, constructors |
| --- | --- | --- | --- | --- |
| 2023 | 20.6 / 19.4 / 8.7% | 19.4 / 12.5 / 4.3% | −0.01 / 0.01 / 0.22 | 0.12 / 0.22 / 0.26 |
| 2024 | 20.0 / 19.3 / 10.6% | 18.2 / 9.1 / 3.0% | −0.01 / 0.03 / 0.22 | 0.11 / 0.23 / 0.30 |
| 2025 | 21.9 / 15.6 / 8.4% | 21.3 / 10.0 / 1.5% | 0.18 / 0.15 / 0.25 | 0.13 / 0.15 / 0.19 |
| 2026 | 20.8 / 18.1 / 9.2% | 19.6 / 10.6 / 3.0% | 0.05 / 0.06 / 0.23 | 0.12 / 0.20 / 0.25 |

Every negative table falls from cheapest to dearest. Every rise table rises from bottom to
top, except 2025's for drivers, whose middle third sits below its bottom.

## 2026-11-07 — Step 13.1: the strategy scores values

### In plain language

- **The strategy now picks the team with the highest total value,** in championship points
  per race, in place of the old expected points by position. A driver well clear of the field
  now counts as well clear.
- **The DRS term, the budget reward and the negative penalty carry over unchanged,** working on
  values now. The penalty already reads step 12's chance by price third.
- **The old table and the position code are gone.** Nothing in the repo reads them any more.
- **It solves on a real race.** On 2025 race 5, built from the real files, every selected asset
  has a value above zero. Whether it now buys VER in 2023 is step 14.2's check, not run yet.

### Choices Alex made in this step

Agreed before any code:

- **The existing settings stay in 13.1** rather than being removed and added back one part at a
  time. Parts 13.2 to 13.4 become checks of the code against the plan, changing it only where
  it differs.
- **The position code goes now,** as a commit of its own, rather than at the end of step 13.

### Code

- `fast_f1/signal.py`: `SignalTables.values` gives a race's `driver_values` and
  `constructor_values` together, worked out once per race and returned as a copy, as the other
  measures are. `expected_points`, the history behind it, the isotonic averaging, the scipy
  import, `driver_positions`, `constructor_places` and their helpers are removed.
- `linear/strategy_fastf1.py`: reads `values` in place of `expected_points`. Otherwise the
  rules are unchanged:
  - an asset with no value scores zero;
  - a value naming an asset the race lacks raises an error;
  - the DRS nominee is the selected driver with the best value;
  - there is no race-4 chip.

### Tests

- **`SignalTables.values`:** against a stub returning nothing, the main test failed on its
  assertion. Two tests passed vacuously against the stub, so they rest on mutation: the
  no-signal test and the copy test. Three mutations each failed the suite:
  - the cached dict returned uncopied;
  - the constructor empty-race guard dropped;
  - drivers only.
- **The strategy:** the stub kept an `expected_points` returning nothing until the switch, so
  the unchanged strategy scored every asset zero. Seventeen tests failed on their assertions,
  and the real-race test on the renamed attribute. After the switch all 29 passed, and the
  temporary method was removed.
- **Ported, not dropped:** the position tests that covered rules values share now run on
  `driver_values`:
  - the normal and sprint slots;
  - the 2023 sprint rule;
  - reading only the requested race and its pairs;
  - a missing input;
  - floating-point noise, now as "noise alone counts as every signal equal".

  Each passed on the existing code, so each was checked by mutation and failed it: FP3
  dropped on normal weekends, SQ added on sprints, the normal rule on 2023 sprints, no
  rounding, metrics from every race, and pairs from every race. A first try at the
  every-race metrics mutation kept race 3's row by chance and missed the ported test. It
  failed the suite elsewhere, and the retry kept race 2's row and failed the ported test.
- **Removed with their code:** the expected-points table tests, identifier tie-breaks, and
  constructor places. The copy test moved to the price-rise fixture.

The full suite is green, 467 tests, down from 490: three added and 26 removed.

### Left open

- `_look_up` still lets a key past a table's end take the last value. Positions needed that.
  Thirds always run 1 to 3 when a race has at least three assets, so the branch is now
  untested and serves only a table missing its top third.
- Not run: the strategy through the back-test harness. Only the single 2025 race 5 solve, in
  the test suite, has run on real data.

## 2026-11-07 — Step 13.2: DRS checked against the plan

### In plain language

- **The DRS code already does what the plan asks, so nothing changed.** As agreed at step
  13.1, this part is a check rather than a build.
- **The tests would catch it drifting.** Each of the plan's DRS rules was broken on purpose in
  turn, and every break failed a test.

### What was checked

Against plan item 13.2, in `linear/strategy_fastf1.py` and `StrategyBase.get_drs_objective_term`:

- **The term is the helper's, on the values.** A driver with no value counts as zero, and the
  helper's constraints make exactly one selected driver the nominee.
- **It is scaled by `drs_coefficient`, and left out at zero,** with no DRS variables or
  constraints added.
- **The nominee is the selected driver with the best value,** at any coefficient, ties going to
  the first identifier. When no selected driver is valued above zero, an empty string leaves
  the pick to the default.

Six mutations, each restored from a copy with a green run after it, and each failing the
suite:

| Mutation | Failed |
| --- | --- |
| Coefficient ignored | The coefficient test at 0.5 |
| Term kept at zero | The left-out-at-zero test |
| Term on a flat 1.0, not values | The coefficient test at 0.5 and 1, and the nominee test at 1 |
| Nominee ignores the selected team | The nominee test at 0 |
| No default when no driver has a value | Both no-signal DRS tests and the no-signal solve |
| Ties not broken on the identifier | The tie test |

### One wording difference, left as it is

The plan says the default picks "when none has one". The code uses it when no selected driver
is valued above zero, and values bottom out at exactly 0. The two differ only when all five
selected drivers are valued 0. The default then takes the dearest of them, who also scores 0,
so the result is the same.

## 2026-11-07 — Step 13.3: the negative penalty checked against the plan

### In plain language

- **The penalty code already does what the plan asks, so the strategy did not change.**
- **One rule had no test, and now has one.** The plan says the DRS driver's chance of going
  negative counts once, not twice. The code does that, but doubling it went unnoticed by the
  tests, as every penalty test ran with DRS off.

### What was checked

Against plan item 13.3 and the note below the list, in `linear/strategy_fastf1.py`:

- **It subtracts `negative_penalty` times each selected asset's chance,** drivers and
  constructors alike.
- **The chances are step 12's,** from `SignalTables.negative_chance` by price third, and every
  available asset must have one.
- **A penalty of zero leaves the team unchanged,** and the chances are not even read.
- **The DRS driver's chance is not doubled.**

Six mutations, each restored from a copy with a green run after it:

| Mutation | Failed |
| --- | --- |
| Constructors' chances left out | The penalty test at 1 and 6 |
| Drivers' chances left out | The penalty test at 1 and 6 |
| Penalty applied at zero as 1 | The penalty test at 0, and the chances-read-only-with-a-penalty test |
| Chances read at zero | The chances-read-only-with-a-penalty test |
| A missing chance not checked | The missing-chance test, for a driver and a constructor |
| The DRS driver's chance doubled | **Nothing, at first** |

### The test added

`test_strategy_fastf1_does_not_double_the_drs_drivers_chance` turns DRS on and gives the
likely DRS driver a chance of their own. The best team, worked out by hand, scores 28.8. With
the doubling mutation, the LP gives DRS to the driver with the lower chance and scores 28.6,
as predicted, so the test fails. On the real code it passes. This is a test only, with no
change to the strategy.

The full suite is green, 468 tests, up from 467.

## 2026-11-07 — Step 13.4: the budget reward checked against the plan

### In plain language

- **The budget reward already does what the plan asks, so nothing changed.** It adds
  `budget_reward` times the team's total cost to the objective, and at zero it adds nothing.
- **The tests would catch it drifting.** Five ways of breaking it each failed a test.

### What was checked

Against plan item 13.4, in `linear/strategy_fastf1.py`. Five mutations, each restored from a
copy with a green run after it, and each failing the suite:

| Mutation | Failed |
| --- | --- |
| Reward dropped | The reward test at 0.25 and 1 |
| Reward applied at zero as 1 | The reward test at 0, and ten others that run at zero, among them both real-race solves |
| Sign flipped | The reward test at 0.25 and 1 |
| Reward on unused budget, not total cost | The reward test at 0.25 and 1 |
| Reward doubled | The reward test at 0.25 and 1 |

The reward is on the whole team's cost, so DRS plays no part in it, and the plan's rule
against doubling covers only the chance and the expected rise.

## 2026-11-07 — Step 13.5: the price-rise reward

### In plain language

- **The strategy can now reward assets expected to rise in price.** This was new code, not a
  check: until now, nothing in the strategy read step 12's expected rises.
- **At its default of zero, nothing changes.** The rises are not even read.
- **The tests would catch it drifting.** Eight ways of breaking it each failed a test.

### What was built

In `linear/strategy_fastf1.py`, as proposed to Alex and agreed:

- **A keyword `price_rise_reward=0.0`,** the name and default the requirements set.
- **The objective adds `price_rise_reward` times each selected asset's expected rise,** from
  `SignalTables.price_rise`, drivers and constructors alike.
- **The DRS driver's rise is not doubled,** as DRS does not double a price change.
- **An asset with no rise scores zero for it.** `price_rise` gives a rise only to an asset
  with a value, so a missing rise is expected, unlike a missing chance of going negative,
  which raises.
- **A rise naming an asset the race does not have raises,** as for values and chances.
- **At zero the rises are not read,** as for the chances.

### Tests

Nine new test cases, written first. All nine failed because the strategy did not accept the
keyword, a weak failure that says nothing of the behaviour, so the mutations below carry it:

- the reward at 0, 1 and 5, with teams and objectives found by brute force: 20, 20.3, and
  22.5 once the reward is past 2.5 and D6's higher rise outweighs D3's higher value;
- the DRS driver's rise counted once: 31.2, where doubling gives 31.7;
- the rises read only with a reward, and then for this season and race;
- a rise for an unknown driver, and one for an unknown constructor, raising;
- the real 2025 race 5 test, now also run with a reward of 5.

Eight mutations, each on a copy and restored after, and each failing the suite:

| Mutation | Failed |
| --- | --- |
| Constructors' rises left out | The reward test at 1 and 5, and the DRS test |
| Drivers' rises left out | The reward test at 1 and 5, and the DRS test |
| Sign flipped | The reward test at 1 and 5, and the DRS test |
| Rises read at zero | The read-only-with-a-reward test at 0 |
| Reward applied at zero as 1 | The reward test at 0, and the read-only-with-a-reward test at 0 |
| The DRS driver's rise doubled | The DRS test |
| A missing rise raising | The reward test at 1 and 5, the DRS test, and the read test at 5 |
| An unknown rise not checked | Both unknown-asset tests |

A missing rise raising did not fail the real 2025 race 5 test, so in that race every
available asset has a rise.

The full suite is green, 477 tests, up from 468.

### Not run

The reward through the back-test harness. Only the 2025 race 5 solve has run on real data
with it.

## 2026-11-07 — Step 13.6: a race with no signal checked against the plan

### In plain language

- **A race with no signal already solves, so the strategy did not change.** This finishes
  step 13.
- **It is now tested with each penalty and reward switched on,** not just at the defaults.
  The price-rise reward, new in step 13.5, had never been tried on such a race.
- **On real data, 2026 race 19 solves at every setting,** with a full team and the default
  DRS pick.

### What "every asset zero" means

Every asset's **value** is zero, and so is its expected rise, as only an asset with a value
has one. The chance of going negative and the team's cost come from prices, not the signal,
so the penalty and the budget reward still count. Agreed with Alex to leave it so: 2026 race
19 has no points to score, so this cannot move the result, as the requirements already note.

### Tests

`test_strategy_fastf1_solves_a_race_with_no_signal` now also runs with a penalty of 6, a
budget reward of 1 and a price-rise reward of 5. The stub gives no rises by default, as the
real tables do for a race with no signal. Each case passed on the existing code, as expected
of a check, so three mutations, each on a copy and restored after, show the cases can fail:

| Mutation | Failed |
| --- | --- |
| Rises looked up without a default of zero | The price-rise case, and three step 13.5 tests |
| No rises raising | The price-rise case, and the read-with-a-reward test |
| No values raising | All four cases, and both no-signal DRS tests |

The penalty and budget reward cases guard only against a break that stops the solve. No
mutation specific to them was found that a no-signal race would expose.

The full suite is green, 480 tests, up from 477.

### Real-data check

From a throwaway script, not kept, on 2026 race 19, which is priced but has no metrics rows:
no values, no rises, and chances for all 33 assets. The team was the five cheapest drivers in
races 18 and 19 and the two cheapest constructors, with two moves.

| Settings | Status | Objective | Chances read | Rises read | Selected | DRS |
| --- | --- | --- | --- | --- | --- | --- |
| Defaults | Optimal | None | 0 | 0 | 7 | Default |
| Penalty 6 | Optimal | -6.91 | 33 | 0 | 7 | Default |
| Budget reward 1 | Optimal | 77.1 | 0 | 0 | 7 | Default |
| Price-rise reward 5 | Optimal | None | 0 | 0 | 7 | Default |
| All three | Optimal | 70.19 | 33 | 0 | 7 | Default |

The objective is None where every coefficient is zero, as step 6 found of PuLP.

Not run: the strategy through a season. Step 14.2 is the first to do that.

## 2026-11-07 — Step 14.2: the VER check

### In plain language

- **The check passes.** The rebuilt strategy, at its defaults, holds VER in 93% of 2023's
  team-races from race 10 onwards. The mark, fixed before the run, was more than half.
- **The fault that stepping back found is gone.** The old design held VER in 28% of team-races
  and P2PM in 96%. Counted the same way, the rebuilt strategy now holds him in 93%.
- **It lost him in two races.** In races 17 and 18, 6 of the 15 teams dropped him, and most
  had him back by race 19. Both were sprint weekends, but 2023's other four sprint weekends
  show no such drop, so this says nothing yet about format. Step 16's format check is where
  that gets settled.
- **It also finished ahead of P2PM on these teams, but that is context, not a result.** On 15
  teams in one season, the strategy was 290 points ahead after race 9 and 500 ahead at the end.
  Fifteen teams cannot decide anything, and 2023 is the season that most favours a strategy
  that buys VER. Steps 16 and 17 give the verdict.

### What was run

A throwaway script, not kept, on the real metrics file and archive. 2023 was re-simulated race
by race through `run_for_team` for the 15 teams of *Stepping back*: 5 a band, seed 2,
default edges, starting at race 1. `StrategyFastF1` ran at its defaults: DRS coefficient 1, no
penalty, no rewards. `StrategyMaxP2PM` ran beside it for comparison. A team holds VER in a race
if any held driver's identifier starts `VER@`.

| Team-races holding VER | StrategyFastF1 | StrategyMaxP2PM |
| --- | --- | --- |
| Races 10 onwards (the check), of 195 | 182, 93.3% | 195, 100% |
| Races 2 onwards, of 315 | 293, 93.0% | 302, 95.9% |
| All races, of 330 | 298, 90.3% | 307, 93.0% |

Race 1 is the sampled starting team, which held VER in 5 of 15 for both strategies.

**These are the same teams as before.** P2PM's 95.9% from race 2 onwards matches the 96% of
*Stepping back*, which shows its shares counted from race 2. The old design's 28% is therefore
directly comparable with the 93.0% here.

Share of teams holding VER, by race:

| Race | 1 | 2 | 3 | 4 | 5–16 | 17 | 18 | 19 | 20–22 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| StrategyFastF1 | 33% | 60% | 93% | 87% | 100% | 60% | 60% | 93% | 100% |
| StrategyMaxP2PM | 33% | 33% | 80% | 100% | 100% | 100% | 100% | 100% | 100% |

2023's sprint weekends, which take the sprint rule in the metrics file, are races 4, 9, 12, 17,
18 and 20. Mean points in race 17 were 299 for FastF1 and 319 for P2PM, and in race 18 219
and 207.

Mean final total points were 5,971 for FastF1 and 5,472 for P2PM. Budgets were not recorded.

### Not run

2024 and 2025 race by race, and the strategy through the back-test harness. Neither is part of
this check. Step 16 runs the harness.

## 2026-11-07 — Step 15.1: the values' scale, and the tuning values

### In plain language

- **The tuning values are fixed, before any run:**
  - negative penalty 6.5, 13 and 26;
  - budget reward 0.1, 0.25 and 0.5;
  - price-rise reward 5, 10 and 20.

  Alex agreed them on 2026-11-07, and they are not to be adjusted after seeing results.
- **The penalty and the price-rise reward are each centred on what the measure points to,
  at half, the same and double.** A negative costs about 13 value units. 1m of expected
  rise is worth about 10.
- **The budget reward is set well below what 1m buys.** At 0.93, which is what 1m buys, a
  reward would make spend count as much as the value it buys, and spending the whole budget
  has lost before: Max Budget trails by 21–36%. So the three values are about a ninth, a
  quarter and a half of it.
- **Every measure held steady across 2023–25.** No season's figure was more than 13% from
  the pooled one.
- **Alex is to re-assess these values when 2026 finishes,** on measures that then include
  2026. That is a `BACKLOG.md` item.

### What was measured

A throwaway script, not kept, on 2023–25 from race 2, leaving 2026 out. It took each asset's
value from `load_signal_tables().values`, and its price and actual fantasy points from the
archive: 2,008 asset-races, 1,338 drivers and 670 constructors. These are the same
asset-races as step 14.1.

| Measure | Pooled | By season, 2023 / 2024 / 2025 |
| --- | --- | --- |
| Fantasy points per value unit: the slope of points on value | 1.73 | 1.74 / 1.71 / 1.75 |
| How far a negative falls below what its value predicts, in value units | 13.4 | 12.7 / 14.1 / 13.3 |
| Value per 1m of price: the median of each race's slope of value on price | 0.93 | 1.01 / 0.98 / 0.81 |
| Races left after a race | 10.7 mean, 11 median | |

More detail:

- **Negatives:** 299 of the 2,008 went negative, at −11.8 fantasy points on average, and 23.2
  below the line for their value. Dividing by 1.73 gives 13.4 value units: 12.9 for drivers
  and 14.8 for constructors.
- **Price:** value per 1m is 0.70 for drivers and 1.24 for constructors. The pooled figure's
  interquartile range across races is 0.81 to 1.03.

### How the values follow

- **Negative penalty.** The term is the penalty times the chance, so a penalty equal to the
  cost of a negative, 13, makes the term an expected cost. The values are half, the same and
  double: 6.5, 13 and 26.

  The cost may be partly counted twice. The fit of points on value already includes the
  average rate of negatives, so only the gap in chance between price thirds is new. For
  drivers that gap is 9% against 21%, about 1.5 value units at 13. Double allows for it
  mattering more than that.
- **Price-rise reward.** A 1m rise adds 1m of budget for every race left. 1m buys 0.93 value a
  race, for 10.7 races on average, so it is worth about 10. The values are half, the same and
  double: 5, 10 and 20. At 10, the tables' rises of 0 to 0.3m a race are worth 0 to 3 value
  units, about the size of the penalty's term.

  One setting holds all season, as the plan has it, so the reward overvalues a rise late in
  the season and undervalues one early on. If the reward clears the bar, a version that
  shrinks as the races run out is a possible later item.
- **Budget reward.** A reward at 0.93 would count each 1m of spend as much as the value it
  buys, which leans towards spending everything. So the three values are 0.1, 0.25 and 0.5.
  For comparison, step 8's 0.25 to 1 were in fantasy points, which is 0.14 to 0.58 in value
  units.

## 2026-11-07 — Step 15.2: the tuning labels

### In plain language

- **Done.** `backtest/cli.py` can now run the 11 labels in the plan's table, each built by
  `make_variant` with one change from the base, at step 15.1's values:
  - `StrategyFastF1`, the base;
  - `FastF1_Drs0`;
  - `FastF1_Neg6p5`, `FastF1_Neg13` and `FastF1_Neg26`;
  - `FastF1_Bud01`, `FastF1_Bud025` and `FastF1_Bud05`;
  - `FastF1_Rise5`, `FastF1_Rise10` and `FastF1_Rise20`.
- **Step 7's labels are gone, but four names carry over, with the new design behind them:**
  `StrategyFastF1`, `FastF1_Drs0`, `FastF1_Bud025` and `FastF1_Bud05`. Step 8's stores,
  `outputs/fastf1_v2_tuning_*`, hold rows under all four from the old design. This entry first
  named only the two budget labels. Alex asked for the correction on 2026-11-07.
- **A run resumed from an old store would reuse those rows without warning.** The harness
  skips any team whose key is already in its store. The key is label, season and starting
  team only, with no seed or setting in it. Step 16 draws the same teams as step 8, so in
  2025 every one of the 300 teams under each of the four labels is already in
  `outputs/fastf1_v2_tuning_2025.parquet`. The only sign would be a "skipped" line in the log.
  This was run, not reasoned. P2PM's 300 are there too, which does no harm as it has not
  changed. Labels with new names have none.
- **Only those three stores are exposed.** No other store in `outputs/` holds a FastF1 row,
  and step 17's `outputs/fastf1_v2_results.parquet` does not exist yet. Step 16 writes to new
  stores, as the plan says, and step 17 now has a check against this.
- **The price-rise reward has now been through the harness,** which step 13.5 had not done.

### Tests

The settings test now also checks the price-rise reward. One new test checks that the
`StrategyFastF1` labels the CLI accepts are exactly these 11. Nine cases failed first, for the
labels not yet registered and for step 7's still present. `Bud025` and `Bud05` passed from the
start, as their settings did not change.

Four mutations, each on a copy and restored after, each failed a test:

| Mutation | Failed |
| --- | --- |
| `Rise10` given 5 | Its settings case |
| `Neg26` with a price-rise reward as well | Its settings case |
| `Bud01` setting the penalty in place of the reward | Its settings case |
| Step 7's `FastF1_Neg6` left in | Both registry tests |

The full suite is green, 485 tests, up from 480.

### Real run

`--seasons 2025 --sample-size 1 --seed 2 --strategies StrategyFastF1 FastF1_Rise10
FastF1_Neg13 FastF1_Bud01`, into the scratchpad. It exited 0 in 24s with no error or warning,
and stored 15 rows: one per label per team, P2PM included, all at race 24. Each variant's
totals and budgets differ from the base's, so its setting reaches the harness. Nothing is read
from three teams.

Not run: `Neg6p5`, `Neg26`, `Bud025`, `Bud05`, `Rise5`, `Rise20` and `Drs0` through the
harness. Each differs from a label that did run only in its value, which the settings test
covers. Step 16 runs them all.

## 2026-11-07 — Step 16: tuning on 2023–25

### In plain language

- **No lever cleared the bar, so nothing is tuned.** Step 17 runs `StrategyFastF1` at its
  defaults: DRS coefficient 1, no negative penalty, no budget reward and no price-rise reward.
  Its comparison is `FastF1_Drs0`. No combination run was needed, as no lever cleared.
- **Ten variants tried,** all listed below with the failures. 2026 was not run or looked at.
- **Keeping DRS is supported:** leaving it out lost in every season. Every other lever gained in
  one or two seasons and lost in the rest.
- **The redesigned base now beats P2PM in 2023 and 2024, and trails it in 2025.** It was
  +483 points a team in 2023, +190 in 2024 and −154 in 2025, beating P2PM on 98%, 89% and 24%
  of teams. Step 8's design trailed by 315 to 385 in every season, on the same teams. These
  are the seasons that flatter the signal, so 2026, in step 17, is the fair read.
- **2025's loss looks like budget.** The base ends 2025 10.6m behind P2PM, and no reward
  closed that gap. In 2025, price moves followed recent points per 1m far more closely than in
  2023–24, which is what P2PM picks on (*Why 2025 ends 10m behind on budget*, below).
- **The format check finds no sprint effect,** so no sprint variant is added. Alex chose to
  run it against P2PM, since the chosen setting is the base itself and so has no gap to the base
  to split. In 2025 the loss falls on normal weekends.

### Choices Alex made in this step

- **The format check runs against P2PM, not the base.** The plan checks whether the chosen
  setting's gains or losses against the base fall mainly on sprint weekends. With the base
  chosen, that gap is zero by construction. Alex chose on 2026-11-07 to split the base's gap to
  P2PM by format instead, as the only form of the check that could find anything. A sprint
  variant would still have had to clear the bar against the base.

### What was run

A timing run first: 2025, all 11 labels, 3 teams a band, into the scratchpad. 108
simulations in 87s at a peak RSS of 266 MB.

Then, for each of 2023, 2024 and 2025, one background process, the three in parallel:

`backtest.cli --seasons <season> --sample-size 100 --seed 2 --strategies StrategyFastF1
FastF1_Drs0 FastF1_Neg6p5 FastF1_Neg13 FastF1_Neg26 FastF1_Bud01 FastF1_Bud025 FastF1_Bud05
FastF1_Rise5 FastF1_Rise10 FastF1_Rise20 --output outputs/fastf1_v2_step16_<season>.parquet
--summary outputs/fastf1_v2_step16_<season>_summary.csv`

All three exited 0 with no error or warning in their logs, in 60 to 69 minutes, at a peak RSS
of 254 to 279 MB each.

The bar against the base is the harness's own: `pair_with_baseline`, `season_summary` and
`verdict` from `backtest/metrics.py`, run with `StrategyFastF1` as the baseline from a
throwaway script, not kept.

### The check that no old row was reused

- **Before the run:** none of the nine `outputs/fastf1_v2_step16_*` files existed, and the
  timing run went to the scratchpad.
- **After the run:** each season's log reads "skipped 0 simulations already in the store", and
  each store holds 300 rows per label for its season, 12 labels with P2PM, with no duplicate
  label, season and team. Both pass, so the results are used.
- **The teams are step 8's.** P2PM's 300 results in each season match step 8's store team for
  team, with no points differing, so the comparison with step 8 is like for like.

### Against the base, `StrategyFastF1`

Pooled mean delta, in points a team, with the share of teams that beat the base:

| Label | 2023 | 2024 | 2025 | Seasons positive |
| --- | --- | --- | --- | --- |
| `FastF1_Drs0` | −65.5 (11%) | −28.3 (48%) | −155.5 (20%) | 0 of 3 |
| `FastF1_Neg6p5` | −24.7 (2%) | +32.5 (49%) | −3.0 (40%) | 1 of 3 |
| `FastF1_Neg13` | −57.7 (40%) | +41.0 (62%) | −71.4 (32%) | 1 of 3 |
| `FastF1_Neg26` | −164.9 (6%) | +42.4 (60%) | −54.8 (39%) | 1 of 3 |
| `FastF1_Bud01` | −6.0 (50%) | +9.3 (48%) | −43.7 (29%) | 1 of 3 |
| `FastF1_Bud025` | +26.5 (61%) | +23.5 (55%) | −28.3 (44%) | 2 of 3 |
| `FastF1_Bud05` | +63.4 (87%) | +21.7 (55%) | −20.6 (44%) | 2 of 3 |
| `FastF1_Rise5` | −58.3 (28%) | −31.3 (37%) | +35.3 (58%) | 1 of 3 |
| `FastF1_Rise10` | −65.7 (25%) | −87.6 (28%) | +42.9 (59%) | 1 of 3 |
| `FastF1_Rise20` | −42.5 (49%) | −110.1 (24%) | −62.1 (34%) | 0 of 3 |

Each band gives the same sign as the pooled row in every season for every label except five,
each within 21 points of zero pooled: `Bud01` in 2023 and 2024, `Bud05` in 2025, and
`Neg6p5` in 2025, twice.

The budget reward is the closest miss, gaining in 2023–24 and losing 21 to 44 in 2025. The
penalty gains only in 2024, and the price-rise reward only in 2025, at 5 and 10.

### Against P2PM, for context

| Label | 2023 | 2024 | 2025 |
| --- | --- | --- | --- |
| `StrategyFastF1` | +482.7 (98%) | +190.4 (89%) | −153.9 (24%) |
| `FastF1_Drs0` | +417.2 | +162.1 | −309.4 |
| `FastF1_Neg6p5` | +458.0 | +222.8 | −156.9 |
| `FastF1_Neg13` | +425.0 | +231.4 | −225.3 |
| `FastF1_Neg26` | +317.8 | +232.8 | −208.7 |
| `FastF1_Bud01` | +476.7 | +199.7 | −197.6 |
| `FastF1_Bud025` | +509.2 | +213.9 | −182.2 |
| `FastF1_Bud05` | +546.0 | +212.0 | −174.5 |
| `FastF1_Rise5` | +424.4 | +159.0 | −118.6 |
| `FastF1_Rise10` | +417.0 | +102.7 | −111.0 |
| `FastF1_Rise20` | +440.2 | +80.3 | −216.0 |

Every label is positive in 2023–24 and negative in 2025, so none would pass the harness's
verdict against P2PM on these seasons. Step 8's base, on the same teams, was −315.0, −385.4 and
−357.8.

### Final budgets

Mean `total_budget` at the last race, in millions:

| Label | 2023 | 2024 | 2025 |
| --- | --- | --- | --- |
| `StrategyMaxP2PM` | 135.8 | 127.3 | 138.5 |
| `StrategyFastF1` | 134.7 | 129.7 | 127.9 |
| Variants, range | 132.6–135.7 | 129.5–130.3 | 126.2–128.4 |

The base ends 2023 1.1m behind P2PM, 2024 2.4m ahead and 2025 10.6m behind. Step 8's base
ended 2025 at 124.6, so the redesign closed about 3m of that gap. No reward moved 2025 by more
than 1m. Step 17's budget report on the 500-team run decides whether the gap is raised with
Alex, as the plan says.

### The format check

A throwaway script, not kept, re-simulated `StrategyFastF1` at its defaults and
`StrategyMaxP2PM` race by race through `run_for_team`, for 15 teams a season: 5 a band, seed 2,
default edges, the draw of step 14.2. Each race's format comes from the metrics file's
sessions, as `fast_f1/indicator_analysis.py` classifies it, with 2023's sprint weekends
counted as sprints. Race 1 is the sampled team under both, so it is left out.

The gap is FastF1's points less P2PM's, a team a race, averaged over the 15 teams:

| Season | Format | Races | Mean gap a race | Spread of race gaps (SD) | Share of season's gap |
| --- | --- | --- | --- | --- | --- |
| 2023 | Normal | 15 | +23.7 | 28.1 | 71% |
| 2023 | Sprint | 6 | +24.0 | 30.2 | 29% |
| 2024 | Normal | 17 | +11.0 | 23.6 | 81% |
| 2024 | Sprint | 6 | +7.5 | 43.7 | 19% |
| 2025 | Normal | 17 | −10.8 | 31.5 | 156% |
| 2025 | Sprint | 6 | +10.9 | 50.7 | −56% |

Sprint weekends are 29%, 26% and 26% of each season's races from race 2.

- **No season's gap falls mainly on sprint weekends.** In 2023 a sprint weekend gains the
  same as a normal one. In 2024 the two are within 4 points a race. In 2025 the whole loss is
  on normal weekends, and sprint weekends gained.
- **Six sprint weekends a season cannot separate the formats either way.** Their race gaps
  spread by 30 to 51 points, so a difference of 0 to 22 points a race between formats is well
  inside the noise. The check finds no sign of a sprint effect. It does not show there is none.
- **A race's gap is not only that race's decision.** It also reflects the team carried in from
  earlier races.
- **2023 races 17 and 18,** where step 14.2 saw 6 of 15 teams drop VER, show gaps of −20 and
  +12, both inside 2023's spread.

On these 15 teams, the mean final totals were 5,971, 4,783 and 4,943 for FastF1 and 5,472,
4,550 and 5,060 for P2PM, and the final budgets 135.1, 130.5 and 129.0 against 135.6, 127.3 and
139.5. Each season's gap has the same sign as the 300-team run's.

### Why 2025 ends 10m behind on budget

Alex asked, after the results above.

- **The gap builds all season, not in one event.** The base is 1m behind by race 4, 3.5m by
  race 10, 7.7m by race 15 and 10.5m at the end.
- **Almost all of it is price moves on what each strategy held.** Price moves added 21.8m a
  team for the base against 33.5m for P2PM.
- **No single pick causes it.** It is spread across many midfield assets:
  - P2PM held more of the cheap assets that rose, such as Hülkenberg (10.3 races a team
    against 3.4), Kick Sauber, Russell, Stroll, Bearman, Racing Bulls and Aston Martin, each 0.6
    to 2.2m of the gap.
  - The base held more of the assets whose price fell, such as Sainz at Williams (8 races
    against 3.6) and Lawson at Racing Bulls (13.9 against 1.3).
  - Where both held an asset for as many races, P2PM still tended to earn more from it, as with
    Mercedes, 2.9m against 2.6m, from holding it in the races before it rose.
  - Only the Williams constructor clearly went the base's way, by 1.4m.
- **What makes 2025 different.** In 2025, the next price move followed recent points per 1m
  far more closely than in 2023–24. That is close to what P2PM picks on, so it was holding the
  assets about to rise. In 2023–24 nothing predicted the moves well, and the base's value did as
  well as P2PM's measure. P2PM's final budget fits this: 138.5m in 2025, against 127.3 to 135.8m
  in 2023–24.
- **Why the price-rise reward did not fix it.** This is reasoned, not run. Its expected rises
  for 2025 come from 2023–24, where moves were nearly unpredictable. It gained 35 to 43 points
  in 2025 at 5 and 10, and moved the budget by under 1m.
- **Not known:** whether the game changed how it sets prices for 2025. The data shows only that
  prices behaved differently. Alex is checking the game's rules. Whether 2026 behaves like 2025
  matters for step 17, and 2026 has not been looked at. [2026-11-07: the community's
  reverse-engineered rules say the game did change, to a three-race model that continues in
  2026. They are a working hypothesis, not canonical. See *The game's price-change rules*,
  below.]

How well each measure, known when a team is picked, ranks the next race's price move: the mean
per-race rank correlation, from race 2 to the second last:

| Measure | Drivers 2023 / 2024 / 2025 | Constructors 2023 / 2024 / 2025 |
| --- | --- | --- |
| P2PM's measure, `P2PM Cumulative (3)` | 0.13 / 0.13 / 0.53 | 0.27 / 0.14 / 0.26 |
| Points per 1m, `PPM Cumulative (3)` | 0.08 / 0.12 / 0.57 | 0.19 / 0.11 / 0.44 |
| Points, `Points Cumulative (3)` | 0.15 / 0.13 / 0.44 | 0.24 / 0.13 / 0.14 |
| The base's value | 0.22 / 0.13 / 0.24 | 0.32 / 0.14 / 0.03 |
| The base's value per 1m | 0.15 / 0.13 / 0.38 | 0.24 / 0.10 / 0.20 |
| Price | 0.17 / 0.10 / 0.03 | 0.26 / 0.14 / −0.10 |

The constructor figures rest on about 10 assets a race, so they are noisy.

Two throwaway scripts, not kept. The budget figures re-simulate 2025 race by race for the
format check's 15 teams, and attribute to each held asset its price move from that race to the
next, with no move missing a price. The correlations use the archive's prices and rolling
measures and `load_signal_tables().values`, for 2023–25 only.

### Not run

2026, any combination of levers, and a sprint variant, as none was called for.

## 2026-11-07 — The game's price-change rules: a working hypothesis, not canonical

### In plain language

Alex brought the game's price-change rules, as a fan community worked them out. **F1 has not
published them, so they are not canonical.** They are a reasonable working hypothesis, and they
fit what *Step 16*, *Why 2025 ends 10m behind on budget*, found:

- **2023–24:** a price change was set by the asset's points **in that one race**, relative to
  the field. A team is picked before that race, so nothing known at the time could predict the
  move well. That fits the near-zero rank correlations for 2023–24.
- **2025 onwards:** a price change is set by the asset's **average points per 1m over the last
  three races**. Two of those three races are already known when a team is picked, so the next
  move is largely predictable, and from a measure close to P2PM's own. That fits 2025's
  correlation of about 0.55 for points per 1m and P2PM's measure.
- **2026:** by these rules, the three-race model continues, so 2026 should price like 2025 and
  not like 2023–24. This has not been checked against 2026's data.

What this means for step 17 is for Alex to decide. Step 17 stays on hold until then (`plan.md`).

### Source and status

Reverse-engineered by the player community (F1 Fantasy Tools Discord) and given to this effort
by Alex on 2026-11-07. Not published by F1. The 2025 model has since been checked against the
archive's 2025 and 2026 price moves, and fits them closely once four details are added (*The
2025 model against the archive*, below). The 2024 model has not been checked.

### The rules as given

History:

- 2022: prices followed driver sentiment, so changes were not predictable. The archive starts
  in 2023.
- 2023–2024: a single-race model on Normalized Points. The tiers below are given for 2024. The
  source does not say whether 2023 used the same ones.
- 2025: a rolling three-race model on points per million (PPM).
- 2026: the three-race model continues, with the tier split moved to $18.5M.

**The 2024 model, single race.** Normalized Points is the asset's points this race divided by
the average points of all assets of its type (drivers or constructors) in that race. There are
three price tiers, each with five possible changes, in $M:

| Tier | Price | Possible changes |
| --- | --- | --- |
| A | $25.0M or more | −0.7, −0.5, 0, +0.1, +0.2 |
| B | $15.0M to $24.9M | −0.5, −0.3, +0.1, +0.3, +1.0 |
| C | $14.9M or less | −0.2, −0.1, +0.5, +1.0, +1.5 |

The source showed the Normalized Points range for each outcome in an image, and those ranges
are not captured here. Its example, 2024 Australia: Ferrari scored 92 against a constructor
average of 25.8, so Normalized Points was 3.566. Ferrari was in Tier B and rose $1.0M. The model
gave large swings after each race, and a growing gap in cost between the top teams and the rest.

**The 2025 model, three races.** PPM is points divided by price. The rating is the
equal-weighted average PPM over the last three races. There are two price tiers, split at $20M
in 2025 and $18.5M in 2026:

| Rating | Average 3-race PPM | Tier A, above the split | Tier B, below the split |
| --- | --- | --- | --- |
| Great | Above 1.2 | +0.3 | +0.6 |
| Good | 0.9 to 1.2 | +0.1 | +0.2 |
| Poor | 0.6 to 0.9 | −0.1 | −0.2 |
| Terrible | Below 0.6 | −0.3 | −0.6 |

- At the start of the season, the game behaves as if there were earlier races in which every
  asset scored 0. That drags early price changes down.
- Two-thirds of each change is fixed by previous races, so upcoming changes can be predicted.

Other 2025 changes that affect value:

- Disqualification penalties apply to the constructor only, not the driver.
- Constructors score new pit-stop points, at Grands Prix only, not Sprints.

The source's summary of 2024 against 2025: a single race relative to the field average gave way
to a three-race average of PPM. Three tiers became two, and five outcomes per tier became four,
with smaller, symmetric steps. Price changes became smoother and more predictable, and the cost
of the top assets grew more slowly.

### How it fits this effort's findings

This is reasoned from the rules and *Step 16*'s table, and nothing new was run.

- **Why P2PM gained in 2025.** Its measure, `P2PM Cumulative (3)`, is built on the same three
  races as the game's rating, so it tends to hold the assets the game is about to raise.
- **Why the price-rise reward could not help in 2025.** Its expected rises come from the other
  seasons. For 2025 those were 2023–24, where the single-race model made moves close to
  unpredictable beforehand.
- **Why price alone predicts so little in 2025.** Under the three-race model, a cheap asset
  rises by more than a dear one for the same rating. But the rating itself, not the price,
  decides the direction.
- **The archive's own rolling measures are not the game's rating.** How `PPM Cumulative (3)` is
  computed against an equal-weighted average of three per-race PPMs, and whether the game's
  points are the same fantasy points the archive holds, has not been checked. [2026-11-07:
  both now answered, in *The 2025 model against the archive*, below.]

### The 2025 model against the archive

Alex asked for the 2025 model to be checked against the archive's 2025 and 2026 prices.

**In plain language:** the rules hold. Applied to the archive's own points and prices, they
give the exact next price move for about 97% of 2025–26 moves. That needs four details the
source leaves out, all visible in the data. Applied to 2023–24, the same rules match 3–13%, so
the check can tell a fit from a miss. The game's three-race model is real, and it continues in
2026.

**What was compared.** For each asset and race *r* where both prices are present, the actual
move is the price at race *r*+1 less the price at race *r*. The predicted move comes from the
rules, using the archive's fantasy points and each race's own price for races *r*−2 to *r*, the
race just scored included. A driver is followed by their code across a constructor switch.
Twelve moves around a driver's mid-season team switch were left out (Lawson and Tsunoda in
2025, Lawson in 2026), and so were 21 where a race in the window has no row for the asset. 2026
runs through the last scored race.

**The four details, each added on top of the one before:**

1. **No zero-padding at the start of the season.** The source says early races count as if
   earlier races scored 0. The archive fits better if the rating averages only the races held
   so far.
2. **An asset priced exactly at the split is Tier A.** Alpine at exactly 18.5m in 2026 moved
   by Tier A's steps.
3. **The 2025 split was 18.5m, not 20m.** Williams priced between 18.5m and 19.2m late in 2025
   moved by Tier A's steps. Nothing in the archive priced between 18.5m and 20m in 2025 moved by
   Tier B's.
4. **Prices stop at a floor, and in 2026 at a cap.** The floor was 4.5m in 2025 and 3.0m in
   2026. Assets there, such as Colapinto and Bortoleto in 2025 and Bottas and Stroll in 2026,
   stayed put race after race on ratings that would have cut their price. Mercedes stopped at
   34.0m in 2026 while rated Great. These limits are read from the archive's lowest and highest
   prices, so this detail partly explains the data with itself. The floor's repeated zero moves
   at one price are strong evidence on their own. The 2026 cap rests on one constructor.

Exact match, cumulative:

| Season, type | Moves | As given | + no padding | + at split is A | + 2025 split 18.5m | + floor and cap |
| --- | --- | --- | --- | --- | --- | --- |
| 2023 constructors | 210 | 4% | 3% | 3% | 3% | 5% |
| 2023 drivers | 412 | 3% | 3% | 3% | 3% | 4% |
| 2024 constructors | 230 | 12% | 12% | 12% | 12% | 13% |
| 2024 drivers | 441 | 10% | 10% | 10% | 10% | 10% |
| 2025 constructors | 230 | 91% | 95% | 95% | 97% | 97% |
| 2025 drivers | 451 | 85% | 88% | 88% | 90% | 97% |
| 2026 constructors | 209 | 88% | 91% | 92% | 92% | 97% |
| 2026 drivers | 404 | 84% | 90% | 90% | 90% | 97% |

The move sizes tell the same story. In 2025–26, 93–100% of moves are one of 0.1, 0.2, 0.3 or
0.6, and in 2023–24, 43–70%.

**The 38 moves still missed in 2025–26.** Every one is one band off, mostly on a rating close
to a threshold: 20 of them are within 0.03 of 0.6, 0.9 or 1.2. That suggests the game's PPM differs
slightly from the archive's, perhaps in the points counted or the price used, but this was not
pursued. Four of 2026's constructor misses fall on race 6 (Aston Martin, Audi, Cadillac and
Haas), which may be worth a look at that race's archive points.

**What this answers from the section above.**

- The game's points are the archive's fantasy points, or close enough to give a 97% exact
  match.
- The archive's `PPM Cumulative (3)` is not the game's rating, and this is read from
  `import_data/derivations.py`. It is the total points divided by the total price over the
  three races *before* race *r*, so races *r*−3 to *r*−1. The game's rating for the move after
  race *r* is the mean of each race's own points per 1m over races *r*−2 to *r*. Two of the
  three races overlap, which fits how well `PPM Cumulative (3)` ranked 2025's moves, about 0.57
  for drivers.

One throwaway script, not kept, run on 2023–26 from `load_archive_data_season`.

## 2026-11-07 — Step 16 read again, in the light of the price rules

Alex ruled on 2026-11-07 that the rules stayed the same from 2025 to 2026, and that they are to
be assumed the same in 2027, in the absence of further information. Tuning is to be reviewed and
refined. Before anything is re-run, Alex asked what step 16's runs can teach, such as whether
any lever behaved better in 2025 than in 2023–24.

### In plain language

- **One lever did better in 2025: the price-rise reward.** At 5 and 10 it was the only lever
  to gain in 2025, +35 and +43 points a team, and it lost in both 2023 and 2024. No other
  lever gained in 2025, and the budget reward went from gaining in 2023–24 to losing.
- **The reward was working from the wrong table in every season.** Its expected rises come from
  the other seasons, which mixed the two price models:
  - In 2023–24, almost everything rose most races, whatever its value. There was little to
    choose between assets. Their tables, built partly from 2025, said there was.
  - In 2025, good value rose and poor value fell. For drivers, the gap was about five times
    what 2023–24 showed.
    Its table, built from 2023–24, said the gap was small.

  So the reward overrated rises where they did not matter, and lost. It underrated them where
  they did, and still gained.
- **2023–24 can no longer tune anything about price.** They ran under a price model that has
  gone and is not expected back. That also flatters the base against P2PM there: P2PM's edge
  in reading price moves was much weaker in 2023–24 (*Why 2025 ends 10m behind on budget*).
- **Under the rules, the next move is largely known when the team is picked.** Two of its
  three races are already scored. A table of past averages by third is a weak stand-in for a
  move the game's own rules could compute.

The penalty, the budget reward and DRS show nothing that the rules explain. What follows for
tuning is for Alex to decide.

### What each lever did in 2025, against 2023–24

From step 16's stores, final race only. Pooled mean delta against the base, in points a team,
and the change in mean final budget, in 1m:

| Label | Points 2023 / 2024 / 2025 | Budget 2023 / 2024 / 2025 |
| --- | --- | --- |
| `FastF1_Rise5` | −58 / −31 / **+35** | −0.1 / +0.2 / +0.5 |
| `FastF1_Rise10` | −66 / −88 / **+43** | +0.2 / −0.1 / +0.3 |
| `FastF1_Rise20` | −43 / −110 / −62 | +0.5 / +0.4 / −0.6 |
| `FastF1_Bud01` | −6 / +9 / −44 | −0.8 / +0.2 / −0.8 |
| `FastF1_Bud025` | +27 / +24 / −28 | −0.2 / +0.4 / −0.7 |
| `FastF1_Bud05` | +63 / +22 / −21 | +1.0 / +0.6 / −1.0 |
| `FastF1_Neg6p5` | −25 / +33 / −3 | −1.1 / +0.4 / −0.1 |
| `FastF1_Neg13` | −58 / +41 / −71 | −1.5 / +0.3 / −0.4 |
| `FastF1_Neg26` | −165 / +42 / −55 | −2.1 / +0.1 / −0.6 |
| `FastF1_Drs0` | −66 / −28 / −156 | +0.1 / −0.2 / −1.7 |

- **The price-rise reward** at 5 and 10 gained points in 2025 but added only 0.3 to 0.5m of
  budget, against P2PM's 10.6m lead. At 20 it lost in every season.
- **The budget reward** gained in 2023–24 and lost in 2025, and cost budget in 2025 at every
  value. The rules give a reason, reasoned and not run: an asset above the split moves by
  half the step of one below it, so spending on dear assets slows budget growth from 2025.
- **The penalty** gained only in 2024, at every value. The rules do not explain that. Under
  them a negative also cuts the asset's price, which the penalty does not count, but 2025 shows
  no gain from it.
- **Leaving DRS out** lost in every season, most in 2025. Nothing in the price rules bears on
  it.

### The price-rise tables, given against the season's own

Step 12's mean price move to the next race, in 1m, by third on value per 1m, third 3 holding
the best value. "Given" is the table the season ran with, from the other two of 2023–25.
"Own" is the season's own, which no run saw:

| Type, third | Given 2023 / 2024 / 2025 | Own 2023 / 2024 / 2025 |
| --- | --- | --- |
| Drivers, 1 | −0.01 / −0.01 / +0.18 | +0.19 / +0.17 / −0.18 |
| Drivers, 2 | +0.01 / +0.03 / +0.15 | +0.18 / +0.13 / −0.11 |
| Drivers, 3 | +0.22 / +0.22 / +0.25 | +0.24 / +0.25 / +0.20 |
| Constructors, 1 | +0.12 / +0.11 / +0.13 | +0.12 / +0.13 / +0.10 |
| Constructors, 2 | +0.22 / +0.23 / +0.15 | +0.16 / +0.14 / +0.29 |
| Constructors, 3 | +0.26 / +0.30 / +0.19 | +0.23 / +0.16 / +0.36 |

Third 3's rise less third 1's, which is all the reward uses to tell assets apart:

| Type | Given 2023 / 2024 / 2025 | Own 2023 / 2024 / 2025 |
| --- | --- | --- |
| Drivers | 0.23 / 0.23 / 0.07 | 0.06 / 0.08 / 0.38 |
| Constructors | 0.15 / 0.19 / 0.07 | 0.11 / 0.03 / 0.27 |

In 2023–24, drivers in every third rose about 0.2m a race on average, so prices drifted up
across the board. In 2025, the worse two thirds of drivers fell. 2023's and 2024's given tables
each take half their rows from 2025, which is where their steep gap comes from.

### Not run

Nothing was re-simulated. One throwaway script, not kept, read the step 16 stores and
`load_signal_tables()`'s rise history.

## 2026-11-07 — A rules-based price rise: what it can and cannot show

Alex asked whether recalculating 2025's expected price rise from the rules would give a better
read on whether the price-rise lever improves results. This is reasoned, and nothing was run.

### In plain language

- **It would give the lever its first fair test, but in 2025 only.** Step 16's lever ran in
  2025 on a table that showed about a fifth of the real gap between drivers. Under the rules,
  two of the three races that set the next move are already scored when the team is picked.
  Only the coming race is unknown, and the signal's value is an estimate of it. A rise worked
  out from the rules should predict 2025's moves far better than an average by value third.
- **The stake is worth testing.** P2PM's budget lead over the base built to 10.6m by the end
  of 2025, about 5m on average across the season. At 0.93 value units a race per 1m and 1.73
  fantasy points per value unit (step 15.1), 5m is worth about 8 points a race, so about 150 to
  200 points a season. That is about the size of the 154-point gap. It is an upper bound, as it
  assumes the extra budget is all spent, and P2PM leaves 2.3 to 4.3m unspent.
- **It tests whether the lever can help, not whether it wins.** 2026, in step 17, stays the
  only fair read.

### What it cannot show

- **One season.** 2023–24 cannot test a rules-based rise, as their prices followed a model that
  has gone. Choosing the reward's value on 2025 and judging it on 2025 is in-sample, so a gain
  is weaker evidence than it looks.
- **The harness's bar needs a ruling.** It asks for a gain in every season. For this lever,
  2023–24 can show at most that it does no harm.
- **The coming race must come from the signal, never from its actual points.** Reading them
  would be look-ahead and flatter the lever.
- **The reward's scale may need a fresh look.** 5, 10 and 20 sit beside the old tables' rises
  of 0 to 0.3m a race. A rules-based rise runs from −0.6 to +0.6m, so the same value counts for
  more. A rise is also worth less as the season runs out, which one setting ignores.
- **A small leak from 2026.** The floor and cap added in *The 2025 model against the archive*
  were read from the archive's 2025–26 prices. It matters only for assets at the floor or the
  cap.

### Alex's decision

**Alex accepted on 2026-11-07 that a rules-based price rise will have limited back-testing,**
and asked for the change to be planned.

## 2026-11-07 — Step 19: the conversion for estimate (a), fixed before the comparison

Estimate (a) turns an asset's signal value into expected fantasy points for race *r*. Alex
chose on 2026-11-07 a least-squares line with an intercept, fitted for drivers and
constructors separately, over the plan's single slope through the origin. A bare slope would
miss the baseline that fantasy points have and the value lacks, and constructors score
differently from drivers.

Fitted on 2023–24 only, races 2 onwards, on each scored asset with a value from
`load_signal_tables().values`. 2025 is not in the fit, and this is logged before any 2025
comparison is run:

| Type | Asset-races | Fantasy points for race *r* | Correlation |
| --- | --- | --- | --- |
| Drivers | 879 | 1.538 + 1.469 × value | 0.58 |
| Constructors | 440 | 5.948 + 1.687 × value | 0.71 |

One throwaway script, not kept.

## 2026-11-07 — Step 19: the accuracy check on 2025

### In plain language

- **It passes, and estimate (a) is chosen.** Working the next price move out from the rules,
  with race *r*'s points estimated from the signal, misses the actual move by 0.15m on
  average. Step 16's table missed by 0.32 to 0.40m. Alex confirmed the choice of (a) on
  2026-11-07.
- **(a) beats (b), leaving race *r* out, by 9.8%,** which clears the 5% bar. The signal adds
  a little on top of the two races already scored, which carry most of the prediction.
- **The rules are coded correctly.** Fed race *r*'s actual points instead, the same code gives
  the exact move 96.5% of the time, as the archive check found.

### Why the fit uses 2023–24, though their price rules differ

Alex asked this on 2026-11-07. The fit turns a signal value into fantasy points scored, and
price does not enter it. The 2025 change was to how prices move, not to how points are scored,
so 2023–24 can still say how values relate to points. 2025 is left out because it is the
season being tested on.

**A limit, reasoned and not measured:** scoring did change a little in 2025. Constructors gained
pit-stop points, and disqualification penalties fall on the constructor only. The constructor
line could be slightly off for 2025. Step 15.1 found points per value unit steady across
2023–25, so the effect is expected to be small.

### What was run

A throwaway script, not kept, on 2025, races 2 onwards. It covers each asset with a value that
is priced at both race *r* and race *r*+1 under the same identifier, so a driver's move across
a team switch drops out. The rules are applied as `plan.md` gives them, with 2025's figures:
split 18.5m, floor 4.5m, no cap. A rating of exactly 1.2 or 0.9 counts as Good, and exactly 0.6
as Poor. Races *r*−2 and *r*−1 use the archive's points over each race's own price, following a
driver by code. A window race with no row for the asset counts as zero points, which happened
3 times. Moves are compared after rounding to 0.1m.

| Estimate | Drivers, 436 moves | Constructors, 220 moves | Pooled, 656 moves |
| --- | --- | --- | --- |
| (a) race *r* from the signal | 0.152 / 66% / 0.73 | 0.148 / 73% / 0.63 | 0.151 / 68% / 0.73 |
| (b) race *r* left out | 0.172 / 65% / 0.69 | 0.158 / 73% / 0.60 | 0.167 / 68% / 0.68 |
| Step 16's 2025 table | 0.396 / 0% / 0.29 | 0.317 / 0% / 0.24 | 0.370 / 0% / 0.09 |
| Check: race *r*'s actual points | 0.014 / 96% / 0.99 | 0.012 / 97% / 0.99 | 0.013 / 97% / 0.99 |

Each cell is the mean absolute error in 1m, the share of exact matches, and the rank
correlation with the actual move. The table's averages never land on a game step, so its exact
share is zero by design. The check reads race *r*'s result, and is there only to test the code,
never as a candidate.

- **The choice:** (a)'s pooled error is 9.8% below (b)'s, so (a), against the 5% bar.
- **The pass:** (a)'s error is below the table's for drivers, 0.152 against 0.396, and for
  constructors, 0.148 against 0.317.

Step 20's real-data check is to reproduce (a)'s row.

## 2026-11-07 — Step 20: the rules-based rise, in the code

### In plain language

- **`price_rise` now works the next price move out from the game's rules,** with estimate
  (a) for the coming race. Its contract is unchanged, so `StrategyFastF1` and `linear/` are
  untouched. Step 12's rise tables are gone. The negative chances are as they were.
- **On the real 2025 data it gives exactly step 19's figures for (a).**
- **One existing test changed, as Alex agreed.** With the reward on, the strategy on 2025
  race 5 now keeps BOR, valued 0 and expected to hold, over HUL, valued 0.70 and expected to
  fall 0.6m. That is the reward working: the old tables' rises were almost all positive, so
  this never happened. The real-race test now checks, with the reward only, that every
  selected asset has a value rather than a positive one. That still catches identifiers that
  do not match, which is what the check is for.

### What was built

Two commits, each test-first:

1. `rule_price_move(rating, price, season)`, with each season's split, floor and cap in
   `PRICE_RULES`. A season after 2026 takes 2026's figures, and one before 2025 is an error.
   A floor or cap stops a move but never pushes an asset already beyond it back inside. That
   case is beyond what `plan.md` covers, and Alex agreed it on 2026-11-07. It matters only if
   a later season prices an asset above 34.0m or below 3.0m.
2. `price_rise` on the rules, with the points-from-value line in `POINTS_FROM_VALUE`.

### Tests

- **25 for the rules,** all seen failing on assertions against a stub before the code was
  written. They cover each band at 1.2, 0.9 and 0.6, each tier, the split itself, the floor
  and cap in each season, 2027 taking 2026's figures, and 2023–24 refused. The guard that
  stops a limit pushing an asset back was confirmed by mutation: dropping it for the cap or
  the floor turns its own test red.
- **12 for `price_rise`,** seen failing against the old code, which asked for a rise table
  that no longer applies. Because that failure is an error rather than a wrong answer, each
  rule was also confirmed by mutation, restored from a copy with the suite green between
  rounds:

| Mutation | Tests turned red |
| --- | --- |
| Race 1 inside race 4's window | the rules test |
| Zero-padding to three races | race 2's held-so-far test |
| Estimate left out | 5 |
| Race *r*'s own points read | 4, the own-points test among them |
| A missing held race skipped, not counted as zero | the missing-row test |
| A driver not followed by code | 4, the switch test among them |
| The season ignored, 2025's rules always used | 2026's season-rules test |
| 2023–24 not emptied | both 2023–24 tests |
| The constructor fit used for drivers | 2 |

The full suite passes, 514 tests.

### Real-data check

A throwaway script, not kept, ran the built `price_rise` on 2025, races 2 onwards, against the
actual moves of assets priced at both races under one identifier. It gave 436 driver moves at
0.1523 mean absolute error, 66.3% exact and 0.727 rank correlation, and 220 constructor moves
at 0.1482, 72.7% and 0.627. That matches step 19's (a) row to four places. The check would
have failed had the window, the padding or the estimate differed from step 19's script, as
each changes these figures.

### Not run

No back-test was run. That is step 22.

## 2026-11-07 — Step 21: the labels

### In plain language

The three price-rise labels are renamed, so step 22 starts from no stored rows. Under the old
names, step 16's stores hold rows built from the old rise tables. A run that pointed at one of
those stores would have reused them without saying so.

### What was done

`FastF1_Rise5`, `FastF1_Rise10` and `FastF1_Rise20` in `STRATEGIES` became
`FastF1_RuleRise5`, `FastF1_RuleRise10` and `FastF1_RuleRise20`, at the same values. The
test's table of labels was renamed first. Five tests failed: the registry still held the old
names, and the command line refused the new ones. After the rename, the full suite passes,
514 tests.

A read of each store's label column in `outputs/` found the old names only in
`fastf1_v2_step16_2023`, `_2024` and `_2025`. The new names appear in none.

### Not run

No back-test was run. That is step 22.
