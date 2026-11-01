# indicator_analysis_v1 — Log

Execution log for the indicator_analysis_v1 effort. Newest entries at the bottom.
Requirements and plan live alongside in `requirements.md` and `plan.md`.

## Status summary

- Effort started 2026-10-31. Step 1 (docs) is complete.
- Steps 2–6 completed 2026-10-31: analysis frame, scoring, the bar, selection and
  fitted weights, and the report, all in `fast_f1/indicator_analysis.py`.
- Step 7 completed 2026-10-31: findings below. The effort is done.
- Step 8, the first race, added and completed 2026-11-01: below.
- A rough estimate of what a Spearman gain is worth, 2026-11-01: last entry below.

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

## 2026-10-31 — Findings

### In plain language

Spearman runs from 1 (the signal orders the drivers exactly as they finished) to 0
(no relationship). "Rolling points" below means championship points over three races.

- **Normal weekends: add constructor rolling points and FP3 to driver rolling
  points.** That moves Spearman against fantasy points from 0.560 to 0.600. The gain
  is real but modest, and it held on 2026, which played no part in choosing it.
- **Sprint weekends: use driver and constructor rolling points, and leave practice
  out.** Even that can't be separated from driver rolling points alone. Every
  combination that added practice to rolling points scored lower than without it.
- **Odds: not proven either way.** Within 2026, odds add nothing measurable to the
  best non-odds combination. Sixteen races can't rule out a modest benefit.
- **Fitted weights: not worth having.** Simple equal-weight sums do as well on normal
  weekends and clearly better on sprint weekends.
- **Current `AggregateRank`: not clearly different from rolling points.** So the gate
  for *Build a strategy on the FastF1 indicators* does not stop that work.

None of this says these signals pick better fantasy teams, or that they beat P2PM.
Rolling points is a proxy for P2PM's input, not P2PM, which uses fantasy points and
divides by price. Only a back-test can answer that.

### Results against the bar: fantasy points (primary)

The winner was chosen on 2023–25 (2024–25 for sprint weekends). Gains are mean
per-race Spearman with the 95% interval. "Pass" means R8's two conditions both hold.

| Normal weekends | Races | Gain | Interval | Pass |
| --- | --- | --- | --- | --- |
| Driver + constructor + FP3 vs rolling | 60 | +0.040 | +0.021 to +0.060 | Yes |
| The same, 2026 alone | 11 | +0.062 | +0.022 to +0.111 | Yes |
| Choice made without each season, vs rolling | 60 | +0.035 | +0.012 to +0.056 | Yes |
| Winner vs rebuilt aggregate | 60 | +0.017 | −0.004 to +0.042 | No |
| Rebuilt aggregate vs rolling | 60 | +0.023 | −0.009 to +0.053 | No |
| Fitted weights vs unseen-season choice | 60 | +0.006 | −0.006 to +0.018 | No |

| Sprint weekends | Races | Gain | Interval | Pass |
| --- | --- | --- | --- | --- |
| Driver + constructor vs rolling | 18 | +0.014 | −0.009 to +0.038 | No |
| Winner vs rebuilt aggregate | 18 | +0.070 | +0.005 to +0.141 | Yes |
| Rebuilt aggregate vs rolling | 18 | −0.056 | −0.126 to +0.011 | No |
| Fitted weights vs unseen-season choice | 18 | −0.040 | −0.072 to −0.013 | No, clearly worse |

Against rolling points, the normal-weekend winner moves the top-3 hit rate from 0.533
to 0.572 and the top-5 from 0.643 to 0.657. These are secondary and were not put
through the bar.

The choice is stable. Leaving out any one season picks driver + constructor + FP3 or
the same plus FP2 on normal weekends, and driver + constructor in every fold on sprint
weekends. On normal weekends those two options score 0.600 and 0.601, so FP2's place
is a coin toss.

### Results against the bar: finishing position (secondary)

