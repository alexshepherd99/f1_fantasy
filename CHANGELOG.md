# Changelog

What changed, newest first, one line each. The effort's docs carry the detail.

- **2026-11-09** — Old batch back-test scripts removed; `backtest` is the only multi-team back-test ([remove_batch_script_v1](docs/remove_batch_script_v1/))
- **2026-11-08** — FastF1 strategy with a price-rise reward beats Max P2PM in back-test; the live 2026 team stays on Max P2PM ([fastf1_v2](docs/fastf1_v2/))
- **2026-10-31** — `fast_f1` signs in to an F1 account, which the timing service now requires
- **2026-10-31** — Indicator analysis: which FastF1 inputs predict fantasy points ([indicator_analysis_v1](docs/indicator_analysis_v1/))
- **2026-10-05** — Betting odds strategy picks its DRS driver inside the LP; back-tested on 2026, it loses to Max P2PM ([odds_drs_v1](docs/odds_drs_v1/))
- **2026-09-29** — Max points, and Max P2PM without the race-4 reset, back-tested; both lose to Max P2PM ([max_points_v1](docs/max_points_v1/))
- **2026-09-19** — Sampled, paired back-test against Max P2PM ([backtest_v1](docs/backtest_v1/))
- **2026-07-27** — FastF1 practice, points and odds indicators ([fastf1_v1](docs/fastf1_v1/))
- **2026-07-26** — Betting odds converted to their true implied probability; odds-based picks logged before this date can't be reproduced
- **2026-07-24** — Repo onboarded to `agentic`; development from here is agent-led
- **2025-10-29** — Project started: hand-written LP strategies and a full back-test over 2023–2025
