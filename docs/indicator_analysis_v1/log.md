# indicator_analysis_v1 — Log

Execution log for the indicator_analysis_v1 effort. Newest entries at the bottom.
Requirements and plan live alongside in `requirements.md` and `plan.md`.

## Status summary

- Effort started 2026-10-31. Step 1 (docs) is complete.
- Steps 2–6 completed 2026-10-31: analysis frame, scoring, the bar, selection and
  fitted weights, and the report, all in `fast_f1/indicator_analysis.py`.
- Step 7 completed 2026-10-31: findings below. The effort is done.

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