| Comparison | Races | Gain | Interval | Pass |
| --- | --- | --- | --- | --- |
| Normal: driver + constructor + FP2 + FP3 vs rolling | 60 | +0.059 | +0.035 to +0.084 | Yes |
| The same, 2026 alone | 11 | +0.089 | +0.049 to +0.135 | Yes |
| Sprint: driver + constructor + SQ vs rolling | 18 | +0.042 | +0.014 to +0.075 | Yes |
| The same, 2026 alone | 6 | +0.026 | −0.008 to +0.061 | No |
| Sprint: choice made without each season, vs rolling | 18 | +0.010 | −0.045 to +0.060 | No |

The sprint result is fragile: it passes overall but not on unseen seasons.

Sprint Qualifying helps predict the finish but not fantasy points, which is the one
place the two targets give a different answer about an indicator. The obvious
explanation, that fantasy points also pay for the sprint and for overtaking, has been
reasoned and not tested.

### Odds (2026 only, 16 races, race 4 left out)

| Comparison, fantasy points | Gain | Interval | Pass |
| --- | --- | --- | --- |
| Odds vs best non-odds | −0.026 | −0.056 to +0.003 | No |
| Odds + best non-odds vs best non-odds | −0.004 | −0.018 to +0.008 | No |
| Odds vs rolling | +0.020 | −0.032 to +0.077 | No |
| Odds + best non-odds vs odds | +0.021 | 0.000 to +0.043 | Yes, barely |

The last row's pass is at the edge of its interval on one season, where R8's second
condition adds nothing, and should not carry weight.

On finishing position, odds do beat rolling points (+0.060, +0.012 to +0.114), but
not the best non-odds combination (−0.008, −0.035 to +0.018).

Capture point changes little. Split into 9 pre-weekend and 7 during-weekend races,
odds against the best non-odds combination is −0.038 and −0.009 on fantasy points,
with both intervals spanning zero. Odds taken later do look slightly better, but these
splits are far too small to separate.

### What else was learned

- **Grid position is not a ceiling for fantasy points.** R6 called it one. On normal
  weekends it scores 0.515 against fantasy points, and the winner beats it by 0.086
  (0.038 to 0.135). For finishing position it behaves as expected, scoring 0.673, and
  it beats rolling points (+0.081). There is no known upper limit on how predictable
  fantasy points are.
- **Driver and constructor rolling points overlap heavily** (0.875 within a race), yet
  summing them still gains something. `docs/fastf1_v1/log.md` dropped the constructor
  from `AggregateRank` as redundant, measured on ten races. This does not overturn
  that: the winner does not pass against the aggregate on normal weekends.
- **Practice looks stronger in 2026.** FP2 scores 0.619 against fantasy points in 2026
  and 0.430 across 2023–25. FP3 alone (0.655) also beats the normal-weekend winner
  (0.644) on 2026's 11 races. One season cannot say whether that lasts, and it is the
  first season of new regulations.
- **Lap count and stint length are weak**, about 0.25 at best against fantasy points
  in any format across all seasons. They were screened only.

### Sensitivities (R10, plus finishers only from R4)

None changes the normal-weekend answer. Against rolling points, the winner gains
+0.044 with no-time drivers removed and +0.040 on finishers only, and both pass. True
ranks in place of the stored scaled ranks change nothing (0.000, −0.011 to +0.012), so
the concern about one slow lap squeezing a sum does not matter in practice.

### Checks and their limits

Each behavioural change was confirmed by deliberately breaking the finished code, 60
mutations in all. Eleven at first went uncaught. Seven were real test gaps, closed
with new tests, and one exposed a redundant check, which was removed. The other three
were caught all along: the mutation script counted only `FAILED` lines, so a crash in
the shared fixture read as a survivor. The script was corrected, and all eleven were
rechecked.

Reading the first results exposed one bug, which the tests had missed: 2026 race 4's
post-qualifying odds still counted in the standalone odds score. A test was seen
failing on it (4 races counted, not 3) before the fix. The fix moved only the sprint
odds score, and a rerun showed the comparisons table unchanged.

