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
- Decisions so far: no hard rule on maximum spend, with a small reward per 1m spent to be
  tested; the objective scores in expected fantasy points by signal position; a constructor
  scores on its own rolling place, converted the same way; negatives get no separate term in
  the base strategy, with a soft penalty as a tested variant; DRS sits inside the objective at
  a coefficient of 1, with zero as the comparison; the signal is built from the component
  columns, leaving `AggregateRank` to its own backlog item; and the verdict is the harness's
  across four seasons, with coefficients fixed on 2023–25 before 2026 is run.

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
