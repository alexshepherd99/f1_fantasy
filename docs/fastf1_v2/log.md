# fastf1_v2 — Log

Execution log for the fastf1_v2 effort. Newest entries at the bottom. Requirements live
alongside in `requirements.md`, and `plan.md` follows once its questions are answered.

## Status summary

- Effort opened 2026-11-01. The backlog item has moved to `requirements.md`. Questions
  are being asked one at a time, and no code has been written.
- Paused 2026-11-01 at question 1 of 8, which has been put to Alex and not yet answered.
  Questions 2 to 8, their evidence and how to resume are in `requirements.md`.
- Only decision so far: no hard rule on maximum spend, and a soft term gets tested.
- Nothing from this effort is committed yet: `docs/fastf1_v2/` and the `BACKLOG.md` edit are
  in the working tree.

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