The headline normal-weekend result was recomputed separately from the raw workbooks
with pandas alone, without importing the module. It matched at the precision reported:
60 races, 0.600 against 0.560, and the same gain in each season. A shuffled signal
scored about zero (−0.02) in that recomputation, so the scoring can show no
relationship.

The overall intervals include the seasons the winner was chosen on, which flatters
them; the 2026 and unseen-season rows are the fairer read. No correction is made for
trying 15 combinations. Wet practice sessions are not separated, because the file has
no weather flag.

### Reading the snapshot columns

R9's capture point split reads the `Odds_*` snapshot columns, which `CLAUDE.md` says
consumers should not use without asking. It was covered by the agreed proposal. They
are read only to label each race, and no score uses their prices.

## 2026-11-01 — The first race (R12)

### In plain language

**There is no clear best signal for race 1, and four races cannot produce one.** Last
season's fantasy points, the race 1 fantasy price and FP3 all score about 0.6 on
Spearman against fantasy points. That is broadly in line with the 0.60 the best
combination reaches at later normal weekends, though those are different races. Any of
the three is a usable starting point, and this does not rank them.

Odds scored highest, but only 2026 has them, and FP2 scored almost the same in that
race. Practice alone has been unsteady: FP2 ranged from 0.29 to 0.85.

None of this says which signal picks the better opening team. Budget and transfers sit
in between, and only a back-test can show that.

### Results: fantasy points (primary)

Mean Spearman is per season, then averaged. "Own data" scores each signal on what it
has. "Same drivers" uses only the drivers and seasons that every listed signal has,
which removes 2023 and anyone with no previous season.

| Signal | 2023 | 2024 | 2025 | 2026 | Own data | Same drivers |
| --- | --- | --- | --- | --- | --- | --- |
| Odds | - | - | - | 0.872 | 0.872 (1 race) | - |
| Last season's points | - | 0.802 | 0.405 | 0.735 | 0.647 (3 races) | 0.647 |
| FP3 | 0.538 | 0.631 | 0.451 | 0.760 | 0.595 | 0.590 |
| Race 1 price | 0.375 | 0.779 | 0.559 | 0.663 | 0.594 | 0.622 |
| FP2 + FP3 | 0.522 | 0.530 | 0.450 | 0.837 | 0.585 | 0.614 |
| FP2 | 0.435 | 0.356 | 0.286 | 0.854 | 0.483 | 0.549 |
| Grid (reference) | 0.403 | 0.677 | 0.342 | 0.522 | 0.486 | - |

Every signal with more than one season moves by at least 0.3 between its best and
worst, while the top three on the same drivers sit within about 0.03 of each other. So
the gaps between signals are far smaller than the swing within any one. Grid is too
late to pick a team, and it scores level with FP2 and below the others.

Top-3 and top-5 hit rates are in the output and are not used here. With one race a
season, one driver moves a season's top-3 figure by a third.

### Results: finishing position (secondary)

On the same drivers, FP2 + FP3 scores 0.714, FP3 0.688, last season's points 0.661,
price 0.648 and FP2 0.637. Odds score 0.809 on 2026 alone, with FP2 at 0.837 in that
race. The order differs from the fantasy-points one, which is more reason not to rank
them.

### Limits

- The season-to-season changes could be down to the circuit, weather or a regulation
  change. The data here cannot separate those, and no weather flag exists.
- Last season's points are a plain total, so a part-season driver reads as weak. A
  driver who missed the season before, rookie or returnee, has no score.
- A driver with no practice time scores 0 on that session, as in the main analysis.
- FP1 on normal weekends and pre-season testing were not tried, as they are not in the
  metrics file.
- 2026 race 1's odds are the post-FP2 price, so they match that season's routine of
  picking the team after FP2.

### Checks

Neither new function could fail meaningfully before it existed, so each behaviour was
confirmed by breaking the finished code instead, 27 mutations in all. One went uncaught
at first: reporting the top-5 figure as the top-3 one. A test was added and caught it.

