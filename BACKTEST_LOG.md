# Back-test log

Key findings from strategy back-tests, newest at the bottom. Each entry is a
summary only. The full detail is in the effort's own docs, which each entry
links to.

Unless an entry says otherwise, a strategy is compared with **Max P2PM**, the
strategy picking the live team. The comparison uses the `backtest` module: the
same seeded sample of 1,500 starting teams per season, 500 from each value band,
simulated under both strategies and compared team by team. A strategy **beats
the baseline** only if its mean points difference, pooled over all three bands,
is positive in every season tested.

## Summary

| Strategy | Effort | Tested | Seasons | Mean delta vs P2PM (points/season) | Beats P2PM? | Outcome |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Zero-stop (`StrategyZeroStop`) | [backtest_v1](docs/backtest_v1/) | 2026-09-18 | 2023, 2024, 2025 | −1,358, −1,019, −1,763 | No, 0 of 3 seasons | Control, loses as expected |
| Max budget (`StrategyMaxBudget`) | [backtest_v1](docs/backtest_v1/) | 2026-09-18 | 2023, 2024, 2025 | −1,302, −979, −1,748 | No, 0 of 3 seasons | Control, loses as expected |
| Max points (`StrategyMaxPoints`) | [max_points_v1](docs/max_points_v1/) | 2026-09-20 | 2023, 2024, 2025 | −14.5, −156.2, −4.4 | No, 0 of 3 seasons | Hypothesis refuted |
| P2PM without race-4 reset (`StrategyMaxP2PMNoReset`) | [max_points_v1](docs/max_points_v1/) | 2026-09-29 | 2023, 2024, 2025 | +1.8, −32.3, −168.0 | No, 1 of 3 seasons | Keep the race-4 chip |

## Zero-stop and Max budget controls — `backtest_v1` (2026-09-18)

**Question.** These are the two simple control strategies. Zero-stop keeps the
starting team all season and only changes a driver when forced to. Max budget
just spends as much of the budget as it can. Neither was expected to win.
They were run to check the new `backtest` module against a result already
known from the full back-test in January, which showed both well behind P2PM.

**Result: both lose heavily in every season.** For scale, P2PM's pooled mean
was 5,505, 4,547 and 4,948 points in 2023, 2024 and 2025.

| Strategy | Season | Mean delta | Mean delta % | Teams beating P2PM |
| :--- | :--- | :--- | :--- | :--- |
| Zero-stop | 2023 | −1,358 | −24.8% | 0.8% |
| Zero-stop | 2024 | −1,019 | −22.4% | 1.7% |
| Zero-stop | 2025 | −1,763 | −35.7% | 0% |
| Max budget | 2023 | −1,302 | −23.7% | 0% |
| Max budget | 2024 | −979 | −21.5% | 0.3% |
| Max budget | 2025 | −1,748 | −35.3% | 0% |

**Key findings.**

- **P2PM's objective is worth about a quarter to a third of a season's
  points.** Both controls trail P2PM by 21% to 36%, and almost never beat it on
  any single starting team. Max budget re-solves every race just as P2PM does,
  yet loses by about as much as Zero-stop. So the gain comes from *what* P2PM
  optimises, not simply from making transfers.
- **For Zero-stop, a cheaper starting team does worse.** It is stuck with its
  starting team, so the cheapest band, (90, 95], loses most in every season.
  In 2023 the loss goes from −1,547 there to −1,184 in (99.5, 100]. Max budget
  shows no such pattern, since it can trade up.
- **The sample is representative.** In the top band, the sampled means matched
  the full January population within sampling error for eight of nine
  strategy-seasons. The ninth was Max budget 2024, about 2.3 standard errors
  out. That is the luck of the draw, not the engine, and it doesn't change the
  conclusion.
- **Results are now reproducible.** Cross-checking against January exposed a
  randomness in `linear/`. Asset order depended on Python's per-process hash
  seed, which could change a control's season total by up to 50 points between
  runs. This was fixed at source in `534d1a9`, and all 215 mismatches with
  January were confirmed to come from it. P2PM matched January exactly
  throughout.

**Full detail:** [`docs/backtest_v1/log.md`](docs/backtest_v1/log.md),
*Verification 4* and the entries around it. The numbers above come from
`outputs/backtest_v1_summary.csv`.

## Max points — `max_points_v1` (2026-09-20)

**Question.** Max P2PM scores each asset by points² ÷ price. Does dividing by
price penalise expensive assets twice, when the budget cap already limits them?
If so, maximising the rolling three-race points total directly should do
better.

**Set-up.** `StrategyMaxPoints` differs from Max P2PM in its objective alone. It
copies P2PM's race-4 unlimited-moves chip and its DRS nomination rule, so
neither of those is part of the comparison. The strategy has no concentration
constraint and no tuning coefficients.

**Result: it loses in all three seasons.**

| Season | Mean delta | Std err | Median delta | Teams beating P2PM |
| :--- | :--- | :--- | :--- | :--- |
| 2023 | −14.5 | 1.4 | −18 | 41% |
| 2024 | −156.2 | 3.9 | −213 | 18% |
| 2025 | −4.4 | 5.2 | +39 | 58% |

**Key findings.**

- **The divisor is not a mistake.** The hypothesis was falsified. 2025's −4.4 is
  within noise, and 2023's is real but small, at about −0.26% of season points.
