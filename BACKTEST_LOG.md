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
| Max points (`StrategyMaxPoints`) | [max_points_v1](docs/max_points_v1/) | 2026-09-20 | 2023, 2024, 2025 | −14.5, −156.2, −4.4 | No, 0 of 3 seasons | Hypothesis refuted |

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
  dividing by price still did.
- **The starting team stops mattering by race 4.** Under both strategies, the
  race-4 unlimited-moves chip rebuilds nearly all 1,500 starting teams into the
  same line-up: 1 distinct team in 2023, 6 in 2024 and 10 in 2025. So a
  sampled back-test gets far less independent information after race 4 than
  its sample size suggests. This applies to every back-test, not just this one.
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