The season figures against fantasy points were recomputed from the raw workbooks with
pandas alone, without importing the module. Price, last season's points, FP2, FP3,
FP2 + FP3 and odds all matched to three decimals, as did price on the same drivers. The
grid row, finishing position and the other same-drivers figures were not recomputed. A
shuffled price scored about zero in each season, so the recomputation can show no
relationship.

The real entry point was run, and the six existing output files came out byte-identical,
so the main analysis did not move.

## 2026-11-01 — What a Spearman gain might be worth

A deliberately rough estimate, asked for as "pure approximation in the first instance".
It came from a throwaway script that is not kept and has no tests. The method below is
enough to rebuild it.

### In plain language

**Moving from rolling points to the normal-weekend winner, a gain of 0.04, looks worth
roughly 50 to 130 points a season, or about 1–3% of P2PM's 4,500–5,500.** As a rule of
thumb, each 0.01 of Spearman is worth about 15–25 points a season.

That is the same size as differences that have decided earlier back-tests (Max Points
lost by 4 to 156 a season, and removing the race-4 chip moved results by 2 to 168). But
it is small against luck in one season, as tiny changes to the signal alone moved a
simulated season by a similar amount. It might show up across several seasons and
would be hard to see in one.

**This is not a comparison with P2PM.** It only measures rolling points against the
winner inside a simplified simulation. It does not say an indicator strategy would beat
P2PM, which only a back-test can show.

### Three views

Rolling points is the baseline. The candidate is driver + constructor + FP3 on normal
weekends, and driver + constructor on sprint weekends. All three count drivers only.

| View | What it does | Gain from +0.04 |
| --- | --- | --- |
| 1. Top five, no limits | Each of 60 normal races, take the signal's top five | +2.1 a race (−2.1 to +6.3) |
| 2. Degraded result | Add noise to the actual result, and read points against Spearman | +4.1 a race, or +2.4 with a budget of 70 |
| 3. Season simulation | Pick under a driver budget, with two moves a race | +2.2 to +6.2 a race, or +46 to +131 a season |

View 2 is where the rule of thumb comes from: 0.6 (budget) to 1.0 (no budget) points a
race per 0.01, near a Spearman of 0.6, over about 24 races.

View 1 gains about half of what view 2's no-budget figure predicts, with an interval
that spans zero. A plausible reason, reasoned and not tested, is that Spearman counts
all twenty positions and a team only uses five.

View 3 picks the highest-signal team of five under the budget, starting from race 2.
A driver who leaves is replaced with a free move, and race 4 has unlimited moves, as
P2PM's chip does. DRS doubles the team's highest-signal driver. Season gains in points:

| Driver budget | 2023 | 2024 | 2025 | 2026 | Mean |
| --- | --- | --- | --- | --- | --- |
| 60 | −30 | −51 | +106 | +161 | +46 |
| 70 | +72 | +22 | +121 | +85 | +75 |
| 80 | +114 | +174 | +291 | −55 | +131 |
| No limit | −11 | −20 | +210 | +95 | +68 |

Adding random noise of 0.02 to the rolling points signal, with no real change, moved a
season's total with a standard deviation of 19–93 points across 20 runs. So most single
cells above cannot be told from noise. The direction is positive in 11 of 16, and those
cells are not independent.

### Limits

- Constructors are not modelled, and neither are unused-transfer carryover or chips
  other than the race 4 reset.
- The budget is fixed, while a real team's value grows through a season. Top-five
  drivers cost about 126 on average, so view 1 could not actually be afforded.
- The winner was chosen on 2023–25, which flatters those seasons. 2026 is the fair read,
  and its gains are +161, +85, −55 and +95.
- 2026 has 17 races scored, and the others 21–23.
- The noise size in the check above is a judgement call. A different one changes the
  floor.

### Checks

The simulation asserted its move limit and team size on every race, and no rolling-points
or winner team went over budget. Under budgets of 70 and no limit, a random signal scored far below rolling
points in every season, and perfect foresight far above. In view 1, a random pick
scored 54.8 a race, against 55.4 expected by chance. These show that the simulation
behaves, not that its size estimate is right. It has not been compared with the real
engine.