- **Pure points is higher-variance, not simply worse.** In 2025 it beats P2PM on
  58% of starting teams and still loses on the mean, because its worst teams
  lose by up to 713 points. The price divisor appears to buy downside
  protection.
- **Concentration risk is not the cause.** The proposal predicted a pure-points
  objective would stack a constructor with both its drivers and get burned.
  Measured over every race, it doesn't. In 2024, its worst season, it stacks in
  0.7% of team-races against P2PM's 6.5%. More concentrated teams did slightly
  *better*, not worse.
- **2024 is unexplained.** The loss builds steadily from race 5 onwards rather
  than coming from a few bad weekends. An untested hypothesis is that 2024's
  drivers scored so little that rolling points barely told them apart, while
  dividing by price still did. [Refuted 2026-09-29: across the whole field,
  2024's drivers scored their usual share, and rolling points ranked them better
  than in any other season. The loss comes from about eight races where the two
  strategies traded differently, mostly Red Bull held instead of Ferrari or
  McLaren and the Mercedes drivers missed mid-season. It is within the noise of
  what is effectively one path, so 2024 needs no special explanation.]
- **The standard errors above overstate precision** (added 2026-09-29). They
  treat the 1,500 starting teams as independent, but after race 4 each strategy
  holds only a few distinct line-ups a race. This is reasoned from the race-4
  finding below, not measured. [Confirmed 2026-09-29, and not caused by the
  chip: see *P2PM without the race-4 reset* below.]
- **The starting team stops mattering by race 4.** Under both strategies, the
  race-4 unlimited-moves chip rebuilds nearly all 1,500 starting teams into the
  same line-up: 1 distinct team in 2023, 6 in 2024 and 10 in 2025. So a
  sampled back-test gets far less independent information after race 4 than
  its sample size suggests. This applies to every back-test, not just this one.
  [Corrected 2026-09-29: the chip only finishes the collapse. Ordinary moves in
  races 2 and 3 already bring 1,500 teams down to a few hundred, and without the
  chip they mostly converge again within a few races. See *P2PM without the
  race-4 reset* below.]
- **DRS nomination is a bigger lever than the objective.** A perfect-hindsight
  DRS pick would have added 98 to 226 points a season over the current rule.
  The objective change was worth −4 to −156 by comparison. Modelling DRS inside
  the LP with the same inputs would pick the same driver, so any gain has to
  come from a better nomination signal. This is reasoned from the LP's
  structure and has not been run.

**A trap to avoid.** A first run was confounded, because `StrategyMaxPoints` had
no DRS nomination while P2PM did. It showed an apparent 2023 win that
disappeared once the DRS rule was matched. Its results were purged. Only
`outputs/max_points_v1_results.parquet` and `max_points_v1_drs_summary.csv` are
valid.

**Full detail:** [`docs/max_points_v1/log.md`](docs/max_points_v1/log.md),
starting with its plain-language recap under *Next session — start here*.
Requirements, plan and design rationale are in the same folder.

## P2PM without the race-4 reset — `max_points_v1` (2026-09-29)

**Question.** Max P2PM plays the unlimited-moves chip at race 4 and can rebuild
the whole team. Is that worth doing? And is the chip why starting teams end up
identical, which limits how much a back-test can tell us?

**Set-up.** `StrategyMaxP2PMNoReset` is Max P2PM with race 4 treated as an
ordinary race: two moves, or three with a carried-over free transfer. Nothing
else differs. This compares the chip at race 4 against never playing it. It
does not test playing it at a different race, since chips are not modelled.

**Result: the chip is worth keeping.**

| Season | Mean delta | Median delta | p10 delta | Teams beating P2PM |
| :--- | :--- | :--- | :--- | :--- |
| 2023 | +1.8 | 0 | 0 | 10.7% |
| 2024 | −32.3 | 0 | −158 | 10.7% |
| 2025 | −168.0 | −33 | −583 | 11.1% |

**Key findings.**

- **Rebuilding at race 4 gets to the strong team sooner.** Without it, teams
  reach roughly the same line-up two moves at a time and lose points meanwhile.
  In 2025 that costs 11 to 16 points a race from race 4 to 8, and three-quarters
  of the season's loss is in by race 11. 2023 is a wash: from race 6 both score
  the same.
- **The chip is not what makes starting teams identical.** By race 3, before
  any chip, ordinary moves have already brought 1,500 starting teams down to
  268–432 distinct line-ups, as every team chases the same top-rated assets.
  Without the chip, race 4 has 17, 111 and 109 line-ups where P2PM has 1, 7 and
  10. But by mid-season they converge again to within one or two of P2PM's
  count.
- **So the standard-error caveat above holds for every strategy tested here.**
  A back-test of 1,500 starting teams rests on a handful of independent paths
  per season, whatever the chip does. Read these standard errors as describing
  those paths, not how the strategies would compare in general.
- **The season deltas are not significance tests.** 2024's −32 is best read as
  "probably small and negative". 2025's −168 builds up over six races, so it is
  not one bad weekend.

**Full detail:** [`docs/max_points_v1/log.md`](docs/max_points_v1/log.md),
*P2PM without the race-4 reset*. The numbers come from
`outputs/max_points_v1_no_reset_summary.csv` and
`outputs/max_points_v1_no_reset_lineups.csv`.
