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
